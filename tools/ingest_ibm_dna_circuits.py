#!/usr/bin/env python3
"""
IBM Quantum DNA Circuit Ingestion Script

This script ingests validated DNA circuits from TMT-OS (D:\tmt-os) into the
TMT Quantum Vault structure for use as templates in the staged optimization workflow.

Workflow stages:
1. Ingest old circuits, job results, backend metadata, and DNA-to-qubit mappings
2. Rank circuits by quality and relevance
3. Select best circuits as templates
4. Generate new circuit variants
5. Validate on IBM hardware
6. Promote winners to new agents

Usage:
    python ingest_ibm_dna_circuits.py --source D:\tmt-os --dest ./dna_circuits_library
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add tmt_quantum_vault to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def load_json_file(filepath: str) -> dict[str, Any]:
    """Load and parse a JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_dna_sequence_from_json(filepath: str) -> str | None:
    """Extract DNA sequence from JSON file if present."""
    try:
        data = load_json_file(filepath)

        # Direct sequence field
        if 'sequence' in data:
            seq = data['sequence']
            if isinstance(seq, str) and all(c in 'ACGTacgt' for c in seq):
                return seq.upper()

        # In some formats, it might be nested
        if 'circuit_info' in data:
            if 'sequence' in data['circuit_info']:
                seq = data['circuit_info']['sequence']
                if isinstance(seq, str) and all(c in 'ACGTacgt' for c in seq):
                    return seq.upper()

        return None
    except Exception:
        return None


def extract_dna_sequence_from_qasm(filepath: str) -> str | None:
    """Extract DNA sequence from QASM file if present."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Look for common DNA patterns in QASM files
        import re
        # Pattern for explicit sequence declarations
        patterns = [
            r'dna_sequence["\']?\s*[:=]\s*["\']?([ACGT]+)["\']?',
            r'ACGT[ACGT]*',  # Standard DNA pattern
            r'[ACGT]{4,}',  # 4+ base sequences
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(0).upper()

        return None
    except Exception:
        return None


def calculate_dna_metrics(sequence: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    """Calculate standard DNA metrics for a sequence."""
    if not sequence:
        return {}

    seq = sequence.upper()
    n = len(seq)

    # GC Content
    gc_count = seq.count('G') + seq.count('C')
    gc_content = gc_count / n if n > 0 else 0

    # Palindrome detection (simplified)
    palindromes = 0
    for i in range(n // 2):
        complement_map = {'A': 'T', 'T': 'A', 'C': 'G', 'G': 'C'}
        if seq[i] == complement_map.get(seq[n - 1 - i]):
            palindromes += 1

    # Basic phi approximation from sequence pattern
    # (This is a heuristic - actual phi comes from vault evaluation)
    phi_score = 0.5 + 0.1 * (gc_content - 0.5) ** 2

    # Build metrics dictionary
    metrics = {
        'length': n,
        'gc_content': round(gc_content, 4),
        'palindrome_score': palindromes,
        'phi_approx': round(phi_score, 4),
    }

    # Add special metrics from metadata if present
    if metadata:
        # Add consciousness peak if present (strong indicator)
        if 'consciousness_peak' in metadata:
            peak = metadata['consciousness_peak']
            if 'phi_score_at_20' in peak:
                metrics['consciousness_phi'] = round(peak['phi_score_at_20'], 4)
            if 'activation_at_20' in peak:
                metrics['consciousness_activation'] = round(peak['activation_at_20'], 4)

        # Add fibonacci clustering if present
        if 'fibonacci_clustering' in metadata:
            fib = metadata['fibonacci_clustering']
            if 'enhancement' in fib:
                metrics['fibonacci_enhancement'] = round(fib['enhancement'], 4)
            if 'mean_activation_fib' in fib:
                metrics['fibonacci_mean_activation'] = round(fib['mean_activation_fib'], 4)

    return metrics


def create_circuit_entry(
    filepath: str,
    metadata: dict[str, Any],
    dna_sequence: str | None = None
) -> dict[str, Any]:
    """Create a standardized circuit entry for the library."""
    filename = os.path.basename(filepath)

    entry = {
        'circuit_id': f"CIR_{filename.replace('.', '_').lower()}",
        'source_file': filepath,
        'circuit_type': 'dna_quantum',
        'created_at': datetime.now().isoformat(),
        'metadata': metadata,
    }

    # Extract DNA metrics from various sources
    dna_metrics = {}

    # Get special metrics from metadata if present
    if metadata:
        # Add consciousness peak if present (strong indicator)
        if 'consciousness_peak' in metadata:
            peak = metadata['consciousness_peak']
            if 'phi_score_at_20' in peak:
                dna_metrics['consciousness_phi'] = round(peak['phi_score_at_20'], 4)
            if 'activation_at_20' in peak:
                dna_metrics['consciousness_activation'] = round(peak['activation_at_20'], 4)

        # Add fibonacci clustering if present
        if 'fibonacci_clustering' in metadata:
            fib = metadata['fibonacci_clustering']
            if 'enhancement' in fib:
                dna_metrics['fibonacci_enhancement'] = round(fib['enhancement'], 4)
            if 'mean_activation_fib' in fib:
                dna_metrics['fibonacci_mean_activation'] = round(fib['mean_activation_fib'], 4)

        # Add hamming weight info
        if 'hamming_weight' in metadata:
            hw = metadata['hamming_weight']
            if 'watson_mean' in hw:
                dna_metrics['hamming_watson_mean'] = round(hw['watson_mean'], 4)
            if 'crick_mean' in hw:
                dna_metrics['hamming_crick_mean'] = round(hw['crick_mean'], 4)
            if 'bridge_mean' in hw:
                dna_metrics['hamming_bridge_mean'] = round(hw['bridge_mean'], 4)

    # Add DNA metrics if sequence available
    if dna_sequence:
        seq_metrics = calculate_dna_metrics(dna_sequence, metadata)
        # Merge with metadata-derived metrics (metadata takes precedence)
        dna_metrics = {**seq_metrics, **dna_metrics}
        entry['dna_sequence'] = dna_sequence

    # Only add dna_metrics if we have any useful data
    if dna_metrics:
        entry['dna_metrics'] = dna_metrics

    return entry


def ingest_dna_results(dna_results_file: str) -> list[dict[str, Any]]:
    """Ingest DNA quantum results from IBM jobs."""
    data = load_json_file(dna_results_file)
    results = []

    # Handle different result file formats
    if 'jobs' in data:
        # Format: Multiple jobs with backend info
        for job in data['jobs']:
            entry = {
                'job_id': job.get('job_id', 'unknown'),
                'backend': job.get('backend', 'unknown'),
                'shots': job.get('shots', 1000),
                'qubits': job.get('qubits', 0),
                'original_depth': job.get('original_depth', 0),
                'transpiled_depth': job.get('transpiled_depth', 0),
            }
            results.append(entry)

    if 'results' in data:
        # Format: Phi DNA structures with multiple sequences
        for seq_name, metrics in data['results'].items():
            entry = {
                'sequence_name': seq_name,
                'phi_correlation': metrics.get('phi_correlation', 0),
                'fractal_dimension': metrics.get('fractal_dimension', 0),
                'quantum_coherence': metrics.get('quantum_coherence', 0),
            }
            results.append(entry)

    return results


def rank_circuits(circuits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rank circuits by quality metrics."""
    ranked = []

    for circuit in circuits:
        score = 0
        factors = []

        # Score based on DNA metrics (from vault evaluation)
        if 'fitness' in circuit:
            fitness = circuit['fitness']
            score += fitness * 100
            factors.append(f"fitness={fitness:.4f}")

        if 'phi_score' in circuit:
            phi = circuit['phi_score']
            if phi > 0.5:
                score += 20
            factors.append(f"phi={phi:.4f}")

        if 'fibonacci_alignment' in circuit:
            fib = circuit['fibonacci_alignment']
            if fib > 0.8:
                score += 15
            factors.append(f"fibonacci={fib:.4f}")

        # Special metrics from IBM job results
        if 'dna_metrics' in circuit:
            metrics = circuit['dna_metrics']

            # Consciousness phi (strong indicator of quality)
            if 'consciousness_phi' in metrics:
                c_phi = metrics['consciousness_phi']
                score += c_phi * 50
                factors.append(f"conc_phi={c_phi:.4f}")

            # Fibonacci enhancement (bonus for > 1.0)
            if 'fibonacci_enhancement' in metrics:
                fib_enh = metrics['fibonacci_enhancement']
                if fib_enh > 1.0:
                    score += (fib_enh - 1) * 30
                factors.append(f"fib_enh={fib_enh:.4f}")

            # Fibonacci mean activation
            if 'fibonacci_mean_activation' in metrics:
                fib_act = metrics['fibonacci_mean_activation']
                if fib_act > 0.3:
                    score += fib_act * 20
                factors.append(f"fib_act={fib_act:.4f}")

            # Hamming weight metrics (quality indicator)
            if 'hamming_watson_mean' in metrics:
                hw = metrics['hamming_watson_mean']
                if hw > 15:
                    score += hw * 0.5
                factors.append(f"ham_watson={hw:.2f}")

            # Basic sequence metrics
            if 'gc_content' in metrics:
                gc = metrics['gc_content']
                # GC ~0.5 is ideal for DNA stability
                gc_score = 1 - abs(gc - 0.5)
                score += gc_score * 5
                factors.append(f"gc={gc:.2f}")

            if 'palindrome_score' in metrics:
                pals = metrics['palindrome_score']
                if pals > 0:
                    score += pals * 0.5
                factors.append(f"palindromes={pals}")

        # Backend quality (Torino > Fez for general quality)
        if 'backend' in circuit:
            backend = circuit['backend']
            if 'torino' in backend:
                score += 5
                factors.append("backend=ibm_torino")
            elif 'fez' in backend:
                score += 3
                factors.append("backend=ibm_fez")

        # Job result quality
        if 'counts' in circuit:
            counts = circuit['counts']
            if isinstance(counts, dict):
                # More unique counts = better coherence
                unique_states = len(counts)
                score += min(unique_states, 50) * 0.1
                factors.append(f"unique_states={unique_states}")

        # High shot count indicates quality runs
        if 'shots' in circuit:
            shots = circuit['shots']
            if shots >= 10000:
                score += 5
                factors.append(f"shots={shots:,}")

        circuit['rank_score'] = round(score, 2)
        circuit['rank_factors'] = factors
        ranked.append(circuit)

    # Sort by score descending
    ranked.sort(key=lambda x: x.get('rank_score', 0), reverse=True)

    # Add rank position
    for i, circuit in enumerate(ranked):
        circuit['rank_position'] = i + 1

    return ranked


def generate_ingestion_report(
    circuits: list[dict[str, Any]],
    output_path: str
) -> None:
    """Generate an ingestion summary report."""
    report = {
        'ingestion_timestamp': datetime.now().isoformat(),
        'total_circuits': len(circuits),
        'quality_distribution': {
            'excellent (score > 150)': len([c for c in circuits if c.get('rank_score', 0) > 150]),
            'good (score 100-150)': len([c for c in circuits if 100 <= c.get('rank_score', 0) <= 150]),
            'fair (score 50-100)': len([c for c in circuits if 50 <= c.get('rank_score', 0) < 100]),
            'low (score < 50)': len([c for c in circuits if c.get('rank_score', 0) < 50]),
        },
        'top_circuits': circuits[:10],
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, default=str)

    print(f"Report saved to: {output_path}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Ingest IBM Quantum DNA circuits into the vault library'
    )
    parser.add_argument(
        '--source', '-s',
        default='D:/tmt-os',
        help='Source directory containing TMT-OS quantum data'
    )
    parser.add_argument(
        '--dest', '-d',
        default='./dna_circuits_library',
        help='Destination directory for the DNA circuits library'
    )

    args = parser.parse_args()

    source_path = Path(args.source)
    dest_path = Path(args.dest)

    if not source_path.exists():
        print(f"Error: Source directory not found: {source_path}")
        sys.exit(1)

    # Create destination directory
    dest_path.mkdir(parents=True, exist_ok=True)

    print(f"Ingesting DNA circuits from: {source_path}")
    print(f"Destination: {dest_path}")

    # Discover DNA-related files
    dna_files = []
    for ext in ['*.json', '*.qasm']:
        dna_files.extend(source_path.rglob(ext))

    dna_files = [f for f in dna_files if 'dna' in f.name.lower() or 'qasm' in f.name.lower()]

    print(f"Found {len(dna_files)} DNA/QASM files")

    # Process files
    circuits = []
    for filepath in dna_files:
        try:
            if filepath.suffix == '.json':
                data = load_json_file(str(filepath))

                # Extract sequence if present (check both JSON and QASM)
                sequence = extract_dna_sequence_from_json(str(filepath))
                if not sequence:
                    sequence = extract_dna_sequence_from_qasm(str(filepath))

                entry = create_circuit_entry(
                    str(filepath),
                    data,
                    dna_sequence=sequence
                )
                circuits.append(entry)

            elif filepath.suffix == '.qasm':
                # QASM file - extract basic info
                sequence = extract_dna_sequence_from_qasm(str(filepath))
                entry = create_circuit_entry(
                    str(filepath),
                    {'file_type': 'qasm'},
                    dna_sequence=sequence
                )
                circuits.append(entry)

        except Exception as e:
            print(f"Warning: Could not process {filepath}: {e}")
            continue

    print(f"Ingested {len(circuits)} circuit entries")

    # Rank circuits
    ranked = rank_circuits(circuits)

    # Save ranked circuits
    library_file = dest_path / 'dna_circuits_library.json'
    with open(library_file, 'w', encoding='utf-8') as f:
        json.dump(ranked, f, indent=2, default=str)

    print(f"Saved library to: {library_file}")

    # Generate report
    report_file = dest_path / 'ingestion_report.json'
    generate_ingestion_report(ranked, str(report_file))

    # Print summary
    print("\n" + "=" * 60)
    print("INGESTION SUMMARY")
    print("=" * 60)
    print(f"Total circuits ingested: {len(circuits)}")
    print(f"Top 5 circuits by rank:")

    for circuit in ranked[:5]:
        print(f"  {circuit.get('rank_position')}. {circuit.get('circuit_id', 'unknown')}")
        print(f"     Score: {circuit.get('rank_score', 0):.2f}")
        print(f"     Factors: {', '.join(circuit.get('rank_factors', []))}")

    print("\nNext steps:")
    print("  1. Review the DNA circuits library at:", dest_path)
    print("  2. Identify templates for agent DNA generation")
    print("  3. Generate variants from high-scoring circuits")
    print("  4. Validate new circuits on IBM hardware")


if __name__ == '__main__':
    main()
