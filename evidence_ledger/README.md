# Hardware Evidence Ledger v2

> **STATUS: DRAFT** - This is a provenance infrastructure, not yet the canonical proof layer. See Acceptance Criteria below.

## What This Is

This is a **PROV-compliant provenance system** for the TMT Quantum Vault 17-node Toroidal Merkaba lattice. It follows FAIR principles and the PROV-O model to ensure scientific reproducibility.

## What This Is NOT (Yet)

This is **not yet the canonical scientific proof layer** because:

1. **Entity Mismatch**: 17 agents expected, 16 captured in ledger (Observer missing from checkpoint)
2. **Provenance Incompleteness**: Hardware runs not yet linked to agent DNA
3. **Benchmark Incompleteness**: Ablation coverage still partial (1/40 runs)

## PROV Model

The ledger follows the W3C PROV-O ontology:

```
Entity (never changes)
├── Raw Result File (IBM job output)
├── Decoded DNA File (extracted sequence)
├── Circuit Definition (QASM)
└── Checkpoint Snapshot (immutable state)

Activity (transforms entities)
├── Circuit Execution (on IBM hardware)
├── DNA Extraction (decoding algorithm)
├── Fitness Calculation (scoring)
└── Optimization Run

Agent (who/what acted)
├── Quantum Backend (ibm_fez, ibm_kingston, etc.)
├── Researcher (human)
├── Script (software)
└── Lattice Agent (node in the system)
```

## Files

| File | Purpose |
|------|---------|
| `ledger_schema_v2.json` | PROV-compliant JSON Schema |
| `hardware_evidence_ledger_v2.json` | Main ledger (v2) |
| `provenance_builder.py` | Tool to build provenance chains |
| `ledger_manager.py` | Legacy v1 manager |
| `VALIDATION_PROTOCOL.md` | Validation protocol |

## Quick Start

### Verify Provenance Integrity

```bash
cd evidence_ledger
python provenance_builder.py verify
```

### Generate Provenance Report

```bash
python provenance_builder.py report
```

### Link Hardware Run to Agent

```bash
python provenance_builder.py link \
  --job-id d6v0oo2f84ks73depsr0 \
  --agent-id 4 \
  --dna-segment CGGCGCGAAAAATGCGGATACTTAATA
```

### Compute File Checksums

```bash
python provenance_builder.py compute-checksums
```

## Current Status

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Total Agents | 17 | 17 | ✅ PASS |
| Average Fitness | 0.8809 | ≥ 0.87 | ✅ PASS |
| Agents with Provenance | 0 | 17 | ❌ FAIL |
| Provenance Completeness | 0% | 100% | ❌ FAIL |
| Ablation Runs | 1 | 40 | ❌ FAIL |
| Third-Party Verifiable | No | Yes | ❌ FAIL |

## Acceptance Criteria

To become the **canonical proof layer**, the ledger must satisfy:

| Criterion | Status | Notes |
|-----------|--------|-------|
| All 17 agents present | ✅ PASS | All 17 agents from baseline are present |
| Provenance linked | ❌ FAIL | No agents have linked hardware provenance chains |
| Metrics reproducible | ❌ FAIL | Cannot regenerate from raw IBM evidence without provenance |
| Ablation complete | ❌ FAIL | Only 1/40 ablation runs complete |
| Third-party verifiable | ❌ FAIL | Missing: who, what backend, what circuit, what code version, how derived |

## Next Milestones

1. **17/17 agents represented** ✅ COMPLETE
2. **17/17 provenance-linked** 🔄 IN PROGRESS
   - Link each agent's DNA to specific IBM job IDs
   - Document decoding algorithm version
   - Compute checksums for all raw files
3. **Metrics reproducible from raw IBM evidence** ⏳ PENDING
4. **Ablation study complete (40 runs)** ⏳ PENDING
5. **Third-party verifiable** ⏳ PENDING

## Provenance Chain Structure

Each chain must answer:

- **WHO** generated the data (researcher, script, backend)
- **WHAT** backend and circuit were used
- **WHEN** the execution occurred
- **HOW** the final score was derived (algorithm version)

Example chain:

```json
{
  "chain_id": "uuid-xxx",
  "agent_id": 4,
  "agent_directory": "Agent_Bronze",
  "is_complete": true,
  "entities": [
    "job-d6v0oo2f84ks73depsr0",
    "dna-sha256:abc123..."
  ],
  "activities": [
    "circuit-execution-001",
    "dna-extraction-001"
  ],
  "chain_summary": {
    "raw_result_job_id": "d6v0oo2f84ks73depsr0",
    "backend": "ibm_kingston",
    "shots": 4096,
    "decoded_dna_hash": "sha256:...",
    "fitness_calculation_version": "2.0.0"
  }
}
```

## FAIR Principles

The ledger follows FAIR principles:

- **Findable**: Persistent IDs for all entities
- **Accessible**: All raw results stored in `circuits/results/`
- **Interoperable**: JSON-LD compatible schema
- **Reusable**: Rich metadata with detailed provenance

## References

- [PROV-O: The PROV Ontology](https://www.w3.org/TR/prov-o/)
- [FAIR Principles](https://www.go-fair.org/fair-principles/)
- [Data Provenance Best Practices](https://www.secoda.co/blog/best-practices-for-documenting-data-provenance)

---

**Maintainer:** TMT Quantum Vault Team  
**Schema Version:** 2.0.0  
**Last Updated:** 2026-03-29
  "backend": "ibm_kingston",
  "status": "Completed",
  "shots": 4096,
  "circuit_depth": 122,
  "qubits_used": 21,
  "raw_result_path": "circuits/results/job-d6v0oo2f84ks73depsr0-result.json"
}
```

## Key Claims

The following claims are **falsifiable** and traceable through this ledger:

1. **Sierpinski Invariant**: In the Sierpinski family, the sacred-score ratio shows a depth-invariant fixed-point signature at $1/\varphi \approx 0.618$ across 23 IBM hardware runs (depths 3-5).

  Newer promoter-panel experiments indicate this ~0.618 regime may also operate as a broader hardware-observable baseline across circuit families, motivating calibration-aware comparisons for family-specific residual effects.

2. **Fitness Baseline**: The 17-node lattice achieves average fitness ≥ 0.87 with phi-threshold 0.618.

3. **Hardware Provenance**: Every DNA segment is traceable to an IBM Quantum job ID.

4. **QRNG Entropy**: The QRNG service on ibm_fez achieves perfect entropy efficiency (1.0).

## Adding New Evidence

### Adding a Hardware Run

```python
from ledger_manager import HardwareEvidenceLedger

ledger = HardwareEvidenceLedger("hardware_evidence_ledger_v0.1.0-alpha.json")
ledger.load_ledger()

ledger.add_hardware_run(
    job_id="new-job-id",
    backend="ibm_fez",
    shots=4096,
    status="Completed",
    raw_result_path="circuits/results/job-new-result.json"
)

ledger.save_ledger()
```

### Linking Run to Agent

```python
ledger.link_run_to_agent(
    agent_id=4,
    job_id="new-job-id",
    decoded_segment="ATCGATCG",
    contribution_weight=1.0
)
```

## References

- IBM Quantum: https://quantum.ibm.com/
- Baseline Release: `baseline_v0.1.0-alpha.json`
- Checkpoint: `checkpoints/vault_state_post_training.json`
- Circuit Results: `circuits/results/`

---

**Maintainer:** TMT Quantum Vault Team  
**Last Updated:** 2026-03-28