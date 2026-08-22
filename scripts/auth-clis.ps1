# Authenticate gh, huggingface-cli, and wrangler on Windows (PowerShell).

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot

function Test-Command {
    param([string]$Name)
    return [bool](Get-Command -Name $Name -ErrorAction SilentlyContinue)
}

Push-Location $repoRoot
Write-Host "🔐 TMT Quantum Vault — CLI authentication (Windows)"
Write-Host "====================================================="

if (Test-Command "gh") {
    Write-Host ""
    Write-Host "GitHub CLI (gh)"
    Write-Host "---------------"
    $status = gh auth status 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Already authenticated"
    } else {
        gh auth login --web
    }
} else {
    Write-Host "❌ gh not found. Run setup-clis.ps1 first."
}

if (Test-Command "huggingface-cli") {
    Write-Host ""
    Write-Host "Hugging Face CLI (huggingface-cli)"
    Write-Host "----------------------------------"
    $whoami = huggingface-cli whoami 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Already authenticated as: $whoami"
    } else {
        Write-Host "Get a token at https://huggingface.co/settings/tokens"
        huggingface-cli login
    }
} else {
    Write-Host "❌ huggingface-cli not found. Run setup-clis.ps1 first."
}

if (Test-Command "wrangler") {
    Write-Host ""
    Write-Host "Cloudflare Wrangler"
    Write-Host "-------------------"
    $whoami = wrangler whoami 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Already authenticated"
    } else {
        Write-Host "This will open a browser to authenticate with Cloudflare."
        wrangler login
    }
} else {
    Write-Host "❌ wrangler not found. Run setup-clis.ps1 first or use npx wrangler."
}

Write-Host ""
Write-Host "✅ Authentication complete."
Pop-Location
