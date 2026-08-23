# Install gh and huggingface-cli on Windows (PowerShell).

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot

function Test-Command {
    param([string]$Name)
    return [bool](Get-Command -Name $Name -ErrorAction SilentlyContinue)
}

function Install-Gh {
    if (Test-Command "gh") {
        Write-Host "[OK] gh already installed: $((gh --version | Select-Object -First 1))"
        return
    }
    Write-Host "[INSTALL] GitHub CLI (gh) via winget..."
    if (Test-Command "winget") {
        winget install --id GitHub.cli
    } else {
        Write-Host "[ERR] winget not found. Install gh from https://github.com/cli/cli#installation"
        exit 1
    }
}

function Install-HuggingfaceCli {
    if (Test-Command "huggingface-cli") {
        Write-Host "[OK] huggingface-cli already installed: $((huggingface-cli --version))"
        return
    }
    Write-Host "[INSTALL] huggingface-cli via pip..."
    python -m pip install --upgrade "huggingface-hub>=0.20"
}

Push-Location $repoRoot
Write-Host "[SETUP] TMT Quantum Vault CLI installer (Windows)"
Write-Host "==================================================="
Install-Gh
Install-HuggingfaceCli
Write-Host ""
Write-Host "[DONE] CLI setup complete. Run 'make auth' (or use WSL) to authenticate."
Pop-Location
