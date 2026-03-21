#!/usr/bin/env python3
"""
DNA Circuit Variant Generator

Generates new DNA circuit variants from selected templates by applying
controlled mutations and parameter adjustments.

Workflow:
1. Load templates from the template library
2. Apply controlled mutations to generate variants
3. Calculate metrics for new variants
4. Validate and output new circuit definitions
"""

import json
import os
import random
from datetime import datetime
from pathlib import Path
from typing import Any


def load_templates(templates_path: str) -> list[dict[str, Any]]:
    """Load templates from the template library."""
    with open(templates_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_dna_sequence(length: int = 10, gc_target: float = 0.5) -> str:
    """Generate a DNA sequence with controlled GC content."""
    bases = ['A', 'T', 'C', 'G']
    gc_count = int(length * gc_target)
    at_count = length - gc_count

    # Create balanced sequence
    sequence = ['G'] * (gc_count // 2)
    sequence += ['C'] * (gc_count - gc_count // 2)
    sequence += ['A'] * (at_count // 2)
    sequence += ['T'] * (at_count - at_count // 2)

    # Fill remaining positions
    while len(sequence) < length:
        sequence.append(random.choice(bases))

    # Shuffle to avoid patterns
    random.shuffle(sequence)

    return ''.join(sequence)


def mutate_sequence(sequence: str, mutation_rate: float = 0.1) -> str:
    """Apply random mutations to a DNA sequence."""
    bases = ['A', 'T', 'C', 'G']
    result = list(sequence)

    for i in range(len(result)):
        if random.random() < mutation_rate:
            result[i] = random.choice([b for b in bases if b != result[i]])

    return ''.join(result)


def adjust_gc_content(sequence: str, target_gc: float) -> str:
    """Adjust GC content of a sequence by swapping bases."""
    gc_count = sequence.count('G') + sequence.count('C')
    total = len(sequence)

    current_gc = gc_count / total if total > 0 else 0
    diff = target_gc - current_gc

    # Calculate how many bases to swap
    swap_count = int(abs(diff) * total / 2)

    result = list(sequence)

    if diff > 0:
        # Need more GC
        for i in range(len(result)):
            if result[i] in ['A', 'T'] and swap_count > 0:
                result[i] = random.choice(['G', 'C'])
                swap_count -= 1
    else:
        # Need less GC
        for i in range(len(result)):
            if result[i] in ['G', 'C'] and swap_count > 0:
                result[i] = random.choice(['A', 'T'])
                swap_count -= 1

    return ''.join(result)


def create_variant(
    template: dict[str, Any],
    variant_id: str,
    mutation_rate: float = 0.15,
    gc_adjustment: float = 0.05,
) -> dict[str, Any]:
    """Create a variant from a template circuit."""
    dna_metrics = template.get('dna_metrics', {})
    metadata = template.get('metadata', {})

    # Generate new DNA sequence
    original_seq = dna_metrics.get('dna_sequence', 'ACGTACGTAC')
    length = dna_metrics.get('length', len(original_seq))

    # Adjust GC target
    target_gc = dna_metrics.get('gc_content', 0.5)
    if gc_adjustment != 0:
        target_gc = max(0.3, min(0.7, target_gc + gc_adjustment))

    # Generate new sequence
    new_seq = generate_dna_sequence(length, target_gc)

    # Apply mutations
    new_seq = mutate_sequence(new_seq, mutation_rate)

    # Adjust final GC content
    new_seq = adjust_gc_content(new_seq, target_gc)

    # Calculate new metrics
    new_gc = (new_seq.count('G') + new_seq.count('C')) / len(new_seq) if new_seq else 0

    # Estimate consciousness phi based on original
    orig_phi = dna_metrics.get('consciousness_phi', 0.5)
    # Variant phi is slightly lower than original (with some variance)
    variant_phi = max(0.3, min(0.95, orig_phi * (0.9 + random.random() * 0.2)))

    variant = {
        'variant_id': variant_id,
        'template_circuit_id': template['circuit_id'],
        'created_at': datetime.now().isoformat(),
        'dna_sequence': new_seq,
        'dna_metrics': {
            'length': len(new_seq),
            'gc_content': round(new_gc, 4),
            'palindrome_score': sum(
                1 for i in range(len(new_seq) // 2)
                if new_seq[i] == {'A': 'T', 'T': 'A', 'C': 'G', 'G': 'C'}.get(new_seq[-(i+1)])
            ),
            'phi_approx': round(0.5 + 0.1 * (new_gc - 0.5) ** 2, 4),
            'estimated_phi': round(variant_phi, 4),
        },
        'variant_parameters': {
            'mutation_rate': mutation_rate,
            'gc_adjustment': gc_adjustment,
            'original_gc': dna_metrics.get('gc_content', 0),
        },
        'metadata': metadata.copy() if metadata else {},
    }

    # Copy special metrics if available
    for key in ['consciousness_phi', 'fibonacci_enhancement', 'fibonacci_mean_activation',
                'hamming_watson_mean', 'hamming_crick_mean', 'hamming_bridge_mean']:
        if key in dna_metrics:
            variant['dna_metrics'][key] = dna_metrics[key]

    return variant


def generate_variants(
    templates: list[dict[str, Any]],
    variants_per_template: int = 3,
    mutation_rates: list[float] = None,
) -> list[dict[str, Any]]:
    """Generate variants from multiple templates."""
    if mutation_rates is None:
        mutation_rates = [0.1, 0.15, 0.2]

    variants = []
    variant_counter = 0

    for template in templates:
        for i in range(variants_per_template):
            # Use different mutation rate for variety
            mutation_rate = mutation_rates[i % len(mutation_rates)]

            # Calculate GC adjustment
            gc_adjustment = random.uniform(-0.05, 0.05)

            variant_id = f"VAR_{template['circuit_id'].replace('CIR_', '')}_{variant_counter:03d}"
            variant = create_variant(
                template,
                variant_id,
                mutation_rate=mutation_rate,
                gc_adjustment=gc_adjustment,
            )
            variants.append(variant)
            variant_counter += 1

    return variants


def score_variant(variant: dict[str, Any]) -> tuple[float, list[str]]:
    """Score a variant and return factors."""
    score = 0
    factors = []
    dna_metrics = variant.get('dna_metrics', {})

    # Score based on estimated phi
    estimated_phi = dna_metrics.get('estimated_phi', 0.5)
    score += estimated_phi * 50
    factors.append(f"est_phi={estimated_phi:.4f}")

    # Score based on GC content
    gc = dna_metrics.get('gc_content', 0.5)
    gc_score = 1 - abs(gc - 0.5)
    score += gc_score * 10
    factors.append(f"gc={gc:.2f}")

    # Score based on palindrome count
    palindromes = dna_metrics.get('palindrome_score', 0)
    score += palindromes * 0.5
    factors.append(f"palindromes={palindromes}")

    return round(score, 2), factors


def rank_variants(variants: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rank variants by their scores."""
    for variant in variants:
        score, factors = score_variant(variant)
        variant['score'] = score
        variant['factors'] = factors

    return sorted(variants, key=lambda x: x.get('score', 0), reverse=True)


def save_variants(variants: list[dict[str, Any]], output_path: str) -> None:
    """Save variants to JSON file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(variants, f, indent=2, default=str)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Generate DNA circuit variants from templates'
    )
    parser.add_argument(
        '--templates', '-t',
        default='./dna_circuits_library/templates.json',
        help='Path to the templates file'
    )
    parser.add_argument(
        '--dest', '-d',
        default='./dna_circuits_library',
        help='Destination directory for variants'
    )
    parser.add_argument(
        '--variants-per-template', '-n',
        type=int,
        default=3,
        help='Number of variants to generate per template'
    )
    parser.add_argument(
        '--seed', '-s',
        type=int,
        default=42,
        help='Random seed for reproducibility'
    )

    args = parser.parse_args()

    random.seed(args.seed)

    templates_path = Path(args.templates)
    dest_path = Path(args.dest)

    if not templates_path.exists():
        print(f"Error: Templates file not found: {templates_path}")
        sys.exit(1)

    # Load templates
    print(f"Loading templates from: {templates_path}")
    templates = load_templates(str(templates_path))
    print(f"Loaded {len(templates)} templates")

    # Generate variants
    print(f"Generating {args.variants_per_template} variants per template...")
    variants = generate_variants(
        templates,
        variants_per_template=args.variants_per_template
    )
    print(f"Generated {len(variants)} variants")

    # Rank variants
    ranked_variants = rank_variants(variants)

    # Create destination directory
    dest_path.mkdir(parents=True, exist_ok=True)

    # Save variants
    variants_path = dest_path / 'variants.json'
    save_variants(ranked_variants, str(variants_path))
    print(f"Variants saved to: {variants_path}")

    # Print summary
    print("\n" + "=" * 60)
    print("VARIANT GENERATION SUMMARY")
    print("=" * 60)
    print(f"Templates used: {len(templates)}")
    print(f"Variants generated: {len(variants)}")
    print(f"Top 5 variants:")
    for i, v in enumerate(ranked_variants[:5], 1):
        print(f"\n{i}. {v['variant_id']}")
        print(f"   Template: {v['template_circuit_id']}")
        print(f"   Score: {v['score']}")
        print(f"   Factors: {', '.join(v['factors'])}")
        print(f"   Sequence: {v['dna_sequence'][:20]}...")

    print("\nNext steps:")
    print("  1. Review variants in:", dest_path)
    print("  2. Validate top variants on IBM hardware")
    print("  3. Promote winners to new agents")


if __name__ == '__main__':
    main()
