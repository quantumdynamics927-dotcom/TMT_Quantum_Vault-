#!/usr/bin/env python3
"""
Promoter Loader Utility — TMT Quantum Vault
============================================

Load, validate, and parse promoter DNA sequences from FASTA files.

Usage:
  python tools/promoter_loader.py --list              # List all promoters
  python tools/promoter_loader.py --show <name>       # Show promoter details
  python tools/promoter_loader.py --seq <name>        # Output DNA sequence only
  python tools/promoter_loader.py --verify <name>     # Verify cryptographic integrity
  python tools/promoter_loader.py --copy              # Copy promoters to circuits/

 promoter sequences:
"""

import json
import hashlib
import hmac
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any

# ── Vault paths ──────────────────────────────────────────────────────────────
VAULT_ROOT = Path(__file__).parent.parent
PROMOTERS_DIR = VAULT_ROOT / "circuits" / "promoters"
EXTERNAL_PROMOTERS = Path(r"E:\AGI model\tmt-os-labs\promoters")

# ── Configuration ────────────────────────────────────────────────────────────
HMAC_KEY_FILE = EXTERNAL_PROMOTERS / "hmac_key.txt"
EXPECTED_LENGTH_RANGE = (70, 85)  # Promoters should be 70-85 bp


def get_promoter_files() -> List[Path]:
    """Get list of all promoter FASTA files."""
    if not EXTERNAL_PROMOTERS.exists():
        return []
    return sorted(EXTERNAL_PROMOTERS.glob("*_promoter.fa"))


def parse_fasta(fasta_path: Path) -> Dict[str, Any]:
    """Parse a FASTA file and extract sequence metadata."""
    content = fasta_path.read_text(encoding="utf-8").strip()
    lines = content.split('\n')

    # Parse header
    header = lines[0].strip().lstrip('>')
    parts = header.split(':')

    # Extract gene name from filename (e.g., "ACTB_Malkuth_promoter" -> "ACTB")
    gene_name = fasta_path.stem.replace("_promoter", "")

    # Chromosome coordinates from header
    chrom_coord = parts[0] if len(parts) > 0 else header

    # DNA sequence (second line)
    dna_sequence = lines[1].strip() if len(lines) > 1 else ""

    return {
        "gene": gene_name,
        "header": header,
        "chromosome_coord": chrom_coord,
        "sequence": dna_sequence,
        "length": len(dna_sequence),
        "gc_content": gc_content(dna_sequence),
        "source_file": str(fasta_path)
    }


def gc_content(sequence: str) -> float:
    """Calculate GC content of DNA sequence."""
    if not sequence:
        return 0.0
    gc_count = sum(1 for base in sequence.upper() if base in 'GC')
    return gc_count / len(sequence)


def compute_sha256(fasta_path: Path) -> str:
    """Compute SHA256 hash of a FASTA file."""
    content = fasta_path.read_text(encoding="utf-8")
    return hashlib.sha256(content.encode()).hexdigest()


def load_hmac_key() -> Optional[bytes]:
    """Load HMAC signing key."""
    if HMAC_KEY_FILE.exists():
        return HMAC_KEY_FILE.read_text(encoding="utf-8").strip().encode()
    return None


def verify_hmac(fasta_path: Path) -> bool:
    """Verify HMAC signature of a FASTA file."""
    hmac_key = load_hmac_key()
    if not hmac_key:
        return False

    content = fasta_path.read_text(encoding="utf-8")
    computed = hmac.new(hmac_key, content.encode(), hashlib.sha256).hexdigest()

    # Check against .sha256 file
    sha_file = fasta_path.with_suffix(".fa.sha256")
    if sha_file.exists():
        stored = sha_file.read_text(encoding="utf-8").strip()
        return hmac.compare_digest(computed, stored)

    return False


def verify_promoter(name: str) -> Dict[str, Any]:
    """Verify a promoter's cryptographic integrity."""
    fasta_file = EXTERNAL_PROMOTERS / f"{name}_promoter.fa"

    if not fasta_file.exists():
        return {"error": f"Promoter not found: {name}"}

    # Compute hashes
    content = fasta_file.read_text(encoding="utf-8")
    sha256 = hashlib.sha256(content.encode()).hexdigest()

    # Load expected hash from metadata
    metadata_file = EXTERNAL_PROMOTERS / f"{name}_promoter.fa.sha256.json"
    expected_hash = None
    if metadata_file.exists():
        metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
        expected_hash = metadata.get("sha256")

    return {
        "name": name,
        "fasta_file": str(fasta_file),
        "computed_sha256": sha256,
        "expected_sha256": expected_hash,
        "match": sha256 == expected_hash,
        "verified": verify_hmac(fasta_file)
    }


def copy_promoters_to_vault() -> int:
    """Copy promoter files to circuits/promoters/ directory."""
    if not PROMOTERS_DIR.exists():
        PROMOTERS_DIR.mkdir(parents=True, exist_ok=True)

    count = 0
    for src in EXTERNAL_PROMOTERS.glob("*.fa*"):
        dst = PROMOTERS_DIR / src.name
        dst.write_text(src.read_text(encoding="utf-8"))
        count += 1

    return count


def load_all_promoters() -> List[Dict[str, Any]]:
    """Load all promoter sequences."""
    promoters = []
    for fasta_file in get_promoter_files():
        promoter = parse_fasta(fasta_file)
        promoter["verified"] = verify_hmac(fasta_file)
        promoter["sha256"] = compute_sha256(fasta_file)
        promoters.append(promoter)
    return promoters


def format_output(promoter: Dict[str, Any]) -> str:
    """Format promoter data for display."""
    lines = [
        f"Gene:        {promoter['gene']}",
        f"Length:      {promoter['length']} bp",
        f"GC Content:  {promoter['gc_content']:.2%}",
        f"Verified:    {promoter.get('verified', 'N/A')}",
        f"Sequence:",
        f"  {promoter['sequence']}",
    ]
    return '\n'.join(lines)


# ── CLI ──────────────────────────────────────────────────────────────────────
def cmd_list():
    """List all promoters."""
    promoters = load_all_promoters()
    print(f"Promoters ({len(promoters)} total):")
    print("-" * 50)
    for p in promoters:
        status = "[OK]" if p.get("verified") else "[FAIL]"
        print(f"  {status} {p['gene']:12} ({p['length']:3} bp) - {p['sequence'][:20]}...")


def cmd_show(args):
    """Show detailed promoter info."""
    name = args.name
    for p in load_all_promoters():
        if p['gene'] == name or p['gene'].lower() == name.lower():
            print(format_output(p))
            return
    print(f"Promoter not found: {name}")


def cmd_seq(args):
    """Output DNA sequence only."""
    name = args.name
    for p in load_all_promoters():
        if p['gene'] == name or p['gene'].lower() == name.lower():
            print(p['sequence'])
            return
    print(f"Promoter not found: {name}")


def cmd_verify(args):
    """Verify promoter integrity."""
    name = args.name
    result = verify_promoter(name)
    print(f"Verification for {name}:")
    print(f"  Computed SHA256: {result.get('computed_sha256', 'N/A')}")
    print(f"  Expected SHA256: {result.get('expected_sha256', 'N/A')}")
    print(f"  Match:           {result.get('match', False)}")
    print(f"  HMAC Verified:   {result.get('verified', False)}")


def cmd_copy():
    """Copy promoters to vault."""
    count = copy_promoters_to_vault()
    print(f"Copied {count} files to {PROMOTERS_DIR}")


def main():
    parser = argparse.ArgumentParser(
        description="Promoter Loader - TMT Quantum Vault",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list", help="List all promoters")

    show_parser = sub.add_parser("show", help="Show promoter details")
    show_parser.add_argument("name", help="Promoter name (e.g., ACTB)")

    seq_parser = sub.add_parser("seq", help="Output DNA sequence only")
    seq_parser.add_argument("name", help="Promoter name")

    verify_parser = sub.add_parser("verify", help="Verify integrity")
    verify_parser.add_argument("name", help="Promoter name")

    sub.add_parser("copy", help="Copy promoters to circuits/promoters/")

    args = parser.parse_args()

    if args.command == "list":
        cmd_list()
    elif args.command == "show":
        cmd_show(args)
    elif args.command == "seq":
        cmd_seq(args)
    elif args.command == "verify":
        cmd_verify(args)
    elif args.command == "copy":
        cmd_copy()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
