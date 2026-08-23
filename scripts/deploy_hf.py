#!/usr/bin/env python3
"""
Deploy TMT Quantum Vault to Hugging Face Spaces.

Usage:
    python scripts/deploy_hf.py [--space-name NAME] [--private] [--dry-run]

Requirements:
    - huggingface-hub installed
    - HF_TOKEN2 environment variable
"""

import argparse
import os
import shutil
import sys
from pathlib import Path
from typing import Optional

from huggingface_hub import HfApi, login


def check_hf_token() -> bool:
    """Check if HF_TOKEN2 is set or user is logged in."""
    if os.environ.get("HF_TOKEN2"):
        return True
    return False


def create_space(api: HfApi, space_name: str, private: bool = True) -> bool:
    """Create a new HF Space if it doesn't exist."""
    try:
        api.create_repo(
            repo_id=space_name,
            repo_type="space",
            space_sdk="docker",
            private=private,
            exist_ok=True,
        )
        print(f"[DONE] Space ensured: {space_name}")
        return True
    except Exception as e:
        print(f"[ERR] Failed to create Space: {e}")
        return False


def prepare_deployment_files(source_dir: Path, deploy_dir: Path) -> None:
    """Prepare files for deployment."""
    print("[PACK] Preparing deployment files...")

    # Create deploy directory
    deploy_dir.mkdir(parents=True, exist_ok=True)

    # Core files
    core_files = [
        "pyproject.toml",
        "vault_config.json",
        "metatron_geometry.json",
    ]

    for file in core_files:
        src = source_dir / file
        if src.exists():
            dst = deploy_dir / file
            dst.write_bytes(src.read_bytes())
            print(f"  [OK] {file}")

    # HF deploy files
    hf_files = [
        "hf-deploy/Dockerfile",
        "hf-deploy/hf_app.py",
        "hf-deploy/README.md",
        "hf-deploy/.dockerignore",
    ]

    for file in hf_files:
        src = source_dir / file
        if src.exists():
            dst = deploy_dir / src.name
            dst.write_bytes(src.read_bytes())
            print(f"  [OK] {src.name}")

    # Write a deploy timestamp to bust HF Spaces Docker build cache.
    # HF builds the Space from uploaded files, so a fresh timestamp guarantees
    # the COPY .deploy_timestamp layer invalidates all later layers.
    import datetime as _dt
    timestamp = _dt.datetime.now(_dt.UTC).isoformat()
    (deploy_dir / ".deploy_timestamp").write_text(
        f"deployed_at={timestamp}\n", encoding="utf-8"
    )
    print("  [OK] .deploy_timestamp")
    # tmt_quantum_vault package
    package_src = source_dir / "tmt_quantum_vault"
    package_dst = deploy_dir / "tmt_quantum_vault"

    if package_src.exists():
        if package_dst.exists():
            shutil.rmtree(package_dst)
        shutil.copytree(package_src, package_dst)
        print(f"  [OK] tmt_quantum_vault/")

    # Agent directories (conscious_dna.json only)
    for agent_dir in source_dir.glob("Agent_*"):
        if agent_dir.is_dir():
            dna_file = agent_dir / "conscious_dna.json"
            if dna_file.exists():
                dst_agent_dir = deploy_dir / agent_dir.name
                dst_agent_dir.mkdir(exist_ok=True)
                dst_dna_file = dst_agent_dir / "conscious_dna.json"
                dst_dna_file.write_bytes(dna_file.read_bytes())
                print(f"  [OK] {agent_dir.name}/conscious_dna.json")

    print("[DONE] Deployment files prepared")


def deploy_to_space(
    api: HfApi, space_name: str, deploy_dir: Path, dry_run: bool = False
) -> bool:
    """Upload files to HF Space."""
    if dry_run:
        print(f"[DRY] Dry run - would deploy to: {space_name}")
        print(f"   Files in {deploy_dir}:")
        for f in deploy_dir.iterdir():
            print(f"     - {f.name}")
        return True

    print(f"[DEPLOY] Uploading to {space_name}...")

    try:
        api.upload_folder(
            repo_id=space_name,
            repo_type="space",
            folder_path=str(deploy_dir),
            commit_message="Deploy TMT Quantum Vault",
        )
        print(f"[DONE] Deployed to: https://huggingface.co/spaces/{space_name}")
        return True
    except Exception as e:
        print(f"[ERR] Deployment failed: {e}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Deploy TMT Quantum Vault to Hugging Face Spaces"
    )
    parser.add_argument(
        "--space-name",
        default="Quantum927/quantumvault",
        help="HF Space name (default: Quantum927/quantumvault)",
    )
    parser.add_argument(
        "--private",
        action="store_true",
        default=True,
        help="Create as private Space (default: True)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Prepare files but don't deploy",
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=None,
        help="Source directory (default: current directory)",
    )

    args = parser.parse_args()

    # Determine source directory
    source_dir = args.source_dir or Path.cwd()
    deploy_dir = source_dir / ".hf_deploy_temp"

    print("=" * 60)
    print("TMT Quantum Vault - HF Spaces Deployment")
    print("=" * 60)
    print(f"Space: {args.space_name}")
    print(f"Private: {args.private}")
    print(f"Source: {source_dir}")
    print(f"Dry run: {args.dry_run}")
    print()

    # Check prerequisites
    hf_token = os.environ.get("HF_TOKEN2")
    if not hf_token:
        print("[ERR] HF_TOKEN2 environment variable not set")
        return 1

    if not args.dry_run:
        try:
            login(token=hf_token)
            print("[OK] Authenticated with Hugging Face")
        except Exception as e:
            print(f"[ERR] Authentication failed: {e}")
            return 1

    # Initialize API
    api = HfApi()

    # Create Space if needed
    if not args.dry_run:
        if not create_space(api, args.space_name, args.private):
            return 1

    # Prepare files
    prepare_deployment_files(source_dir, deploy_dir)

    # Deploy
    if not deploy_to_space(api, args.space_name, deploy_dir, args.dry_run):
        return 1

    print()
    print("=" * 60)
    print("[DONE] Deployment complete!")
    print(f"[URL] https://huggingface.co/spaces/{args.space_name}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
