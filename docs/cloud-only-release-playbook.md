# Cloud-Only Release Playbook

## Purpose

This playbook covers release and deployment steps for running TMT Quantum Vault with Ollama cloud models only.

## Prerequisites

- Python 3.13+
- A populated `.venv` or equivalent Python environment
- Ollama CLI installed and authenticated for cloud usage
- `vault_config.json` configured with `preferred_backend: "ollama"` and `mode: "cloud"`
- A verified cloud tag such as `qwen3-coder-next:cloud`

## Local Artifact Policy

- `.vscode/` is ignored and should remain local unless the repository intentionally adopts shared workspace settings.
- `.claude/` is ignored and should not be committed because it may contain user-specific local tool settings.

## Pre-Release Checklist

1. Activate the virtual environment.
2. Install dependencies with `python -m pip install -r requirements.txt`.
3. Run `python -m pytest tests/test_regression.py -q`.
4. Run `python -m tmt_quantum_vault validate`.
5. Run `python -m tmt_quantum_vault runtime --json --record-path Resonance_Logs/daily/runtime-check.json`.
6. Run `python -m tmt_quantum_vault smoke-cloud --json --raw-final-only --record-path Resonance_Logs/daily/smoke-cloud.json`.
7. Run `python -m tmt_quantum_vault agent-task "Produce a short JSON object with keys workflow, validator, and visual, each containing a one-line status." --mode cloud --json --raw-final-only --record-path Resonance_Logs/daily/agent-task-smoke.json`.
8. Optionally run `python -m tmt_quantum_vault release-evidence --json` to bundle the release records into one timestamped directory.

## Release Procedure

1. Confirm the working tree is clean.
2. Push the current branch.
3. Ensure the `pytest` and `diagnostics` GitHub Actions jobs pass.
4. If cloud smoke is needed in CI, run the manual `CI` workflow with `run_smoke=true` and set `cloud_model` to the tag you want to validate on a runner that has cloud-ready Ollama access.

## Operational Diagnostics

- `runtime --json` reports local runtime inventory plus a dedicated `Ollama Cloud` status.
- `doctor --json` combines repository health with runtime statuses.
- `smoke-cloud` is the authoritative end-to-end connectivity check for cloud inference.
- `release-evidence` collects the main diagnostic and runtime records into a single timestamped artifact bundle.

## Exportable Records

The following commands support `--record-path` for structured JSON records:

- `runtime`
- `doctor`
- `smoke-cloud`
- `agent-task`

Use these records for change reviews, incident notes, or release evidence.

The `agent-task` export includes per-stage prompts, system prompts, raw outputs, normalized outputs, stderr, and the invoked command for deeper troubleshooting.

## Rollback

1. Revert the offending commit.
2. Re-run `pytest`, `validate`, and `smoke-cloud`.
3. Push the rollback once cloud diagnostics return to a healthy state.
