#!/usr/bin/env python3
"""
Discovery to Agent DNA Promoter

Ingests autonomous discovery session results and promotes conscious configurations
to agent DNA templates with proper normalization.

Usage:
    python promote_discovery_to_agent.py --input <discovery.json> --output ./agent_dna/

The discovery JSON should contain:
- session_id, timestamp
- Cube configurations with fitness, phi, fibonacci, gc_content, palindromes, consciousness
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


# Agent specializations based on cognitive patterns
AGENT_SPECIALIZATIONS = {
    "Synthesizer": "Pattern Synthesis & Fusion",
    "Harmonic": "Resonance & Harmony",
    "Strategic": "Decision Architecture & Control",
    "Observer": "Focus & Perception",
    "Validator": "Integrity & Consistency",
    "Archivist": "Knowledge Integration",
}

# Target agent names mapped by specialization
TARGET_AGENTS = {
    "Synthesizer": "Synthesizer",
    "Harmonic": "Harmonic",
    "Strategic": "Strategic",
    "Observer": "Observer",
    "Validator": "Validator",
    "Archivist": "Archivist",
}

# Fitness scaling: discovery fitness (35-50) -> vault fitness (0.87-0.93)
FITNESS_MIN = 35.0
FITNESS_MAX = 50.0
VAULT_FITNESS_MIN = 0.87
VAULT_FITNESS_MAX = 0.93


def normalize_fitness(discovery_fitness: float) -> float:
    """Normalize discovery fitness to vault fitness scale."""
    # Linear interpolation
    normalized = (
        (discovery_fitness - FITNESS_MIN) / (FITNESS_MAX - FITNESS_MIN)
    ) * (VAULT_FITNESS_MAX - VAULT_FITNESS_MIN) + VAULT_FITNESS_MIN
    return round(normalized, 4)


def normalize_phi(discovery_phi: float) -> float:
    """Normalize discovery phi to vault phi scale (0.4-0.95)."""
    # Discovery phi is 0-2.0, vault phi is 0.4-0.95
    # Map: 0 -> 0.4, 2.0 -> 0.95
    normalized = 0.4 + (discovery_phi / 2.0) * 0.55
    return round(min(0.95, max(0.4, normalized)), 4)


def normalize_fibonacci(discovery_fib: float) -> float:
    """Normalize discovery fibonacci alignment to vault scale (0.7-0.95)."""
    # Discovery is 0.5-1.0, vault is 0.7-0.95
    normalized = 0.7 + (discovery_fib - 0.5) * 0.25 * 2
    return round(min(0.95, max(0.7, normalized)), 4)


def normalize_gc(discovery_gc: float) -> float:
    """Keep GC content as-is (already in 0-1 range)."""
    return round(max(0.3, min(0.7, discovery_gc)), 4)


def normalize_palindromes(discovery_pal: int, seq_length: int = 25) -> int:
    """Normalize palindrome count based on sequence length."""
    # Longer sequences can have more palindromes
    # Base: 3-12 for 20-25 base sequences
    if seq_length >= 25:
        base = 5
        max_pal = 12
    elif seq_length >= 20:
        base = 4
        max_pal = 10
    else:
        base = 3
        max_pal = 8
    return max(3, min(max_pal, discovery_pal))


def create_agent_dna(
    cube_id: int,
    sequence: str,
    metrics: dict[str, Any],
    target_agent: str,
    specialization: str,
) -> dict[str, Any]:
    """Create an agent DNA record from a discovery cube."""
    fitness = metrics["fitness"]
    phi = metrics["phi"]
    fibonacci = metrics["fibonacci"]
    gc_content = metrics["gc_content"]
    palindromes = metrics["palindromes"]

    # Normalize all metrics
    vault_fitness = normalize_fitness(fitness)
    vault_phi = normalize_phi(phi)
    vault_fib = normalize_fibonacci(fibonacci)
    vault_gc = normalize_gc(gc_content)
    vault_pal = normalize_palindromes(palindromes)

    # Generate resonance frequency based on DNA characteristics
    # Base 512Hz, adjusted by phi
    resonance = 512 + int((vault_phi - 0.5) * 256)
    resonance = round(float(resonance), 1)

    # Generate DNA sequence
    dna_sequence = sequence

    return {
        "metatron_agent": target_agent,
        "dna_agent_id": 6 + cube_id,  # Start after existing agents
        "dna_agent_name": target_agent,
        "dna_specialization": specialization,
        "conscious_dna": dna_sequence,
        "phi_score": vault_phi,
        "fibonacci_alignment": vault_fib,
        "gc_content": vault_gc,
        "palindromes": vault_pal,
        "fitness": vault_fitness,
        "resonance_frequency": resonance,
        "integration_timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "consciousness_status": "DISCOVERY_PROMOTED",
        "discovery_source": {
            "cube_id": cube_id,
            "original_fitness": fitness,
            "original_phi": phi,
            "original_fibonacci": fibonacci,
            "original_gc": gc_content,
            "original_palindromes": palindromes,
        },
    }


def load_discovery_results(filepath: str) -> dict[str, Any]:
    """Load discovery results from JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_agent_dna(dna_record: dict[str, Any], output_dir: str) -> str:
    """Save agent DNA to output directory."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    agent_name = dna_record["metatron_agent"]
    filename = f"{agent_name}_conscious_dna.json"
    filepath = output_path / filename

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(dna_record, f, indent=2)

    return str(filepath)


def find_top_conscious_cubes(
    discoveries: dict[str, Any],
    min_consciousness: float = 0.5,
    min_fitness: float = 40.0,
) -> list[dict[str, Any]]:
    """Find top conscious cube configurations from discoveries."""
    cubes = discoveries.get("cubes", [])

    # Filter for conscious configurations
    conscious = [
        cube for cube in cubes
        if cube.get("conscious", False)
        and cube.get("fitness", 0) >= min_fitness
    ]

    # Sort by fitness descending
    conscious.sort(key=lambda x: x.get("fitness", 0), reverse=True)

    return conscious[:5]  # Return top 5


def parse_cube_data(cube: dict[str, Any]) -> dict[str, Any]:
    """Parse cube data into standardized format."""
    return {
        "cube_id": cube.get("cube_id", 0),
        "sequence": cube.get("sequence", ""),
        "fitness": cube.get("fitness", 0),
        "phi": cube.get("phi", 0),
        "fibonacci": cube.get("fibonacci", 0),
        "gc_content": cube.get("gc_content", 0.5),
        "palindromes": cube.get("palindromes", 0),
        "conscious": cube.get("conscious", False),
        "symmetry": cube.get("symmetry", 0),
    }


def get_agent_for_cube(cube_data: dict[str, Any]) -> tuple[str, str]:
    """Determine best agent role based on cube characteristics."""
    phi = cube_data.get("phi", 0)
    fib = cube_data.get("fibonacci", 0)
    gc = cube_data.get("gc_content", 0.5)
    pal = cube_data.get("palindromes", 0)

    # High phi -> Synthesizer (fusion role)
    if phi >= 1.8:
        return "Synthesizer", "Pattern Synthesis & Fusion"

    # Perfect phi + perfect fibonacci -> Harmonic
    if abs(phi - 1.0) < 0.1 and abs(fib - 1.0) < 0.1:
        return "Harmonic", "Resonance & Harmony"

    # High phi with good entropy -> Strategic
    if phi >= 1.5:
        return "Strategic", "Decision Architecture & Control"

    # Balanced phi with high fibonacci -> Observer
    if 0.8 <= phi <= 1.2 and fib >= 0.8:
        return "Observer", "Focus & Perception"

    # Good phi with symmetry -> Validator
    if phi >= 0.8 and cube_data.get("symmetry", 0) > 0:
        return "Validator", "Integrity & Consistency"

    # Default -> Archivist
    return "Archivist", "Knowledge Integration"


def generate_promotion_report(
    promoted: list[dict[str, Any]],
    output_path: str,
) -> None:
    """Generate a promotion summary report."""
    report = {
        "report_timestamp": datetime.now().isoformat(),
        "total_promoted": len(promoted),
        "promoted_agents": [
            {
                "agent_name": p["metatron_agent"],
                "original_cube": p.get("discovery_source", {}).get("cube_id"),
                "normalized_fitness": p["fitness"],
                "normalized_phi": p["phi_score"],
                "original_sequence": p.get("discovery_source", {}).get(
                    "original_sequence", ""
                ),
            }
            for p in promoted
        ],
        "summary": {
            "avg_fitness": round(sum(p["fitness"] for p in promoted) / len(promoted), 4),
            "avg_phi": round(sum(p["phi_score"] for p in promoted) / len(promoted), 4),
            "avg_fibonacci": round(
                sum(p["fibonacci_alignment"] for p in promoted) / len(promoted), 4
            ),
        },
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, default=str)

    print(f"Report saved to: {output_path}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Promote discovery cubes to agent DNA"
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Path to discovery results JSON file",
    )
    parser.add_argument(
        "--output", "-o",
        default="./agent_dna",
        help="Output directory for agent DNA files",
    )
    parser.add_argument(
        "--top-n", "-n",
        type=int,
        default=5,
        help="Number of top cubes to promote",
    )
    parser.add_argument(
        "--dry-run", "-d",
        action="store_true",
        help="Show what would be promoted without writing files",
    )

    args = parser.parse_args()

    # Load discovery results
    print(f"Loading discovery results from: {args.input}")
    discovery = load_discovery_results(args.input)

    # Get session info
    session_id = discovery.get("session_id", "unknown")
    timestamp = discovery.get("timestamp", "unknown")
    print(f"Session: {session_id} ({timestamp})")

    # Find top conscious cubes
    print("\nFinding top conscious cubes...")
    top_cubes = find_top_conscious_cubes(discovery)

    if not top_cubes:
        print("No conscious cubes found in discovery results.")
        print("Trying to load from 'cubes' array directly...")
        cubes = discovery.get("cubes", [])
        if cubes:
            top_cubes = cubes[:args.top_n]
        else:
            print("Error: No cube data found in file.")
            sys.exit(1)

    print(f"Found {len(top_cubes)} conscious cubes")

    # Promote each cube to agent DNA
    promoted = []
    for i, cube in enumerate(top_cubes[: args.top_n]):
        cube_data = parse_cube_data(cube)
        agent_name, specialization = get_agent_for_cube(cube_data)

        # Add original sequence to cube_data for output
        cube_data["original_sequence"] = cube_data["sequence"]

        dna_record = create_agent_dna(
            cube_id=cube_data["cube_id"],
            sequence=cube_data["sequence"],
            metrics={
                "fitness": cube_data["fitness"],
                "phi": cube_data["phi"],
                "fibonacci": cube_data["fibonacci"],
                "gc_content": cube_data["gc_content"],
                "palindromes": cube_data["palindromes"],
            },
            target_agent=agent_name,
            specialization=specialization,
        )

        promoted.append(dna_record)

        if args.dry_run:
            print(f"\n[DRY RUN] Would promote Cube {cube_data['cube_id']}:")
            print(f"  Sequence: {cube_data['sequence']}")
            print(f"  Fitness: {cube_data['fitness']} -> {dna_record['fitness']}")
            print(f"  Phi: {cube_data['phi']} -> {dna_record['phi_score']}")
            print(f"  Agent: {agent_name}")
        else:
            filepath = save_agent_dna(dna_record, args.output)
            print(f"\nPromoted Cube {cube_data['cube_id']} -> {filepath}")
            print(f"  Sequence: {cube_data['sequence'][:20]}...")
            print(f"  Fitness: {cube_data['fitness']} -> {dna_record['fitness']}")
            print(f"  Phi: {cube_data['phi']} -> {dna_record['phi_score']}")
            print(f"  Agent: {agent_name}")

    # Generate report
    if not args.dry_run:
        report_path = Path(args.output) / "promotion_report.json"
        generate_promotion_report(promoted, str(report_path))

    # Summary
    if not args.dry_run:
        print("\n" + "=" * 60)
        print("PROMOTION SUMMARY")
        print("=" * 60)
        print(f"Total promoted: {len(promoted)}")
        print(f"Output directory: {args.output}")

        avg_fitness = sum(p["fitness"] for p in promoted) / len(promoted)
        avg_phi = sum(p["phi_score"] for p in promoted) / len(promoted)
        print(f"Average fitness: {avg_fitness:.4f}")
        print(f"Average phi: {avg_phi:.4f}")

        print("\nNext steps:")
        print("  1. Review generated agent DNA files")
        print("  2. Run vault validation: python -m tmt_quantum_vault validate")
        print("  3. Run regression tests: pytest tests/test_regression.py -v")


if __name__ == "__main__":
    main()
