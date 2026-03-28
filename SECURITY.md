# Security Policy — TMT Quantum Vault

## Supported Versions

| Version | Supported |
|---------|-----------|
| Latest default branch | ✅ Active |
| Open pull request branches | ⚠️ Best-effort |
| Archived tags and stale forks | ❌ Not supported |

## Scope

This policy covers the repository code, packaged CLI, research tooling, and
tracked data assets, including:

- the `tmt_quantum_vault/` package and CLI workflows
- repository validation and release tooling under `tools/`
- agent DNA profiles, memory stores, and JSON configuration files
- IBM Quantum-related circuit artifacts and ingestion helpers
- dependency, credential, and supply-chain risks that affect this repository

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Please report vulnerabilities privately using one of these channels:

- 📧 Email: `quantumdynamics927@gmail.com`
- 🔒 GitHub Private Security Advisory:
  `https://github.com/quantumdynamics927-dotcom/TMT_Quantum_Vault-/security/advisories/new`

Please include:

1. A clear description of the issue
2. The affected files, commands, or workflows
3. Reproduction steps or a proof of concept
4. Any known impact on confidentiality, integrity, or availability
5. Suggested mitigations, if you have them

## Response Timeline

- **Acknowledgement:** within 3 business days
- **Initial triage:** within 7 business days
- **Status update:** after triage, with follow-up cadence based on severity
- **Fix target:** critical issues are prioritized first, with best-effort public
  remediation once a patch or mitigation is ready

## Handling Sensitive Information

Please help protect users and maintainers by following these rules:

- Never commit API keys, IBM credentials, tokens, wallet secrets, or other
  sensitive material
- Use environment variables, `.env` files kept out of version control, or GitHub
  Actions secrets for operational credentials
- Redact secrets from screenshots, logs, stack traces, and sample payloads
- If you discover exposed credentials in the repository history or automation,
  report them privately and rotate them immediately where possible

## Security Review Areas

When reviewing changes, pay particular attention to:

- file parsing and JSON validation paths
- shell execution or subprocess handling
- runtime networking and model API integrations
- dependency updates and transitive vulnerability exposure
- provenance and integrity of generated research artifacts

## Disclosure Policy

We follow responsible disclosure. Please give maintainers a reasonable
opportunity to investigate and remediate before sharing details publicly. When a
fix is available, maintainers may publish a GitHub Security Advisory and credit
the reporter unless anonymity is requested.
