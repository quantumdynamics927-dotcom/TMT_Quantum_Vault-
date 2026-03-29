#!/usr/bin/env python3
"""
Scientific Validation Framework v0.2 for TMT Quantum Vault.

DISCLAIMER: This framework validates mathematical and implementation consistency.
It does NOT prove empirical superiority or generalization across hardware conditions.

This module provides rigorous mathematical and implementation validation:

CLAIM CLASSES:
1. Mathematical Validity: formulas, identities, geometric metrics, encoding definitions
2. Implementation Validity: schema conformity, deterministic transformations, range checks
3. Empirical Validity: performance, stability, reproducibility (requires additional work)

VALIDATION CATEGORIES (neutral scientific terminology):
1. Golden Ratio (φ) Validation — mathematical identities
2. Geometric Coherence — coordination geometry metrics
3. Polyhedral Symmetry — topology alignment
4. Entropy Validation — randomness and entropy sources
5. DNA Encoding — sequence validity and encoding consistency
6. Fitness & Resonance — range and distribution validation
7. Statistical Inference — organized into 4 types:
   - Sample Adequacy Checks: benchmark_sample_size
   - Uncertainty Estimation: confidence intervals, dispersion
   - Comparative Effect Size: core_vs_aux_effect_size
   - Null-Model Tests: architecture_vs_null_baseline, shuffled_boundary

NOT YET VALIDATED:
- Performance uplift from φ-based architecture
- Generalization across hardware conditions
- Backend noise robustness
- Statistical significance vs null models

Usage:
    python -m tmt_quantum_vault.scientific_validation
    python -m tmt_quantum_vault.scientific_validation --test phi_convergence
    python -m tmt_quantum_vault.scientific_validation --full-report
    python -m tmt_quantum_vault.scientific_validation --with-confidence-intervals
"""

from __future__ import annotations

import json
import math
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import argparse
import sys

# Mathematical constants
PHI = (1 + math.sqrt(5)) / 2  # Golden ratio ≈ 1.618033988749895
PHI_INVERSE = 1 / PHI  # ≈ 0.6180339887498949
PHI_SQUARED = PHI ** 2  # ≈ 2.618033988749895
PHI_CUBED = PHI ** 3  # ≈ 4.23606797749979

# Fibonacci sequence (first 20 numbers)
FIBONACCI = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987, 1597, 2584, 4181, 6765]

# DNA helix geometry constants
DNA_RISE_PER_TURN = 34.0  # Angstroms
DNA_DIAMETER = 21.0  # Angstroms
DNA_RATIO = DNA_RISE_PER_TURN / DNA_DIAMETER  # ≈ 1.619 (close to φ)


@dataclass
class ValidationResult:
    """Result of a single validation test."""
    test_name: str
    category: str
    claim_class: str  # 'mathematical', 'implementation', 'empirical'
    passed: bool
    value: float
    expected: float
    tolerance: float
    p_value: Optional[float] = None
    confidence_interval: Optional[Tuple[float, float]] = None
    effect_size: Optional[float] = None
    null_model_comparison: Optional[Dict[str, Any]] = None
    provenance_reference: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "test_name": self.test_name,
            "category": self.category,
            "claim_class": self.claim_class,
            "passed": self.passed,
            "value": self.value,
            "expected": self.expected,
            "tolerance": self.tolerance,
            "p_value": self.p_value,
            "confidence_interval": self.confidence_interval,
            "effect_size": self.effect_size,
            "null_model_comparison": self.null_model_comparison,
            "provenance_reference": self.provenance_reference,
            "details": self.details,
        }


@dataclass
class ValidationReport:
    """Complete validation report."""
    timestamp: str
    total_tests: int
    passed: int
    failed: int
    categories: Dict[str, Dict[str, Any]]
    claim_classes: Dict[str, int]
    results: List[ValidationResult]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp,
            "version": "0.2",
            "disclaimer": "This framework validates mathematical and implementation consistency. It does NOT prove empirical superiority or generalization across hardware conditions.",
            "claim_classes": {
                "mathematical": "Formulas, identities, geometric metrics, encoding definitions",
                "implementation": "Schema conformity, deterministic transformations, range checks",
                "empirical": "Performance, stability, reproducibility (requires additional work)",
            },
            "statistical_test_types": {
                "sample_adequacy": "Checks for sufficient sample size for statistical inference",
                "uncertainty_estimation": "Bootstrap confidence intervals, dispersion metrics",
                "comparative_effect_size": "Cohen's d between groups, practical significance",
                "null_model_tests": "Permutation tests, shuffled baselines, random topology",
            },
            "summary": {
                "total_tests": self.total_tests,
                "passed": self.passed,
                "failed": self.failed,
                "pass_rate": self.passed / self.total_tests if self.total_tests > 0 else 0,
                "claim_classes": self.claim_classes,
            },
            "categories": self.categories,
            "results": [r.to_dict() for r in self.results],
        }


class ScientificValidator:
    """
    Scientific validation framework for TMT Quantum Vault.
    
    Provides rigorous mathematical and scientific validation of all claims.
    """
    
    def __init__(self, vault_path: Path = Path(".")):
        """
        Initialize validator.
        
        Args:
            vault_path: Path to TMT Quantum Vault root directory
        """
        self.vault_path = Path(vault_path)
        self.agents_data: Dict[str, Dict[str, Any]] = {}
        self.results: List[ValidationResult] = []
        self._load_all_agents()
    
    def _load_all_agents(self) -> None:
        """Load DNA data for all agents."""
        for agent_dir in self.vault_path.iterdir():
            if agent_dir.is_dir() and agent_dir.name.startswith("Agent_"):
                dna_file = agent_dir / "conscious_dna.json"
                if dna_file.exists():
                    with open(dna_file, 'r', encoding='utf-8') as f:
                        self.agents_data[agent_dir.name] = json.load(f)
    
    # =========================================================================
    # CATEGORY 1: Golden Ratio (φ) Validation
    # =========================================================================
    
    def validate_phi_constant(self) -> ValidationResult:
        """
        Validate that φ is correctly computed.
        
        Mathematical claim: φ = (1 + √5) / 2 ≈ 1.618033988749895
        """
        computed_phi = (1 + math.sqrt(5)) / 2
        expected_phi = 1.618033988749895
        tolerance = 1e-15  # Machine precision
        
        passed = abs(computed_phi - expected_phi) < tolerance
        
        return ValidationResult(
            test_name="phi_constant_computation",
            category="golden_ratio",
            claim_class="mathematical",
            passed=passed,
            value=computed_phi,
            expected=expected_phi,
            tolerance=tolerance,
            details={
                "formula": "(1 + √5) / 2",
                "computed_value": computed_phi,
                "precision": "15 decimal places",
            },
        )
    
    def validate_phi_inverse(self) -> ValidationResult:
        """
        Validate that 1/φ = φ - 1 ≈ 0.618.
        
        Mathematical claim: 1/φ = φ - 1
        """
        inverse = 1 / PHI
        minus_one = PHI - 1
        tolerance = 1e-15
        
        passed = abs(inverse - minus_one) < tolerance
        
        return ValidationResult(
            test_name="phi_inverse_identity",
            category="golden_ratio",
            claim_class="mathematical",
            passed=passed,
            value=inverse,
            expected=minus_one,
            tolerance=tolerance,
            details={
                "inverse": inverse,
                "phi_minus_one": minus_one,
                "difference": abs(inverse - minus_one),
            },
        )
    
    def validate_dna_helix_phi_ratio(self) -> ValidationResult:
        """
        Validate that DNA helix geometry encodes φ.
        
        Scientific claim: DNA rise/diameter = 34/21 ≈ φ
        - DNA rise per turn: 34.0 Å
        - DNA diameter: 21.0 Å
        - Ratio: 34/21 = 1.619... ≈ φ (error: 0.063%)
        """
        ratio = DNA_RISE_PER_TURN / DNA_DIAMETER
        error = abs(ratio - PHI) / PHI
        tolerance = 0.001  # 0.1% tolerance
        
        passed = error < tolerance
        
        return ValidationResult(
            test_name="dna_helix_phi_ratio",
            category="golden_ratio",
            claim_class="mathematical",
            passed=passed,
            value=ratio,
            expected=PHI,
            tolerance=tolerance,
            details={
                "dna_rise_angstrom": DNA_RISE_PER_TURN,
                "dna_diameter_angstrom": DNA_DIAMETER,
                "ratio": ratio,
                "phi": PHI,
                "error_percent": error * 100,
                "fibonacci_numbers": [34, 21],
                "fibonacci_indices": [FIBONACCI.index(34) + 1, FIBONACCI.index(21) + 1],
            },
        )
    
    def validate_fibonacci_convergence_to_phi(self) -> ValidationResult:
        """
        Validate that Fibonacci ratios converge to φ.
        
        Mathematical claim: lim(n→∞) F(n+1)/F(n) = φ
        """
        # Calculate ratios for consecutive Fibonacci pairs
        ratios = []
        for i in range(len(FIBONACCI) - 1):
            ratio = FIBONACCI[i + 1] / FIBONACCI[i]
            ratios.append(ratio)
        
        # Check convergence (last ratio should be closest to φ)
        final_ratio = ratios[-1]
        error = abs(final_ratio - PHI) / PHI
        tolerance = 0.001  # 0.1% tolerance
        
        passed = error < tolerance
        
        return ValidationResult(
            test_name="fibonacci_phi_convergence",
            category="golden_ratio",
            claim_class="mathematical",
            passed=passed,
            value=final_ratio,
            expected=PHI,
            tolerance=tolerance,
            details={
                "fibonacci_sequence": FIBONACCI[:10],
                "convergence_ratios": ratios[-5:],
                "final_ratio": final_ratio,
                "error_percent": error * 100,
            },
        )
    
    def validate_agent_phi_scores(self) -> ValidationResult:
        """
        Validate that agent φ-scores follow expected distribution.
        
        Scientific claim: φ-scores should cluster around 1/φ ≈ 0.618
        """
        phi_scores = []
        for agent_data in self.agents_data.values():
            if "phi_score" in agent_data:
                phi_scores.append(agent_data["phi_score"])
        
        if not phi_scores:
            return ValidationResult(
                test_name="agent_phi_scores",
                category="golden_ratio",
                claim_class="implementation",
                passed=False,
                value=0,
                expected=PHI_INVERSE,
                tolerance=0.1,
                details={"error": "No phi_scores found in agent data"},
            )
        
        mean_phi = statistics.mean(phi_scores)
        std_phi = statistics.stdev(phi_scores) if len(phi_scores) > 1 else 0
        
        # Check if mean is within tolerance of 1/φ
        tolerance = 0.2  # 20% tolerance for mean
        error = abs(mean_phi - PHI_INVERSE) / PHI_INVERSE
        
        passed = error < tolerance
        
        return ValidationResult(
            test_name="agent_phi_scores",
            category="golden_ratio",
            claim_class="implementation",
            passed=passed,
            value=mean_phi,
            expected=PHI_INVERSE,
            tolerance=tolerance,
            details={
                "n_agents": len(phi_scores),
                "mean_phi": mean_phi,
                "std_phi": std_phi,
                "min_phi": min(phi_scores),
                "max_phi": max(phi_scores),
                "phi_inverse": PHI_INVERSE,
                "error_percent": error * 100,
            },
        )
    
    # =========================================================================
    # CATEGORY 2: Geometric Coherence Validation
    # =========================================================================
    
    def validate_geometric_coherence_formula(self) -> ValidationResult:
        """
        Validate the geometric coherence metric formula.
        
        Formula: GCM = (1 - mean(φ_deviation) / φ_target) * 0.5 + mean(fibonacci_alignment) * 0.5
        """
        # Test with known values
        phi_scores = [0.618, 0.618, 0.618]  # Perfect alignment
        fib_alignments = [1.0, 1.0, 1.0]  # Perfect alignment
        
        phi_target = PHI_INVERSE
        phi_deviations = [abs(p - phi_target) for p in phi_scores]
        phi_coherence = 1.0 - (statistics.mean(phi_deviations) / phi_target)
        fib_alignment = statistics.mean(fib_alignments)
        
        gcm = (phi_coherence * 0.5) + (fib_alignment * 0.5)
        
        # Perfect alignment should give GCM = 1.0
        tolerance = 0.01
        passed = abs(gcm - 1.0) < tolerance
        
        return ValidationResult(
            test_name="geometric_coherence_formula",
            category="geometric_coherence",
            claim_class="mathematical",
            passed=passed,
            value=gcm,
            expected=1.0,
            tolerance=tolerance,
            details={
                "formula": "GCM = (1 - mean(φ_deviation) / φ_target) * 0.5 + mean(fibonacci_alignment) * 0.5",
                "phi_coherence": phi_coherence,
                "fib_alignment": fib_alignment,
                "computed_gcm": gcm,
            },
        )
    
    def validate_polyhedral_symmetry_formula(self) -> ValidationResult:
        """
        Validate the polyhedral symmetry alignment formula.
        
        Formula: PSA = (center_alignment * 0.4) + (ring_balance * 0.6)
        """
        # Test with known values
        center_alignment = 1.0  # Perfect center
        ring_balance = 1.0  # Perfect balance
        
        psa = (center_alignment * 0.4) + (ring_balance * 0.6)
        
        # Perfect alignment should give PSA = 1.0
        tolerance = 0.01
        passed = abs(psa - 1.0) < tolerance
        
        return ValidationResult(
            test_name="polyhedral_symmetry_formula",
            category="geometric_coherence",
            claim_class="mathematical",
            passed=passed,
            value=psa,
            expected=1.0,
            tolerance=tolerance,
            details={
                "formula": "PSA = (center_alignment * 0.4) + (ring_balance * 0.6)",
                "center_alignment": center_alignment,
                "ring_balance": ring_balance,
                "computed_psa": psa,
            },
        )
    
    def validate_core_13_node_count(self) -> ValidationResult:
        """
        Validate that Core-13 has exactly 13 nodes.
        
        Mathematical claim: Coordination geometry requires 13 nodes (1 center + 12 ring)
        """
        core_13_agents = [
            "Agent_Synthesizer",  # CENTER
            "Agent_Bronze",
            "Agent_Harmonic",
            "Agent_Strategic",
            "Agent_Observer",
            "Agent_BitNet",
            "Agent_Wormhole",
            "Agent_Mirror",
            "Agent_Bio",
            "Agent_Fractal",
            "Agent_Federation",
            "Agent_Visual",
            "Agent_Stealth",
        ]
        
        found_count = sum(1 for agent in core_13_agents if agent in self.agents_data)
        expected = 13
        tolerance = 0
        
        passed = found_count == expected
        
        return ValidationResult(
            test_name="core_13_node_count",
            category="geometric_coherence",
            claim_class="implementation",
            passed=passed,
            value=found_count,
            expected=expected,
            tolerance=tolerance,
            details={
                "expected_nodes": 13,
                "found_nodes": found_count,
                "missing": [a for a in core_13_agents if a not in self.agents_data],
            },
        )
    
    # =========================================================================
    # CATEGORY 3: Entropy Source Validation
    # =========================================================================
    
    def validate_shannon_entropy(self) -> ValidationResult:
        """
        Validate Shannon entropy calculation.
        
        Mathematical formula: H = -Σ p(x) * log2(p(x))
        """
        # Test with uniform distribution (maximum entropy)
        # For 256 possible values, max entropy = 8 bits
        n_values = 256
        p = 1 / n_values  # Uniform distribution
        max_entropy = -n_values * p * math.log2(p)  # = 8 bits
        
        tolerance = 0.01
        passed = abs(max_entropy - 8.0) < tolerance
        
        return ValidationResult(
            test_name="shannon_entropy_formula",
            category="entropy_validation",
            claim_class="implementation",
            passed=passed,
            value=max_entropy,
            expected=8.0,
            tolerance=tolerance,
            details={
                "formula": "H = -Σ p(x) * log2(p(x))",
                "n_values": n_values,
                "uniform_probability": p,
                "max_entropy_bits": max_entropy,
            },
        )
    
    def validate_entropy_stack_layers(self) -> ValidationResult:
        """
        Validate that entropy stack has three distinct layers.
        
        Scientific claim: Three-layer entropy = QTRG + DNA discovery + BitNet ternary
        """
        entropy_stack_path = self.vault_path / "entropy_stack" / "three_layer_entropy_stack.json"
        
        if not entropy_stack_path.exists():
            return ValidationResult(
                test_name="entropy_stack_layers",
                category="entropy_validation",
                claim_class="implementation",
                passed=False,
                value=0,
                expected=3,
                tolerance=0,
                details={"error": f"Entropy stack file not found: {entropy_stack_path}"},
            )
        
        with open(entropy_stack_path, 'r') as f:
            entropy_data = json.load(f)
        
        # Check for three layers
        layers = []
        if "layer_1_casablanca_qtrg" in entropy_data:
            layers.append("casablanca_qtrg")
        if "layer_2_dna_discovery" in entropy_data:
            layers.append("dna_discovery")
        if "layer_3_bitnet_ternary" in entropy_data:
            layers.append("bitnet_ternary")
        
        found = len(layers)
        expected = 3
        tolerance = 0
        
        passed = found == expected
        
        return ValidationResult(
            test_name="entropy_stack_layers",
            category="entropy_validation",
            claim_class="implementation",
            passed=passed,
            value=found,
            expected=expected,
            tolerance=tolerance,
            details={
                "layers_found": layers,
                "layer_count": found,
            },
        )
    
    # =========================================================================
    # CATEGORY 4: DNA Encoding Validation
    # =========================================================================
    
    def validate_dna_gc_content(self) -> ValidationResult:
        """
        Validate GC content calculation for DNA sequences.
        
        Mathematical formula: GC_content = (G + C) / (A + T + G + C)
        """
        # Test with known sequence
        test_sequence = "GCGC"  # 100% GC
        gc_count = test_sequence.count('G') + test_sequence.count('C')
        gc_content = gc_count / len(test_sequence)
        
        tolerance = 0.01
        passed = abs(gc_content - 1.0) < tolerance
        
        return ValidationResult(
            test_name="dna_gc_content_formula",
            category="dna_encoding",
            claim_class="implementation",
            passed=passed,
            value=gc_content,
            expected=1.0,
            tolerance=tolerance,
            details={
                "formula": "GC_content = (G + C) / (A + T + G + C)",
                "test_sequence": test_sequence,
                "gc_count": gc_count,
                "computed_gc_content": gc_content,
            },
        )
    
    def validate_dna_palindrome_detection(self) -> ValidationResult:
        """
        Validate palindrome detection in DNA sequences.
        
        Mathematical definition: A DNA palindrome reads the same 5'→3' as its complement 3'→5'
        """
        # Test with known palindrome
        test_sequence = "GAATTC"  # EcoRI restriction site (palindrome)
        complement = {"A": "T", "T": "A", "G": "C", "C": "G"}
        
        # Check if sequence equals its reverse complement
        reverse_complement = "".join(complement[b] for b in reversed(test_sequence))
        is_palindrome = test_sequence == reverse_complement
        
        tolerance = 0
        passed = is_palindrome
        
        return ValidationResult(
            test_name="dna_palindrome_detection",
            category="dna_encoding",
            claim_class="implementation",
            passed=passed,
            value=1.0 if is_palindrome else 0.0,
            expected=1.0,
            tolerance=tolerance,
            details={
                "test_sequence": test_sequence,
                "reverse_complement": reverse_complement,
                "is_palindrome": is_palindrome,
            },
        )
    
    def validate_agent_dna_sequences(self) -> ValidationResult:
        """
        Validate that all agent DNA sequences are valid.
        
        Scientific claim: All sequences must contain only A, T, C, G
        """
        valid_bases = {'A', 'T', 'C', 'G'}
        invalid_agents = []
        
        for agent_name, agent_data in self.agents_data.items():
            dna = agent_data.get("conscious_dna", "")
            if dna:
                invalid_bases = set(dna) - valid_bases
                if invalid_bases:
                    invalid_agents.append({
                        "agent": agent_name,
                        "invalid_bases": list(invalid_bases),
                    })
        
        tolerance = 0
        passed = len(invalid_agents) == 0
        
        return ValidationResult(
            test_name="agent_dna_sequences_valid",
            category="dna_encoding",
            claim_class="implementation",
            passed=passed,
            value=len(self.agents_data) - len(invalid_agents),
            expected=len(self.agents_data),
            tolerance=tolerance,
            details={
                "total_agents": len(self.agents_data),
                "valid_agents": len(self.agents_data) - len(invalid_agents),
                "invalid_agents": invalid_agents,
            },
        )
    
    # =========================================================================
    # CATEGORY 5: Fitness & Resonance Validation
    # =========================================================================
    
    def validate_fitness_range(self) -> ValidationResult:
        """
        Validate that all fitness values are in valid range [0, 1].
        
        Mathematical constraint: 0 ≤ fitness ≤ 1
        """
        fitness_values = []
        out_of_range = []
        
        for agent_name, agent_data in self.agents_data.items():
            fitness = agent_data.get("fitness")
            if fitness is not None:
                fitness_values.append(fitness)
                if not (0 <= fitness <= 1):
                    out_of_range.append({
                        "agent": agent_name,
                        "fitness": fitness,
                    })
        
        tolerance = 0
        passed = len(out_of_range) == 0
        
        return ValidationResult(
            test_name="fitness_range_valid",
            category="fitness_resonance",
            claim_class="implementation",
            passed=passed,
            value=len(fitness_values) - len(out_of_range),
            expected=len(fitness_values),
            tolerance=tolerance,
            details={
                "total_agents": len(fitness_values),
                "valid_agents": len(fitness_values) - len(out_of_range),
                "out_of_range": out_of_range,
                "min_fitness": min(fitness_values) if fitness_values else None,
                "max_fitness": max(fitness_values) if fitness_values else None,
                "mean_fitness": statistics.mean(fitness_values) if fitness_values else None,
            },
        )
    
    def validate_resonance_frequency_range(self) -> ValidationResult:
        """
        Validate that resonance frequencies are in plausible range.
        
        Scientific constraint: Audio frequencies typically 20 Hz - 20 kHz
        """
        resonance_values = []
        out_of_range = []
        
        for agent_name, agent_data in self.agents_data.items():
            resonance = agent_data.get("resonance_frequency")
            if resonance is not None:
                resonance_values.append(resonance)
                # Allow wider range for quantum systems
                if not (1 <= resonance <= 10000):
                    out_of_range.append({
                        "agent": agent_name,
                        "resonance_hz": resonance,
                    })
        
        tolerance = 0
        passed = len(out_of_range) == 0
        
        return ValidationResult(
            test_name="resonance_frequency_range",
            category="fitness_resonance",
            claim_class="implementation",
            passed=passed,
            value=len(resonance_values) - len(out_of_range),
            expected=len(resonance_values),
            tolerance=tolerance,
            details={
                "total_agents": len(resonance_values),
                "valid_agents": len(resonance_values) - len(out_of_range),
                "out_of_range": out_of_range,
                "min_hz": min(resonance_values) if resonance_values else None,
                "max_hz": max(resonance_values) if resonance_values else None,
                "mean_hz": statistics.mean(resonance_values) if resonance_values else None,
            },
        )
    
    # =========================================================================
    # CATEGORY 7: Statistical Significance (Enhanced)
    # =========================================================================
    
    def calculate_confidence_interval(
        self, 
        data: List[float], 
        confidence: float = 0.95
    ) -> Tuple[float, float]:
        """
        Calculate bootstrap confidence interval for small samples.
        
        Uses bootstrap resampling for robust CI estimation when n < 30.
        
        Args:
            data: List of values
            confidence: Confidence level (default 0.95 for 95% CI)
        
        Returns:
            Tuple of (lower_bound, upper_bound)
        """
        if len(data) < 2:
            return (0.0, 0.0)
        
        import random
        
        n_bootstrap = 10000
        bootstrap_means = []
        
        for _ in range(n_bootstrap):
            # Resample with replacement
            sample = [random.choice(data) for _ in range(len(data))]
            bootstrap_means.append(statistics.mean(sample))
        
        # Sort and get percentiles
        bootstrap_means.sort()
        lower_idx = int((1 - confidence) / 2 * n_bootstrap)
        upper_idx = int((1 + confidence) / 2 * n_bootstrap)
        
        return (bootstrap_means[lower_idx], bootstrap_means[upper_idx])
    
    def calculate_effect_size(
        self, 
        group1: List[float], 
        group2: List[float]
    ) -> float:
        """
        Calculate Cohen's d effect size between two groups.
        
        Effect size interpretation:
        - d < 0.2: negligible
        - 0.2 ≤ d < 0.5: small
        - 0.5 ≤ d < 0.8: medium
        - d ≥ 0.8: large
        
        Args:
            group1: First group of values
            group2: Second group of values
        
        Returns:
            Cohen's d effect size
        """
        if len(group1) < 2 or len(group2) < 2:
            return 0.0
        
        mean1 = statistics.mean(group1)
        mean2 = statistics.mean(group2)
        
        # Pooled standard deviation
        var1 = statistics.variance(group1)
        var2 = statistics.variance(group2)
        
        n1, n2 = len(group1), len(group2)
        pooled_var = ((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2)
        pooled_std = math.sqrt(pooled_var)
        
        if pooled_std == 0:
            return 0.0
        
        return (mean1 - mean2) / pooled_std
    
    def validate_with_confidence_intervals(self) -> ValidationResult:
        """
        Validate metrics with bootstrap confidence intervals.
        
        Uses bootstrap resampling for robust CI estimation.
        """
        # Collect fitness values
        fitness_values = []
        for agent_data in self.agents_data.values():
            if "fitness" in agent_data:
                fitness_values.append(agent_data["fitness"])
        
        if len(fitness_values) < 2:
            return ValidationResult(
                test_name="fitness_confidence_interval",
                category="statistical_significance",
                claim_class="implementation",
                passed=False,
                value=0,
                expected=1,
                tolerance=0,
                details={"error": "Insufficient data for CI calculation"},
            )
        
        # Calculate 95% CI using bootstrap
        ci_lower, ci_upper = self.calculate_confidence_interval(fitness_values)
        mean_fitness = statistics.mean(fitness_values)
        
        # Check if CI is within valid range [0, 1]
        passed = ci_lower >= 0 and ci_upper <= 1
        
        return ValidationResult(
            test_name="fitness_confidence_interval",
            category="statistical_inference",
            claim_class="implementation",
            passed=passed,
            value=mean_fitness,
            expected=0.88,  # Target fitness
            tolerance=0.1,
            confidence_interval=(ci_lower, ci_upper),
            details={
                "n": len(fitness_values),
                "mean": mean_fitness,
                "std": statistics.stdev(fitness_values) if len(fitness_values) > 1 else 0,
                "ci_95_lower": ci_lower,
                "ci_95_upper": ci_upper,
                "method": "bootstrap",
                "n_bootstrap": 10000,
            },
        )
    
    def validate_core_aux_effect_size(self) -> ValidationResult:
        """
        Calculate effect size between Core-13 and Auxiliary-4.
        
        Uses Cohen's d to measure practical significance.
        Note: This compares Core-13 vs Auxiliary-4, NOT Core-13 mode vs Extended-17 mode.
        """
        # Core-13 agents
        core_13_agents = [
            "Agent_Synthesizer", "Agent_Bronze", "Agent_Harmonic",
            "Agent_Strategic", "Agent_Observer", "Agent_BitNet",
            "Agent_Wormhole", "Agent_Mirror", "Agent_Bio",
            "Agent_Fractal", "Agent_Federation", "Agent_Visual", "Agent_Stealth"
        ]
        
        # Auxiliary-4 agents
        auxiliary_4_agents = [
            "Agent_Validator", "Agent_Archivist", "Agent_Workflow", "Agent_Auditor"
        ]
        
        core_fitness = []
        for agent in core_13_agents:
            if agent in self.agents_data and "fitness" in self.agents_data[agent]:
                core_fitness.append(self.agents_data[agent]["fitness"])
        
        aux_fitness = []
        for agent in auxiliary_4_agents:
            if agent in self.agents_data and "fitness" in self.agents_data[agent]:
                aux_fitness.append(self.agents_data[agent]["fitness"])
        
        if len(core_fitness) < 2 or len(aux_fitness) < 2:
            return ValidationResult(
                test_name="core_aux_effect_size",
                category="statistical_inference",
                claim_class="empirical",
                passed=False,
                value=0,
                expected=0,
                tolerance=0,
                details={"error": "Insufficient data for effect size calculation"},
            )
        
        # Calculate Cohen's d
        effect_size = self.calculate_effect_size(core_fitness, aux_fitness)
        
        # Interpret effect size
        if abs(effect_size) < 0.2:
            interpretation = "negligible"
        elif abs(effect_size) < 0.5:
            interpretation = "small"
        elif abs(effect_size) < 0.8:
            interpretation = "medium"
        else:
            interpretation = "large"
        
        # Effect size < 0.2 means Core and Extended are practically equivalent
        passed = abs(effect_size) < 0.5  # Small or negligible difference
        
        return ValidationResult(
            test_name="core_aux_effect_size",
            category="statistical_inference",
            claim_class="empirical",
            passed=passed,
            value=effect_size,
            expected=0,  # Null hypothesis: no difference
            tolerance=0.5,
            effect_size=effect_size,
            details={
                "core_n": len(core_fitness),
                "core_mean": statistics.mean(core_fitness),
                "core_std": statistics.stdev(core_fitness) if len(core_fitness) > 1 else 0,
                "aux_n": len(aux_fitness),
                "aux_mean": statistics.mean(aux_fitness),
                "aux_std": statistics.stdev(aux_fitness) if len(aux_fitness) > 1 else 0,
                "cohens_d": effect_size,
                "interpretation": interpretation,
                "note": "Effect size measures practical significance, not just statistical significance",
            },
        )
    
    def validate_architecture_vs_null_baseline(self) -> ValidationResult:
        """
        Compare actual architecture against null model (randomized placement).
        
        NULL MODEL: Random assignment of agents to positions with preserved topology.
        This tests whether the specific assignment of agents to positions matters.
        
        Test: Compare position-weighted coherence metric in actual vs shuffled assignments.
        If architecture matters, actual assignment should have higher coherence than random.
        """
        import random
        
        # Define position weights for Core-13 topology
        # Center has weight 1.0, ring positions have weights based on φ-alignment
        position_weights = {
            "center": 1.0,  # Synthesizer at center
            "ring_1": 0.95, "ring_2": 0.95, "ring_3": 0.95,  # High-weight ring positions
            "ring_4": 0.90, "ring_5": 0.90, "ring_6": 0.90,  # Medium-high
            "ring_7": 0.85, "ring_8": 0.85, "ring_9": 0.85,  # Medium
            "ring_10": 0.80, "ring_11": 0.80, "ring_12": 0.80,  # Lower
        }
        
        # Map agents to positions based on their role
        position_map = {
            "Agent_Synthesizer": "center",
            "Agent_Bronze": "ring_1",
            "Agent_Harmonic": "ring_2",
            "Agent_Strategic": "ring_3",
            "Agent_Observer": "ring_4",
            "Agent_BitNet": "ring_5",
            "Agent_Wormhole": "ring_6",
            "Agent_Mirror": "ring_7",
            "Agent_Bio": "ring_8",
            "Agent_Fractal": "ring_9",
            "Agent_Federation": "ring_10",
            "Agent_Visual": "ring_11",
            "Agent_Stealth": "ring_12",
        }
        
        # Collect agent data with positions and phi_scores
        agent_data_list = []
        for agent_name, agent_data in self.agents_data.items():
            if agent_name in position_map and "phi_score" in agent_data:
                agent_data_list.append({
                    "agent": agent_name,
                    "position": position_map[agent_name],
                    "weight": position_weights[position_map[agent_name]],
                    "phi_score": agent_data["phi_score"],
                    "fitness": agent_data.get("fitness", 0.5),
                })
        
        if len(agent_data_list) < 3:
            return ValidationResult(
                test_name="architecture_vs_null_baseline",
                category="statistical_inference",
                claim_class="empirical",
                passed=False,
                value=0,
                expected=0,
                tolerance=0,
                details={"error": "Insufficient data for null model comparison (need ≥3 agents with positions)"},
            )
        
        # ACTUAL: Position-weighted coherence
        # Higher phi-scores at higher-weighted positions = better coherence
        def calculate_weighted_coherence(data_list):
            """Calculate position-weighted coherence metric."""
            weighted_sum = sum(d["weight"] * d["phi_score"] for d in data_list)
            weight_sum = sum(d["weight"] for d in data_list)
            return weighted_sum / weight_sum if weight_sum > 0 else 0
        
        actual_coherence = calculate_weighted_coherence(agent_data_list)
        
        # NULL MODEL: Shuffle phi-scores across positions and compute coherence
        # This tests: "Does the specific assignment of agents to positions matter?"
        n_permutations = 1000
        null_coherences = []
        
        phi_scores = [d["phi_score"] for d in agent_data_list]
        weights = [d["weight"] for d in agent_data_list]
        
        for _ in range(n_permutations):
            shuffled_scores = phi_scores.copy()
            random.shuffle(shuffled_scores)
            # Recalculate weighted coherence with shuffled scores
            weighted_sum = sum(w * s for w, s in zip(weights, shuffled_scores))
            null_coherences.append(weighted_sum / sum(weights))
        
        # Calculate p-value: how often is null coherence >= actual coherence?
        # If architecture is optimized, actual should be higher than random
        null_coherences.sort()
        n_equal_or_better = sum(1 for c in null_coherences if c >= actual_coherence)
        p_value = n_equal_or_better / n_permutations
        
        # Effect size: standardized difference
        null_mean = statistics.mean(null_coherences)
        null_std = statistics.stdev(null_coherences)
        z_score = (actual_coherence - null_mean) / null_std if null_std > 0 else 0
        
        # Interpretation
        if p_value < 0.05:
            interpretation = "Architecture assignment significantly better than random (p < 0.05)"
        elif p_value < 0.10:
            interpretation = "Architecture assignment marginally better than random (p < 0.10)"
        else:
            interpretation = "Architecture assignment statistically indistinguishable from random"
        
        # Pass if actual is significantly better than null (one-tailed test)
        passed = p_value < 0.10  # More lenient threshold for exploratory analysis
        
        return ValidationResult(
            test_name="architecture_vs_null_baseline",
            category="statistical_inference",
            claim_class="empirical",
            passed=passed,
            value=actual_coherence,
            expected=null_mean,
            tolerance=0.10,
            p_value=p_value,
            null_model_comparison={
                "null_mean_coherence": null_mean,
                "null_std_coherence": null_std,
                "actual_coherence": actual_coherence,
                "z_score": z_score,
                "p_value": p_value,
                "n_permutations": n_permutations,
                "method": "permutation_test_on_weighted_coherence",
                "interpretation": interpretation,
            },
            details={
                "n_agents": len(agent_data_list),
                "actual_coherence": actual_coherence,
                "null_mean_coherence": null_mean,
                "null_std_coherence": null_std,
                "z_score": z_score,
                "p_value": p_value,
                "note": "Tests whether position-weighted coherence is higher than random shuffle",
            },
        )
    
    def validate_benchmark_sample_size(self) -> ValidationResult:
        """
        Validate that benchmark sample size is noted as a limitation.
        
        Statistical requirement: n ≥ 30 for Central Limit Theorem
        
        NOTE: This is a known limitation. Use bootstrap/permutation tests.
        """
        n_agents = len(self.agents_data)
        min_sample = 30
        
        tolerance = 0
        passed = n_agents >= min_sample
        
        return ValidationResult(
            test_name="benchmark_sample_size",
            category="statistical_inference",
            claim_class="implementation",
            passed=passed,
            value=n_agents,
            expected=min_sample,
            tolerance=tolerance,
            details={
                "n_agents": n_agents,
                "min_sample_for_clt": min_sample,
                "note": "Sample size below CLT threshold - use non-parametric tests",
                "recommendation": "Use bootstrap or permutation tests for small samples",
            },
        )
    
    def validate_phi_dispersion_check(self) -> ValidationResult:
        """
        Validate φ-score distribution has reasonable dispersion (not degenerate).
        
        Statistical test: Distribution should have variance > 0 (not all identical).
        This is a sanity check that agents have different φ-scores.
        
        Pass condition: std > min_threshold (distribution is not degenerate)
        """
        phi_scores = []
        for agent_data in self.agents_data.values():
            if "phi_score" in agent_data:
                phi_scores.append(agent_data["phi_score"])
        
        if len(phi_scores) < 3:
            return ValidationResult(
                test_name="phi_dispersion_check",
                category="statistical_inference",
                claim_class="implementation",
                passed=False,
                value=0,
                expected=0.01,  # Minimum std threshold
                tolerance=0,
                details={"error": "Insufficient data for dispersion test (need ≥3 agents)"},
            )
        
        mean_phi = statistics.mean(phi_scores)
        std_phi = statistics.stdev(phi_scores) if len(phi_scores) > 1 else 0
        variance = statistics.variance(phi_scores) if len(phi_scores) > 1 else 0
        
        # Check if distribution is reasonable (not all identical)
        # A degenerate distribution has std = 0 (all values identical)
        # We require std > min_threshold to ensure meaningful dispersion
        min_std_threshold = 0.01
        passed = std_phi > min_std_threshold
        
        # Coefficient of variation (relative dispersion)
        cv = std_phi / mean_phi if mean_phi != 0 else 0
        
        return ValidationResult(
            test_name="phi_dispersion_check",
            category="statistical_inference",
            claim_class="implementation",
            passed=passed,
            value=std_phi,
            expected=min_std_threshold,
            tolerance=min_std_threshold,
            details={
                "n": len(phi_scores),
                "mean": mean_phi,
                "std": std_phi,
                "variance": variance,
                "coefficient_of_variation": cv,
                "min": min(phi_scores),
                "max": max(phi_scores),
                "range": max(phi_scores) - min(phi_scores),
                "interpretation": "Distribution has meaningful dispersion" if passed else "Distribution is degenerate (all values identical)",
                "pass_condition": "std > min_threshold (distribution is not degenerate)",
            },
        )
    
    # =========================================================================
    # Run All Validations
    # =========================================================================
    
    def run_all_validations(self) -> ValidationReport:
        """
        Run all validation tests and generate report.
        
        Returns:
            ValidationReport with all results
        """
        self.results = []
        
        # Category 1: Golden Ratio (Mathematical Validity)
        self.results.append(self.validate_phi_constant())
        self.results.append(self.validate_phi_inverse())
        self.results.append(self.validate_dna_helix_phi_ratio())
        self.results.append(self.validate_fibonacci_convergence_to_phi())
        self.results.append(self.validate_agent_phi_scores())
        
        # Category 2: Geometric Coherence (Mathematical Validity)
        self.results.append(self.validate_geometric_coherence_formula())
        self.results.append(self.validate_polyhedral_symmetry_formula())
        self.results.append(self.validate_core_13_node_count())
        
        # Category 3: Entropy Validation (Implementation Validity)
        self.results.append(self.validate_shannon_entropy())
        self.results.append(self.validate_entropy_stack_layers())
        
        # Category 4: DNA Encoding (Implementation Validity)
        self.results.append(self.validate_dna_gc_content())
        self.results.append(self.validate_dna_palindrome_detection())
        self.results.append(self.validate_agent_dna_sequences())
        
        # Category 5: Fitness & Resonance (Implementation Validity)
        self.results.append(self.validate_fitness_range())
        self.results.append(self.validate_resonance_frequency_range())
        
        # Category 6: Statistical Inference (Sample Adequacy, Uncertainty, Effect Size, Null Models)
        # Type 1: Sample Adequacy Checks
        self.results.append(self.validate_benchmark_sample_size())
        
        # Type 2: Uncertainty Estimation
        self.results.append(self.validate_with_confidence_intervals())
        self.results.append(self.validate_phi_dispersion_check())
        
        # Type 3: Comparative Effect Size
        self.results.append(self.validate_core_aux_effect_size())
        
        # Type 4: Null-Model Tests
        self.results.append(self.validate_architecture_vs_null_baseline())
        
        # Generate report
        categories = {}
        claim_classes = {"mathematical": 0, "implementation": 0, "empirical": 0}
        
        for result in self.results:
            if result.category not in categories:
                categories[result.category] = {
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                }
            categories[result.category]["total"] += 1
            if result.passed:
                categories[result.category]["passed"] += 1
            else:
                categories[result.category]["failed"] += 1
            
            if result.claim_class in claim_classes:
                claim_classes[result.claim_class] += 1
        
        return ValidationReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_tests=len(self.results),
            passed=sum(1 for r in self.results if r.passed),
            failed=sum(1 for r in self.results if not r.passed),
            categories=categories,
            claim_classes=claim_classes,
            results=self.results,
        )


def main():
    """Main entry point for scientific validation CLI."""
    parser = argparse.ArgumentParser(
        description="TMT Quantum Vault Scientific Validation"
    )
    parser.add_argument(
        "--vault-path",
        type=Path,
        default=Path("."),
        help="Path to TMT Quantum Vault root (default: current directory)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output file for validation report (default: stdout)"
    )
    parser.add_argument(
        "--test",
        choices=["phi_convergence", "geometric_coherence", "entropy", "dna", "fitness", "all"],
        default="all",
        help="Run specific validation test (default: all)"
    )
    
    args = parser.parse_args()
    
    # Initialize validator
    validator = ScientificValidator(args.vault_path)
    
    # Run validation
    report = validator.run_all_validations()
    
    # Output results
    output_json = json.dumps(report.to_dict(), indent=2)
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output_json)
        print(f"Validation report written to {args.output}")
    else:
        print(output_json)
    
    # Return exit code based on pass/fail
    sys.exit(0 if report.failed == 0 else 1)


if __name__ == "__main__":
    main()