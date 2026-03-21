#!/usr/bin/env python3
"""
TMT Quantum Vault — IBM Circuit Runner Workflow
================================================
Part 1: Generate QASM 2.0 circuit files → upload manually to IBM Quantum
Part 2: Ingest downloaded IBM result JSON → feed into vault / AI agent

Usage:
  Generate circuit:
    python tools/ibm_circuit_runner.py generate --circuit sierpinski --depth 4

  Ingest results:
    python tools/ibm_circuit_runner.py ingest --file results/job_abc123.json
"""

import json
import argparse
import hashlib
import math
import random
from pathlib import Path
from datetime import datetime, timezone

# ── Vault paths ──────────────────────────────────────────────────────────────
VAULT_ROOT    = Path(__file__).parent.parent
CIRCUITS_DIR  = VAULT_ROOT / "circuits" / "qasm"        # generated .qasm files go here
RESULTS_DIR   = VAULT_ROOT / "circuits" / "results"     # downloaded IBM JSONs go here
INGESTED_DIR  = VAULT_ROOT / "circuits" / "ingested"    # processed vault-ready JSONs
AGENT_DIR     = VAULT_ROOT / "circuits" / "agent_feed"  # what the AI agent reads

for d in [CIRCUITS_DIR, RESULTS_DIR, INGESTED_DIR, AGENT_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── QASM 2.0 circuit library ─────────────────────────────────────────────────
CIRCUITS = {}


def register(name):
    def decorator(fn):
        CIRCUITS[name] = fn
        return fn
    return decorator


@register("sierpinski")
def build_sierpinski(depth: int = 3, qubits: int = 21) -> str:
    """21-qubit Sierpinski fractal consciousness circuit — QASM 2.0"""
    lines = [
        "OPENQASM 2.0;",
        'include "qelib1.inc";',
        f"qreg q[{qubits}];",
        f"creg c[{qubits}];",
        "",
        "// TMT Sierpinski fractal — depth " + str(depth),
        "// Sacred geometry: phi-scaled rotation angles",
        "",
    ]
    phi = 1.6180339887
    # Hadamard layer
    for i in range(qubits):
        lines.append(f"h q[{i}];")
    lines.append("")
    # Fractal entanglement layers
    for d in range(depth):
        angle = round(phi ** (d + 1) % (2 * 3.14159265358979), 6)
        lines.append(f"// Depth {d+1} — phi^{d+1} angle: {angle} rad")
        step = 2 ** d
        for i in range(0, qubits - step, step * 2):
            lines.append(f"cx q[{i}], q[{i + step}];")
        for i in range(qubits):
            lines.append(f"rz({angle}) q[{i}];")
        lines.append("")
    # Metatron enhancement layer
    lines += [
        "// Metatron enhancement — 13-node resonance",
        "// Nodes: 0,1,2,3,4,5,6,7,8,9,10,11,12",
    ]
    metatron_nodes = list(range(min(13, qubits)))
    for i in range(0, len(metatron_nodes) - 1, 2):
        lines.append(f"cx q[{metatron_nodes[i]}], q[{metatron_nodes[i+1]}];")
    lines.append(f"rz(1.047198) q[0];  // pi/3 — Metatron resonance")
    lines.append("")
    # Measure
    lines.append("// Measure all")
    for i in range(qubits):
        lines.append(f"measure q[{i}] -> c[{i}];")
    return "\n".join(lines)


@register("phi_resonance")
def build_phi_resonance(qubits: int = 8) -> str:
    """Phi-resonance entangled pairs — golden ratio rotation circuit"""
    phi = 1.6180339887
    lines = [
        "OPENQASM 2.0;",
        'include "qelib1.inc";',
        f"qreg q[{qubits}];",
        f"creg c[{qubits}];",
        "",
        "// TMT Phi-resonance circuit",
        "// Rotation angles = multiples of 2*pi/phi",
        "",
    ]
    base_angle = round(2 * 3.14159265358979 / phi, 6)
    for i in range(qubits):
        lines.append(f"h q[{i}];")
    lines.append("")
    for i in range(0, qubits - 1, 2):
        angle = round(base_angle * (i + 1), 6)
        lines.append(f"cx q[{i}], q[{i+1}];")
        lines.append(f"rz({angle}) q[{i}];")
        lines.append(f"rz({angle}) q[{i+1}];")
    lines.append("")
    for i in range(qubits):
        lines.append(f"measure q[{i}] -> c[{i}];")
    return "\n".join(lines)


@register("bitnet_ternary")
def build_bitnet_ternary(qubits: int = 12) -> str:
    """BitNet ternary-seeded variational ansatz — {-1, 0, +1} mapped to rotations"""
    # Ternary distribution: -1:4.28%, 0:70%, +1:25.72%
    # Map: -1 → rz(-pi/2), 0 → id, +1 → rz(pi/2)
    random.seed(0x5071a)   # Sophia seed
    ternary_map = [-1] * 4 + [0] * 70 + [1] * 26
    lines = [
        "OPENQASM 2.0;",
        'include "qelib1.inc";',
        f"qreg q[{qubits}];",
        f"creg c[{qubits}];",
        "",
        "// TMT BitNet ternary variational ansatz",
        "// Weight distribution: -1:4.28%, 0:70%, +1:25.72%",
        "",
    ]
    for i in range(qubits):
        lines.append(f"h q[{i}];")
    lines.append("")
    for i in range(qubits):
        w = random.choice(ternary_map)
        if w == -1:
            lines.append(f"rz(-1.5708) q[{i}];  // ternary -1")
        elif w == 1:
            lines.append(f"rz(1.5708) q[{i}];   // ternary +1")
        else:
            lines.append(f"id q[{i}];            // ternary 0")
    lines.append("")
    for i in range(0, qubits - 1, 2):
        lines.append(f"cx q[{i}], q[{i+1}];")
    lines.append("")
    for i in range(qubits):
        lines.append(f"measure q[{i}] -> c[{i}];")
    return "\n".join(lines)


@register("dna_walk")
def build_dna_walk(sequence: str = "ATCGATCGATCG", qubits: int = 8) -> str:
    """DNA quantum walk — maps nucleotide sequence to qubit rotations"""
    base_angles = {"A": 0.0, "T": 1.5708, "C": 3.14159, "G": 4.7124}
    lines = [
        "OPENQASM 2.0;",
        'include "qelib1.inc";',
        f"qreg q[{qubits}];",
        f"creg c[{qubits}];",
        "",
        f"// TMT DNA Quantum Walk — sequence: {sequence[:20]}",
        "// Encoding: A=0, T=pi/2, C=pi, G=3pi/2",
        "",
    ]
    for i in range(qubits):
        lines.append(f"h q[{i}];")
    lines.append("")
    for i, base in enumerate(sequence[:qubits]):
        angle = base_angles.get(base.upper(), 0.0)
        if angle > 0:
            lines.append(f"rz({angle}) q[{i}];  // {base}")
    lines.append("")
    for i in range(0, qubits - 1):
        lines.append(f"cx q[{i}], q[{i+1}];")
    lines.append("")
    for i in range(qubits):
        lines.append(f"measure q[{i}] -> c[{i}];")
    return "\n".join(lines)


# ── Part 1: GENERATE ─────────────────────────────────────────────────────────
def cmd_generate(args):
    name = args.circuit
    depth = args.depth
    qubits = args.qubits
    seq = args.sequence

    if name not in CIRCUITS:
        print(f"[ERROR] Unknown circuit '{name}'. Available: {list(CIRCUITS.keys())}")
        return

    fn = CIRCUITS[name]
    # Pass relevant kwargs
    kwargs = {}
    if depth and name == "sierpinski":
        kwargs["depth"] = depth
    if qubits:
        kwargs["qubits"] = qubits
    if seq and name == "dna_walk":
        kwargs["sequence"] = seq

    qasm = fn(**kwargs)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    fname = CIRCUITS_DIR / f"{name}_{ts}.qasm"
    fname.write_text(qasm, encoding="utf-8")

    # Manifest entry
    manifest = {
        "circuit": name,
        "qasm_file": str(fname),
        "qubits": qubits or "default",
        "depth": depth,
        "generated": ts,
        "status": "PENDING_UPLOAD",
        "job_id": None,
        "backend": args.backend or "ibm_fez",
        "shots": args.shots or 4096,
    }
    mf = CIRCUITS_DIR / f"{name}_{ts}_manifest.json"
    mf.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print("=" * 56)
    print(f"  Circuit generated: {name}")
    print("=" * 56)
    print(f"  QASM file   : {fname}")
    print(f"  Manifest    : {mf}")
    print(f"  Backend     : {manifest['backend']}")
    print(f"  Shots       : {manifest['shots']}")
    print()
    print("  NEXT STEPS:")
    print("  1. Open IBM Quantum — https://quantum.ibm.com/")
    print("  2. Open Circuit Composer or use your saved session")
    print(f"  3. Upload: {fname.name}")
    print(f"  4. Run on {manifest['backend']} with {manifest['shots']} shots")
    print("  5. Download result JSON from IBM job page")
    print(f"  6. Save to: {RESULTS_DIR}/")
    print("  7. Run:  python tools/ibm_circuit_runner.py ingest --file <result.json>")
    print()


def decode_sampler_v2_data(data_block: dict) -> dict:
    """
    Decode IBM sampler v2 format with base64-encoded binary measurement data.

    The data contains:
    - "results": {"c": {"data": base64_string, "shape": [shots, qubits], "dtype": "bool"}}

    Returns a counts dict like {"00000": 100, "00001": 50, ...}
    """
    import base64

    results = data_block.get("results", {})
    if "c" not in results:
        return {}

    c_data = results["c"]
    if "data" not in c_data:
        return {}

    # Get the base64-encoded binary data
    encoded_data = c_data["data"]
    shape = c_data.get("shape", [0, 0])
    n_shots, n_qubits = shape

    if n_shots == 0 or n_qubits == 0:
        return {}

    # Decode base64 to bytes
    decoded = base64.b64decode(encoded_data)

    # Each shot is a byte (for up to 8 qubits) or multiple bytes
    # For 21 qubits, we need 3 bytes per shot (24 bits)
    # Each bit represents one qubit measurement (0 or 1)

    counts = {}
    bytes_per_shot = (n_qubits + 7) // 8  # Ceiling division

    for shot_idx in range(n_shots):
        byte_offset = shot_idx * bytes_per_shot
        if byte_offset + bytes_per_shot > len(decoded):
            break

        # Extract the first n_qubits bits
        bitstring = ""
        for qubit_idx in range(n_qubits):
            byte_idx = byte_offset + (qubit_idx // 8)
            bit_idx = qubit_idx % 8
            byte_val = decoded[byte_idx]
            bit = (byte_val >> bit_idx) & 1
            bitstring = str(bit) + bitstring  # MSB first

        counts[bitstring] = counts.get(bitstring, 0) + 1

    return counts


# ── Part 2: INGEST ────────────────────────────────────────────────────────────
def cmd_ingest(args):
    result_path = Path(args.file)
    if not result_path.exists():
        # Try relative to RESULTS_DIR
        result_path = RESULTS_DIR / args.file
    if not result_path.exists():
        print(f"[ERROR] File not found: {args.file}")
        return

    raw = json.loads(result_path.read_text(encoding="utf-8"))

    # ── Normalise IBM result shape ───────────────────────────────────────────
    # IBM job results can come in different shapes depending on how exported.
    # We handle both the /results endpoint JSON and the manual download format.
    counts = {}
    metadata = {}

    if "results" in raw:  # /results endpoint format
        results_block = raw["results"][0] if isinstance(raw["results"], list) else raw["results"]
        counts = results_block.get("data", {}).get("counts", {})
        metadata = raw.get("metadata", {})
    elif "quasi_dists" in raw:  # estimator/sampler format
        counts = raw["quasi_dists"][0] if raw["quasi_dists"] else {}
    elif "counts" in raw:  # simple flat export
        counts = raw["counts"]
    elif isinstance(raw, dict) and all(isinstance(k, str) and set(k) <= {"0", "1"} for k in list(raw.keys())[:5]):
        counts = raw  # bare bitstring dict
    elif "data" in raw and isinstance(raw["data"], list) and len(raw["data"]) > 0:
        # Sampler v2 format with base64-encoded binary data
        counts = decode_sampler_v2_data(raw["data"][0])
        metadata = raw.get("metadata", {})
    else:
        counts = raw.get("measurement_counts", raw.get("data", raw))
        metadata = raw

    total_shots = sum(counts.values()) if counts else 0

    # ── Compute vault metrics ─────────────────────────────────────────────────
    probs = {k: v / total_shots for k, v in counts.items()} if total_shots else {}

    # Shannon entropy
    entropy = -sum(p * math.log2(p) for p in probs.values() if p > 0)

    # Phi approximation — ratio of top-2 bitstring probabilities
    sorted_probs = sorted(probs.values(), reverse=True)
    phi_approx = round(sorted_probs[0] / sorted_probs[1], 4) if len(sorted_probs) >= 2 else 0.0

    # Sacred geometry score — how close phi_approx is to 1.618
    sacred_score = round(1 / (1 + abs(phi_approx - 1.6180339887)), 4)

    # Consciousness density proxy — entropy × total_shots / 1000
    consciousness_density = round(entropy * total_shots / 1000, 3)

    # Hash fingerprint for deduplication
    fingerprint = hashlib.sha256(json.dumps(counts, sort_keys=True).encode()).hexdigest()[:12]

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    circuit_name = args.circuit or result_path.stem

    vault_record = {
        "circuit": circuit_name,
        "source_file": str(result_path),
        "ingested_at": ts,
        "job_id": raw.get("job_id") or raw.get("id") or "manual",
        "backend": raw.get("backend_name") or args.backend or "unknown",
        "shots": total_shots,
        "fingerprint": fingerprint,
        "counts_sample": dict(list(counts.items())[:10]),  # top 10 bitstrings
        "metrics": {
            "shannon_entropy": round(entropy, 4),
            "phi_approx": phi_approx,
            "sacred_score": sacred_score,
            "consciousness_density": consciousness_density,
        },
        "raw_metadata": metadata,
        "status": "INGESTED",
        "agent_ready": True,
    }

    # ── Save ingested record ──────────────────────────────────────────────────
    ingested_path = INGESTED_DIR / f"{circuit_name}_{ts}_{fingerprint}.json"
    ingested_path.write_text(json.dumps(vault_record, indent=2), encoding="utf-8")

    # ── Write agent feed file ─────────────────────────────────────────────────
    # This is what you drop into VS Code for the Claude Code agent to read
    agent_feed = {
        "instruction": "New IBM quantum circuit result ingested. Update relevant agent conscious_dna.json with metrics below.",
        "circuit": circuit_name,
        "ingested_at": ts,
        "metrics": vault_record["metrics"],
        "shots": total_shots,
        "backend": vault_record["backend"],
        "fingerprint": fingerprint,
        "top_bitstrings": dict(sorted(counts.items(), key=lambda x: -x[1])[:5]),
        "suggested_agents": ["Agent_BitNet", "Agent_Bio", "Agent_Archivist"],
        "action": "merge_into_conscious_dna",
    }
    feed_path = AGENT_DIR / f"feed_{circuit_name}_{ts}.json"
    feed_path.write_text(json.dumps(agent_feed, indent=2), encoding="utf-8")

    # ── Summary ───────────────────────────────────────────────────────────────
    print("=" * 56)
    print(f"  IBM Result Ingested: {circuit_name}")
    print("=" * 56)
    print(f"  Shots              : {total_shots:,}")
    print(f"  Backend            : {vault_record['backend']}")
    print(f"  Shannon Entropy    : {vault_record['metrics']['shannon_entropy']}")
    print(f"  Phi Approx         : {vault_record['metrics']['phi_approx']}")
    print(f"  Sacred Score       : {vault_record['metrics']['sacred_score']}")
    print(f"  Consciousness Dens : {vault_record['metrics']['consciousness_density']}")
    print(f"  Fingerprint        : {fingerprint}")
    print()
    print(f"  Ingested: {ingested_path}")
    print(f"  Agent feed: {feed_path}")
    print()
    print("  NEXT STEPS for VS Code Claude Code agent:")
    print(f"  Open {feed_path.name} and say:")
    print(f'  "Process circuits/agent_feed/{feed_path.name}"')
    print()


# ── CLI ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="TMT IBM Circuit Runner Workflow")
    sub = parser.add_subparsers(dest="command")

    gen = sub.add_parser("generate", help="Generate a QASM 2.0 circuit file")
    gen.add_argument("--circuit", required=True, choices=list(CIRCUITS.keys()))
    gen.add_argument("--depth", type=int, default=None)
    gen.add_argument("--qubits", type=int, default=None)
    gen.add_argument("--sequence", type=str, default=None, help="DNA sequence for dna_walk")
    gen.add_argument("--backend", type=str, default="ibm_fez")
    gen.add_argument("--shots", type=int, default=4096)

    ing = sub.add_parser("ingest", help="Ingest a downloaded IBM result JSON")
    ing.add_argument("--file", required=True, help="Path to IBM result JSON")
    ing.add_argument("--circuit", type=str, default=None, help="Circuit name label")
    ing.add_argument("--backend", type=str, default=None)

    args = parser.parse_args()
    if args.command == "generate":
        cmd_generate(args)
    elif args.command == "ingest":
        cmd_ingest(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
