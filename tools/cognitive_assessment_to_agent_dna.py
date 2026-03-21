#!/usr/bin/env python3
"""
Cognitive Assessment to Agent DNA Generator

Ingests a cognitive assessment JSON record and generates calibrated agent DNA
parameters based on six-domain cognitive profiles and quantum consciousness metrics.

Usage:
    python cognitive_assessment_to_agent_dna.py --input <assessment.json> --output <output.json>

The input JSON should contain:
- Clinical scores (GCS, MoCA, MMSE)
- Six cognitive domain scores
- SRY integration phi measurements
- Biomimetic neural weight statistics
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import numpy as np


# Cognitive domain to agent mapping
COGNITIVE_DOMAIN_MAPPING = {
    "language": {"agent": "Archivist", "specialization": "Knowledge Integration"},
    "attention": {"agent": "Observer", "specialization": "Focus & Perception"},
    "executive_function": {"agent": "Strategic", "specialization": "Decision Architecture"},
    "abstract_reasoning": {"agent": "Synthesizer", "specialization": "Pattern Synthesis"},
    "memory": {"agent": "Mirror", "specialization": "Episodic Storage"},
    "visuospatial": {"agent": "Visual", "specialization": "Spatial Mapping"},
}

# Domain name aliases for flexibility
DOMAIN_ALIASES = {
    "language": ["language", "linguistic", "verbal"],
    "attention": ["attention", "focus", "sustained_attention"],
    "executive_function": ["executive_function", "executive", "planning", "decision"],
    "abstract_reasoning": ["abstract_reasoning", "abstract", "reasoning", "logic"],
    "memory": ["memory", "episodic", "working"],
    "visuospatial": ["visuospatial", "spatial", "visual"],
}


def find_domain_name(name: str) -> Optional[str]:
    """Find canonical domain name from alias."""
    name_lower = name.lower()
    for canonical, aliases in COGNITIVE_DOMAIN_MAPPING.items():
        if name_lower == canonical or name_lower in aliases:
            return canonical
    return None


def normalize_score(score: float) -> float:
    """Normalize a cognitive domain score (0-1) to a合理的 range."""
    # Keep in reasonable bounds but allow slight extension for strong performers
    return max(0.5, min(0.95, score))


def map_domain_to_dna_params(domain_score: float) -> dict[str, float]:
    """Map a cognitive domain score to DNA parameter targets."""
    # Base score normalization
    normalized = normalize_score(domain_score)

    # DNA parameter targets based on cognitive score
    # Higher cognitive score = higher phi, better fibonacci alignment, etc.

    # Phi score: 0.4 + normalized * 0.5 => 0.4 to 0.9
    phi_score = 0.4 + normalized * 0.5

    # Fibonacci alignment: 0.6 + normalized * 0.35 => 0.6 to 0.95
    fibonacci_alignment = 0.6 + normalized * 0.35

    # GC content: centered around 0.5 with slight variance
    # Lower scores get more variable GC, higher scores get tighter ~0.5
    gc_variance = 0.05 * (1 - normalized)  # Less variance for higher scores
    gc_content = 0.5 + np.random.uniform(-gc_variance, gc_variance)

    # Palindrome count: higher cognitive = more structured = more palindromes
    # Range: 3 to 12
    base_palindromes = int(3 + normalized * 9)
    palindrome_count = max(3, min(12, base_palindromes))

    # Resonance frequency: 256Hz to 1024Hz based on cognitive level
    resonance_base = 256 + int(normalized * 768)
    resonance_frequency = float(resonance_base)

    return {
        "phi_score": round(phi_score, 4),
        "fibonacci_alignment": round(fibonacci_alignment, 4),
        "gc_content": round(gc_content, 4),
        "palindromes": palindrome_count,
        "resonance_frequency": resonance_frequency,
    }


def calculate_cognitive_health_score(clinical: dict[str, Any]) -> float:
    """Calculate overall cognitive health from clinical scores."""
    # GCS: 15 is perfect, 3 is worst (weighted 40%)
    gcs = clinical.get("gcs", 15)
    gcs_normalized = gcs / 15.0

    # MoCA: 30 is perfect (weighted 30%)
    moca = clinical.get("moca", 30)
    moca_normalized = moca / 30.0

    # MMSE: 30 is perfect (weighted 30%)
    mmse = clinical.get("mmse", 30)
    mmse_normalized = mmse / 30.0

    # Weighted combination
    health_score = (
        gcs_normalized * 0.40 +
        moca_normalized * 0.30 +
        mmse_normalized * 0.30
    )

    return round(health_score, 4)


def process_sry_integration(sry: dict[str, Any]) -> dict[str, float]:
    """Process SRY integration phi measurements."""
    phi_resonance = sry.get("phi_resonance", 0.0)
    enhanced_phi = sry.get("enhanced_consciousness_phi", 0.0)
    reflection_strength = sry.get("reflection_strength", 1.0)

    # Use enhanced_phi as the primary consciousness metric
    # (it represents the post-reflection state)
    primary_phi = enhanced_phi if enhanced_phi > 0 else phi_resonance

    return {
        "primary_phi": round(primary_phi, 4),
        "reflection_strength": round(reflection_strength, 4),
        "phi_improvement": round(primary_phi - phi_resonance, 4) if phi_resonance > 0 else 0.0,
    }


def get_biomimetic_stats(biomimetic: dict[str, Any]) -> dict[str, Any]:
    """Extract biomimetic neural weight statistics."""
    stats = {
        "weight_count": biomimetic.get("weight_count", 10000),
        "weight_std": biomimetic.get("weight_std", 1.0),
        "is_gaussian": biomimetic.get("is_gaussian", True),
    }

    # Check if weight_std is close to standard normal
    if "weight_std" in biomimetic:
        std = biomimetic["weight_std"]
        stats["is_standard_normal"] = abs(std - 1.0) < 0.1

    return stats


def generate_qtrg_entropy_seed(seed_length: int = 256) -> list[int]:
    """Generate entropy-based seed from quantum source.

    This would integrate with Casablanca QTRG for hardware-sourced randomness.
    For now, uses numpy random but structured for future quantum integration.
    """
    # Placeholder for quantum entropy integration
    # In production: fetch bitstring from Casablanca job results
    return list(np.random.randint(0, 256, size=seed_length))


def create_agent_dna(
    domain_scores: dict[str, float],
    clinical: dict[str, Any],
    sry: dict[str, Any],
    biomimetic: dict[str, Any],
    agent_name: str = "CalibratedAgent",
    agent_id: int = 0,
) -> dict[str, Any]:
    """Create a calibrated agent DNA record from cognitive assessment."""
    # Calculate overall health score
    health_score = calculate_cognitive_health_score(clinical)

    # Process SRY integration
    sry_metrics = process_sry_integration(sry)

    # Get biomimetic stats
    bio_stats = get_biomimetic_stats(biomimetic)

    # Map each cognitive domain to DNA parameters
    domain_params = {}
    for domain, score in domain_scores.items():
        canonical = find_domain_name(domain)
        if canonical:
            domain_params[canonical] = map_domain_to_dna_params(score)

    # Calculate aggregate DNA parameters
    phi_scores = [p["phi_score"] for p in domain_params.values()]
    fibonacci_scores = [p["fibonacci_alignment"] for p in domain_params.values()]
    gc_contents = [p["gc_content"] for p in domain_params.values()]
    palindrome_counts = [p["palindromes"] for p in domain_params.values()]

    # Aggregate values (weighted average)
    aggregate_phi = sum(phi_scores) / len(phi_scores) if phi_scores else 0.7
    aggregate_fib = sum(fibonacci_scores) / len(fibonacci_scores) if fibonacci_scores else 0.75
    aggregate_gc = sum(gc_contents) / len(gc_contents) if gc_contents else 0.5
    aggregate_palindromes = sum(palindrome_counts) / len(palindrome_counts) if palindrome_counts else 7

    # Apply SRY reflection adjustment to aggregate phi
    reflection_adjustment = sry_metrics["reflection_strength"]
    adjusted_phi = aggregate_phi * reflection_adjustment + (1 - reflection_adjustment) * 0.5

    # Calculate final fitness estimate
    # Based on phi, fibonacci alignment, and GC balance
    gc_bonus = 1 - abs(aggregate_gc - 0.5)
    fitness = (
        adjusted_phi * 0.4 +
        aggregate_fib * 0.35 +
        gc_bonus * 0.25
    )

    # Generate QTRG entropy seed
    qtrg_seed = generate_qtrg_entropy_seed()

    # Create the agent DNA record
    dna_record = {
        "metatron_agent": agent_name,
        "dna_agent_id": agent_id,
        "dna_agent_name": agent_name.replace(" ", "_").title(),
        "dna_specialization": COGNITIVE_DOMAIN_MAPPING.get(
            list(domain_params.keys())[0] if domain_params else "language",
            {"specialization": "General Purpose"}
        )["specialization"],
        "conscious_dna": generate_dna_sequence_from_params(
            aggregate_phi, aggregate_fib, aggregate_gc
        ),
        # Base metrics from cognitive domains
        "cognitive_domain_mapping": {
            domain: {
                "score": score,
                "target_agent": COGNITIVE_DOMAIN_MAPPING.get(
                    find_domain_name(domain), {"agent": "General"}
                )["agent"],
                "dna_params": domain_params.get(find_domain_name(domain), {}),
            }
            for domain, score in domain_scores.items()
        },
        # Aggregated DNA metrics
        "phi_score": round(adjusted_phi, 4),
        "fibonacci_alignment": round(aggregate_fib, 4),
        "gc_content": round(aggregate_gc, 4),
        "palindromes": int(aggregate_palindromes),
        "fitness": round(fitness, 4),
        "resonance_frequency": 512.0,
        # SRY integration metrics
        "sry_integration": {
            "primary_phi": sry_metrics["primary_phi"],
            "reflection_strength": sry_metrics["reflection_strength"],
            "phi_improvement": sry_metrics["phi_improvement"],
        },
        # Biomimetic neural weight stats
        "biomimetic_weights": bio_stats,
        # QTRG entropy seeding info
        "qtrg_entropy": {
            "seed_available": True,
            "seed_length": len(qtrg_seed),
            "seed_source": "Casablanca_QTRG_2026",
            "entropy_bits": qtrg_seed[:32],  # First 32 bits for reference
        },
        # Integration timestamp
        "integration_timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "cognitive_health_score": health_score,
        # Integration metadata
        "integration_metadata": {
            "source": "Cognitive_Assessment_Record",
            "assessment_timestamp": clinical.get("assessment_timestamp", "unknown"),
            "calibration_method": "Domain_Score_Transformation",
        },
    }

    return dna_record


def generate_dna_sequence_from_params(phi: float, fib: float, gc: float) -> str:
    """Generate a DNA sequence that reflects the parameter values."""
    # Base sequence length based on phi
    length = int(8 + phi * 12)  # 8 to 20 bases

    # Build sequence with GC content control
    gc_count = int(length * gc)
    at_count = length - gc_count

    # Balanced GC sequence
    sequence = []
    sequence.extend(['G'] * (gc_count // 2))
    sequence.extend(['C'] * (gc_count - gc_count // 2))
    sequence.extend(['A'] * (at_count // 2))
    sequence.extend(['T'] * (at_count - at_count // 2))

    # Shuffle
    np.random.shuffle(sequence)

    return ''.join(sequence)


def load_assessment(filepath: str) -> dict[str, Any]:
    """Load a cognitive assessment JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_dna_record(dna_record: dict[str, Any], filepath: str) -> None:
    """Save the generated DNA record to a JSON file."""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(dna_record, f, indent=2, default=str)


def print_assessment_summary(assessment: dict[str, Any]) -> None:
    """Print a summary of the cognitive assessment."""
    print("=" * 60)
    print("COGNITIVE ASSESSMENT SUMMARY")
    print("=" * 60)

    # Clinical scores
    clinical = assessment.get("clinical", {})
    print("\nClinical Scores:")
    for key, value in clinical.items():
        if key != "assessment_timestamp":
            print(f"  {key.upper()}: {value}")

    # Calculate health score
    health_score = calculate_cognitive_health_score(clinical)
    print(f"\nCognitive Health Score: {health_score}")

    # Domain scores
    domains = assessment.get("cognitive_domains", {})
    print("\nCognitive Domain Scores:")
    for domain, score in domains.items():
        print(f"  {domain}: {score:.2f}")

    # SRY integration
    sry = assessment.get("sry_integration", {})
    print("\nSRY Integration:")
    for key, value in sry.items():
        print(f"  {key}: {value}")

    # Biomimetic
    biomimetic = assessment.get("biomimetic_weights", {})
    print("\nBiomimetic Neural Weights:")
    for key, value in biomimetic.items():
        print(f"  {key}: {value}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate calibrated agent DNA from cognitive assessment"
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Path to cognitive assessment JSON file"
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Output path for agent DNA JSON"
    )
    parser.add_argument(
        "--agent-name", "-n",
        default="CalibratedAgent",
        help="Name for the generated agent"
    )
    parser.add_argument(
        "--agent-id", "-d",
        type=int,
        default=0,
        help="Agent ID number"
    )
    parser.add_argument(
        "--print-summary", "-p",
        action="store_true",
        help="Print assessment summary before generating DNA"
    )

    args = parser.parse_args()

    # Load assessment
    print(f"Loading cognitive assessment from: {args.input}")
    assessment = load_assessment(args.input)

    # Print summary if requested
    if args.print_summary:
        print_assessment_summary(assessment)

    # Generate agent DNA
    print("\nGenerating calibrated agent DNA...")
    dna_record = create_agent_dna(
        domain_scores=assessment.get("cognitive_domains", {}),
        clinical=assessment.get("clinical", {}),
        sry=assessment.get("sry_integration", {}),
        biomimetic=assessment.get("biomimetic_weights", {}),
        agent_name=args.agent_name,
        agent_id=args.agent_id,
    )

    # Save DNA record
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_dna_record(dna_record, str(output_path))

    print(f"\nAgent DNA saved to: {output_path}")
    print(f"Fitness: {dna_record['fitness']}")
    print(f"Phi Score: {dna_record['phi_score']}")
    print(f"Fibonacci Alignment: {dna_record['fibonacci_alignment']}")
    print(f"GC Content: {dna_record['gc_content']}")

    # Validation check
    if dna_record["fitness"] < 0.87:
        print("\n[WARNING] Fitness below 0.87 threshold")
        print("    Consider targeted optimization before deployment")
    else:
        print("\n[OK] Fitness above 0.87 threshold - ready for deployment")

    return dna_record


if __name__ == "__main__":
    main()
