# Secret Scanning Policy

This repository must not contain live credentials, tokens, API keys, passwords, private keys, or connection strings with embedded secrets.

## Scope

Apply secret scanning to:

- tracked source files
- tracked JSON configuration and data files
- workflow files under `.github/workflows/`
- documentation snippets that include commands or environment setup

Do not treat these paths as meaningful secret-scanning signal unless there is a specific reason to inspect them:

- `.git/`
- `.venv/`
- `.mypy_cache/`
- `.pytest_cache/`
- `__pycache__/`
- generated release evidence under `Resonance_Logs/daily/release-evidence-*`

## Accepted Patterns

These are allowed when they do not include a live secret value:

- environment variable names such as `OLLAMA_API_KEY`
- GitHub Actions secret references such as `${{ secrets.OLLAMA_API_KEY }}`
- obvious test placeholders such as `test-key`
- examples that describe how to set a secret without embedding the secret itself

## Required Handling

If you need credentials for runtime or CI:

- use environment variables for local execution
- use GitHub Actions secrets for hosted workflows
- keep secret names in configuration, not secret values
- avoid copying credential-bearing shell history, cache files, or generated outputs into the repository

## Review Workflow

Before merging runtime, CI, or configuration changes:

1. Scan tracked files for potential secrets.
2. Ignore generated caches and virtual-environment content.
3. Review each hit to separate placeholders and secret names from real secret material.
4. Block the change if a live secret value is present.

## Response Procedure

If a live secret is discovered in this repository:

1. Revoke or rotate the credential immediately.
2. Remove the secret from the working tree.
3. Assess whether git history cleanup is required.
4. Re-scan the affected files and related configuration.
5. Document the remediation in the pull request or incident notes.

## Repo Notes

- The current repository intentionally references `OLLAMA_API_KEY` as a secret name in CI and runtime configuration.
- Test coverage may use placeholder values for cloud-auth failure paths.
- Scanner results from local cache directories are considered noise unless a reviewer has a specific reason to inspect those files.