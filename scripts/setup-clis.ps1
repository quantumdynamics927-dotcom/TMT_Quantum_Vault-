# Install gh, huggingface-cli, and wrangler on Windows (PowerShell).

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot

function Test-Command {
    param([string]$Name)
    return [bool](Get-Command -Name $Name -ErrorAction SilentlyContinue)
}

function Install-Gh {
    if (Test-Command "gh") {
        Write-Host "✅ gh already installed: $((gh --version | Select-Object -First 1))"
        return
    }
    Write-Host "⬇️  Installing GitHub CLI (gh) via winget..."
    if (Test-Command "winget") {
        winget install --id GitHub.cli
    } else {
        Write-Host "❌ winget not found. Install gh from https://github.com/cli/cli#installation"
        exit 1
    }
}

function Install-HuggingfaceCli {
    if (Test-Command "huggingface-cli") {
        Write-Host "✅ huggingface-cli already installed: $((huggingface-cli --version))"
        return
    }
    Write-Host "⬇️  Installing huggingface-cli via pip..."
    python -m pip install --upgrade "huggingface-hub>=0.20"
}

function Install-Wrangler {
    if (Test-Command "wrangler") {
        Write-Host "✅ wrangler already installed: $((wrangler --version))"
        return
    }
    if (Test-Command "npm") {
        Write-Host "⬇️  Installing wrangler via npm..."
        npm install -g wrangler
    } else {
        Write-Host "⚠️  npm not found. Falling back to npx for wrangler."
    }
}

Push-Location $repoRoot
Write-Host "🔧 TMT Quantum Vault — CLI installer (Windows)"
Write-Host "==============================================="
Install-Gh
Install-HuggingfaceCli
Install-Wrangler
Write-Host ""
Write-Host "✅ CLI setup complete. Run 'make auth' (or use WSL) to authenticate."
Pop-Location
