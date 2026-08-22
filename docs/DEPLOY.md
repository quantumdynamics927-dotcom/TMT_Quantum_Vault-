# TMT Quantum Vault - Deploy Guide

This project deploys the Docker Space to Hugging Face Spaces. GitHub CLI (`gh`) is used for commit and workflow control.

---

## One-time setup

### 1. Install the CLIs

On Linux/WSL/macOS:

```bash
make setup-clis
```

On Windows PowerShell:

```powershell
.\scripts\setup-clis.ps1
```

This installs (or updates) `gh` and `huggingface-cli`.

### 2. Authenticate

On Linux/WSL/macOS:

```bash
make auth
```

On Windows PowerShell:

```powershell
.\scripts\auth-clis.ps1
```

You will be prompted to log in to GitHub and Hugging Face in your browser.

### 3. Verify

```bash
make status
```

Expected output shows your GitHub username and HF username.

---

## Local deploy commands

### Hugging Face Spaces

```bash
make deploy-hf
```

This runs `python scripts/deploy_hf.py`, which:

1. Prepares a temporary deployment tree with `pyproject.toml`, `vault_config.json`, `metatron_geometry.json`, the `tmt_quantum_vault/` package, and `conscious_dna.json` files.
2. Creates the Space if it does not exist.
3. Uploads the tree with `huggingface-cli upload --repo-type space`.

Requirements:

- `HF_TOKEN` environment variable set, or already logged in via `huggingface-cli login`.

---

## CI / GitHub Actions

The repository includes workflows under `.github/workflows/`:

| Workflow | Purpose | Trigger |
|---|---|---|
| `deploy-hf.yml` | Deploy to HF Spaces via `huggingface-cli` | Push to `main` affecting deployable paths |
| `deploy-hf-docker.yml` | Same Docker-based deploy, triggered by config changes | Push to `main` affecting `pyproject.toml` etc. |

### Required GitHub secrets

| Secret | Used by | How to obtain |
|---|---|---|
| `HF_TOKEN` | `deploy-hf.yml`, `deploy-hf-docker.yml` | https://huggingface.co/settings/tokens |
| `GITHUB_TOKEN` | workflow status / `gh` | Provided automatically by GitHub Actions |

---

## Notes

- The local dashboard (`index.html`, `dashboard.js`, `research-status.html`) is intended for localhost use only and is not deployed to an external static host.
- Vercel artifacts were removed: `@vercel/analytics` is gone and `.vercel/` is no longer referenced in `hf-deploy/.dockerignore`.
