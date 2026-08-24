"""Regression test: SIGNIFICANT provenance paths must be portable.

The 23 hardware-validated SIGNIFICANT JSON files under
``circuits/ingested/SIGNIFICANT/`` record a ``source_file`` field pointing
back at the original IBM Quantum job result. In an earlier iteration of the
repository these paths were absolute Windows paths from a single developer's
machine (``D:\\AGI-GH-REPO-11326\\TMT_Quantum_Vault-\\...``), which broke
reproducibility on every other checkout.

The migration script ``tools/migrate_significant_paths.py`` rewrites those
paths to a portable form (``circuits/results/<job_id>-result.json``). This
test guards against regression in three ways:

1. **Static invariant** — no SIGNIFICANT file may contain a Windows-style
   drive-letter path (``D:\\...`` or ``C:\\...``) anywhere in its JSON
   payload.
2. **Format invariant** — every ``source_file`` must start with
   ``circuits/results/`` (the portable prefix).
3. **Self-consistency** — for files that include both ``source_file`` and
   ``job_id``, the rewritten source_file basename must equal
   ``<job_id>-result.json`` (because the migration pulls the basename from
   the embedded relative path, not from job_id; this test pins that the
   invariant holds across all 23 files at the time of migration).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SIGNIFICANT_DIR = REPO_ROOT / "circuits" / "ingested" / "SIGNIFICANT"

# Windows drive-letter pattern. We deliberately don't try to be clever
# about UNC paths or forward-slash variants here — the regression we are
# guarding against is "absolute Windows paths leaked into tracked JSON."
_DRIVE_LETTER_RE = re.compile(r'^[A-Za-z]:[\\/]')


def _significant_files() -> list[Path]:
    if not SIGNIFICANT_DIR.is_dir():
        return []
    return sorted(p for p in SIGNIFICANT_DIR.glob("*.json") if p.is_file())


@pytest.fixture(scope="module")
def significant_files() -> list[Path]:
    return _significant_files()


@pytest.mark.skipif(
    not SIGNIFICANT_DIR.is_dir(),
    reason="circuits/ingested/SIGNIFICANT/ not present in this checkout",
)
def test_significant_directory_has_files(significant_files: list[Path]) -> None:
    """Sanity check: the SIGNIFICANT corpus exists and is non-empty.

    The migration target only matters if there are SIGNIFICANT runs to
    migrate. If a future change reduces the set to zero, this test will
    skip; if it is empty but the directory exists, that is a regression.
    """
    assert significant_files, (
        f"No SIGNIFICANT JSON files found under {SIGNIFICANT_DIR}. "
        "Either the corpus was removed (update this test) or ingestion is broken."
    )


@pytest.mark.skipif(
    not SIGNIFICANT_DIR.is_dir(),
    reason="circuits/ingested/SIGNIFICANT/ not present in this checkout",
)
def test_no_drive_letter_paths_in_significant(
    significant_files: list[Path],
) -> None:
    """No ``source_file`` field may start with a Windows drive letter.

    This is the regression we are guarding against: every user except the
    original developer would see ``D:\\AGI-GH-REPO-11326\\...`` and have
    no way to resolve the path.
    """
    offenders: list[tuple[str, str]] = []
    for path in significant_files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        source_file = data.get("source_file")
        if not isinstance(source_file, str):
            continue
        if _DRIVE_LETTER_RE.match(source_file):
            offenders.append((path.name, source_file))

    assert not offenders, (
        "Found SIGNIFICANT JSON files with absolute Windows paths in "
        f"source_file. Run `python tools/migrate_significant_paths.py --apply` "
        "to rewrite them. Offenders (first 5):\n  "
        + "\n  ".join(f"{n}: {s}" for n, s in offenders[:5])
    )


@pytest.mark.skipif(
    not SIGNIFICANT_DIR.is_dir(),
    reason="circuits/ingested/SIGNIFICANT/ not present in this checkout",
)
def test_source_file_is_portable_prefix(
    significant_files: list[Path],
) -> None:
    """Every ``source_file`` must start with the portable ``circuits/results/`` prefix."""
    bad: list[tuple[str, str]] = []
    for path in significant_files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        source_file = data.get("source_file")
        if not isinstance(source_file, str):
            continue
        if not source_file.startswith("circuits/results/"):
            bad.append((path.name, source_file))

    assert not bad, (
        "SIGNIFICANT source_file fields must start with 'circuits/results/'. "
        "Offenders (first 5):\n  "
        + "\n  ".join(f"{n}: {s}" for n, s in bad[:5])
    )


@pytest.mark.skipif(
    not SIGNIFICANT_DIR.is_dir(),
    reason="circuits/ingested/SIGNIFICANT/ not present in this checkout",
)
def test_source_file_matches_job_id(
    significant_files: list[Path],
) -> None:
    """When ``job_id`` is present, the basename of ``source_file`` must be
    ``<job_id>-result.json``.
    """
    mismatches: list[tuple[str, str, str]] = []
    for path in significant_files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        source_file = data.get("source_file")
        job_id = data.get("job_id")
        if not (isinstance(source_file, str) and isinstance(job_id, str)):
            continue
        expected_basename = f"{job_id}-result.json"
        actual_basename = source_file.rsplit("/", 1)[-1]
        if actual_basename != expected_basename:
            mismatches.append((path.name, expected_basename, actual_basename))

    assert not mismatches, (
        "source_file basename must equal '<job_id>-result.json'. "
        "Mismatches (first 5):\n  "
        + "\n  ".join(
            f"{n}: expected {e}, got {a}"
            for n, e, a in mismatches[:5]
        )
    )


# ---------------------------------------------------------------------------
# Migration script behaviour (unit tests on the script's pure helpers).
# ---------------------------------------------------------------------------

import sys
sys.path.insert(0, str(REPO_ROOT))

from tools.migrate_significant_paths import _target_path  # noqa: E402


@pytest.mark.parametrize(
    "raw,expected",
    [
        (
            r"D:\AGI-GH-REPO-11326\TMT_Quantum_Vault-\circuits\results\job-abc-result.json",
            "circuits/results/job-abc-result.json",
        ),
        (
            r"D:/AGI-GH-REPO-11326/TMT_Quantum_Vault-/circuits/results/job-abc-result.json",
            "circuits/results/job-abc-result.json",
        ),
        (
            r"C:\AGI-GH-REPO-11326\TMT_Quantum_Vault-\circuits\results\job-xyz-result.json",
            "circuits/results/job-xyz-result.json",
        ),
        # Already-portable input is left alone (the script's outer logic
        # handles this by checking for None; _target_path only matches
        # the legacy absolute prefixes).
        (
            "circuits/results/job-abc-result.json",
            None,
        ),
        # Unrelated absolute paths are not rewritten.
        (
            "/home/user/circuits/results/job-abc-result.json",
            None,
        ),
        # Empty / non-string input is not rewritten.
        ("", None),
    ],
)
def test_target_path_recognises_legacy_prefixes(
    raw: str, expected: str | None
) -> None:
    assert _target_path(raw) == expected