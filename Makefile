# TMT Quantum Vault Makefile
#
# Local development helpers and CLI-driven Hugging Face deploy control.
# CI runs the same checks via .github/workflows/.

.PHONY: help setup-clis auth status test test-audit clean-reports deploy-hf

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
	@echo "  make setup-clis    Install gh and huggingface-cli."
	@echo "  make auth          Authenticate gh and huggingface-cli."
	@echo "  make status        Show auth status for gh/huggingface-cli."
	@echo "  make test          Run the full pytest suite."
	@echo "  make test-audit    Run only the audit tool's tests."
	@echo "  make audit         Run the deterministic repo audit (no LLM)."
	@echo "  make clean-reports Remove all generated audit reports."
	@echo "  make deploy-hf     Deploy to Hugging Face Spaces via huggingface-cli."

setup-clis:
	$(SETUP_SCRIPT)

auth:
	$(AUTH_SCRIPT)

status:
	@echo "GitHub CLI"
	@echo "----------"
	@gh auth status 2>/dev/null || echo "[NOT AUTH] Run: make auth"
	@echo
	@echo "Hugging Face CLI"
	@echo "----------------"
	@huggingface-cli whoami 2>/dev/null || echo "[NOT AUTH] Run: make auth"

test:
	$(PYTHON) -m pytest tests/ -q

test-audit:
	$(PYTHON) -m pytest tests/test_audit.py -v

audit:
	$(PYTHON) tools/audit.py

clean-reports:
	rm -f audit_reports/deterministic_audit_*

deploy-hf:
	@echo "[DEPLOY] Hugging Face Spaces..."
	$(PYTHON) scripts/deploy_hf.py --space-name Quantum927/quantumvault --private
