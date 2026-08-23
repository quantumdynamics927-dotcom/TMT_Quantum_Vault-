#!/usr/bin/env bash
# Install gh and huggingface-cli for local deploy control.
# Works on Ubuntu/Debian, macOS (brew), and WSL.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

check_command() {
    command -v "$1" >/dev/null 2>&1
}

install_gh() {
    if check_command gh; then
        echo "[OK] gh already installed: $(gh --version | head -n 1)"
        return 0
    fi
    echo "[INSTALL] GitHub CLI (gh)..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        if check_command brew; then
            brew install gh
        else
            echo "[ERR] Homebrew not found. Install from https://github.com/cli/cli#installation"
            return 1
        fi
    else
        curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | \
            sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
        sudo chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | \
            sudo tee /etc/apt/sources.list.d/github-cli.list >/dev/null
        sudo apt-get update && sudo apt-get install -y gh
    fi
}

install_huggingface_cli() {
    if check_command huggingface-cli; then
        echo "[OK] huggingface-cli already installed: $(huggingface-cli --version)"
        return 0
    fi
    echo "[INSTALL] huggingface-cli via huggingface-hub..."
    python3 -m pip install --upgrade "huggingface-hub>=0.20"
}

cd "$REPO_ROOT"
echo "[SETUP] TMT Quantum Vault CLI installer"
echo "========================================"
install_gh
install_huggingface_cli
echo
echo "[DONE] CLI setup complete. Run 'make auth' to authenticate."
