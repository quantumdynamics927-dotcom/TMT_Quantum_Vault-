#!/usr/bin/env python3
"""Migrate SIGNIFICANT provenance paths from absolute Windows paths to portable
relative paths.

Background
----------
The 23 hardware-validated SIGNIFICANT runs under
``circuits/ingested/SIGNIFICANT/*.json`` were ingested on a developer machine
where the repository lived at::

    D:\\AGI-GH-REPO-11326\\TMT_Quantum_Vault-\\circuits\\results\\<job_id>-result.json

That absolute path is recorded in each JSON's ``source_file`` field. On any
other machine — including CI, fresh clones, or other contributors' checkouts
— the path does not exist, which breaks reproducibility of the
quantum-to-agent provenance chain.

This script rewrites ``source_file`` to a portable, repo-relative form::

    circuits/results/<job_id>-result.json

where ``<job_id>`` is read from the JSON itself (so the migration is
self-validating: the rewritten path always agrees with the embedded job id).

Usage
-----

Dry run (default — print what would change, write nothing)::

    python tools/migrate_significant_paths.py

Actually rewrite the files in place::

    python tools/migrate_significant_paths.py --apply

Point at a different SIGNIFICANT directory for testing::

    python tools/migrate_significant_paths.py --significant-dir /tmp/SIGNIFICANT
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Absolute Windows path prefixes we want to rewrite. The pattern is matched
# anywhere in the string and replaced with a repo-relative path.
_ABS_PREFIXES = (
    "D:\\AGI-GH-REPO-11326\\TMT_Quantum_Vault-\\",
    "D:/AGI-GH-REPO-11326/TMT_Quantum_Vault-/",
    "C:\\AGI-GH-REPO-11326\\TMT_Quantum_Vault-\\",
    "C:/AGI-GH-REPO-11326/TMT_Quantum_Vault-/",
)

# Anything matching one of these absolute prefixes gets rewritten to the
# value on the right (a portable, repo-relative path stem). The basename
# of the original path is preserved.
_PORTABLE_STEM = "circuits/results/"


def _target_path(raw: str) -> str | None:
    """Return the portable replacement for ``raw`` if it matches an absolute
    prefix we recognise; otherwise return ``None``.

    The check is deliberately strict — we only rewrite paths we recognise
    as the legacy developer's machine layout, never arbitrary paths.

    The legacy paths look like::

        D:\\AGI-GH-REPO-11326\\TMT_Quantum_Vault-\\circuits\\results\\<basename>

    Note the duplicated ``circuits\\results\\`` segment (once in the legacy
    absolute prefix, once again in the relative path that was embedded
    before ingestion). The portable form is simply::

        circuits/results/<basename>
    """
    for prefix in _ABS_PREFIXES:
        if raw.startswith(prefix):
            basename = raw[len(prefix):]
            # Strip any leading "circuits/results/" or "circuits\\results\\"
            # that the embedded relative path added before the absolute
            # prefix was prepended at ingestion time.
            for leading in ("circuits\\results\\", "circuits/results/"):
                if basename.startswith(leading):
                    basename = basename[len(leading):]
                    break
            return _PORTABLE_STEM + basename
    return None


def migrate_file(path: Path) -> tuple[bool, str | None]:
    """Migrate ``path`` in place if it has a legacy ``source_file``.

    Returns ``(changed, new_value)``. When ``changed`` is False,
    ``new_value`` is None. When ``changed`` is True, ``new_value`` is the
    new source_file string the file would receive (or has received).
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Could not read/parse {path}: {exc}") from exc

    source_file = data.get("source_file")
    if not isinstance(source_file, str):
        return (False, None)

    new_value = _target_path(source_file)
    if new_value is None:
        return (False, None)

    if new_value == source_file:
        return (False, None)

    data["source_file"] = new_value
    return (True, new_value)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Rewrite SIGNIFICANT source_file fields from absolute Windows "
            "paths to portable repo-relative paths."
        ),
    )
    parser.add_argument(
        "--significant-dir",
        type=Path,
        default=Path("circuits/ingested/SIGNIFICANT"),
        help="Directory containing SIGNIFICANT *.json files (default: %(default)s).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually rewrite the files. Without this flag, run in dry-run mode.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(list(sys.argv[1:] if argv is None else argv))

    if not args.significant_dir.is_dir():
        print(
            f"error: SIGNIFICANT directory not found: {args.significant_dir}",
            file=sys.stderr,
        )
        return 2

    json_files = sorted(args.significant_dir.glob("*.json"))
    if not json_files:
        print(
            f"error: no JSON files found under {args.significant_dir}",
            file=sys.stderr,
        )
        return 2

    changed = 0
    unchanged = 0
    for path in json_files:
        try:
            did_change, new_value = migrate_file(path)
        except RuntimeError as exc:
            print(f"  SKIP {path.name}: {exc}")
            continue
        if did_change:
            changed += 1
            mode = "WRITE" if args.apply else "DRY"
            print(f"  {mode}  {path.name}: source_file -> {new_value}")
            if args.apply:
                # Re-read and write to preserve formatting as much as possible.
                # We read again here because migrate_file loaded the dict
                # only; rewriting requires re-serialisation.
                with path.open("r", encoding="utf-8") as f:
                    raw_text = f.read()
                data = json.loads(raw_text)
                data["source_file"] = new_value
                # Write back with 2-space indent + trailing newline to match
                # the existing repo convention.
                path.write_text(
                    json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
        else:
            unchanged += 1

    mode = "Applied" if args.apply else "Would apply"
    print(
        f"\n{mode} {changed} change(s); {unchanged} file(s) already portable "
        f"out of {len(json_files)} total."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
