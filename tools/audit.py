#!/usr/bin/env python3
"""
TMT Quantum Vault — Deterministic Repository Audit
==================================================

A stdlib-only audit script that surfaces 22 specific findings about this
repo's current state. Produces console + JSON + Markdown reports.

Re-runnable, idempotent, exit code 1 if any CRITICAL finding.

NO new pip dependencies. NO imports from tmt_quantum_vault. NO reading of
binary blobs. NO re-implementation of ruff/black/mypy/bandit/safety (CI
already runs them).

Usage:
    python tools/audit.py
    python tools/audit.py --severity-floor WARNING
    python tools/audit.py --repo-root /path/to/repo --output-dir ./reports
    python tools/audit.py --keep 5
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tomllib
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

# Ensure UTF-8 stdout/stderr on Windows so the console summary renders
# the em-dash and other Unicode used in the report correctly.
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (ValueError, OSError):
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (ValueError, OSError):
        pass

# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

TOOL_NAME = "tools/audit.py"
TOOL_VERSION = "0.1.0"
SCHEMA_VERSION = "1.0"

SEVERITY_RANK = {"CRITICAL": 4, "WARNING": 3, "SUGGESTION": 2, "INFO": 1}
SEVERITIES = ("CRITICAL", "WARNING", "SUGGESTION", "INFO")

# Directories to never recurse into. Mirrors the spirit of docs/secret-scanning-policy.md.
EXCLUDED_DIRS = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "env",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "node_modules",
        "__pycache__",
        ".claude",
        "audit_reports",
        "dist",
        "build",
        ".eggs",
        ".tox",
        ".idea",
        ".vscode",
    }
)

# Filenames that signal a dependency lockfile
LOCKFILE_CANDIDATES = (
    "requirements.lock",
    "requirements.in",  # pip-tools pair
    "poetry.lock",
    "uv.lock",
    "Pipfile.lock",
    "pdm.lock",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
)

# Size thresholds for "too large" / "too many" findings
CLI_FILE_LINE_THRESHOLD = 4000
TEST_FILE_LINE_THRESHOLD = 2000
CONSCIOUS_DNA_THRESHOLD = 10


# ══════════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ══════════════════════════════════════════════════════════════════════════════


@dataclass
class Finding:
    """A single audit finding. Shape mirrors the LLM auditor's Finding dataclass."""

    id: str
    title: str
    severity: str  # CRITICAL | WARNING | SUGGESTION | INFO
    category: str
    path: str | None
    lines: tuple[int, int] | None
    evidence: dict[str, Any]
    related_finding_ids: list[str] = field(default_factory=list)
    why_it_matters: str = ""
    remediation: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["lines"] = list(self.lines) if self.lines is not None else None
        return d


@dataclass
class AuditContext:
    """Repository state captured up-front, shared by all checks."""

    repo_root: Path
    is_windows: bool
    is_git: bool
    head_commit: str
    branch: str
    tracked_files: set[str] = field(default_factory=set)
    untracked_files: set[str] = field(default_factory=set)
    ignored_untracked_files: set[str] = field(default_factory=set)
    pyproject: dict[str, Any] = field(default_factory=dict)
    requirements_text: str = ""
    gitignore_text: str = ""


# ══════════════════════════════════════════════════════════════════════════════
# AUDIT CONTEXT BUILDING
# ══════════════════════════════════════════════════════════════════════════════


def _run_git(repo_root: Path, args: list[str]) -> subprocess.CompletedProcess:
    """Run a git command in the repo root. Returns CompletedProcess with stdout text."""
    return subprocess.run(
        ["git", "-C", str(repo_root)] + args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def build_context(repo_root: Path) -> AuditContext:
    """Build an AuditContext by querying git and reading config files."""
    ctx = AuditContext(
        repo_root=repo_root,
        is_windows=os.name == "nt",
        is_git=(repo_root / ".git").exists(),
        head_commit="unknown",
        branch="unknown",
    )

    if ctx.is_git:
        head = _run_git(repo_root, ["rev-parse", "HEAD"])
        if head.returncode == 0:
            ctx.head_commit = head.stdout.strip() or "unknown"
        branch = _run_git(repo_root, ["rev-parse", "--abbrev-ref", "HEAD"])
        if branch.returncode == 0:
            ctx.branch = branch.stdout.strip() or "unknown"

        tracked = _run_git(repo_root, ["ls-files"])
        if tracked.returncode == 0:
            ctx.tracked_files = {
                line.strip() for line in tracked.stdout.splitlines() if line.strip()
            }

        untracked = _run_git(repo_root, ["ls-files", "--others", "--exclude-standard"])
        if untracked.returncode == 0:
            ctx.untracked_files = {
                line.strip() for line in untracked.stdout.splitlines() if line.strip()
            }

        ignored_untracked = _run_git(
            repo_root, ["ls-files", "--others", "--ignored", "--exclude-standard"]
        )
        if ignored_untracked.returncode == 0:
            ctx.ignored_untracked_files = {
                line.strip()
                for line in ignored_untracked.stdout.splitlines()
                if line.strip()
            }

    # Read config files (best-effort, tolerate absence)
    req_path = repo_root / "requirements.txt"
    if req_path.is_file():
        ctx.requirements_text = req_path.read_text(encoding="utf-8", errors="replace")

    pp_path = repo_root / "pyproject.toml"
    if pp_path.is_file():
        try:
            ctx.pyproject = tomllib.loads(pp_path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            ctx.pyproject = {}

    gi_path = repo_root / ".gitignore"
    if gi_path.is_file():
        ctx.gitignore_text = gi_path.read_text(encoding="utf-8", errors="replace")

    return ctx


# ══════════════════════════════════════════════════════════════════════════════
# UTILITIES
# ══════════════════════════════════════════════════════════════════════════════


def is_excluded(path: Path) -> bool:
    """True if any part of the path is in EXCLUDED_DIRS."""
    return any(part in EXCLUDED_DIRS for part in path.parts)


def relative(p: Path, ctx: AuditContext) -> str:
    """Return a forward-slash relative path for display."""
    try:
        return p.resolve().relative_to(ctx.repo_root.resolve()).as_posix()
    except ValueError:
        return str(p)


def sha256_file(p: Path) -> str | None:
    """SHA-256 hex digest of file contents, or None on error."""
    try:
        h = hashlib.sha256()
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def git_check_ignore(p: Path, ctx: AuditContext) -> bool:
    """True if the path is matched by a .gitignore rule."""
    if not ctx.is_git:
        return False
    rel = relative(p, ctx)
    res = _run_git(ctx.repo_root, ["check-ignore", "--", rel])
    return res.returncode == 0


def git_tracked(p: Path, ctx: AuditContext) -> bool:
    """True if the path is tracked in git."""
    return relative(p, ctx) in ctx.tracked_files


def line_count(p: Path) -> int:
    """Count lines in a text file. Returns 0 on error."""
    try:
        with p.open("rb") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


# ══════════════════════════════════════════════════════════════════════════════
# CHECKS
# ══════════════════════════════════════════════════════════════════════════════


# ── F-001 / F-019 — *.enc.json handling ────────────────────────────────────────


def check_F001_untracked_enc_json(ctx: AuditContext) -> list[Finding]:
    """Find *.enc.json files that are present but not gitignored."""
    findings: list[Finding] = []
    for p in ctx.repo_root.rglob("*.enc.json"):
        if is_excluded(p):
            continue
        if git_check_ignore(p, ctx):
            continue
        rel = relative(p, ctx)
        if rel in ctx.untracked_files or rel not in ctx.tracked_files:
            findings.append(
                Finding(
                    id="F-001",
                    title="Untracked encrypted ledger present (*.enc.json ignore is commented out)",
                    severity="CRITICAL",
                    category="gitignore-and-tracking",
                    path=rel,
                    lines=None,
                    evidence={
                        "size_bytes": p.stat().st_size if p.exists() else None,
                        "git_status": "untracked",
                        "ignored": False,
                    },
                    related_finding_ids=["F-002", "F-019"],
                    why_it_matters=(
                        "A `git add .` will commit encrypted material whose decryption "
                        "key is gitignored — the artifact becomes un-decryptable on any "
                        "other clone."
                    ),
                    remediation=(
                        "Either uncomment the `*.enc.json` rule in .gitignore, or "
                        "establish a documented policy for what gets committed and "
                        "use `git rm --cached` on the plaintext sibling."
                    ),
                )
            )
    return findings


def check_F019_commented_ignore_rule(ctx: AuditContext) -> list[Finding]:
    """Flag a commented-out gitignore rule that is a footgun."""
    if not ctx.gitignore_text:
        return []
    findings: list[Finding] = []
    for i, line in enumerate(ctx.gitignore_text.splitlines(), start=1):
        # Commented-out *.enc.json rule
        if re.match(r"^\s*#\s*.*\*\.enc\.json", line):
            findings.append(
                Finding(
                    id="F-019",
                    title="Commented-out ignore rule in .gitignore",
                    severity="INFO",
                    category="gitignore-and-tracking",
                    path=".gitignore",
                    lines=(i, i),
                    evidence={"line": line.rstrip()},
                    related_finding_ids=["F-001"],
                    why_it_matters=(
                        "Commented ignore rules are easy to miss and lose their "
                        "documentary value. Better as a real rule with a justification "
                        "in README."
                    ),
                    remediation=(
                        "Either enable the rule and explain why, or move the rationale "
                        "to docs/secret-scanning-policy.md and delete the commented "
                        "line."
                    ),
                )
            )
    return findings


# ── F-002 / F-005 / F-020 — secret_key.bin ────────────────────────────────────


def _candidate_secret_key_paths(ctx: AuditContext) -> list[Path]:
    """Return the list of paths the audit should scan for secret keys.

    Both the legacy in-repo path and the new default (~/.tmt-vault/keys/)
    are scanned, so a future regression at either location is caught.
    """
    paths: list[Path] = [
        ctx.repo_root / "evidence_ledger" / "secret_key.bin",
    ]
    # New default key directory outside the repo.
    default_dir = Path.home() / ".tmt-vault" / "keys"
    if default_dir.is_dir():
        for child in sorted(default_dir.glob("*.bin")):
            paths.append(child)
    # Also scan for any .bin file dropped inside the repo (the new flow puts
    # them outside, but a buggy custom --key-dir might still leak one in).
    for p in ctx.repo_root.rglob("*.bin"):
        if is_excluded(p):
            continue
        if p.is_file() and p not in paths:
            paths.append(p)
    return paths


def check_F002_secret_key_on_disk(ctx: AuditContext) -> list[Finding]:
    """Detect any secret_key.bin present on disk (in-repo or in ~/.tmt-vault/keys/)."""
    findings: list[Finding] = []
    for p in _candidate_secret_key_paths(ctx):
        if not p.is_file():
            continue
        # Resolve absolute path and check whether it is inside the repo.
        try:
            abs_repo = ctx.repo_root.resolve()
            abs_p = p.resolve()
            in_repo = abs_repo in abs_p.parents or abs_p == abs_repo
        except OSError:
            in_repo = False
        try:
            rel = relative(p, ctx)
        except ValueError:
            rel = str(p)
        # Flag a key as CRITICAL when it sits inside the repo, WARN when it
        # is at the (intended) outside location — this lets a regression
        # where someone re-introduces an in-repo key stay loud.
        severity = "CRITICAL" if in_repo else "WARNING"
        related = ["F-005", "F-020"]
        findings.append(
            Finding(
                id="F-002",
                title=f"ML-KEM-768 secret key present at {rel}",
                severity=severity,
                category="secrets-and-encryption",
                path=rel,
                lines=None,
                evidence={
                    "size_bytes": p.stat().st_size,
                    "ignored": git_check_ignore(p, ctx),
                    "in_repo": in_repo,
                },
                related_finding_ids=related,
                why_it_matters=(
                    "The .gitignore correctly catches this file, but its presence "
                    "on disk with default ACLs means anyone with read access to "
                    "the user account can decrypt the entire ledger."
                ),
                remediation=(
                    "Store secret keys in ~/.tmt-vault/keys/ (the default for "
                    "tmt-vault encrypt-ledger). Restrict permissions with "
                    "chmod 600 (POSIX) or icacls (Windows)."
                ),
            )
        )
    return findings


def check_F005_no_chmod_on_secret_key_write(ctx: AuditContext) -> list[Finding]:
    """Scan cli.py for write_bytes(sk) without adjacent permission tightening."""
    cli = ctx.repo_root / "tmt_quantum_vault" / "cli.py"
    if not cli.is_file():
        return []
    try:
        src = cli.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    findings: list[Finding] = []
    # Find every write_bytes(sk) / write_bytes(secret_key) call site.
    pattern = re.compile(
        r"(sk_path|key_path|secret_key_path)\s*\.\s*write_bytes\s*\(",
        re.MULTILINE,
    )
    for m in pattern.finditer(src):
        line_no = src[: m.start()].count("\n") + 1
        # Look at a 1000-char window for permission tightening. This is
        # wide enough to catch a helper function call like
        # `_harden_secret_key_permissions(sk_path)` on the line right after
        # the write.
        window_start = max(0, m.start() - 500)
        window_end = min(len(src), m.end() + 1000)
        window = src[window_start:window_end].lower()
        tightens = (
            "os.chmod" in window
            or "icacls" in window
            or "win32_set_file_permissions" in window
            or "_harden" in window
            or "_restrict_perm" in window
            or "set_ownership_and_perm" in window
        )
        if tightens:
            continue
        findings.append(
            Finding(
                id="F-005",
                title="secret_key.bin written without permission tightening",
                severity="WARNING",
                category="cli-hygiene",
                path=relative(cli, ctx),
                lines=(line_no, line_no),
                evidence={"snippet": m.group(0)},
                related_finding_ids=["F-002", "F-020"],
                why_it_matters=(
                    "On POSIX, default umask 0o022 leaves the file group/world "
                    "readable. On Windows the file inherits the parent directory's "
                    "ACL, which may include the Users group."
                ),
                remediation=(
                    "After write_bytes(sk), call os.chmod(path, 0o600) on POSIX and "
                    "use win32 security descriptors (or icacls) on Windows."
                ),
            )
        )
    return findings


def check_F020_secret_key_mode(ctx: AuditContext) -> list[Finding]:
    """Check existing secret_key.bin file mode on POSIX (any *.bin in candidate paths).

    On Windows, POSIX mode bits are not honored (ACLs are used instead), so
    F-020 is skipped there — the hardening is done via icacls at write time.
    """
    if ctx.is_windows:
        return []
    findings: list[Finding] = []
    for p in _candidate_secret_key_paths(ctx):
        if not p.is_file():
            continue
        st = p.stat()
        mode = st.st_mode & 0o777
        if not (mode & 0o044):  # not group/other readable
            continue
        try:
            rel = relative(p, ctx)
        except ValueError:
            rel = str(p)
        findings.append(
            Finding(
                id="F-020",
                title=f"Secret key is group/other readable ({rel})",
                severity="WARNING",
                category="secrets-and-encryption",
                path=rel,
                lines=None,
                evidence={"mode_octal": oct(mode), "size_bytes": st.st_size},
                related_finding_ids=["F-002", "F-005"],
                why_it_matters=(
                    "Other users on the same host can read the key. On a shared "
                    "CI runner this is a real risk."
                ),
                remediation=(
                    "chmod 600 on the .bin file (and 0o700 on the directory). "
                    "On Windows, use icacls to remove inheritance and grant the "
                    "current user Full only."
                ),
            )
        )
    return findings


# ── F-003 — duplicate plaintext ───────────────────────────────────────────────


def check_F003_plaintext_decrypted_duplicate(ctx: AuditContext) -> list[Finding]:
    """Check if tracked plaintext matches an untracked .decrypted.json."""
    findings: list[Finding] = []
    for tracked in ctx.tracked_files:
        p = ctx.repo_root / tracked
        if not p.is_file():
            continue
        if not tracked.endswith(".json"):
            continue
        sibling = tracked.replace(".json", ".decrypted.json")
        if sibling in ctx.untracked_files:
            q = ctx.repo_root / sibling
            if not q.is_file():
                continue
            h1 = sha256_file(p)
            h2 = sha256_file(q)
            if h1 is None or h2 is None:
                continue
            if h1 == h2:
                findings.append(
                    Finding(
                        id="F-003",
                        title="Tracked plaintext and untracked .decrypted.json are byte-identical",
                        severity="WARNING",
                        category="secrets-and-encryption",
                        path=tracked,
                        lines=None,
                        evidence={
                            "tracked_sha256": h1,
                            "decrypted_sibling": sibling,
                            "decrypted_sha256": h2,
                            "size_bytes": p.stat().st_size,
                        },
                        related_finding_ids=["F-001", "F-002"],
                        why_it_matters=(
                            "Two byte-identical files in the working tree, one tracked "
                            "and one untracked, is a confused-deputy situation: which is "
                            "the source of truth?"
                        ),
                        remediation=(
                            "Decide which is authoritative, delete or rename the "
                            "duplicate, and document the encryption workflow in "
                            "README."
                        ),
                    )
                )
    return findings


# ── F-004 — XOR fallback in crypto ───────────────────────────────────────────


def check_F004_xor_fallback(ctx: AuditContext) -> list[Finding]:
    """Detect `try: ... except ImportError: XOR ...` fallback in vault_encryptor.py."""
    p = ctx.repo_root / "tmt_quantum_vault" / "crypto" / "vault_encryptor.py"
    if not p.is_file():
        return []
    try:
        src = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    # Find try/except ImportError blocks that fall back to XOR
    findings: list[Finding] = []
    # Match: try: <anything with cryptography> ... except ImportError: <anything with ^ or xor>
    pattern = re.compile(
        r"try:\s*\n"
        r"\s*from\s+cryptography[\s\S]*?"
        r"except\s+ImportError[\s\S]*?"
        r"bytes\(\s*a\s*\^\s*b\s+for\b",
        re.MULTILINE,
    )
    for m in pattern.finditer(src):
        line_no = src[: m.start()].count("\n") + 1
        findings.append(
            Finding(
                id="F-004",
                title="Silent crypto downgrade: AES-GCM falls back to XOR when `cryptography` is missing",
                severity="CRITICAL",
                category="crypto-impl",
                path=relative(p, ctx),
                lines=(line_no, line_no + src[m.start() : m.end()].count("\n")),
                evidence={"snippet_excerpt": src[m.start() : m.end()].splitlines()[0]},
                related_finding_ids=["F-005", "F-011", "F-012"],
                why_it_matters=(
                    "If `cryptography` fails to install (broken wheel, musl alpine, "
                    "offline), the fallback uses XOR with a derived key — trivially "
                    "breakable. The higher-level AESGCMEncryptor correctly raises, so "
                    "the failure is inconsistent across the module: an artifact "
                    "encrypted on a no-cryptography host is unreadable elsewhere."
                ),
                remediation=(
                    "Remove the XOR fallback. Raise ImportError with an actionable "
                    "message: 'pip install cryptography>=42.0 is required for "
                    "evidence-ledger encryption'."
                ),
            )
        )
    return findings


# ── F-006 — decrypt-ledger lacks preflight ────────────────────────────────────


def check_F006_decrypt_no_key_validation(ctx: AuditContext) -> list[Finding]:
    """Check that decrypt-ledger has key length validation and clear error path."""
    cli = ctx.repo_root / "tmt_quantum_vault" / "cli.py"
    if not cli.is_file():
        return []
    try:
        src = cli.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    # Find decrypt-ledger function and look for length/constant-time checks
    m = re.search(
        r"def\s+decrypt_ledger\s*\([^)]*\)\s*->\s*None:\s*\"\"\".*?\"\"\"([\s\S]*?)(?=\n@app\.command|\ndef\s+\w+\(|\Z)",
        src,
        re.DOTALL,
    )
    if not m:
        return []
    body = m.group(1)
    if "len(secret_key)" in body or "hmac.compare_digest" in body:
        return []

    line_no = src[: m.start()].count("\n") + 1
    return [
        Finding(
            id="F-006",
            title="decrypt-ledger lacks key-length preflight and clear 'wrong key' error",
            severity="WARNING",
            category="cli-hygiene",
            path=relative(cli, ctx),
            lines=(line_no, line_no + body.count("\n")),
            evidence={"missing_checks": ["len(secret_key) == 64", "hmac.compare_digest"]},
            related_finding_ids=["F-004"],
            why_it_matters=(
                "If the user passes the wrong key, AEAD authentication raises a raw "
                "stack trace (~200 chars). A clear 'Wrong key — authentication "
                "failed' message is friendlier and prevents users from sharing "
                "stack traces in public issues."
            ),
            remediation=(
                "Before calling decrypt_file, check `len(secret_key) == 64` and "
                "wrap decrypt_file in try/except that maps the AEAD tag-mismatch to "
                "a friendly error."
            ),
        )
    ]


# ── F-007 — private method from CLI ───────────────────────────────────────────


def check_F007_private_method_from_cli(ctx: AuditContext) -> list[Finding]:
    """Flag `generator._<name>(` calls in cli.py (private API access)."""
    cli = ctx.repo_root / "tmt_quantum_vault" / "cli.py"
    if not cli.is_file():
        return []
    try:
        src = cli.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    findings: list[Finding] = []
    pattern = re.compile(r"\b\w+\._\w+\s*\(", re.MULTILINE)
    for m in pattern.finditer(src):
        if m.group(0).startswith("_"):  # dunder, skip
            continue
        line_no = src[: m.start()].count("\n") + 1
        findings.append(
            Finding(
                id="F-007",
                title="CLI reaches into a private (underscore-prefixed) method",
                severity="SUGGESTION",
                category="cli-hygiene",
                path=relative(cli, ctx),
                lines=(line_no, line_no),
                evidence={"call": m.group(0)},
                related_finding_ids=[],
                why_it_matters=(
                    "The leading underscore is a contract: the method is not part of "
                    "the public API. Bypassing it means refactoring the generator "
                    "silently breaks the CLI."
                ),
                remediation=(
                    "Rename to a public method (`load_qrng_seed`) or expose a "
                    "thin wrapper on the generator."
                ),
            )
        )
    return findings


# ── F-008 — zero default seed ─────────────────────────────────────────────────


def check_F008_zero_default_seed(ctx: AuditContext) -> list[Finding]:
    """Detect typer.Option with default='000000000000' in fingerprint/circuit commands."""
    cli = ctx.repo_root / "tmt_quantum_vault" / "cli.py"
    if not cli.is_file():
        return []
    try:
        src = cli.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    findings: list[Finding] = []
    pattern = re.compile(
        r'typer\.Option\s*\(\s*[\'"]000000000000[\'"]\s*[,)]', re.MULTILINE
    )
    for m in pattern.finditer(src):
        line_no = src[: m.start()].count("\n") + 1
        findings.append(
            Finding(
                id="F-008",
                title="Default seed is all zeros — fingerprints collide across users",
                severity="WARNING",
                category="crypto-impl",
                path=relative(cli, ctx),
                lines=(line_no, line_no),
                evidence={"default": "000000000000"},
                related_finding_ids=["F-007", "F-012"],
                why_it_matters=(
                    "A 'fingerprint' that is not unique is not a fingerprint. Every "
                    "user running the command without --seed gets the same output, "
                    "breaking the threat model in the README."
                ),
                remediation=(
                    "Default the seed to secrets.token_bytes(6).hex() so each "
                    "invocation is unique; require --seed only for reproducibility."
                ),
            )
        )
    return findings


# ── F-009 — symlink to absolute user path ─────────────────────────────────────


def check_F009_absolute_path_symlink(ctx: AuditContext) -> list[Finding]:
    """Detect symlinks whose targets contain an absolute user home path."""
    findings: list[Finding] = []
    for p in ctx.repo_root.rglob("*"):
        if is_excluded(p):
            continue
        if not p.is_symlink():
            continue
        try:
            target = os.readlink(str(p))
        except OSError:
            continue
        is_abs = os.path.isabs(target)
        has_user_path = (
            "/Users/" in target
            or "\\Users\\" in target
            or "/home/" in target
            or "C:\\" in target
        )
        if is_abs and has_user_path:
            findings.append(
                Finding(
                    id="F-009",
                    title="Symlink points to a user-specific absolute path",
                    severity="WARNING",
                    category="repo-hygiene",
                    path=relative(p, ctx),
                    lines=None,
                    evidence={"target": target, "is_symlink": True},
                    related_finding_ids=[],
                    why_it_matters=(
                        "Privacy leak (Windows username + ollama install fact); "
                        "portability break (the symlink will not resolve on any "
                        "other machine)."
                    ),
                    remediation=(
                        "Replace the symlink with a real file or a path-relative "
                        "symlink, and document the model location in README."
                    ),
                )
            )
    return findings


# ── F-010 — tracked-but-also-ignored ──────────────────────────────────────────


def check_F010_tracked_but_gitignored(ctx: AuditContext) -> list[Finding]:
    """Find files that are tracked AND matched by a gitignore rule."""
    if not ctx.is_git:
        return []
    findings: list[Finding] = []
    # Only check root-level files (the issue is at the top of .gitignore)
    for tracked in sorted(ctx.tracked_files):
        if "/" in tracked:
            continue
        if not (ctx.repo_root / tracked).is_file():
            continue
        res = _run_git(ctx.repo_root, ["check-ignore", "--", tracked])
        if res.returncode == 0:
            findings.append(
                Finding(
                    id="F-010",
                    title=f"Tracked file is also matched by .gitignore ({tracked})",
                    severity="SUGGESTION",
                    category="gitignore-and-tracking",
                    path=tracked,
                    lines=None,
                    evidence={"ignore_rule": res.stdout.strip()},
                    related_finding_ids=[],
                    why_it_matters=(
                        "The gitignore rule is dead (the file is already in the "
                        "index) and confuses new contributors. `git rm --cached` "
                        "would let the rule take effect."
                    ),
                    remediation=(
                        f"`git rm --cached {tracked}` and commit. The file will "
                        "still exist locally but no longer be tracked."
                    ),
                )
            )
    return findings


# ── F-011 — qiskit-ibm-runtime mismatch ───────────────────────────────────────


def check_F011_qiskit_ibm_runtime_mismatch(ctx: AuditContext) -> list[Finding]:
    """Check that pyproject.toml runtime optional deps match requirements.txt; flag missing or unbounded.

    Dev-tooling groups (e.g. `dev`) are exempt from the "missing from requirements.txt" check
    because they legitimately live in a dev manifest. We still flag their unbounded specs.
    """
    findings: list[Finding] = []
    if not ctx.pyproject:
        return findings

    opt = ctx.pyproject.get("project", {}).get("optional-dependencies", {})
    reqs_lower = ctx.requirements_text.lower()

    for group_name, group_deps in opt.items():
        is_dev_group = group_name in {"dev", "dev-tools", "lint", "test", "tests"}
        for dep in group_deps:
            # dep is a string like "qiskit-ibm-runtime>=0.20"
            m = re.match(r"^([A-Za-z0-9_.\-]+)\s*([<>=!~].*)?$", dep.strip())
            if not m:
                continue
            name = m.group(1)
            spec = (m.group(2) or "").strip()
            # Normalize: qiskit-ibm-runtime vs qiskit-ibm-runtime[...]
            if not is_dev_group and name.lower() not in reqs_lower:
                findings.append(
                    Finding(
                        id="F-011",
                        title=f"Optional dep `{name}` declared in pyproject.toml but absent from requirements.txt",
                        severity="WARNING",
                        category="reproducibility",
                        path="pyproject.toml",
                        lines=None,
                        evidence={
                            "optional_group": group_name,
                            "spec": spec,
                        },
                        related_finding_ids=["F-013"],
                        why_it_matters=(
                            "Either the optional group is dead code (nothing "
                            "installs it) or requirements.txt is the de-facto "
                            "source of truth and is silently diverging. Both are "
                            "supply-chain risk."
                        ),
                        remediation=(
                            f"Either add `{name}` to requirements.txt, or move the "
                            f"dep out of optional-dependencies if it is unused."
                        ),
                    )
                )
            # Check upper bound (always flag, including for dev groups)
            if spec and not re.search(r"<", spec) and not spec.startswith("=="):
                findings.append(
                    Finding(
                        id="F-011",
                        title=f"`{name}` spec `{spec}` has no upper bound",
                        severity="SUGGESTION",
                        category="reproducibility",
                        path="pyproject.toml",
                        lines=None,
                        evidence={"spec": spec, "optional_group": group_name},
                        related_finding_ids=["F-013"],
                        why_it_matters=(
                            "Unbounded ranges allow any future major; combined "
                            "with no lockfile, this makes supply-chain incidents "
                            "harder to bisect."
                        ),
                        remediation=(
                            f"Pin `{name}` to a known-good range, e.g. "
                            f"`{name}>=0.20,<1.0`."
                        ),
                    )
                )
    return findings


# ── F-012 — zero tests for new modules ────────────────────────────────────────


def check_F012_no_tests_for_new_modules(ctx: AuditContext) -> list[Finding]:
    """Confirm that no test file imports tmt_quantum_vault.crypto or .circuits."""
    tests_dir = ctx.repo_root / "tests"
    if not tests_dir.is_dir():
        return [
            Finding(
                id="F-012",
                title="No tests/ directory found (cannot verify coverage of new modules)",
                severity="WARNING",
                category="test-coverage",
                path="tests/",
                lines=None,
                evidence={"missing": ["tmt_quantum_vault.crypto", "tmt_quantum_vault.circuits"]},
                related_finding_ids=["F-004"],
                why_it_matters=(
                    "1,181 LOC of crypto-adjacent code merged without a regression net."
                ),
                remediation=(
                    "Add tests/test_crypto_vault_encryptor.py and "
                    "tests/test_circuits_merkaba_fingerprint.py with smoke tests."
                ),
            )
        ]

    all_test_text = ""
    for p in tests_dir.rglob("test_*.py"):
        if is_excluded(p):
            continue
        try:
            all_test_text += p.read_text(encoding="utf-8", errors="replace") + "\n"
        except OSError:
            continue

    missing: list[str] = []
    for needle in [
        "tmt_quantum_vault.crypto",
        "tmt_quantum_vault.circuits",
        "MerkabaFingerprintGenerator",
        "VaultEncryptor",
        "VaultDecryptor",
        "encrypt-ledger",
        "decrypt-ledger",
        "generate-fingerprint",
        "merkaba-circuit",
    ]:
        if needle not in all_test_text:
            missing.append(needle)

    if not missing:
        return []
    return [
        Finding(
            id="F-012",
            title="New modules and CLI commands have no direct test coverage",
            severity="WARNING",
            category="test-coverage",
            path="tests/",
            lines=None,
            evidence={"missing_references": missing},
            related_finding_ids=["F-004"],
            why_it_matters=(
                "1,181 LOC of crypto-adjacent code (4 untracked modules + 4 new "
                "CLI commands) merged with zero direct tests. The XOR fallback "
                "(F-004) would have been caught by a smoke test."
            ),
            remediation=(
                "Add tests/test_crypto_vault_encryptor.py and "
                "tests/test_circuits_merkaba_fingerprint.py."
            ),
        )
    ]


# ── F-013 — no lockfile ──────────────────────────────────────────────────────


def check_F013_no_lockfile(ctx: AuditContext) -> list[Finding]:
    """Confirm no dependency lockfile is present."""
    present = [name for name in LOCKFILE_CANDIDATES if (ctx.repo_root / name).is_file()]
    if present:
        return []
    return [
        Finding(
            id="F-013",
            title="No dependency lockfile present",
            severity="SUGGESTION",
            category="reproducibility",
            path=None,
            lines=None,
            evidence={"checked": list(LOCKFILE_CANDIDATES)},
            related_finding_ids=["F-011"],
            why_it_matters=(
                "Reproducible builds and CVE bisection both require a lockfile. "
                "requirements.txt is the source of truth and uses unbounded "
                ">=X,<Y ranges."
            ),
            remediation=(
                "Adopt pip-tools (`pip-compile` to produce requirements.txt from "
                "requirements.in), or migrate to uv/poetry/pdm."
            ),
        )
    ]


# ── F-014 — too many conscious_dna.json ───────────────────────────────────────


def check_F014_conscious_dna_count(ctx: AuditContext) -> list[Finding]:
    """Count tracked conscious_dna.json files."""
    if not ctx.is_git:
        return []
    matches = [t for t in ctx.tracked_files if t.endswith("conscious_dna.json")]
    if len(matches) <= CONSCIOUS_DNA_THRESHOLD:
        return []
    return [
        Finding(
            id="F-014",
            title=f"{len(matches)} tracked conscious_dna.json artifacts",
            severity="SUGGESTION",
            category="repo-hygiene",
            path=None,
            lines=None,
            evidence={"count": len(matches), "threshold": CONSCIOUS_DNA_THRESHOLD},
            related_finding_ids=[],
            why_it_matters=(
                "These are deterministic output of cli.create_agents; they can be "
                "regenerated from source. Committing them bloats the repo and "
                "makes merges noisy."
            ),
            remediation=(
                "Move the JSON files under a single tracked directory (e.g. "
                "agents/<name>/conscious_dna.json) and add it to .gitignore; "
                "regenerate in CI."
            ),
        )
    ]


# ── F-015 / F-016 — file size thresholds ─────────────────────────────────────


def check_F015_cli_too_large(ctx: AuditContext) -> list[Finding]:
    """Flag tmt_quantum_vault/cli.py if it exceeds the line threshold."""
    cli = ctx.repo_root / "tmt_quantum_vault" / "cli.py"
    if not cli.is_file():
        return []
    n = line_count(cli)
    if n <= CLI_FILE_LINE_THRESHOLD:
        return []
    return [
        Finding(
            id="F-015",
            title=f"tmt_quantum_vault/cli.py is {n} lines (> {CLI_FILE_LINE_THRESHOLD})",
            severity="SUGGESTION",
            category="repo-hygiene",
            path=relative(cli, ctx),
            lines=None,
            evidence={"line_count": n, "threshold": CLI_FILE_LINE_THRESHOLD},
            related_finding_ids=["F-007", "F-008"],
            why_it_matters=(
                "Hard to review PRs that touch this file; high merge-conflict "
                "probability; hidden dead code."
            ),
            remediation=(
                "Split the new crypto/circuit commands into "
                "tmt_quantum_vault/cli_crypto.py and cli_circuits.py and import "
                "their Typer apps into cli.app."
            ),
        )
    ]


def check_F016_regression_test_too_large(ctx: AuditContext) -> list[Finding]:
    """Flag tests/test_regression.py if it is more than 2x the median test file."""
    tests_dir = ctx.repo_root / "tests"
    if not tests_dir.is_dir():
        return []
    sizes: list[tuple[Path, int]] = []
    for p in tests_dir.rglob("test_*.py"):
        if is_excluded(p):
            continue
        n = line_count(p)
        if n > 0:
            sizes.append((p, n))
    if not sizes:
        return []
    median = sorted(n for _, n in sizes)[len(sizes) // 2]
    threshold = max(TEST_FILE_LINE_THRESHOLD, 2 * median)
    for p, n in sizes:
        if n > threshold:
            return [
                Finding(
                    id="F-016",
                    title=f"{relative(p, ctx)} is {n} lines (>{threshold} = 2x median)",
                    severity="SUGGESTION",
                    category="repo-hygiene",
                    path=relative(p, ctx),
                    lines=None,
                    evidence={"line_count": n, "median": median, "threshold": threshold},
                    related_finding_ids=[],
                    why_it_matters=(
                        "Single regression file likely contains disabled/slow/"
                        "integration tests mingled with unit tests, hiding "
                        "real coverage gaps."
                    ),
                    remediation=(
                        "Split into tests/test_<dimension>.py files (e.g. "
                        "test_cli_crypto.py, test_circuits_fingerprint.py) and "
                        "mark slow/integration tests with @pytest.mark.slow."
                    ),
                )
            ]
    return []


# ── F-017 — untracked package subdirs ─────────────────────────────────────────


def check_F017_untracked_package_subdir(ctx: AuditContext) -> list[Finding]:
    """Flag tmt_quantum_vault subdirs that are entirely untracked but imported."""
    if not ctx.is_git:
        return []
    findings: list[Finding] = []
    pkg = ctx.repo_root / "tmt_quantum_vault"
    if not pkg.is_dir():
        return findings

    cli = pkg / "cli.py"
    cli_text = ""
    if cli.is_file():
        try:
            cli_text = cli.read_text(encoding="utf-8", errors="replace")
        except OSError:
            cli_text = ""

    for sub in sorted(pkg.iterdir()):
        if not sub.is_dir() or is_excluded(sub):
            continue
        if sub.name.startswith("__") or sub.name.startswith("."):
            continue
        if sub.name in ("orchestration",):  # known-tracked, skip
            continue
        # Check if anything in this subdir is tracked
        tracked_in_sub = any(
            str(sub.relative_to(ctx.repo_root)) in t
            or t.startswith(str(sub.relative_to(ctx.repo_root)) + "/")
            for t in ctx.tracked_files
        )
        if tracked_in_sub:
            continue
        # Check if cli.py imports from this subdir
        import_pattern = f"tmt_quantum_vault.{sub.name}"
        if import_pattern in cli_text or f".{sub.name}" in cli_text:
            findings.append(
                Finding(
                    id="F-017",
                    title=f"Package subdirectory `{sub.name}/` is untracked but imported",
                    severity="SUGGESTION",
                    category="gitignore-and-tracking",
                    path=relative(sub, ctx),
                    lines=None,
                    evidence={"imported_in": "tmt_quantum_vault/cli.py"},
                    related_finding_ids=["F-001", "F-012"],
                    why_it_matters=(
                        "Fresh clone cannot run the CLI without these subdirs; "
                        "they are untracked but functionally required."
                    ),
                    remediation=(
                        f"`git add tmt_quantum_vault/{sub.name}/` and commit, "
                        f"or move the import behind a lazy/optional path."
                    ),
                )
            )
    return findings


# ── F-018 — .pkl files tracked ────────────────────────────────────────────────


def check_F018_pkl_tracked(ctx: AuditContext) -> list[Finding]:
    """Surface tracked .pkl files (pickle deserialization surface area)."""
    if not ctx.is_git:
        return []
    pkls = sorted(t for t in ctx.tracked_files if t.endswith(".pkl"))
    if not pkls:
        return []
    return [
        Finding(
            id="F-018",
            title=f"{len(pkls)} .pkl file(s) tracked (pickle surface area)",
            severity="INFO",
            category="repo-hygiene",
            path=None,
            lines=None,
            evidence={"files": pkls},
            related_finding_ids=[],
            why_it_matters=(
                "No code in tmt_quantum_vault/ imports pickle today, so this is "
                "latent risk: a future `pickle.load(open(.pkl))` will execute "
                "arbitrary code from a tracked artifact."
            ),
            remediation=(
                "Replace .pkl with .json.gz (already present alongside) or "
                ".safetensors; or document explicitly that these files must be "
                "regenerated, never loaded from untrusted sources."
            ),
        )
    ]


# ── F-021 — no tmt-vault audit subcommand ─────────────────────────────────────


def check_F021_no_audit_subcommand(ctx: AuditContext) -> list[Finding]:
    """Note that the audit is not exposed as a CLI subcommand."""
    cli = ctx.repo_root / "tmt_quantum_vault" / "cli.py"
    if not cli.is_file():
        return []
    try:
        src = cli.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    if "@app.command(\"audit\")" in src or "@app.command('audit')" in src:
        return []
    return [
        Finding(
            id="F-021",
            title="No `tmt-vault audit` subcommand; tools/audit.py is standalone",
            severity="INFO",
            category="cli-hygiene",
            path="tmt_quantum_vault/cli.py",
            lines=None,
            evidence={},
            related_finding_ids=[],
            why_it_matters=(
                "Discoverability. The audit is invisible to anyone who only "
                "interacts with the package via its CLI."
            ),
            remediation=(
                "Consider wrapping tools/audit.py as a tmt-vault audit "
                "subcommand in a follow-up PR."
            ),
        )
    ]


# ── F-022 — no Makefile / tox.ini ─────────────────────────────────────────────


def check_F022_no_makefile(ctx: AuditContext) -> list[Finding]:
    """Note absence of Makefile or tox.ini for local audit runs."""
    if (ctx.repo_root / "Makefile").is_file() or (ctx.repo_root / "tox.ini").is_file():
        return []
    return [
        Finding(
            id="F-022",
            title="No Makefile or tox.ini for local `make audit` runs",
            severity="INFO",
            category="repo-hygiene",
            path=None,
            lines=None,
            evidence={},
            related_finding_ids=[],
            why_it_matters=(
                "CI is the only way to run the full matrix. A `make audit` "
                "target lowers the barrier for local runs."
            ),
            remediation=(
                "Add a 5-line Makefile with `audit: ; python tools/audit.py`."
            ),
        )
    ]


# ══════════════════════════════════════════════════════════════════════════════
# CHECK REGISTRY
# ══════════════════════════════════════════════════════════════════════════════


CHECK_REGISTRY: list[Callable[[AuditContext], list[Finding]]] = [
    check_F001_untracked_enc_json,
    check_F002_secret_key_on_disk,
    check_F003_plaintext_decrypted_duplicate,
    check_F004_xor_fallback,
    check_F005_no_chmod_on_secret_key_write,
    check_F006_decrypt_no_key_validation,
    check_F007_private_method_from_cli,
    check_F008_zero_default_seed,
    check_F009_absolute_path_symlink,
    check_F010_tracked_but_gitignored,
    check_F011_qiskit_ibm_runtime_mismatch,
    check_F012_no_tests_for_new_modules,
    check_F013_no_lockfile,
    check_F014_conscious_dna_count,
    check_F015_cli_too_large,
    check_F016_regression_test_too_large,
    check_F017_untracked_package_subdir,
    check_F018_pkl_tracked,
    check_F019_commented_ignore_rule,
    check_F020_secret_key_mode,
    check_F021_no_audit_subcommand,
    check_F022_no_makefile,
]


# ══════════════════════════════════════════════════════════════════════════════
# REPORT BUILDING
# ══════════════════════════════════════════════════════════════════════════════


def run_audit(ctx: AuditContext) -> list[Finding]:
    """Run every registered check and return the consolidated finding list."""
    findings: list[Finding] = []
    for check in CHECK_REGISTRY:
        try:
            findings.extend(check(ctx))
        except Exception as e:  # noqa: BLE001 — checks should not crash the audit
            findings.append(
                Finding(
                    id=f"INTERNAL-ERROR-{check.__name__}",
                    title=f"Check {check.__name__} raised an exception",
                    severity="INFO",
                    category="internal",
                    path=None,
                    lines=None,
                    evidence={"error": repr(e)},
                    why_it_matters="The audit itself has a bug.",
                    remediation="Open an issue with the error message.",
                )
            )
    # Stable sort: severity rank descending, then ID ascending
    findings.sort(key=lambda f: (-SEVERITY_RANK.get(f.severity, 0), f.id))
    return findings


def totals(findings: Iterable[Finding]) -> dict[str, int]:
    """Return a dict of severity counts plus total and per-category counts."""
    out: dict[str, int] = {s: 0 for s in SEVERITIES}
    out["total"] = 0
    by_cat: dict[str, int] = {}
    for f in findings:
        out[f.severity] = out.get(f.severity, 0) + 1
        out["total"] += 1
        by_cat[f.category] = by_cat.get(f.category, 0) + 1
    out["by_category"] = by_cat  # type: ignore[assignment]
    return out


def build_report(ctx: AuditContext, findings: list[Finding]) -> dict[str, Any]:
    """Assemble the JSON-serializable report."""
    return {
        "schema_version": SCHEMA_VERSION,
        "tool": TOOL_NAME,
        "tool_version": TOOL_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repo_root": str(ctx.repo_root),
        "branch": ctx.branch,
        "head_commit": ctx.head_commit,
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "is_git": ctx.is_git,
        "totals": totals(findings),
        "findings": [f.to_dict() for f in findings],
    }


# ══════════════════════════════════════════════════════════════════════════════
# OUTPUT RENDERING
# ══════════════════════════════════════════════════════════════════════════════


def render_console(report: dict[str, Any], severity_floor: str) -> str:
    """Return the human-readable console summary as a string."""
    floor_rank = SEVERITY_RANK.get(severity_floor, 1)
    sev = report["totals"]
    lines: list[str] = []
    lines.append(f"[TMT Audit] Deterministic Audit — {report['generated_at_utc']}")
    lines.append(
        f"Repo:     {report['repo_root']}    Branch: {report['branch']}    "
        f"HEAD: {report['head_commit'][:8]}"
    )
    lines.append("")
    lines.append(
        f"Severity summary:  CRITICAL={sev.get('CRITICAL', 0)}  "
        f"WARNING={sev.get('WARNING', 0)}  "
        f"SUGGESTION={sev.get('SUGGESTION', 0)}  "
        f"INFO={sev.get('INFO', 0)}  "
        f"Total={sev.get('total', 0)}"
    )
    cat = sev.get("by_category", {}) or {}
    if cat:
        cat_str = "  ".join(f"{k}={v}" for k, v in sorted(cat.items()))
        lines.append(f"Category summary:  {cat_str}")
    lines.append("")

    visible = [f for f in report["findings"] if SEVERITY_RANK.get(f["severity"], 0) >= floor_rank]
    for f in visible:
        loc = f["path"] or "-"
        if f["lines"]:
            loc += f":{f['lines'][0]}-{f['lines'][1]}"
        lines.append(f"[{f['severity']:9s}] {f['id']:6s}  {f['title'][:60]:60s}  {loc}")

    return "\n".join(lines)


def render_markdown(report: dict[str, Any], severity_floor: str) -> str:
    """Return the human-readable Markdown report as a string."""
    floor_rank = SEVERITY_RANK.get(severity_floor, 1)
    sev = report["totals"]
    lines: list[str] = []
    lines.append(f"# Deterministic Audit Report")
    lines.append("")
    lines.append(f"- **Repository:** `{report['repo_root']}`")
    lines.append(f"- **Branch:** `{report['branch']}`")
    lines.append(f"- **HEAD commit:** `{report['head_commit']}`")
    lines.append(f"- **Generated:** {report['generated_at_utc']}")
    lines.append(f"- **Tool:** {report['tool']} v{report['tool_version']}")
    lines.append(f"- **Severity floor:** {severity_floor}")
    lines.append("")
    lines.append("## Severity summary")
    lines.append("")
    lines.append("| Severity | Count |")
    lines.append("|----------|------:|")
    for s in SEVERITIES:
        lines.append(f"| {s} | {sev.get(s, 0)} |")
    lines.append(f"| **Total** | **{sev.get('total', 0)}** |")
    lines.append("")
    cat = sev.get("by_category", {}) or {}
    if cat:
        lines.append("## Findings by category")
        lines.append("")
        lines.append("| Category | Count |")
        lines.append("|----------|------:|")
        for k, v in sorted(cat.items()):
            lines.append(f"| {k} | {v} |")
        lines.append("")

    visible = [f for f in report["findings"] if SEVERITY_RANK.get(f["severity"], 0) >= floor_rank]
    if not visible:
        lines.append("_No findings at or above the severity floor._")
        lines.append("")

    # Group by category
    by_cat: dict[str, list[dict[str, Any]]] = {}
    for f in visible:
        by_cat.setdefault(f["category"], []).append(f)

    for category in sorted(by_cat):
        lines.append(f"## {category}")
        lines.append("")
        for f in by_cat[category]:
            lines.append(f"### [{f['severity']}] {f['id']} — {f['title']}")
            lines.append("")
            if f["path"]:
                loc = f["path"]
                if f["lines"]:
                    loc += f":{f['lines'][0]}"
                    if f["lines"][1] != f["lines"][0]:
                        loc += f"-{f['lines'][1]}"
                lines.append(f"**Location:** `{loc}`")
                lines.append("")
            if f["evidence"]:
                lines.append("**Evidence:**")
                lines.append("")
                lines.append("```json")
                lines.append(json.dumps(f["evidence"], indent=2))
                lines.append("```")
                lines.append("")
            if f["why_it_matters"]:
                lines.append(f"**Why it matters:** {f['why_it_matters']}")
                lines.append("")
            if f["remediation"]:
                lines.append(f"**Remediation:** {f['remediation']}")
                lines.append("")
            if f.get("related_finding_ids"):
                related = ", ".join(f["related_finding_ids"])
                lines.append(f"**Related:** {related}")
                lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("Re-run:")
    lines.append("")
    lines.append("```bash")
    lines.append("python tools/audit.py")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════


def prune_old_reports(output_dir: Path, keep: int) -> None:
    """Keep only the N most recent JSON+MD pairs in output_dir."""
    if keep <= 0:
        return
    jsons = sorted(output_dir.glob("deterministic_audit_*.json"), key=lambda p: p.name)
    md5s = sorted(output_dir.glob("deterministic_audit_*.md"), key=lambda p: p.name)
    for old in jsons[:-keep]:
        try:
            old.unlink()
        except OSError:
            pass
    for old in md5s[:-keep]:
        try:
            old.unlink()
        except OSError:
            pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tools/audit.py",
        description="Deterministic (no-LLM) repository audit for TMT_Quantum_Vault-.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Path to the repository root (default: parent of tools/).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "audit_reports",
        help="Directory for JSON+Markdown reports (default: ./audit_reports).",
    )
    parser.add_argument(
        "--severity-floor",
        choices=SEVERITIES,
        default="INFO",
        help="Minimum severity to display (default: INFO = show everything).",
    )
    parser.add_argument(
        "--keep",
        type=int,
        default=5,
        help="Number of historical reports to retain (default: 5).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the console summary (only write files and exit code).",
    )
    args = parser.parse_args(argv)

    repo_root: Path = args.repo_root.resolve()
    output_dir: Path = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    ctx = build_context(repo_root)
    findings = run_audit(ctx)
    report = build_report(ctx, findings)

    if not args.quiet:
        print(render_console(report, args.severity_floor))

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = output_dir / f"deterministic_audit_{timestamp}"
    (base.with_suffix(".json")).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (base.with_suffix(".md")).write_text(
        render_markdown(report, args.severity_floor), encoding="utf-8"
    )
    if not args.quiet:
        print("")
        print(f"Reports:")
        print(f"  {base.with_suffix('.json')}")
        print(f"  {base.with_suffix('.md')}")

    prune_old_reports(output_dir, args.keep)

    # Exit code: 1 if any CRITICAL, 0 otherwise
    if report["totals"].get("CRITICAL", 0) > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
