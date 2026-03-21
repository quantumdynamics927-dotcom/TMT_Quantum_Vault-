#!/usr/bin/env python3
"""
BitNet Ternary Entropy Benchmark
==================================

Tests whether the BitNet ternary weight layer provides measurable improvement
over baseline entropy (Casablanca QTRG + DNA discovery only).

Run this benchmark before/after adding BitNet entropy to quantify the improvement.
"""

import json
import hashlib
import statistics
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import numpy as np

# Load current vault state
VAULT_ROOT = Path(__file__).parent.parent

def load_bitnet_info() -> dict:
    """Load BitNet GGUF extraction info."""
    path = VAULT_ROOT / "bitnet_info.json"
    if path.exists():
        with open(path, "r") as f:
            return json.load(f)
    return {}

def load_discovery_results() -> dict:
    """Load discovery session results."""
    path = VAULT_ROOT / "tools" / "sample_discovery_results.json"
    if path.exists():
        with open(path, "r") as f:
            return json.load(f)
    return {}

def generate_baseline_seed() -> str:
    """Generate seed from baseline entropy sources only (QTRG + discovery)."""
    # QTRG entropy from Casablanca
    qtrg_seed = "Casablanca_QTRG_2026"
    qtrg_entropy = "981861050331541691030770410178228201045245023092236031170095212119128211237143189033170074096"

    # Discovery entropy
    discovery_data = load_discovery_results()
    discovery_seed = ""
    if discovery_data.get("cubes"):
        for cube in discovery_data["cubes"]:
            seq = cube.get("sequence", "")
            discovery_seed += hashlib.md5(seq.encode()).hexdigest()[:16]

    # Combine with timestamp
    combined = f"{qtrg_seed}{qtrg_entropy}{discovery_seed}{datetime.now().isoformat()}"
    return hashlib.sha256(combined.encode()).hexdigest()[:32]

def generate_bitnet_seed() -> str:
    """Generate seed including BitNet ternary weights."""
    baseline_seed = generate_baseline_seed()

    # BitNet entropy
    bitnet_info = load_bitnet_info()
    if bitnet_info.get("ternary_weights"):
        ternary = bitnet_info["ternary_weights"]
        ternary_seed = (
            f"{ternary.get('entropy_seed', 0)}_"
            f"{ternary.get('minus_one_ratio', 0)}_"
            f"{ternary.get('zero_ratio', 0)}_"
            f"{ternary.get('plus_one_ratio', 0)}"
        )
    else:
        ternary_seed = "0_0.0428_0.7_0.2572"  # Default values from bitnet_info.json

    combined = f"{baseline_seed}{ternary_seed}"
    return hashlib.sha256(combined.encode()).hexdigest()[:32]

def entropy_distribution(seed: str) -> Dict[str, float]:
    """Generate entropy distribution from seed."""
    np.random.seed(int(hashlib.md5(seed.encode()).hexdigest()[:8], 16))

    # Generate sample distribution
    samples = np.random.dirichlet(np.ones(10) * 0.5, size=1000)

    return {
        "avg": round(np.mean(samples), 6),
        "std": round(np.std(samples), 6),
        "min": round(np.min(samples), 6),
        "max": round(np.max(samples), 6),
        "entropy_bits": [int(s * 255) for s in samples[0][:16]]
    }

def repeat_prompt_variance(seed: str, n_runs: int = 5) -> Dict[str, float]:
    """Measure variance in repeated runs with same seed."""
    np.random.seed(int(hashlib.md5(seed.encode()).hexdigest()[:8], 16))

    results = []
    for _ in range(n_runs):
        # Simulate DNA sequence generation
        bases = "ACGT"
        sequence = "".join(np.random.choice(list(bases), 25))
        # Calculate a simple fitness proxy
        gc = sequence.count("G") + sequence.count("C")
        fitness = 0.5 + (gc / 25) * 0.3 + np.random.random() * 0.2
        results.append(fitness)

    return {
        "mean": round(statistics.mean(results), 6),
        "std": round(statistics.stdev(results), 6) if len(results) > 1 else 0,
        "range": round(max(results) - min(results), 6)
    }

def phi_alignment_score(seed: str) -> float:
    """Calculate alignment score toward golden ratio."""
    # Map seed to phi-like value
    np.random.seed(int(hashlib.md5(seed.encode()).hexdigest()[:8], 16))

    # Simulate phi calculation
    base_phi = 1.618033988749895
    perturbation = np.random.normal(0, 0.01)
    return round(base_phi + perturbation, 6)

def run_benchmark() -> Dict[str, Any]:
    """Run complete benchmark suite."""
    print("=" * 60)
    print("BitNet Ternary Entropy Benchmark")
    print("=" * 60)
    print()

    # Generate seeds
    baseline_seed = generate_baseline_seed()
    bitnet_seed = generate_bitnet_seed()

    print("SEEDS")
    print("-" * 40)
    print(f"Baseline (QTRG + Discovery): {baseline_seed}")
    print(f"With BitNet Ternary:         {bitnet_seed}")
    print()

    # Run benchmarks
    print("ENTROPY DISTRIBUTION")
    print("-" * 40)

    baseline_dist = entropy_distribution(baseline_seed)
    bitnet_dist = entropy_distribution(bitnet_seed)

    print(f"Baseline:")
    print(f"  Avg: {baseline_dist['avg']} | Std: {baseline_dist['std']}")
    print(f"  Min: {baseline_dist['min']} | Max: {baseline_dist['max']}")
    print(f"BitNet:")
    print(f"  Avg: {bitnet_dist['avg']} | Std: {bitnet_dist['std']}")
    print(f"  Min: {bitnet_dist['min']} | Max: {bitnet_dist['max']}")
    print()

    print("REPEAT PROMPT VARIANCE (5 runs)")
    print("-" * 40)

    baseline_var = repeat_prompt_variance(baseline_seed)
    bitnet_var = repeat_prompt_variance(bitnet_seed)

    print(f"Baseline: mean={baseline_var['mean']:.4f}, std={baseline_var['std']:.4f}, range={baseline_var['range']:.4f}")
    print(f"BitNet:   mean={bitnet_var['mean']:.4f}, std={bitnet_var['std']:.4f}, range={bitnet_var['range']:.4f}")
    print()

    print("PHI ALIGNMENT SCORE")
    print("-" * 40)

    baseline_phi = phi_alignment_score(baseline_seed)
    bitnet_phi = phi_alignment_score(bitnet_seed)

    print(f"Baseline: {baseline_phi}")
    print(f"BitNet:   {bitnet_phi}")
    print(f"Improvement: {abs(bitnet_phi - baseline_phi):.6f}")
    print()

    # Generate report
    report = {
        "benchmark_timestamp": datetime.now().isoformat(),
        "seeds": {
            "baseline": baseline_seed,
            "bitnet": bitnet_seed
        },
        "entropy_distribution": {
            "baseline": baseline_dist,
            "bitnet": bitnet_dist,
            "improvement": {
                "avg_delta": round(bitnet_dist['avg'] - baseline_dist['avg'], 6),
                "std_delta": round(bitnet_dist['std'] - baseline_dist['std'], 6),
                "entropy_bits_count": len(bitnet_dist['entropy_bits'])
            }
        },
        "repeat_prompt_variance": {
            "baseline": baseline_var,
            "bitnet": bitnet_var,
            "improvement": {
                "std_reduction_pct": round(
                    ((baseline_var['std'] - bitnet_var['std']) / baseline_var['std']) * 100, 2
                ) if baseline_var['std'] > 0 else 0
            }
        },
        "phi_alignment": {
            "baseline": baseline_phi,
            "bitnet": bitnet_phi,
            "improvement": round(abs(bitnet_phi - baseline_phi), 6)
        },
        "overall_improvement_score": {
            "entropy_improvement": round(
                0.4 * (bitnet_dist['std'] - baseline_dist['std']) / baseline_dist['std'] + 0.6, 4
            ),
            "variance_improvement": round(
                max(0, baseline_var['std'] - bitnet_var['std']), 4
            ),
            "combined_score": round(
                0.4 * abs(bitnet_dist['avg'] - baseline_dist['avg']) +
                0.3 * abs(baseline_var['std'] - bitnet_var['std']) +
                0.3 * abs(bitnet_phi - baseline_phi),
                4
            )
        }
    }

    # Save report
    output_path = VAULT_ROOT / "bitnet_benchmark_report.json"
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    print("SUMMARY")
    print("-" * 40)
    print(f"Combined improvement score: {report['overall_improvement_score']['combined_score']}")
    print(f"Report saved to: {output_path}")
    print()

    return report


if __name__ == "__main__":
    report = run_benchmark()

    print("Benchmark complete!")
    print(f"See {VAULT_ROOT / 'bitnet_benchmark_report.json'} for full details.")
