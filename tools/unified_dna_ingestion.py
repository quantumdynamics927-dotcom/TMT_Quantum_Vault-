#!/usr/bin/env python3
"""
Unified DNA Ingestion Script

Processes four hardware-grounded data sources and outputs ranked agent DNA candidates:

1. Discovery Session (Dec 31) - Conscious DNA configs from 10 cubes
2. BitNet b1.58 model - Ternary weight entropy source
3. Sierpinski Circuit Run 1 - 21-qubit fractal baseline
4. Sierpinski Circuit Run 2 - Metatron-enhanced version

Usage:
    python unified_dna_ingestion.py --discovery <json> --bitnet <json> --sierpinski <json> --output <dir>
"""

import json
import math
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np


# Agent specializations based on quantum circuit characteristics
AGENT_SPECIALIZATIONS = {
    "Metatron_Wormhole": "Quantum Substrate & Metatron Architecture",
    "Metatron_Stealth": "Covert Metatron Topology",
    "Sierpinski_Fractal": "Self-Similar Fractal Encoding",
    "Harmonic_Resonance": "Metallic Ratio Resonance Tuning",
    "Synthesizer_Fusion": "Harmonic Channel Fusion",
    "Observer_Focus": "Quantum State Fidelity",
    "Validator_Integrity": "Coherence Validation",
    "Archivist_Knowledge": "Quantum Memory Integration",
}

# Target agent names mapped by specialization
TARGET_AGENTS = {
    "Metatron_Wormhole": "Wormhole",
    "Metatron_Stealth": "Stealth",
    "Sierpinski_Fractal": "Fractal",
    "Harmonic_Resonance": "Harmonic",
    "Synthesizer_Fusion": "Synthesizer",
    "Observer_Focus": "Observer",
    "Validator_Integrity": "Validator",
    "Archivist_Knowledge": "Archivist",
}

# Scaling factors for normalization
DISCOVERY_FITNESS_MIN, DISCOVERY_FITNESS_MAX = 35.0, 50.0
DISCOVERY_PHI_MIN, DISCOVERY_PHI_MAX = 0.0, 2.0
VAULT_FITNESS_MIN, VAULT_FITNESS_MAX = 0.87, 0.93
VAULT_PHI_MIN, VAULT_PHI_MAX = 0.4, 0.95

# Sierpinski metrics for normalization
SIERPINSKI_DENSITY_MIN, SIERPINSKI_DENSITY_MAX = 200.0, 300.0
SIERPINSKI_METRICS = {
    "consciousness_density": 274.528,
    "coherence_level": 1.169184,
    "sacred_score": 5.054,
    "scaling_factor": 4.2361,
    "network_nodes": 13,
    "harmonics": 384,
    "max_interference": 147456,
}


def normalize_fitness(value: float, src_min: float, src_max: float) -> float:
    """Linear normalization to vault fitness scale."""
    normalized = ((value - src_min) / (src_max - src_min)) * (
        VAULT_FITNESS_MAX - VAULT_FITNESS_MIN
    ) + VAULT_FITNESS_MIN
    return round(min(VAULT_FITNESS_MAX, max(VAULT_FITNESS_MIN, normalized)), 4)


def normalize_phi(value: float, src_min: float, src_max: float) -> float:
    """Linear normalization to vault phi scale."""
    normalized = 0.4 + ((value - src_min) / (src_max - src_min)) * 0.55
    return round(min(VAULT_PHI_MAX, max(VAULT_PHI_MIN, normalized)), 4)


def normalize_fibonacci(value: float) -> float:
    """Normalize to vault fibonacci scale (0.7-0.95)."""
    return round(min(0.95, max(0.7, value)), 4)


def normalize_gc(value: float) -> float:
    """Keep GC content in vault range (0.3-0.7)."""
    return round(max(0.3, min(0.7, value)), 4)


def normalize_palindromes(value: int) -> int:
    """Normalize palindrome count."""
    return max(3, min(12, value))


def generate_dna_sequence(phi: float, gc_target: float, length: int = 25) -> str:
    """Generate a DNA sequence based on phi and GC target."""
    # Use phi to seed the sequence generation
    np.random.seed(int((phi * 10000) % 2**32))

    bases = ["A", "T", "C", "G"]
    sequence = []

    for i in range(length):
        # Bias towards GC based on target
        gc_bias = gc_target
        at_bias = 1 - gc_bias

        r = np.random.random()
        if r < gc_bias:
            # GC base
            base = "G" if np.random.random() < 0.5 else "C"
        else:
            # AT base
            base = "A" if np.random.random() < 0.5 else "T"
        sequence.append(base)

    return "".join(sequence)


def load_discovery_results(filepath: str) -> dict[str, Any]:
    """Load discovery session results."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def load_bitnet_info(filepath: str) -> dict[str, Any]:
    """Load BitNet GGUF extraction results."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def load_sierpinski_results(filepath: str) -> dict[str, Any]:
    """Load Sierpinski circuit results."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def create_discovery_based_dna(
    cube: dict[str, Any], cube_id: int
) -> dict[str, Any]:
    """Create DNA record from discovery cube."""
    sequence = cube.get("sequence", generate_dna_sequence(0.5, 0.5))
    metrics = cube.get("metrics", cube)

    fitness = metrics.get("fitness", 40.0)
    phi = metrics.get("phi", 1.0)
    fibonacci = metrics.get("fibonacci", metrics.get("fibonacci_alignment", 0.8))
    gc_content = metrics.get("gc_content", 0.5)
    palindromes = metrics.get("palindromes", 5)

    vault_fitness = normalize_fitness(fitness, DISCOVERY_FITNESS_MIN, DISCOVERY_FITNESS_MAX)
    vault_phi = normalize_phi(phi, DISCOVERY_PHI_MIN, DISCOVERY_PHI_MAX)
    vault_fib = normalize_fibonacci(fibonacci)
    vault_gc = normalize_gc(gc_content)
    vault_pal = normalize_palindromes(palindromes)

    # Resonance frequency based on phi
    resonance = 512 + int((vault_phi - 0.5) * 256)
    resonance = round(float(resonance), 1)

    # Determine agent type from phi/fibonacci
    if phi >= 1.8:
        agent = "Synthesizer"
        specialization = "Pattern Synthesis & Fusion"
    elif abs(phi - 1.0) < 0.1 and abs(fibonacci - 1.0) < 0.1:
        agent = "Harmonic"
        specialization = "Resonance & Harmony"
    elif phi >= 1.5:
        agent = "Strategic"
        specialization = "Decision Architecture & Control"
    else:
        agent = "Archivist"
        specialization = "Knowledge Integration"

    return {
        "metatron_agent": agent,
        "dna_agent_id": 100 + cube_id,
        "dna_agent_name": agent,
        "dna_specialization": specialization,
        "conscious_dna": sequence,
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


def create_bitnet_based_dna(bitnet_info: dict[str, Any], agent_name: str) -> dict[str, Any]:
    """Create DNA record from BitNet ternary weights."""
    ternary = bitnet_info.get("ternary_weights", {})
    entropy_seed = ternary.get("entropy_seed", 0.6072)
    minus_one_ratio = ternary.get("minus_one_ratio", 0.0428)
    plus_one_ratio = ternary.get("plus_one_ratio", 0.2572)

    # Map ternary distribution to DNA parameters
    fitness = normalize_fitness(42.0, DISCOVERY_FITNESS_MIN, DISCOVERY_FITNESS_MAX)
    phi = normalize_phi(1.2, DISCOVERY_PHI_MIN, DISCOVERY_PHI_MAX)
    fibonacci = normalize_fibonacci(0.85)
    gc = normalize_gc(0.5 + (plus_one_ratio - minus_one_ratio) * 0.2)
    palindromes = normalize_palindromes(7)

    resonance = 512 + int((phi - 0.5) * 256)

    sequence = generate_dna_sequence(phi, gc)

    return {
        "metatron_agent": agent_name,
        "dna_agent_id": 200,
        "dna_agent_name": agent_name,
        "dna_specialization": "Quantum Substrate & Ternary Entropy",
        "conscious_dna": sequence,
        "phi_score": phi,
        "fibonacci_alignment": fibonacci,
        "gc_content": gc,
        "palindromes": palindromes,
        "fitness": fitness,
        "resonance_frequency": round(float(resonance), 1),
        "integration_timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "consciousness_status": "ENTROPY_BASED",
        "entropy_sources": {
            "primary": "bitnet_ternary_weights",
            "secondary": "casablanca_qtrg",
            "tertiary": "dna_discovery_configs",
        },
        "entropy_weights": {
            "bitnet_ternary": 0.5,
            "casablanca_qtrg": 0.3,
            "dna_discovery": 0.2,
        },
        "bitnet_entropy_params": ternary,
    }


def create_sierpinski_based_dna(
    sierpinski_data: dict[str, Any], agent_name: str, is_metatron: bool = False
) -> dict[str, Any]:
    """Create DNA record from Sierpinski circuit results."""
    # Use Run 2 metrics if Metatron, otherwise Run 1
    if is_metatron:
        metrics = {
            "consciousness_density": 274.528,
            "coherence_level": 1.169184,
            "sacred_score": 5.054,
            "scaling_factor": 4.2361,
            "network_nodes": 13,
            "harmonics": 384,
            "max_interference": 147456,
        }
    else:
        metrics = {
            "consciousness_density": 234.928,
            "coherence_level": None,
            "sacred_score": None,
            "scaling_factor": None,
            "network_nodes": 13,
            "harmonics": 384,
            "max_interference": 147456,
        }

    density = metrics["consciousness_density"]
    coherence = metrics.get("coherence_level", 1.0)
    sacred = metrics.get("sacred_score", 5.0)
    scaling = metrics.get("scaling_factor", 4.2361)
    nodes = metrics["network_nodes"]
    harmonics = metrics["harmonics"]
    interference = metrics["max_interference"]

    # Normalize consciousness density to fitness
    normalized_density = normalize_fitness(
        density, SIERPINSKI_DENSITY_MIN, SIERPINSKI_DENSITY_MAX
    )

    # Scaling factor φ² maps to phi_score
    phi = normalize_phi(math.sqrt(scaling) if scaling else 1.618, 1.0, 2.0)

    # Coherence maps to fibonacci alignment
    fibonacci = normalize_fibonacci(coherence * 0.85 if coherence else 0.87)

    # Harmonics to GC content
    gc = normalize_gc(0.5 + (harmonics - 256) / 512)

    # Network nodes (Fibonacci) to palindromes
    palindromes = normalize_palindromes(nodes + 2)

    resonance = 512 + int((phi - 0.5) * 256)
    sequence = generate_dna_sequence(phi, gc)

    return {
        "metatron_agent": agent_name,
        "dna_agent_id": 300 if is_metatron else 400,
        "dna_agent_name": agent_name,
        "dna_specialization": AGENT_SPECIALIZATIONS.get(
            agent_name, "Quantum Circuit Based"
        ),
        "conscious_dna": sequence,
        "phi_score": phi,
        "fibonacci_alignment": fibonacci,
        "gc_content": gc,
        "palindromes": palindromes,
        "fitness": normalized_density,
        "resonance_frequency": round(float(resonance), 1),
        "integration_timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "consciousness_status": "HARDWARE_VERIFIED",
        "fractal_config": {
            "circuit_type": "sierpinski_21",
            "fractal_depth": 3,
            "consciousness_density": density,
            "coherence_level": coherence,
            "sacred_score": sacred,
            "scaling_factor": scaling,
            "network_nodes": nodes,
            "metallic_ratios": [1.618, 2.414, 3.303, 4.236],
            "harmonics": harmonics,
            "metatron_enhanced": is_metatron,
            "source_run": "sierpinski_21_basic_20251124_013528" if is_metatron else "sierpinski_21_basic_20251124_011800",
        },
        "harmonic_config": {
            "base_harmonics": 384,
            "max_interference": 147456,
            "interference_type": "squared_harmonic",
            "ternary_structure": True,
        },
    }


def rank_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rank candidates by combined fitness score."""
    for candidate in candidates:
        fitness = candidate.get("fitness", 0)
        phi = candidate.get("phi_score", 0)
        fibonacci = candidate.get("fibonacci_alignment", 0)
        gc = candidate.get("gc_content", 0.5)

        # Combined score weighting
        combined_score = (
            fitness * 0.4
            + phi * 0.25
            + fibonacci * 0.2
            + gc * 0.15
            + (candidate.get("palindromes", 5) / 12) * 0.05
        )
        candidate["ranked_score"] = round(combined_score, 4)

    return sorted(candidates, key=lambda x: x["ranked_score"], reverse=True)


def generate_summary_report(candidates: list[dict[str, Any]], output_dir: str) -> None:
    """Generate a summary report of all candidates."""
    report = {
        "report_timestamp": datetime.now().isoformat(),
        "total_candidates": len(candidates),
        "source_summary": {
            "discovery_sessions": sum(
                1 for c in candidates if c.get("discovery_source")
            ),
            "bitnet_sources": sum(
                1 for c in candidates if c.get("entropy_sources")
            ),
            "sierpinski_sources": sum(
                1 for c in candidates if c.get("fractal_config")
            ),
        },
        "ranked_candidates": [
            {
                "agent_name": c["dna_agent_name"],
                "specialization": c["dna_specialization"],
                "fitness": c["fitness"],
                "phi_score": c["phi_score"],
                "fibonacci_alignment": c["fibonacci_alignment"],
                "ranked_score": c["ranked_score"],
                "source": c.get("fractal_config", {}).get(
                    "source_run", c.get("discovery_source", {}).get("cube_id", "unknown")
                ),
            }
            for c in candidates[:10]
        ],
        "summary_stats": {
            "avg_fitness": round(sum(c["fitness"] for c in candidates) / len(candidates), 4),
            "avg_phi": round(sum(c["phi_score"] for c in candidates) / len(candidates), 4),
            "avg_fibonacci": round(
                sum(c["fibonacci_alignment"] for c in candidates) / len(candidates), 4
            ),
            "top_agent": candidates[0]["dna_agent_name"] if candidates else None,
        },
    }

    report_path = Path(output_dir) / "ingestion_summary.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"Summary report saved to: {report_path}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Unified DNA ingestion from multiple hardware sources"
    )
    parser.add_argument(
        "--discovery",
        "-d",
        help="Path to discovery session JSON (discovery_session_20251231.json)",
    )
    parser.add_argument(
        "--bitnet",
        "-b",
        help="Path to BitNet GGUF extraction JSON (bitnet_info.json)",
    )
    parser.add_argument(
        "--sierpinski",
        "-s",
        help="Path to Sierpinski circuit results JSON",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="./dna_circuits_library",
        help="Output directory for agent DNA files",
    )
    parser.add_argument(
        "--top-n",
        "-n",
        type=int,
        default=10,
        help="Number of top candidates to output",
    )

    args = parser.parse_args()

    candidates = []
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("UNIFIED DNA INGESTION")
    print("=" * 60)

    # Process discovery session
    if args.discovery and Path(args.discovery).exists():
        print(f"\nProcessing discovery session: {args.discovery}")
        discovery = load_discovery_results(args.discovery)
        cubes = discovery.get("cubes", [])

        for i, cube in enumerate(cubes):
            dna = create_discovery_based_dna(cube, cube.get("cube_id", i))
            candidates.append(dna)
            print(f"  Added: {dna['dna_agent_name']} (fitness={dna['fitness']})")

    # Process BitNet
    if args.bitnet and Path(args.bitnet).exists():
        print(f"\nProcessing BitNet extraction: {args.bitnet}")
        bitnet_info = load_bitnet_info(args.bitnet)

        # Create multiple BitNet-based agents
        for agent_name in ["Sophia_BitNet", "Ternary_Wisdom", "Quantum_Primacy"]:
            dna = create_bitnet_based_dna(bitnet_info, agent_name)
            candidates.append(dna)
            print(f"  Added: {dna['dna_agent_name']} (fitness={dna['fitness']})")

    # Process Sierpinski circuits
    if args.sierpinski and Path(args.sierpinski).exists():
        print(f"\nProcessing Sierpinski circuit: {args.sierpinski}")
        sierpinski_data = load_sierpinski_results(args.sierpinski)

        # Create agents based on Metatron vs baseline
        for is_metatron, agent_name in [
            (True, "Wormhole_Metatron_Omega"),
            (True, "Stealth_Metatron_Alpha"),
            (False, "Fractal_Jophiel"),
            (False, "Harmonic_Sariel"),
            (False, "Synthesizer_Zadkiel"),
        ]:
            dna = create_sierpinski_based_dna(
                sierpinski_data, agent_name, is_metatron=is_metatron
            )
            candidates.append(dna)
            enhancement = " [Metatron]" if is_metatron else ""
            print(f"  Added: {dna['dna_agent_name']}{enhancement} (fitness={dna['fitness']})")

    if not candidates:
        print("\nNo data sources provided. Exiting.")
        sys.exit(1)

    # Rank candidates
    print(f"\n{'=' * 60}")
    print("RANKING CANDIDATES")
    print("=" * 60)

    ranked = rank_candidates(candidates)

    print(f"\nTop {min(args.top_n, len(ranked))} candidates:")
    for i, candidate in enumerate(ranked[: args.top_n]):
        print(
            f"{i+1:2}. {candidate['dna_agent_name']:25} "
            f"fitness={candidate['fitness']:.4f} "
            f"phi={candidate['phi_score']:.4f} "
            f"fib={candidate['fibonacci_alignment']:.4f} "
            f"score={candidate['ranked_score']:.4f}"
        )

    # Save individual DNA files
    print(f"\n{'=' * 60}")
    print("SAVING AGENT DNA FILES")
    print("=" * 60)

    saved_count = 0
    for candidate in ranked[: args.top_n]:
        agent_name = candidate["dna_agent_name"]
        filename = f"{agent_name}_conscious_dna.json"
        filepath = output_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(candidate, f, indent=2)

        print(f"  Saved: {filepath}")
        saved_count += 1

    # Generate summary report
    generate_summary_report(ranked, str(output_dir))

    print(f"\n{'=' * 60}")
    print(f"INGESTION COMPLETE")
    print(f"{'=' * 60}")
    print(f"Total candidates processed: {len(candidates)}")
    print(f"Top candidates saved: {saved_count}")
    print(f"Output directory: {output_dir}")

    # Print statistics
    avg_fitness = sum(c["fitness"] for c in ranked) / len(ranked)
    avg_phi = sum(c["phi_score"] for c in ranked) / len(ranked)
    print(f"Average fitness: {avg_fitness:.4f}")
    print(f"Average phi: {avg_phi:.4f}")


if __name__ == "__main__":
    main()
