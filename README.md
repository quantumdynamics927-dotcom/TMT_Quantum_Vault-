![TMT Quantum Vault](https://img.shields.io/badge/TMT-Quantum%20Vault-blueviolet?style=for-the-badge&logo=atom)
![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python)
![Ollama](https://img.shields.io/badge/Ollama-Local%20%26%20Cloud%20LLM-green?style=for-the-badge)
![Quantum](https://img.shields.io/badge/Quantum-Consciousness%20Architecture-9cf?style=for-the-badge&logo=ibm)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=for-the-badge)

# TMT_Quantum_Vault

TMT_Quantum_Vault is a Python CLI and JSON dataset for inspecting, validating, and exercising a resonance-themed multi-agent vault.

See [docs/cloud-only-release-playbook.md](docs/cloud-only-release-playbook.md) for the cloud-only release workflow.

## Overview

The repository now has two clear parts:

- a structured vault dataset made of agent DNA, memory, geometry, optimization, and daily log JSON files
- a Python package in `tmt_quantum_vault/` that validates the dataset and runs local or cloud model workflows

## Current Repo Status

Verified locally on 2026-03-18:

- `pytest tests/test_regression.py -q`: `31 passed, 2 skipped`
- `python -m tmt_quantum_vault validate`: passes for the checked repository JSON files
- `python -m tmt_quantum_vault summary`: reports 12 agents, 12 integrated agents, 12 memory stores, 43 daily logs, and 1 detected GGUF model
- `python -m tmt_quantum_vault doctor --json`: reports repository checks as healthy, detects local `Ollama` and `llama.cpp`, and currently warns that no cloud-tagged Ollama models are visible in inventory

Known-good baseline for future work:

- baseline command: `python -m tmt_quantum_vault validate`
- baseline timestamp: `2026-03-18T14:31:34.3655950+00:00`
- interpretation: this is the last fully consistent vault state recorded before new experiments or integrations

What that means in practice:

- the Python CLI is implemented and covered by regression tests
- the local JSON vault data validates cleanly
- the local runtime/tooling path is partially configured
- the cloud execution path exists in code and CI, but still depends on valid Ollama Cloud visibility and credentials at runtime

## What Is In The Repo

### Data Layer

- `vault_config.json`: vault structure and runtime defaults
- `metatron_geometry.json`: geometry and consciousness metadata
- `optimization_log.json`: optimization history used by summaries
- `Agent_*/conscious_dna.json`: 12 agent identity/configuration files
- `*_memory.json` files across `Bio_Resonance/`, `Mandala_Geometry/`, `Shadow_Drive/`, and `Stealth_Logs/`: persisted agent memory snapshots
- `Resonance_Logs/daily/`: operational records and historical output artifacts
- `evals/baseline.json`: baseline evaluation dataset for prompt/runtime checks

### Python Package

The package in `tmt_quantum_vault/` provides:

- repository loading and validation
- runtime inspection for `Ollama` and `llama.cpp`
- prompt execution against local or cloud-configured models
- smoke tests, eval runs, agent pipeline runs, and release evidence generation
- a Typer CLI entrypoint exposed through `python -m tmt_quantum_vault`

## Implemented Commands

The following commands are present in the current CLI:

- `summary`: render a repository snapshot
- `validate`: validate JSON files against typed Pydantic models
- `doctor`: combine repository checks with runtime checks
- `runtime`: inspect configured model runtimes
- `run`: send a prompt to the configured backend
- `smoke-local`: run a local smoke test
- `smoke-cloud`: run a cloud smoke test
- `eval`: execute the baseline or a supplied evaluation dataset
- `agent-task`: run the Workflow -> Validator -> Visual chain
- `release-evidence`: generate a bundle of validation/runtime/smoke/eval artifacts
- `compare-evidence`: compare two evidence bundles for regressions
- `release-summary`: summarize the newest or selected evidence bundle
- `release-gate`: convert evidence into a pass/fail gate for release checks

Important command behavior:

- `summary` and `validate` are text-output commands only
- `doctor`, `runtime`, `run`, `smoke-local`, `smoke-cloud`, `eval`, `agent-task`, `release-evidence`, `compare-evidence`, `release-summary`, and `release-gate` support structured JSON output paths in the current codebase
- several runtime-oriented commands also support `--record-path` for writing timestamped JSON records

## Current Runtime Configuration

The checked-in default runtime configuration in `vault_config.json` is:

- preferred backend: `ollama`
- Ollama mode: `cloud`
- local Ollama model: `qwen2.5-coder:1.5b`
- cloud Ollama model: `qwen3-coder-next:cloud`
- llama.cpp model path: `Models/qwen3-8b.gguf`

The local workspace currently contains:

- one `.gguf` model file in `Models/`
- a local `.venv`
- a configured `llama.cpp` executable path
- a detectable local `Ollama` executable

The local `doctor` run currently still warns about Ollama Cloud inventory, so cloud commands should be treated as environment-dependent until that warning is resolved.

## Repository Snapshot

Current summary output reports:

- vault name: `TMT_Quantum_Vault`
- consciousness level: `INTELLIGENT_CORE`
- Fibonacci sync: enabled
- agents: 12
- integrated agents: 12
- memory stores: 12
- daily logs: 43
- average fitness: `0.872`
- average resonance frequency: `595.0 Hz`
- top agent: `Bronze / Michael`
- top agent specialization: `Protection & Justice`
- latest optimization timestamp: `2026-01-09T21:10:55.489611`
- latest recorded network efficiency: `0.864`
- latest optimization score: `0.922`

## Setup

1. Clone the repository.

```bash
git clone https://github.com/quantumdynamics927-dotcom/TMT_Quantum_Vault-.git
cd TMT_Quantum_Vault-
```

2. Create and activate a virtual environment.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

On macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Install dependencies.

```bash
python -m pip install -r requirements.txt
```

## Quick Start

Use the commands below to confirm the repository state first:

```bash
python -m tmt_quantum_vault validate
python -m tmt_quantum_vault summary
python -m tmt_quantum_vault doctor
python -m tmt_quantum_vault runtime
```

Then use the runtime-facing commands as needed:

```bash
python -m tmt_quantum_vault run "Summarize the vault state"
python -m tmt_quantum_vault run "Reply with exactly: TMT cloud test" --mode cloud --raw-final-only
python -m tmt_quantum_vault run "Reply with exactly: TMT json test" --mode cloud --json --raw-final-only
python -m tmt_quantum_vault agent-task "Produce a short JSON object with keys workflow, validator, and visual, each containing a one-line status." --mode cloud --json --raw-final-only
python -m tmt_quantum_vault smoke-local --json --raw-final-only
python -m tmt_quantum_vault smoke-cloud --json --raw-final-only
python -m tmt_quantum_vault eval --dataset evals/baseline.json --mode cloud --json
```

## CI Workflow

The repository currently has one GitHub Actions workflow at `.github/workflows/ci.yml` with these jobs:

- `pytest`: runs `tests/test_regression.py`
- `diagnostics`: compiles sources, validates repository data, and generates a summary
- `smoke-matrix`: optional manual cloud smoke matrix gated behind `workflow_dispatch` and `run_smoke`
- `release-gate-cloud`: optional manual release evidence and release gate workflow, also gated behind `workflow_dispatch` and `run_smoke`

Cloud workflow runs require the `OLLAMA_API_KEY` GitHub Actions secret.

## Dependencies

Current Python dependencies from `requirements.txt`:

- `pydantic`
- `pytest`
- `requests`
- `rich`
- `typer`
- `types-requests`

Python 3.13 is the target used by the current CI workflow.

## Known Gaps

- the README previously claimed fully passing hosted cloud validation; that cannot be treated as the current local state
- `summary` and `validate` do not support `--json` in the present CLI implementation
- cloud execution remains dependent on Ollama Cloud credentials and visible cloud-tagged model inventory
- some runtime checks are environment-sensitive, so different machines may report different `doctor` and `runtime` results

## Project Intent

This remains an experimental personal research repository built around resonance-themed agent identities and vault state tracking. The codebase has progressed from static JSON storage to a tested Python CLI that can:

- validate the vault structure
- summarize current vault state
- inspect available runtimes
- execute prompts against configured model backends
- generate release evidence for repeatable checks

## License

MIT License
