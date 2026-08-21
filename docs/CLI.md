# TMT Quantum Vault — CLI Reference

> **Version:** 1.0
> **Last Updated:** August 22, 2026

---

## Overview

The TMT Quantum Vault CLI provides commands for validation, orchestration, quantum circuit generation, and system management. All commands are accessed via `python -m tmt_quantum_vault <command>`.

---

## Core Commands

### `summary`
Display a comprehensive summary of the TMT Quantum Vault repository.

```bash
python -m tmt_quantum_vault summary
```

### `validate`
Validate repository data against schemas and check integrity.

```bash
python -m tmt_quantum_vault validate
```

### `doctor`
Run diagnostics to check system health and dependencies.

```bash
python -m tmt_quantum_vault doctor
```

### `runtime`
Inspect runtime dependencies (Ollama, llama.cpp, cloud).

```bash
python -m tmt_quantum_vault runtime
```

### `run`
Run a prompt through the configured runtime backend.

```bash
python -m tmt_quantum_vault run "Your prompt here"
```

---

## Local Testing Commands

### `smoke-local`
Run local smoke tests against the configured Ollama instance.

```bash
python -m tmt_quantum_vault smoke-local
```

### `smoke-cloud`
Run smoke tests against Ollama cloud API (requires `OLLAMA_API_KEY`).

```bash
python -m tmt_quantum_vault smoke-cloud
```

---

## Evaluation Commands

### `eval`
Evaluate prompt execution results.

```bash
python -m tmt_quantum_vault eval [OPTIONS]
```

### `compare-evidence`
Compare evidence from multiple runs or sources.

```bash
python -m tmt_quantum_vault compare-evidence [OPTIONS]
```

### `agi-validate`
Validate agent DNA integrity and consciousness metrics.

```bash
python -m tmt_quantum_vault agi-validate
```

### `agi-eval-smoke`
Run smoke evaluation for agent integration.

```bash
python -m tmt_quantum_vault agi-eval-smoke
```

---

## Release Commands

### `release-summary`
Generate a release summary for a version.

```bash
python -m tmt_quantum_vault release-summary [OPTIONS]
```

### `release-gate`
Run release gate checks before publishing.

```bash
python -m tmt_quantum_vault release-gate [OPTIONS]
```

### `release-evidence`
Generate evidence report for a release.

```bash
python -m tmt_quantum_vault release-evidence [OPTIONS]
```

---

## Agent Commands

### `agent`
Inspect individual agent profiles.

```bash
python -m tmt_quantum_vault agent [OPTIONS]
```

### `agent-task`
Execute a task through a specific agent.

```bash
python -m tmt_quantum_vault agent-task [OPTIONS]
```

### `create-agents`
Generate `conscious_dna.json` for all agent directories.

```bash
python -m tmt_quantum_vault create-agents [OPTIONS]
```

---

## Orchestration Commands

### `orch-status`
Show orchestration system status and agent profiles.

```bash
python -m tmt_quantum_vault orch-status
```

### `orch-execute`
Execute a task through the orchestration system.

```bash
python -m tmt_quantum_vault orch-execute [OPTIONS]
```

### `orch-benchmark`
Run the orchestration benchmark suite.

```bash
python -m tmt_quantum_vault orch-benchmark [OPTIONS]
```

### `orch-report`
Generate a coordination analysis report.

```bash
python -m tmt_quantum_vault orch-report [OPTIONS]
```

### `orch-agents`
List all registered agents and their profiles.

```bash
python -m tmt_quantum_vault orch-agents [OPTIONS]
```

### `orch-matrix`
Show TMT Benchmark Matrix tasks.

```bash
python -m tmt_quantum_vault orch-matrix [OPTIONS]
```

### `orch-run-matrix`
Run TMT Benchmark Matrix tasks with explicit simulation/live semantics.

```bash
python -m tmt_quantum_vault orch-run-matrix [OPTIONS]
```

---

## Research Commands

### `ablation`
Run ablation study to measure component contribution.

```bash
python -m tmt_quantum_vault ablation [OPTIONS]
```

---

## Cryptography Commands

### `encrypt-ledger`
Encrypt the hardware evidence ledger using quantum-secure cryptography.

```bash
python -m tmt_quantum_vault encrypt-ledger [OPTIONS]
```

### `decrypt-ledger`
Decrypt an encrypted evidence ledger.

```bash
python -m tmt_quantum_vault decrypt-ledger [OPTIONS]
```

### `generate-fingerprint`
Generate a Merkaba quantum fingerprint.

```bash
python -m tmt_quantum_vault generate-fingerprint [OPTIONS]
```

---

## Quantum Circuit Commands

### `merkaba-circuit`
Generate Merkaba circuit in specified format (QASM, Qiskit, etc.).

```bash
python -m tmt_quantum_vault merkaba-circuit [OPTIONS]
```

---

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OLLAMA_API_KEY` | API key for Ollama cloud access | For cloud commands |
| `OLLAMA_BASE_URL` | Base URL for Ollama API (default: http://localhost:11434) | No |

---

## Output Formats

Many commands support JSON output via the `--json` flag:

```bash
python -m tmt_quantum_vault orch-status --json
```

---

## See Also

- [README.md](../README.md) — Project overview
- [ARCHITECTURE.md](./ARCHITECTURE.md) — System architecture
- [CHANGELOG.md](../CHANGELOG.md) — Version history
