#!/usr/bin/env python3
"""
Agent_Analyst — Autonomous φ-Scoring Pipeline
==============================================

Dual-Watch Design:
- circuits/results/  -> watch for NEW *.json files (active trigger)
- circuits/qasm/     -> watch for NEW *.qasm files (passive context loader)

Usage:
  Run analysis on new results:
    python tools/agent_analyst.py analyze

  Watch for new files (manual trigger):
    python tools/agent_analyst.py watch

  Ingest specific result:
    python tools/agent_analyst.py ingest --file <result.json>
"""

import json
import hashlib
import math
import os
import time
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None
    FileSystemEventHandler = object

# ── Vault paths ──────────────────────────────────────────────────────────────
VAULT_ROOT    = Path(__file__).parent.parent
CIRCUITS_DIR  = VAULT_ROOT / "circuits" / "qasm"
RESULTS_DIR   = VAULT_ROOT / "circuits" / "results"
INGESTED_DIR  = VAULT_ROOT / "circuits" / "ingested"
AGENT_DIR     = VAULT_ROOT / "circuits" / "agent_feed"
SIGNIFICANT_DIR = INGESTED_DIR / "SIGNIFICANT"

for d in [CIRCUITS_DIR, RESULTS_DIR, INGESTED_DIR, AGENT_DIR, SIGNIFICANT_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Configuration
SIGIFICANT_THRESHOLD = 0.618  # sacred_score threshold for SIGNIFICANT flagging
PHI_TOLERANCE = 0.01  # Allow +/- 0.01 deviation from 1/Phi


# ── QASM parsing ──────────────────────────────────────────────────────────────
def parse_qasm_depth(qasm_path: Path) -> Dict[str, Any]:
    """Parse QASM file to extract circuit metadata."""
    content = qasm_path.read_text(encoding="utf-8")

    # Extract depth from comments or circuit structure
    depth = None
    n_qubits = 21  # Default

    for line in content.split('\n'):
        if 'depth' in line.lower() and '//' in line:
            # Comment format: // Depth 4 — phi^4 angle
            parts = line.split('depth')
            if len(parts) > 1:
                try:
                    depth = int(parts[1].split()[0])
                except (ValueError, IndexError):
                    pass
        if 'qreg q[' in line:
            try:
                n_qubits = int(line.split('[')[1].split(']')[0])
            except (ValueError, IndexError):
                pass

    return {
        "qasm_path": str(qasm_path),
        "qasm_name": qasm_path.stem,
        "depth": depth,
        "n_qubits": n_qubits,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "QASM_READY"
    }


# ── File watching helpers ────────────────────────────────────────────────────
def get_processed_files(directory: Path, suffix: str) -> set:
    """Get set of already processed files."""
    processed = set()
    for f in directory.glob(f"*{suffix}"):
        processed.add(f.name)
    return processed


def decode_sampler_v2_data(data_block: dict) -> dict:
    """Decode IBM sampler v2 format with base64-encoded binary measurement data."""
    import base64

    results = data_block.get("results", {})
    if "c" not in results:
        return {}

    c_data = results["c"]
    if "data" not in c_data:
        return {}

    encoded_data = c_data["data"]
    shape = c_data.get("shape", [0, 0])
    n_shots, n_qubits = shape

    if n_shots == 0 or n_qubits == 0:
        return {}

    decoded = base64.b64decode(encoded_data)
    bytes_per_shot = (n_qubits + 7) // 8

    counts = {}
    for shot_idx in range(n_shots):
        byte_offset = shot_idx * bytes_per_shot
        if byte_offset + bytes_per_shot > len(decoded):
            break

        bitstring = ""
        for qubit_idx in range(n_qubits):
            byte_idx = byte_offset + (qubit_idx // 8)
            bit_idx = qubit_idx % 8
            byte_val = decoded[byte_idx]
            bit = (byte_val >> bit_idx) & 1
            bitstring = str(bit) + bitstring

        counts[bitstring] = counts.get(bitstring, 0) + 1

    return counts


# ── Core analysis functions ──────────────────────────────────────────────────
def compute_metrics(counts: dict) -> Dict[str, Any]:
    """Compute vault metrics from measurement counts."""
    total_shots = sum(counts.values()) if counts else 0
    probs = {k: v / total_shots for k, v in counts.items()} if total_shots else {}

    # Shannon entropy
    entropy = -sum(p * math.log2(p) for p in probs.values() if p > 0)

    # Phi approximation — ratio of top-2 bitstring probabilities
    sorted_probs = sorted(probs.values(), reverse=True)
    phi_approx = round(sorted_probs[0] / sorted_probs[1], 4) if len(sorted_probs) >= 2 else 0.0

    # Sacred geometry score — how close phi_approx is to 1.618
    sacred_score = round(1 / (1 + abs(phi_approx - 1.6180339887)), 4)

    # Consciousness density proxy
    consciousness_density = round(entropy * total_shots / 1000, 3)

    return {
        "total_shots": total_shots,
        "entropy": round(entropy, 4),
        "phi_approx": phi_approx,
        "sacred_score": sacred_score,
        "consciousness_density": consciousness_density
    }


def analyze_result(result_path: Path, circuit_metadata: Optional[Dict] = None) -> Dict[str, Any]:
    """Analyze an IBM result JSON and compute metrics."""
    raw = json.loads(result_path.read_text(encoding="utf-8"))

    # Extract counts
    counts = {}
    if "results" in raw:
        results_block = raw["results"][0] if isinstance(raw["results"], list) else raw["results"]
        counts = results_block.get("data", {}).get("counts", {})
    elif "quasi_dists" in raw:
        counts = raw["quasi_dists"][0] if raw["quasi_dists"] else {}
    elif "counts" in raw:
        counts = raw["counts"]
    elif isinstance(raw, dict) and all(isinstance(k, str) and set(k) <= {"0", "1"} for k in list(raw.keys())[:5]):
        counts = raw
    elif "data" in raw and isinstance(raw["data"], list) and len(raw["data"]) > 0:
        counts = decode_sampler_v2_data(raw["data"][0])
    else:
        counts = raw.get("measurement_counts", raw.get("data", raw))

    # Compute metrics
    metrics = compute_metrics(counts)

    # Determine if SIGNIFICANT
    is_significant = metrics["sacred_score"] >= SIGIFICANT_THRESHOLD
    phi_convergent = abs(metrics["sacred_score"] - 0.618) <= PHI_TOLERANCE

    # Build vault record
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    fingerprint = hashlib.sha256(json.dumps(counts, sort_keys=True).encode()).hexdigest()[:12]

    record = {
        "circuit": circuit_metadata.get("qasm_name", result_path.stem) if circuit_metadata else result_path.stem,
        "source_file": str(result_path),
        "ingested_at": ts,
        "backend": raw.get("backend_name", "unknown"),
        "fingerprint": fingerprint,
        "counts_sample": dict(list(counts.items())[:10]),
        "metrics": metrics,
        "is_significant": is_significant,
        "phi_convergent": phi_convergent,
        "depth": circuit_metadata.get("depth") if circuit_metadata else None,
        "n_qubits": circuit_metadata.get("n_qubits") if circuit_metadata else None,
        "status": "INGESTED"
    }

    return record


def ingest_result(result_path: Path, circuit_metadata: Optional[Dict] = None) -> Path:
    """Ingest a result and save to ingested folder."""
    record = analyze_result(result_path, circuit_metadata)

    # Save to ingested
    ingested_path = INGESTED_DIR / f"{record['circuit']}_{record['ingested_at']}_{record['fingerprint']}.json"
    ingested_path.write_text(json.dumps(record, indent=2), encoding="utf-8")

    # Flag SIGNIFICANT if threshold met
    if record["is_significant"]:
        sign_path = SIGNIFICANT_DIR / f"{record['circuit']}_{record['ingested_at']}_{record['fingerprint']}.json"
        sign_path.write_text(json.dumps(record, indent=2), encoding="utf-8")

    # Publish agent feed
    feed_path = AGENT_DIR / f"feed_{record['circuit']}_{record['ingested_at']}.json"
    feed_data = {
        "instruction": "New IBM quantum circuit result ingested. Review for Phi-convergence and potential DNA update.",
        "circuit": record["circuit"],
        "ingested_at": record["ingested_at"],
        "metrics": record["metrics"],
        "depth": record.get("depth"),
        "is_significant": record["is_significant"],
        "phi_convergent": record["phi_convergent"],
        "backend": record["backend"],
        "fingerprint": record["fingerprint"],
        "action": "review_dna_correlation" if record["phi_convergent"] else "archive"
    }
    feed_path.write_text(json.dumps(feed_data, indent=2), encoding="utf-8")

    return ingested_path


# ── Watcher handlers ─────────────────────────────────────────────────────────
class CircuitWatcher(FileSystemEventHandler):
    """Watch circuits/ directories for new files."""

    def __init__(self):
        self.processed_qasm = set()
        self.processed_results = set()

    def on_created(self, event):
        if event.is_directory:
            return

        path = Path(event.src_path)
        suffix = path.suffix.lower()

        # Watch results/ for JSON files (active trigger)
        if suffix == ".json" and path.parent.name == "results":
            if path.name in self.processed_results:
                return

            self.processed_results.add(path.name)
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] NEW RESULT: {path.name}")

            # Check for corresponding QASM context
            qasm_name = path.stem.replace("-result", "")
            qasm_file = CIRCUITS_DIR / f"{qasm_name}.qasm"
            circuit_metadata = None

            if qasm_file.exists():
                circuit_metadata = parse_qasm_depth(qasm_file)
                print(f"  -> Found QASM context: {qasm_file.name}")

            # Ingest
            ingested_path = ingest_result(path, circuit_metadata)
            record = analyze_result(path, circuit_metadata)

            print(f"  -> Ingested: {ingested_path.name}")
            print(f"  -> Metrics: sacred_score={record['metrics']['sacred_score']}, "
                  f"Phi Convergent={record['phi_convergent']}")

            if record["is_significant"]:
                print(f"  -> FLAGGED SIGNIFICANT")

            return

        # Watch qasm/ for new files (passive context loader)
        if suffix == ".qasm" and path.parent.name == "qasm":
            if path.name in self.processed_qasm:
                return

            self.processed_qasm.add(path.name)
            metadata = parse_qasm_depth(path)
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] NEW QASM: {path.name}")
            print(f"  -> Depth: {metadata['depth']}, Qubits: {metadata['n_qubits']}")
            print(f"  -> Context loaded. Waiting for results...")


# ── CLI commands ─────────────────────────────────────────────────────────────
def cmd_watch():
    """Start file watching in current session."""
    if not WATCHDOG_AVAILABLE:
        print("watchdog library not installed. Install with: pip install watchdog")
        print("Running in one-shot mode instead...\n")
        cmd_analyze()
        return

    print("Agent_Analyst started. Watching for new circuit files...")
    print(f"  circuits/qasm/    -> passive context loader")
    print(f"  circuits/results/ -> active trigger")
    print("Press Ctrl+C to stop.\n")

    event_handler = CircuitWatcher()
    observer = Observer()
    observer.schedule(event_handler, str(CIRCUITS_DIR), recursive=False)
    observer.schedule(event_handler, str(RESULTS_DIR), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


def cmd_analyze():
    """Analyze all unprocessed results and QASM files."""
    print("Agent_Analyst: Analyzing circuit files...\n")

    # Process new QASM files
    qasm_files = list(CIRCUITS_DIR.glob("*.qasm"))
    processed_qasm = set(f.name for f in qasm_files if f.name.startswith("sierpinski"))
    print(f"Found {len(processed_qasm)} QASM files in qasm/")

    # Process new results
    result_files = list(RESULTS_DIR.glob("*.json"))
    processed_results = set(f.name for f in result_files if "result" in f.name.lower())
    print(f"Found {len(processed_results)} result files in results/")

    # Ingest each result
    for result_path in sorted(result_files):
        if "result" not in result_path.name.lower():
            continue

        # Check for corresponding QASM
        qasm_name = result_path.stem.replace("-result", "").replace("_result", "")
        qasm_file = CIRCUITS_DIR / f"{qasm_name}.qasm"
        circuit_metadata = parse_qasm_depth(qasm_file) if qasm_file.exists() else None

        ingested_path = ingest_result(result_path, circuit_metadata)
        record = analyze_result(result_path, circuit_metadata)

        print(f"\n{result_path.name}")
        print(f"  sacred_score: {record['metrics']['sacred_score']}")
        print(f"  Phi Convergent: {record['phi_convergent']}")
        if record["is_significant"]:
            print(f"  -> FLAGGED SIGNIFICANT")


def cmd_ingest(args):
    """Ingest a specific result file."""
    result_path = Path(args.file)
    if not result_path.exists():
        # Try relative to RESULTS_DIR
        result_path = RESULTS_DIR / args.file
    if not result_path.exists():
        print(f"[ERROR] File not found: {args.file}")
        return

    # Check for QASM context
    qasm_name = result_path.stem.replace("-result", "").replace("_result", "")
    qasm_file = CIRCUITS_DIR / f"{qasm_name}.qasm"
    circuit_metadata = parse_qasm_depth(qasm_file) if qasm_file.exists() else None

    ingested_path = ingest_result(result_path, circuit_metadata)
    record = analyze_result(result_path, circuit_metadata)

    print("=" * 56)
    print(f"  IBM Result Ingested: {record['circuit']}")
    print("=" * 56)
    print(f"  Shots              : {record['metrics']['total_shots']:,}")
    print(f"  Backend            : {record['backend']}")
    print(f"  Shannon Entropy    : {record['metrics']['entropy']}")
    print(f"  Phi Approx         : {record['metrics']['phi_approx']}")
    print(f"  Sacred Score       : {record['metrics']['sacred_score']}")
    print(f"  Consciousness Dens : {record['metrics']['consciousness_density']}")
    print(f"  Phi Convergent       : {record['phi_convergent']}")
    print(f"  SIGNIFICANT        : {record['is_significant']}")
    print(f"\n  Ingested: {ingested_path}")
    print(f"  Agent feed: {AGENT_DIR / f'feed_{record["circuit"]}_{record["ingested_at"]}.json'}")


def cmd_qasm_context(args):
    """Get QASM context for a result file."""
    result_path = Path(args.file)
    if not result_path.exists():
        result_path = RESULTS_DIR / args.file

    qasm_name = result_path.stem.replace("-result", "").replace("_result", "")
    qasm_file = CIRCUITS_DIR / f"{qasm_name}.qasm"

    if qasm_file.exists():
        metadata = parse_qasm_depth(qasm_file)
        print(f"QASM Context: {qasm_file.name}")
        print(f"  Depth: {metadata['depth']}")
        print(f"  Qubits: {metadata['n_qubits']}")
    else:
        print(f"No QASM found for {result_path.name}")


# ── CLI entry point ──────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Agent_Analyst - Autonomous Phi-Scoring Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Watch for new files:
    python tools/agent_analyst.py watch

  Analyze all pending results:
    python tools/agent_analyst.py analyze

  Ingest specific result:
    python tools/agent_analyst.py ingest --file job_abc123-result.json

  Get QASM context:
    python tools/agent_analyst.py context --file job_abc123-result.json
"""
    )
    sub = parser.add_subparsers(dest="command", title="commands")

    # watch command
    sub.add_parser("watch", help="Watch circuits/ directories for new files")

    # analyze command
    sub.add_parser("analyze", help="Analyze all pending results and QASM files")

    # ingest command
    ing_parser = sub.add_parser("ingest", help="Ingest a specific result JSON")
    ing_parser.add_argument("--file", required=True, help="Path to result JSON")

    # context command
    ctx_parser = sub.add_parser("context", help="Get QASM context for a result")
    ctx_parser.add_argument("--file", required=True, help="Path to result JSON")

    args = parser.parse_args()

    if args.command == "watch":
        cmd_watch()
    elif args.command == "analyze":
        cmd_analyze()
    elif args.command == "ingest":
        cmd_ingest(args)
    elif args.command == "context":
        cmd_qasm_context(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
