#!/usr/bin/env python3
"""
Tests for Scientific Validation Framework.

Tests all mathematical and scientific validation functions.
"""

from __future__ import annotations

import math
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from tmt_quantum_vault.scientific_validation import (
    ScientificValidator,
    ValidationResult,
    ValidationReport,
    PHI,
    PHI_INVERSE,
    PHI_SQUARED,
    FIBONACCI,
    DNA_RISE_PER_TURN,
    DNA_DIAMETER,
)


class TestGoldenRatioValidation:
    """Tests for golden ratio (φ) validation."""
    
    def test_phi_constant_computation(self, tmp_path: Path) -> None:
        """Test that φ is correctly computed."""
        validator = ScientificValidator(tmp_path)
        result = validator.validate_phi_constant()
        
        assert result.passed
        assert result.category == "golden_ratio"
        assert abs(result.value - PHI) < 1e-15
    
    def test_phi_inverse_identity(self, tmp_path: Path) -> None:
        """Test that 1/φ = φ - 1."""
        validator = ScientificValidator(tmp_path)
        result = validator.validate_phi_inverse()
        
        assert result.passed
        assert abs(1/PHI - (PHI - 1)) < 1e-15
    
    def test_dna_helix_phi_ratio(self, tmp_path: Path) -> None:
        """Test that DNA helix geometry encodes φ."""
        validator = ScientificValidator(tmp_path)
        result = validator.validate_dna_helix_phi_ratio()
        
        assert result.passed
        # 34/21 = 1.619... ≈ φ (error < 0.1%)
        assert result.details["error_percent"] < 0.1
    
    def test_fibonacci_phi_convergence(self, tmp_path: Path) -> None:
        """Test that Fibonacci ratios converge to φ."""
        validator = ScientificValidator(tmp_path)
        result = validator.validate_fibonacci_convergence_to_phi()
        
        assert result.passed
        # F(20)/F(19) should be very close to φ
        assert abs(result.value - PHI) < 0.001
    
    def test_fibonacci_sequence_correct(self) -> None:
        """Test that Fibonacci sequence is correct."""
        # Verify first 20 Fibonacci numbers
        for i in range(2, len(FIBONACCI)):
            assert FIBONACCI[i] == FIBONACCI[i-1] + FIBONACCI[i-2]
    
    def test_dna_geometry_constants(self) -> None:
        """Test that DNA geometry constants are correct."""
        assert DNA_RISE_PER_TURN == 34.0
        assert DNA_DIAMETER == 21.0
        # 34 and 21 are consecutive Fibonacci numbers
        assert 34 in FIBONACCI
        assert 21 in FIBONACCI


class TestGeometricCoherenceValidation:
    """Tests for geometric coherence validation."""
    
    def test_geometric_coherence_formula(self, tmp_path: Path) -> None:
        """Test geometric coherence metric formula."""
        validator = ScientificValidator(tmp_path)
        result = validator.validate_geometric_coherence_formula()
        
        assert result.passed
        # Perfect alignment should give GCM = 1.0
        assert abs(result.value - 1.0) < 0.01
    
    def test_polyhedral_symmetry_formula(self, tmp_path: Path) -> None:
        """Test polyhedral symmetry alignment formula."""
        validator = ScientificValidator(tmp_path)
        result = validator.validate_polyhedral_symmetry_formula()
        
        assert result.passed
        # Perfect alignment should give PSA = 1.0
        assert abs(result.value - 1.0) < 0.01
    
    def test_core_13_node_count(self) -> None:
        """Test that Core-13 has exactly 13 nodes."""
        # Use the actual vault path for this test
        vault_path = Path(".")
        if (vault_path / "Agent_Synthesizer").exists():
            validator = ScientificValidator(vault_path)
            result = validator.validate_core_13_node_count()
            assert result.value == 13
        else:
            # Skip if not in vault directory
            pytest.skip("Not in vault directory")


class TestEntropyValidation:
    """Tests for entropy source validation."""
    
    def test_shannon_entropy_formula(self, tmp_path: Path) -> None:
        """Test Shannon entropy calculation."""
        validator = ScientificValidator(tmp_path)
        result = validator.validate_shannon_entropy()
        
        assert result.passed
        # Maximum entropy for 256 values is 8 bits
        assert result.value == 8.0
    
    def test_entropy_stack_layers(self, tmp_path: Path) -> None:
        """Test that entropy stack has three layers."""
        # Create mock entropy stack file
        entropy_dir = tmp_path / "entropy_stack"
        entropy_dir.mkdir()
        entropy_file = entropy_dir / "three_layer_entropy_stack.json"
        
        import json
        entropy_file.write_text(json.dumps({
            "layer_1_casablanca_qtrg": {},
            "layer_2_dna_discovery": {},
            "layer_3_bitnet_ternary": {}
        }))
        
        validator = ScientificValidator(tmp_path)
        result = validator.validate_entropy_stack_layers()
        
        assert result.passed
        assert result.value == 3


class TestDNAEncodingValidation:
    """Tests for DNA encoding validation."""
    
    def test_dna_gc_content_formula(self, tmp_path: Path) -> None:
        """Test GC content calculation."""
        validator = ScientificValidator(tmp_path)
        result = validator.validate_dna_gc_content()
        
        assert result.passed
        # GCGC has 100% GC content
        assert result.value == 1.0
    
    def test_dna_palindrome_detection(self, tmp_path: Path) -> None:
        """Test palindrome detection."""
        validator = ScientificValidator(tmp_path)
        result = validator.validate_dna_palindrome_detection()
        
        assert result.passed
        # GAATTC is a palindrome (EcoRI site)
        assert result.value == 1.0
    
    def test_agent_dna_sequences_valid(self, tmp_path: Path) -> None:
        """Test that all agent DNA sequences are valid."""
        # Create mock agent with valid DNA
        agent_dir = tmp_path / "Agent_Test"
        agent_dir.mkdir()
        
        import json
        dna_file = agent_dir / "conscious_dna.json"
        dna_file.write_text(json.dumps({
            "conscious_dna": "ATCGATCG",
            "fitness": 0.85,
            "phi_score": 0.618
        }))
        
        validator = ScientificValidator(tmp_path)
        result = validator.validate_agent_dna_sequences()
        
        assert result.passed


class TestFitnessResonanceValidation:
    """Tests for fitness and resonance validation."""
    
    def test_fitness_range_valid(self, tmp_path: Path) -> None:
        """Test that fitness values are in valid range."""
        # Create mock agent with valid fitness
        agent_dir = tmp_path / "Agent_Test"
        agent_dir.mkdir()
        
        import json
        dna_file = agent_dir / "conscious_dna.json"
        dna_file.write_text(json.dumps({
            "fitness": 0.85,
            "phi_score": 0.618
        }))
        
        validator = ScientificValidator(tmp_path)
        result = validator.validate_fitness_range()
        
        assert result.passed
    
    def test_resonance_frequency_range(self, tmp_path: Path) -> None:
        """Test that resonance frequencies are in plausible range."""
        # Create mock agent with valid resonance
        agent_dir = tmp_path / "Agent_Test"
        agent_dir.mkdir()
        
        import json
        dna_file = agent_dir / "conscious_dna.json"
        dna_file.write_text(json.dumps({
            "fitness": 0.85,
            "phi_score": 0.618,
            "resonance_frequency": 500.0
        }))
        
        validator = ScientificValidator(tmp_path)
        result = validator.validate_resonance_frequency_range()
        
        assert result.passed


class TestStatisticalSignificance:
    """Tests for statistical significance validation."""
    
    def test_benchmark_sample_size(self, tmp_path: Path) -> None:
        """Test that benchmark sample size is noted."""
        # Create mock agents
        for i in range(17):
            agent_dir = tmp_path / f"Agent_{i}"
            agent_dir.mkdir()
            
            import json
            dna_file = agent_dir / "conscious_dna.json"
            dna_file.write_text(json.dumps({
                "fitness": 0.85,
                "phi_score": 0.618
            }))
        
        validator = ScientificValidator(tmp_path)
        result = validator.validate_benchmark_sample_size()
        
        # 17 agents is below CLT threshold of 30
        # This is expected to fail, but should provide guidance
        assert result.details["n_agents"] == 17
        assert "recommendation" in result.details
    
    def test_phi_dispersion_check(self, tmp_path: Path) -> None:
        """Test φ-score dispersion check (distribution has meaningful variance)."""
        # Create mock agents with varied phi scores
        for i, phi in enumerate([0.5, 0.6, 0.7, 0.8, 0.9]):
            agent_dir = tmp_path / f"Agent_{i}"
            agent_dir.mkdir()
            
            import json
            dna_file = agent_dir / "conscious_dna.json"
            dna_file.write_text(json.dumps({
                "phi_score": phi
            }))
        
        validator = ScientificValidator(tmp_path)
        result = validator.validate_phi_dispersion_check()
        
        assert result.passed
        assert result.details["std"] > 0


class TestValidationResult:
    """Tests for ValidationResult dataclass."""
    
    def test_validation_result_creation(self) -> None:
        """Test creating a validation result."""
        result = ValidationResult(
            test_name="test",
            category="test_category",
            claim_class="mathematical",
            passed=True,
            value=1.0,
            expected=1.0,
            tolerance=0.01,
        )
        
        assert result.test_name == "test"
        assert result.category == "test_category"
        assert result.claim_class == "mathematical"
        assert result.passed
        assert result.value == 1.0
    
    def test_validation_result_to_dict(self) -> None:
        """Test converting result to dictionary."""
        result = ValidationResult(
            test_name="test",
            category="test_category",
            claim_class="implementation",
            passed=True,
            value=1.0,
            expected=1.0,
            tolerance=0.01,
            details={"key": "value"},
        )
        
        d = result.to_dict()
        
        assert d["test_name"] == "test"
        assert d["passed"]
        assert d["details"]["key"] == "value"


class TestValidationReport:
    """Tests for ValidationReport dataclass."""
    
    def test_validation_report_creation(self) -> None:
        """Test creating a validation report."""
        results = [
            ValidationResult("test1", "cat1", "mathematical", True, 1.0, 1.0, 0.01),
            ValidationResult("test2", "cat1", "implementation", False, 0.5, 1.0, 0.01),
        ]
        
        report = ValidationReport(
            timestamp="2026-03-29T00:00:00Z",
            total_tests=2,
            passed=1,
            failed=1,
            categories={"cat1": {"total": 2, "passed": 1, "failed": 1}},
            claim_classes={"mathematical": 1, "implementation": 1},
            results=results,
        )
        
        assert report.total_tests == 2
        assert report.passed == 1
        assert report.failed == 1
    
    def test_validation_report_to_dict(self) -> None:
        """Test converting report to dictionary."""
        results = [
            ValidationResult("test1", "cat1", "mathematical", True, 1.0, 1.0, 0.01),
        ]
        
        report = ValidationReport(
            timestamp="2026-03-29T00:00:00Z",
            total_tests=1,
            passed=1,
            failed=0,
            categories={"cat1": {"total": 1, "passed": 1, "failed": 0}},
            claim_classes={"mathematical": 1},
            results=results,
        )
        
        d = report.to_dict()
        
        assert "summary" in d
        assert d["summary"]["total_tests"] == 1
        assert d["summary"]["passed"] == 1
        assert d["summary"]["failed"] == 0
        assert "pass_rate" in d["summary"]


class TestEffectSizeCalculation:
    """Tests for effect size calculation methods."""
    
    def test_calculate_effect_size_basic(self, tmp_path: Path) -> None:
        """Test basic effect size calculation."""
        validator = ScientificValidator(tmp_path)
        
        # Two groups with clear difference
        group1 = [1.0, 1.1, 1.2, 1.3, 1.4]
        group2 = [2.0, 2.1, 2.2, 2.3, 2.4]
        
        cohens_d, glass_delta, hedges_g, cl_effect = validator.calculate_effect_size(group1, group2)
        
        # Cohen's d should be large (difference ~1.0, pooled std ~0.16)
        assert abs(cohens_d) > 5.0  # Large effect
        assert abs(glass_delta) > 5.0
        assert abs(hedges_g) > 5.0
        # Common language effect size: P(group1 > group2)
        # Since group1 values are all ~1.0-1.4 and group2 values are all ~2.0-2.4,
        # P(group1 > group2) should be very close to 0
        assert cl_effect < 0.01  # Almost no chance group1 > group2
    
    def test_calculate_effect_size_equal_groups(self, tmp_path: Path) -> None:
        """Test effect size with equal groups."""
        validator = ScientificValidator(tmp_path)
        
        # Two identical groups
        group1 = [1.0, 1.0, 1.0]
        group2 = [1.0, 1.0, 1.0]
        
        cohens_d, glass_delta, hedges_g, cl_effect = validator.calculate_effect_size(group1, group2)
        
        # All effect sizes should be 0 or 0.5 (no difference)
        assert cohens_d == 0.0
        assert glass_delta == 0.0
        assert hedges_g == 0.0
        assert cl_effect == 0.5  # 50% probability
    
    def test_calculate_effect_size_small_samples(self, tmp_path: Path) -> None:
        """Test effect size with small samples."""
        validator = ScientificValidator(tmp_path)
        
        # Small samples (n < 2)
        group1 = [1.0]
        group2 = [2.0]
        
        cohens_d, glass_delta, hedges_g, cl_effect = validator.calculate_effect_size(group1, group2)
        
        # Should return zeros for insufficient data
        assert cohens_d == 0.0
        assert glass_delta == 0.0
        assert hedges_g == 0.0
        # Common language effect size also returns 0.0 for insufficient data
        assert cl_effect == 0.0
    
    def test_calculate_effect_size_unequal_variances(self, tmp_path: Path) -> None:
        """Test effect size with unequal variances."""
        validator = ScientificValidator(tmp_path)
        
        # Group 1: high variance
        group1 = [0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5]
        # Group 2: low variance
        group2 = [0.98, 0.99, 1.0, 1.01, 1.02]
        
        cohens_d, glass_delta, hedges_g, cl_effect = validator.calculate_effect_size(group1, group2)
        
        # Glass's delta should use group1's SD
        # Cohen's d uses pooled SD which can be misleading
        assert abs(cohens_d) > 0
        assert abs(glass_delta) > 0
        # Hedges' g should be slightly smaller than Cohen's d due to correction
        assert abs(hedges_g) < abs(cohens_d)


class TestConfidenceInterval:
    """Tests for bootstrap confidence interval calculation."""
    
    def test_confidence_interval_basic(self, tmp_path: Path) -> None:
        """Test basic confidence interval calculation."""
        validator = ScientificValidator(tmp_path)
        
        # Normal-ish distribution
        data = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4]
        
        ci_lower, ci_upper = validator.calculate_confidence_interval(data, confidence=0.95)
        
        # CI should contain the mean
        mean = sum(data) / len(data)
        assert ci_lower < mean < ci_upper
        # CI should be reasonable width
        assert ci_upper - ci_lower < 1.0
    
    def test_confidence_interval_small_sample(self, tmp_path: Path) -> None:
        """Test confidence interval with small sample."""
        validator = ScientificValidator(tmp_path)
        
        # Very small sample
        data = [1.0]
        
        ci_lower, ci_upper = validator.calculate_confidence_interval(data)
        
        # Should return (0, 0) for insufficient data
        assert ci_lower == 0.0
        assert ci_upper == 0.0
    
    def test_confidence_interval_two_points(self, tmp_path: Path) -> None:
        """Test confidence interval with two points."""
        validator = ScientificValidator(tmp_path)
        
        data = [0.8, 0.9]
        
        ci_lower, ci_upper = validator.calculate_confidence_interval(data)
        
        # Should produce a valid CI
        assert ci_lower <= ci_upper


class TestCoreAuxEffectSize:
    """Tests for Core vs Auxiliary effect size validation."""
    
    def test_core_aux_effect_size_with_data(self, tmp_path: Path) -> None:
        """Test Core vs Aux effect size with mock data."""
        import json
        
        # Create mock agents with fitness data
        core_agents = [
            "Agent_Synthesizer", "Agent_Bronze", "Agent_Harmonic",
            "Agent_Strategic", "Agent_Observer", "Agent_BitNet",
            "Agent_Wormhole", "Agent_Mirror", "Agent_Bio",
            "Agent_Fractal", "Agent_Federation", "Agent_Visual", "Agent_Stealth"
        ]
        aux_agents = ["Agent_Validator", "Agent_Archivist", "Agent_Workflow", "Agent_Auditor"]
        
        for agent in core_agents:
            agent_dir = tmp_path / agent
            agent_dir.mkdir()
            (agent_dir / "conscious_dna.json").write_text(json.dumps({
                "fitness": 0.88,
                "phi_score": 0.62
            }))
        
        for agent in aux_agents:
            agent_dir = tmp_path / agent
            agent_dir.mkdir()
            (agent_dir / "conscious_dna.json").write_text(json.dumps({
                "fitness": 0.87,
                "phi_score": 0.61
            }))
        
        validator = ScientificValidator(tmp_path)
        result = validator.validate_core_aux_effect_size()
        
        # Should pass because absolute difference is small
        assert result.passed
        assert "absolute_difference" in result.details
        assert "practical_equivalence_threshold" in result.details
        assert result.details["primary_metric"] == "absolute_difference"


class TestArchitectureVsNullBaseline:
    """Tests for architecture vs null baseline validation."""
    
    def test_architecture_vs_null_with_data(self, tmp_path: Path) -> None:
        """Test architecture vs null baseline with mock data."""
        import json
        
        # Create mock agents with phi_score data
        core_agents = [
            "Agent_Synthesizer", "Agent_Bronze", "Agent_Harmonic",
            "Agent_Strategic", "Agent_Observer", "Agent_BitNet",
            "Agent_Wormhole", "Agent_Mirror", "Agent_Bio",
            "Agent_Fractal", "Agent_Federation", "Agent_Visual", "Agent_Stealth"
        ]
        
        for i, agent in enumerate(core_agents):
            agent_dir = tmp_path / agent
            agent_dir.mkdir()
            # Higher phi scores for higher-weighted positions
            (agent_dir / "conscious_dna.json").write_text(json.dumps({
                "phi_score": 0.7 + (i * 0.02)
            }))
        
        validator = ScientificValidator(tmp_path)
        result = validator.validate_architecture_vs_null_baseline()
        
        # Should have proper structure
        assert "actual_coherence" in result.details
        assert "null_mean_coherence" in result.details
        assert "p_value" in result.details