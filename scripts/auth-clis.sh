#!/usr/bin/env bash
# Authenticate gh, huggingface-cli, and wrangler.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

check_command() {
    command -v "$1" >/dev/null 2>&1
}

echo "🔐 TMT Quantum Vault — CLI authentication"
echo "========================================"

if check_command gh; then
    echo
    echo "GitHub CLI (gh)"
    echo "---------------"
    if gh auth status >/dev/null 2>&1; then
        echo "✅ Already authenticated as: $(gh api user -q '.login' 2>/dev/null || echo 'unknown')"
    else
        gh auth login --web
    fi
else
    echo "❌ gh not found. Run 'make setup-clis' first."
fi

if check_command huggingface-cli; then
    echo
    echo "Hugging Face CLI (huggingface-cli)"
    echo "----------------------------------"
    if huggingface-cli whoami >/dev/null 2>&1; then
        echo "✅ Already authenticated as: $(huggingface-cli whoami)"
    else
        echo "Get a token at https://huggingface.co/settings/tokens"
        huggingface-cli login
    fi
else
    echo "❌ huggingface-cli not found. Run 'make setup-clis' first."
fi

if check_command wrangler; then
    echo
    echo "Cloudflare Wrangler"
    echo "-------------------"
    # wrangler whoami returns 0 when logged in
    if wrangler whoami >/dev/null 2>&1; then
        echo "✅ Already authenticated"
    else
        echo "This will open a browser to authenticate with Cloudflare."
        wrangler login
    fi
else
    echo "❌ wrangler not found. Run 'make setup-clis' first or use npx wrangler."
fi

echo
echo "✅ Authentication complete. Run 'make status' to verify."
