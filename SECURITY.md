# Security Policy — TMT_Quantum_Vault

## Supported Versions

| Version | Supported |
|---------|-----------|
| main (latest) | ✅ Active |
| dev branches  | ⚠️ Best-effort |
| archived tags | ❌ Not supported |

## Scope

This policy covers:
- All 17-agent quantum circuits and vault logic
- IBM Quantum hardware job submission code (Fez, Torino, Casablanca)
- Sacred geometry / DNA circuit modules
- BitNet ternary entropy components
- NFT smart contract integrations
- API keys, IBM tokens, and any credentials used in the pipeline

## Reporting a Vulnerability

**Do NOT open a public GitHub Issue for security vulnerabilities.**

Please report privately via:
- 📧 Email: [your-email@domain.com]
- 🔒 GitHub Private Security Advisory:  
  `https://github.com/quantumdynamics927-dotcom/TMT_Quantum_Vault-/security/advisories/new`

Include in your report:
1. Description of the vulnerability
2. Steps to reproduce
3. Affected modules or agents
4. Potential impact (e.g., credential leak, circuit tampering)

## Response Timeline

- **Acknowledgement:** within 48 hours
- **Initial assessment:** within 7 days
- **Patch or mitigation:** within 30 days for critical issues

## Sensitive Data Notice

This repository interacts with IBM Quantum credentials and potentially 
MetaMask/NFT wallet keys. Never commit API tokens, private keys, or 
IBM access tokens. Use `.env` files or GitHub Secrets exclusively.

## Disclosure Policy

We follow **responsible disclosure**. Once a fix is deployed, we will 
publish a GitHub Security Advisory crediting the reporter (unless 
anonymity is requested).
