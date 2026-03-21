# circuits/qasm/

Generated QASM 2.0 files for upload to IBM Quantum.

## Workflow

1. Generate circuit: `python tools/ibm_circuit_runner.py generate --circuit sierpinski --depth 4`
2. Upload `.qasm` file manually to [IBM Quantum Circuit Composer](https://quantum.ibm.com/)
3. Run on backend (e.g., `ibm_fez`) with configured shots (default 4096)
4. Download result JSON and save to `circuits/results/`
5. Ingest: `python tools/ibm_circuit_runner.py ingest --file <result.json>`

## Manifests

Each circuit has a配套 `*_manifest.json` with:
- Circuit name and parameters
- Backend and shot count
- Status tracking (PENDING_UPLOAD → INGESTED)
- Timestamp and job ID placeholder

## Significance

Significant results (those producing new agent DNA) should be moved to `circuits/ingested/SIGNIFICANT/` before committing to preserve hardware-validated discoveries.
