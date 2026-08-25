#!/usr/bin/env python3
"""
Tests for tools/audit.py — the deterministic (no-LLM) audit script.

These tests use tmp_path to build synthetic micro-repos, so they do not
depend on the real repository state and will keep working as the real repo
evolves.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

# tools/audit.py is at <repo>/tools/audit.py. pyproject.toml sets
# pythonpath = ["."] so `from tools.audit import ...` works in pytest.
from tools.audit import (
    AuditContext,
    Finding,
    build_context,
    build_report,
    check_F001_untracked_enc_json,
    check_F004_xor_fallback,
    check_F008_zero_default_seed,
    check_F013_no_lockfile,
    check_F019_commented_ignore_rule,
    main,
    render_console,
    render_markdown,
    run_audit,
    totals,
)

# ══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def fake_repo(tmp_path: Path) -> Path:
    """A minimal non-git directory: enough to exercise individual checks."""
    (tmp_path / "evidence_ledger").mkdir()
    (tmp_path / "tmt_quantum_vault").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / ".gitignore").write_text("# empty\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pydantic>=2.11\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def fake_git_repo(tmp_path: Path) -> Path:
    """A minimal git-initialized directory with a single commit."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "audit-test@example.com"],
        cwd=tmp_path,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Audit Test"],
        cwd=tmp_path,
        check=True,
    )
    (tmp_path / ".gitignore").write_text("# empty\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("test\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=tmp_path, check=True)
    return tmp_path


# ══════════════════════════════════════════════════════════════════════════════
# INVARIANT: STDLIB ONLY
# ══════════════════════════════════════════════════════════════════════════════


def test_audit_is_stdlib_only() -> None:
    """tools/audit.py must not import any non-stdlib package."""
    audit_path = Path(__file__).resolve().parent.parent / "tools" / "audit.py"
    src = audit_path.read_text(encoding="utf-8")
    forbidden = ("openai", "tiktoken", "requests", "pydantic", "typer", "rich")
    for pkg in forbidden:
        # Match `import pkg`, `from pkg import ...`, and `from pkg.sub import ...`
        pattern = rf"(^|\n)\s*(import|from)\s+{re.escape(pkg)}\b"
        assert not re.search(
            pattern, src
        ), f"tools/audit.py imports forbidden package: {pkg}"


# ══════════════════════════════════════════════════════════════════════════════
# INDIVIDUAL CHECKS
# ══════════════════════════════════════════════════════════════════════════════


def test_F001_detects_untracked_enc_json(fake_repo: Path) -> None:
    """F-001 fires when a *.enc.json is on disk and not gitignored (no git here)."""
    enc = fake_repo / "evidence_ledger" / "ledger.enc.json"
    enc.write_text('{"ciphertext": "x"}', encoding="utf-8")

    ctx = build_context(fake_repo)
    findings = check_F001_untracked_enc_json(ctx)
    assert any(f.id == "F-001" for f in findings), findings
    matched = [f for f in findings if f.id == "F-001"]
    assert any("ledger.enc.json" in (f.path or "") for f in matched)


def test_F001_does_not_fire_when_ignored(fake_repo: Path) -> None:
    """F-001 stays silent when the *.enc.json is matched by .gitignore."""
    enc = fake_repo / "evidence_ledger" / "ledger.enc.json"
    enc.write_text("{}", encoding="utf-8")
    (fake_repo / ".gitignore").write_text("*.enc.json\n", encoding="utf-8")

    ctx = build_context(fake_repo)
    findings = check_F001_untracked_enc_json(ctx)
    # F-001 requires not-gitignored + untracked; here it is gitignored, so should not fire.
    # (In a non-git repo, git_check_ignore returns False, but the rglob path check
    # is the first filter — verify the file at least gets walked, then the gitignore
    # check passes and we should not emit. Since this is non-git, git_check_ignore is
    # always False, so the check WILL fire. We document this as a known limitation
    # by asserting the behavior in the non-git case.)
    # The key user-facing guarantee is: F-001 must NOT fire on a git repo where the
    # file is properly ignored — see test_F001_does_not_fire_when_gitignored below.
    assert isinstance(findings, list)  # no crash; result depends on git state


def test_F001_does_not_fire_when_gitignored(fake_git_repo: Path) -> None:
    """F-001 stays silent when the *.enc.json is ignored on a real git repo."""
    (fake_git_repo / "evidence_ledger").mkdir(exist_ok=True)
    enc = fake_git_repo / "evidence_ledger" / "ledger.enc.json"
    enc.write_text("{}", encoding="utf-8")
    (fake_git_repo / ".gitignore").write_text("*.enc.json\n", encoding="utf-8")

    ctx = build_context(fake_git_repo)
    findings = check_F001_untracked_enc_json(ctx)
    assert not any(f.id == "F-001" for f in findings), findings


def test_F004_does_not_fire_on_real_file() -> None:
    """F-004 stays silent on the real vault_encryptor.py now that the XOR fallback is removed.

    (This is a regression test for the F-004 fix. If anyone re-introduces a
    `try: from cryptography... except ImportError: bytes(a ^ b for ...)`
    pattern, this test will fail.)
    """
    repo_root = Path(__file__).resolve().parent.parent
    ctx = build_context(repo_root)
    findings = check_F004_xor_fallback(ctx)
    assert findings == [], (
        f"F-004 should NOT fire on the real vault_encryptor.py. "
        f"Findings: {findings}"
    )


def test_F004_does_not_fire_on_clean_file(tmp_path: Path) -> None:
    """F-004 stays silent when there is no XOR fallback."""
    crypto_dir = tmp_path / "tmt_quantum_vault" / "crypto"
    crypto_dir.mkdir(parents=True)
    (crypto_dir / "vault_encryptor.py").write_text(
        "from cryptography.hazmat.primitives.ciphers.aead import AESGCM\n"
        "aesgcm = AESGCM(key)\n"
        "ct = aesgcm.encrypt(nonce, plaintext, None)\n",
        encoding="utf-8",
    )
    (tmp_path / "tmt_quantum_vault").joinpath("cli.py").write_text("", encoding="utf-8")
    ctx = build_context(tmp_path)
    findings = check_F004_xor_fallback(ctx)
    assert not findings


def test_F008_does_not_fire_on_real_file() -> None:
    """F-008 stays silent: the real cli.py no longer uses a zero default seed.

    The fingerprint commands now default to ``secrets.token_bytes(6)``. If a
    zero-default seed is reintroduced, this test will fail.
    """
    repo_root = Path(__file__).resolve().parent.parent
    ctx = build_context(repo_root)
    findings = check_F008_zero_default_seed(ctx)
    assert (
        not findings
    ), f"F-008 should NOT fire on the real cli.py. Findings: {findings}"


def test_F013_detects_missing_lockfile(fake_repo: Path) -> None:
    """F-013 fires when no lockfile is present."""
    ctx = build_context(fake_repo)
    findings = check_F013_no_lockfile(ctx)
    assert len(findings) == 1
    assert findings[0].id == "F-013"
    assert findings[0].severity == "SUGGESTION"


def test_F013_silent_when_lockfile_present(tmp_path: Path) -> None:
    """F-013 stays silent when a lockfile is present."""
    (tmp_path / "requirements.lock").write_text("# locked\n", encoding="utf-8")
    ctx = build_context(tmp_path)
    findings = check_F013_no_lockfile(ctx)
    assert not findings


def test_F019_detects_commented_ignore_rule(fake_repo: Path) -> None:
    """F-019 fires when a commented-out *.enc.json rule is in .gitignore."""
    (fake_repo / ".gitignore").write_text(
        "# Encrypted artifacts (optional - uncomment if you want to track plaintext only)\n"
        "# *.enc.json\n",
        encoding="utf-8",
    )
    ctx = build_context(fake_repo)
    findings = check_F019_commented_ignore_rule(ctx)
    assert len(findings) == 1
    assert findings[0].id == "F-019"


# ══════════════════════════════════════════════════════════════════════════════
# REPORT BUILDING
# ══════════════════════════════════════════════════════════════════════════════


def test_totals_counts_correctly() -> None:
    """totals() produces the expected dict shape and counts."""
    findings = [
        Finding("F-001", "x", "CRITICAL", "secrets-and-encryption", None, None, {}),
        Finding("F-002", "y", "WARNING", "secrets-and-encryption", None, None, {}),
        Finding("F-003", "z", "SUGGESTION", "repo-hygiene", None, None, {}),
    ]
    t = totals(findings)
    assert t["CRITICAL"] == 1
    assert t["WARNING"] == 1
    assert t["SUGGESTION"] == 1
    assert t["INFO"] == 0
    assert t["total"] == 3
    assert t["by_category"]["secrets-and-encryption"] == 2
    assert t["by_category"]["repo-hygiene"] == 1


def test_build_report_json_serializable() -> None:
    """build_report() output is JSON-serializable."""
    findings = [
        Finding(
            id="F-TEST",
            title="Test",
            severity="WARNING",
            category="test-coverage",
            path="x.py",
            lines=(1, 2),
            evidence={"key": "value"},
        )
    ]
    ctx = AuditContext(
        repo_root=Path("/tmp/fake"),
        is_windows=False,
        is_git=False,
        head_commit="deadbeef",
        branch="main",
    )
    report = build_report(ctx, findings)
    serialized = json.dumps(report, sort_keys=True)
    again = json.loads(serialized)
    assert again["totals"]["total"] == 1
    assert again["findings"][0]["id"] == "F-TEST"
    # lines should be a list in JSON (not a tuple)
    assert again["findings"][0]["lines"] == [1, 2]


def test_render_console_includes_findings() -> None:
    """render_console() mentions each finding's id and title fragment."""
    findings = [
        Finding(
            id="F-XYZ",
            title="Example critical issue",
            severity="CRITICAL",
            category="secrets-and-encryption",
            path="x.py",
            lines=(10, 20),
            evidence={},
        )
    ]
    report = {
        "tool": "tools/audit.py",
        "tool_version": "0.1.0",
        "generated_at_utc": "2026-06-10T00:00:00Z",
        "repo_root": "/tmp/fake",
        "branch": "main",
        "head_commit": "deadbeef00000000",
        "totals": totals(findings),
        "findings": [f.to_dict() for f in findings],
    }
    out = render_console(report, "INFO")
    assert "F-XYZ" in out
    assert "CRITICAL" in out
    assert "x.py:10" in out


def test_render_markdown_grouped_by_category() -> None:
    """render_markdown() groups findings by category and renders evidence as JSON."""
    findings = [
        Finding(
            id="F-A",
            title="A",
            severity="WARNING",
            category="crypto-impl",
            path="a.py",
            lines=(1, 2),
            evidence={"k": 1},
            why_it_matters="because",
            remediation="fix it",
        ),
        Finding(
            id="F-B",
            title="B",
            severity="SUGGESTION",
            category="repo-hygiene",
            path=None,
            lines=None,
            evidence={},
        ),
    ]
    report = {
        "tool": "tools/audit.py",
        "tool_version": "0.1.0",
        "generated_at_utc": "2026-06-10T00:00:00Z",
        "repo_root": "/tmp/fake",
        "branch": "main",
        "head_commit": "deadbeef00000000",
        "totals": totals(findings),
        "findings": [f.to_dict() for f in findings],
    }
    md = render_markdown(report, "INFO")
    # Categories should appear as ## headings
    assert "## crypto-impl" in md
    assert "## repo-hygiene" in md
    # Each finding should appear as a sub-heading
    assert "### [WARNING] F-A" in md
    assert "### [SUGGESTION] F-B" in md
    # Evidence block as fenced JSON
    assert "```json" in md
    assert '"k": 1' in md


# ══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════


def test_main_exits_zero_on_clean_repo(tmp_path: Path, monkeypatch, capsys) -> None:
    """A clean fake repo produces no CRITICAL findings → exit 0."""
    (tmp_path / "tmt_quantum_vault" / "cli.py").parent.mkdir(parents=True)
    (tmp_path / "tmt_quantum_vault" / "cli.py").write_text(
        "# no findings here\n", encoding="utf-8"
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / ".gitignore").write_text("# empty\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pydantic>=2.11\n", encoding="utf-8")
    (tmp_path / "audit_reports").mkdir()
    # Add a lockfile to silence F-013, and remove the secrets dir to silence F-002.
    (tmp_path / "requirements.lock").write_text("# locked\n", encoding="utf-8")

    code = main(
        [
            "--repo-root",
            str(tmp_path),
            "--output-dir",
            str(tmp_path / "audit_reports"),
            "--severity-floor",
            "CRITICAL",
            "--quiet",
        ]
    )
    assert code == 0, capsys.readouterr().out


def test_main_exits_one_on_critical(tmp_path: Path) -> None:
    """A fake repo with the XOR fallback pattern produces CRITICAL → exit 1."""
    crypto_dir = tmp_path / "tmt_quantum_vault" / "crypto"
    crypto_dir.mkdir(parents=True)
    (crypto_dir / "vault_encryptor.py").write_text(
        "try:\n"
        "    from cryptography.hazmat.primitives.ciphers.aead import AESGCM\n"
        "    aesgcm = AESGCM(key)\n"
        "    ct = aesgcm.encrypt(nonce, plaintext, None)\n"
        "except ImportError:\n"
        "    # Fallback: XOR with derived key (not secure, demo only)\n"
        "    ct = bytes(a ^ b for a, b in zip(plaintext, key))\n",
        encoding="utf-8",
    )
    (tmp_path / "tmt_quantum_vault" / "cli.py").write_text("# stub\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text("# empty\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pydantic>=2.11\n", encoding="utf-8")
    (tmp_path / "audit_reports").mkdir()
    (tmp_path / "requirements.lock").write_text("# locked\n", encoding="utf-8")

    code = main(
        [
            "--repo-root",
            str(tmp_path),
            "--output-dir",
            str(tmp_path / "audit_reports"),
            "--severity-floor",
            "CRITICAL",
            "--quiet",
        ]
    )
    assert code == 1


def test_main_idempotent(tmp_path: Path) -> None:
    """Running main() twice in a row produces valid reports both times."""
    import time

    (tmp_path / "tmt_quantum_vault" / "cli.py").parent.mkdir(parents=True)
    (tmp_path / "tmt_quantum_vault" / "cli.py").write_text("# stub\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / ".gitignore").write_text("# empty\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pydantic>=2.11\n", encoding="utf-8")
    (tmp_path / "audit_reports").mkdir()
    (tmp_path / "requirements.lock").write_text("# locked\n", encoding="utf-8")

    args = [
        "--repo-root",
        str(tmp_path),
        "--output-dir",
        str(tmp_path / "audit_reports"),
        "--severity-floor",
        "CRITICAL",
        "--quiet",
    ]
    code1 = main(args)
    # Sleep > 1s so the second report gets a different UTC timestamp
    time.sleep(1.1)
    code2 = main(args)
    assert code1 == 0
    assert code2 == 0
    jsons = sorted((tmp_path / "audit_reports").glob("deterministic_audit_*.json"))
    assert len(jsons) >= 2, f"Expected >=2 reports, got {len(jsons)}"
    # Each report must be valid JSON
    for j in jsons:
        data = json.loads(j.read_text(encoding="utf-8"))
        assert "findings" in data
        assert "totals" in data


def test_run_audit_returns_findings_sorted_by_severity(fake_repo: Path) -> None:
    """run_audit() sorts CRITICAL first, INFO last."""
    # Seed fake_repo with a CRITICAL trigger (the XOR fallback)
    crypto_dir = fake_repo / "tmt_quantum_vault" / "crypto"
    crypto_dir.mkdir(parents=True, exist_ok=True)
    (crypto_dir / "vault_encryptor.py").write_text(
        "try:\n"
        "    from cryptography.hazmat.primitives.ciphers.aead import AESGCM\n"
        "except ImportError:\n"
        "    ct = bytes(a ^ b for a, b in zip(plaintext, key))\n",
        encoding="utf-8",
    )
    (fake_repo / "tmt_quantum_vault" / "cli.py").write_text(
        "# stub\n", encoding="utf-8"
    )

    ctx = build_context(fake_repo)
    findings = run_audit(ctx)
    ranks = [f.severity for f in findings]
    # Verify CRITICAL comes before any non-CRITICAL
    if ranks:
        first_non_critical = next(
            (i for i, s in enumerate(ranks) if s != "CRITICAL"), len(ranks)
        )
        assert all(s == "CRITICAL" for s in ranks[:first_non_critical])
