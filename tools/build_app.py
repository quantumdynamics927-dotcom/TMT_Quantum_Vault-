#!/usr/bin/env python3
"""
Build the Cloudflare Pages static app/ directory from repo root assets.

Usage:
    python tools/build_app.py [--app-dir app]

Copies the static dashboard assets into app/ so `wrangler pages deploy app/`
can publish them without duplicating source files in git.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


STATIC_FILES = [
    "index.html",
    "dashboard.js",
    "research-status.html",
]


def build_app(app_dir: Path, repo_root: Path) -> None:
    """Copy static assets into the Cloudflare Pages app directory."""
    app_dir.mkdir(parents=True, exist_ok=True)

    for name in STATIC_FILES:
        src = repo_root / name
        dst = app_dir / name
        if src.exists():
            shutil.copy2(src, dst)
            print(f"  [OK] {name}")
        else:
            print(f"  [WARN] {name} not found in repo root, skipping")

    # Ensure a minimal 404 page exists
    not_found = app_dir / "404.html"
    if not not_found.exists():
        not_found.write_text(
            "<!DOCTYPE html>"
            "<html><head><title>Not Found</title></head>"
            "<body><h1>404 — Page Not Found</h1></body></html>",
            encoding="utf-8",
        )
        print("  [OK] 404.html")

    print(f"[DONE] Cloudflare Pages app built in {app_dir}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build Cloudflare Pages static app directory"
    )
    parser.add_argument(
        "--app-dir",
        type=Path,
        default=Path("app"),
        help="Destination app directory (default: app/)",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root (default: parent of tools/)",
    )
    args = parser.parse_args()

    repo_root = args.repo_root or Path(__file__).resolve().parents[1]
    build_app(args.app_dir.resolve(), repo_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
