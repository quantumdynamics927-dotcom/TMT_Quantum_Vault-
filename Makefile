# TMT Quantum Vault — Makefile
#
# Local development helpers and CLI-driven deploy/release control.
# CI runs the same checks via .github/workflows/.

.PHONY: help setup-clis auth status test test-audit clean-reports release deploy-hf deploy-cf

# Detect platform so the right install/auth scripts run.
ifeq ($(OS),Windows_NT)
	SETUP_SCRIPT := powershell -ExecutionPolicy Bypass -File scripts/setup-clis.ps1
	AUTH_SCRIPT := powershell -ExecutionPolicy Bypass -File scripts/auth-clis.ps1
else
	SETUP_SCRIPT := bash scripts/setup-clis.sh
	AUTH_SCRIPT := bash scripts/auth-clis.sh
endif

# Allow overriding the Python interpreter (handy on WSL/Windows hybrid setups).
PYTHON ?= python

help:
	@echo "Targets:"
	@echo "  make setup-clis    Install gh, huggingface-cli, and wrangler."
	@echo "  make auth          Authenticate all three CLIs."
	@echo "  make status        Show auth status for gh/huggingface/wrangler."
	@echo "  make test          Run the full pytest suite."
	@echo "  make test-audit    Run only the audit tool's tests."
	@echo "  make audit         Run the deterministic repo audit (no LLM)."
	@echo "  make clean-reports Remove all generated audit reports."
	@echo "  make release       Create a GitHub release and upload dist artifacts."
	@echo "                     Usage: make release VERSION=0.4.1"
	@echo "  make deploy-hf     Deploy to Hugging Face Spaces via huggingface-cli."
	@echo "  make deploy-cf     Deploy the static app/ directory to Cloudflare Pages."

setup-clis:
	$(SETUP_SCRIPT)

auth:
	$(AUTH_SCRIPT)

status:
	@echo "GitHub CLI"
	@echo "----------"
	@gh auth status 2>/dev/null || echo "❌ Not authenticated. Run: make auth"
	@echo
	@echo "Hugging Face CLI"
	@echo "----------------"
	@huggingface-cli whoami 2>/dev/null || echo "❌ Not authenticated. Run: make auth"
	@echo
	@echo "Cloudflare Wrangler"
	@echo "-------------------"
	@wrangler whoami 2>/dev/null || echo "❌ Not authenticated. Run: make auth"

test:
	$(PYTHON) -m pytest tests/ -q

test-audit:
	$(PYTHON) -m pytest tests/test_audit.py -v

audit:
	$(PYTHON) tools/audit.py

clean-reports:
	rm -f audit_reports/deterministic_audit_*

release:
	@if [ -z "$(VERSION)" ]; then \
		echo "❌ VERSION is required. Usage: make release VERSION=0.4.1"; \
		exit 1; \
	fi
	@echo "📦 Building release v$(VERSION)..."
	$(PYTHON) -m build
	@echo "🏷️  Creating GitHub release v$(VERSION)..."
	gh release create "v$(VERSION)" \
		--title "v$(VERSION)" \
		--generate-notes \
		dist/*

deploy-hf:
	@echo "🚀 Deploying to Hugging Face Spaces..."
	$(PYTHON) scripts/deploy_hf.py --space-name Quantum927/quantumvault --private

deploy-cf:
	@echo "🚀 Building static app/ and deploying to Cloudflare Pages..."
	$(PYTHON) tools/build_app.py
	wrangler pages deploy app/ --project-name tmt-quantum-vault --branch main
