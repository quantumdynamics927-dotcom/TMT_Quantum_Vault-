# Contributing to TMT Quantum Vault

Thank you for contributing to TMT Quantum Vault. This repository mixes a typed
Python CLI, validation logic, and research artifacts derived from quantum and
DNA-inspired workflows, so small, well-scoped changes are strongly preferred.

## Before You Start

- Read the project overview in [`README.md`](README.md).
- Review the architecture notes in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).
- Follow the community expectations in [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).
- Review [`ETHICS.md`](ETHICS.md) and [`SECURITY.md`](SECURITY.md) before opening
  issues or proposing changes that affect safety, security, or system behavior.

## Development Setup

```bash
git clone https://github.com/quantumdynamics927-dotcom/TMT_Quantum_Vault-
cd TMT_Quantum_Vault-
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .[dev]
```

If you need the optional quantum execution dependencies:

```bash
python -m pip install -e .[qiskit]
```

## Validation Commands

Please run the relevant existing checks before opening a pull request:

```bash
ruff check tmt_quantum_vault/ tests/test_regression.py
black --check tmt_quantum_vault/ tests/test_regression.py
python -m compileall tmt_quantum_vault tests
python -m pytest tests/ -v --tb=short
python -m tmt_quantum_vault validate
python -m tmt_quantum_vault summary
```

For documentation-only changes, at minimum confirm that linked commands and file
paths remain accurate.

## Pull Request Guidelines

- Keep changes focused and easy to review.
- Update user-facing documentation when behavior, workflows, or repository
  structure changes.
- Avoid reformatting unrelated files.
- Include enough context in the pull request description for reviewers to
  understand the problem, the change, and the validation performed.

## Issues and Feature Requests

- Use GitHub Issues for bugs, questions, and documentation improvements.
- Do **not** open public issues for security vulnerabilities; follow the private
  reporting process in [`SECURITY.md`](SECURITY.md).

## Research and Data Integrity

This repository contains generated artifacts, logs, and hardware-derived data.
When updating those assets:

- Preserve provenance where possible.
- Avoid editing historical records unless the change is a documented correction.
- Note any downstream documentation or validation implications in the same pull
  request.
