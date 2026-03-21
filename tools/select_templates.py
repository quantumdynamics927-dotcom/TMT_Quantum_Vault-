#!/usr/bin/env python3
"""
Template Selection Script

Selects high-quality DNA circuits from the ingested library to use as templates
for generating new agent DNA variants.

Workflow:
1. Load the DNA circuits library
2. Filter by minimum quality threshold
3. Identify best templates based on various criteria
4. Generate template summary report
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def load_library(library_path: str) -> list[dict[str, Any]]:
    """Load the DNA circuits library."""
    with open(library_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def filter_by_threshold(circuits: list[dict[str, Any]], min_score: float = 10.0) -> list[dict[str, Any]]:
    """Filter circuits by minimum rank score."""
    return [c for c in circuits if c.get('rank_score', 0) >= min_score]


def select_best_templates(
    circuits: list[dict[str, Any]],
    top_n: int = 5
) -> list[dict[str, Any]]:
    """Select the top N circuits by rank score."""
    sorted_circuits = sorted(circuits, key=lambda x: x.get('rank_score', 0), reverse=True)
    return sorted_circuits[:top_n]


def identify_unique_template_types(circuits: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Identify unique template types based on circuit characteristics."""
    types = {
        'high_consciousness_phi': [],
        'high_fibonacci_enhancement': [],
        'high_hamming_mean': [],
        'balanced_gc': [],
    }

    for circuit in circuits:
        dna_metrics = circuit.get('dna_metrics', {})

        if dna_metrics.get('consciousness_phi', 0) > 0.8:
            types['high_consciousness_phi'].append(circuit['circuit_id'])

        if dna_metrics.get('fibonacci_enhancement', 0) > 1.05:
            types['high_fibonacci_enhancement'].append(circuit['circuit_id'])

        if dna_metrics.get('hamming_watson_mean', 0) > 18:
            types['high_hamming_mean'].append(circuit['circuit_id'])

        gc = dna_metrics.get('gc_content', 0)
        if 0.45 <= gc <= 0.55:
            types['balanced_gc'].append(circuit['circuit_id'])

    # Remove empty categories
    return {k: v for k, v in types.items() if v}


def calculate_template_diversity(templates: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate diversity metrics for the selected templates."""
    scores = [t.get('rank_score', 0) for t in templates]
    metrics = [t.get('dna_metrics', {}) for t in templates]

    diversity = {
        'score_range': {
            'min': min(scores),
            'max': max(scores),
            'range': max(scores) - min(scores),
        },
        'unique_factors': list(set(
            factor
            for t in templates
            for factor in t.get('rank_factors', [])
        )),
        'unique_sources': list(set(
            os.path.basename(t.get('source_file', ''))
            for t in templates
        )),
    }

    return diversity


def generate_template_report(
    templates: list[dict[str, Any]],
    diversity: dict[str, Any],
    output_path: str
) -> None:
    """Generate a template selection report."""
    report = {
        'report_timestamp': datetime.now().isoformat(),
        'total_templates': len(templates),
        'templates': [
            {
                'circuit_id': t['circuit_id'],
                'rank_position': t.get('rank_position'),
                'rank_score': t.get('rank_score'),
                'rank_factors': t.get('rank_factors', []),
                'dna_metrics': t.get('dna_metrics', {}),
                'source_file': t.get('source_file'),
            }
            for t in templates
        ],
        'diversity': diversity,
        'summary': {
            'top_score': diversity['score_range']['max'],
            'score_spread': diversity['score_range']['range'],
            'unique_factors': len(diversity['unique_factors']),
            'unique_sources': len(diversity['unique_sources']),
        },
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, default=str)

    print(f"Report saved to: {output_path}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Select DNA circuit templates from the ingested library'
    )
    parser.add_argument(
        '--library', '-l',
        default='./dna_circuits_library/dna_circuits_library.json',
        help='Path to the DNA circuits library'
    )
    parser.add_argument(
        '--dest', '-d',
        default='./dna_circuits_library',
        help='Destination directory for templates'
    )
    parser.add_argument(
        '--min-score', '-m',
        type=float,
        default=10.0,
        help='Minimum rank score for template selection'
    )
    parser.add_argument(
        '--top-n', '-n',
        type=int,
        default=5,
        help='Number of top circuits to select as templates'
    )

    args = parser.parse_args()

    library_path = Path(args.library)
    dest_path = Path(args.dest)

    if not library_path.exists():
        print(f"Error: Library file not found: {library_path}")
        sys.exit(1)

    # Load and filter circuits
    print(f"Loading library from: {library_path}")
    circuits = load_library(str(library_path))
    print(f"Total circuits in library: {len(circuits)}")

    # Filter by minimum score
    filtered = filter_by_threshold(circuits, args.min_score)
    print(f"Circuits above score {args.min_score}: {len(filtered)}")

    # Select top templates
    templates = select_best_templates(filtered, args.top_n)
    print(f"Selected {len(templates)} templates")

    # Calculate diversity
    diversity = calculate_template_diversity(templates)

    # Create destination directory
    dest_path.mkdir(parents=True, exist_ok=True)

    # Save templates
    templates_path = dest_path / 'templates.json'
    with open(templates_path, 'w', encoding='utf-8') as f:
        json.dump(templates, f, indent=2, default=str)
    print(f"Templates saved to: {templates_path}")

    # Generate report
    report_path = dest_path / 'template_selection_report.json'
    generate_template_report(templates, diversity, str(report_path))

    # Print summary
    print("\n" + "=" * 60)
    print("TEMPLATE SELECTION SUMMARY")
    print("=" * 60)
    print(f"Top {len(templates)} templates:")
    for i, t in enumerate(templates, 1):
        print(f"\n{i}. {t['circuit_id']}")
        print(f"   Rank: {t.get('rank_position')} | Score: {t.get('rank_score')}")
        print(f"   Factors: {', '.join(t.get('rank_factors', []))}")

    print(f"\nDiversity Analysis:")
    print(f"  Score range: {diversity['score_range']['min']:.2f} - {diversity['score_range']['max']:.2f}")
    print(f"  Unique factors: {len(diversity['unique_factors'])}")
    print(f"  Unique sources: {len(diversity['unique_sources'])}")

    print("\nNext steps:")
    print("  1. Review templates in:", dest_path)
    print("  2. Generate variants from high-scoring templates")
    print("  3. Validate new circuits on IBM hardware")


if __name__ == '__main__':
    main()
