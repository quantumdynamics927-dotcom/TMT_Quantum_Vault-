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
    
    def test_phi_score_distribution(self, tmp_path: Path) -> None:
        """Test φ-score distribution analysis."""
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
        result = validator.validate_phi_score_distribution()
        
        assert result.passed
        assert result.details["std"] > 0


class TestValidationResult:
    """Tests for ValidationResult dataclass."""
    
    def test_validation_result_creation(self) -> None:
        """Test creating a validation result."""
        result = ValidationResult(
            test_name="test",
            category="test_category",
            passed=True,
            value=1.0,
            expected=1.0,
            tolerance=0.01,
        )
        
        assert result.test_name == "test"
        assert result.category == "test_category"
        assert result.passed
        assert result.value == 1.0
    
    def test_validation_result_to_dict(self) -> None:
        """Test converting result to dictionary."""
        result = ValidationResult(
            test_name="test",
            category="test_category",
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
            ValidationResult("test1", "cat1", True, 1.0, 1.0, 0.01),
            ValidationResult("test2", "cat1", False, 0.5, 1.0, 0.01),
        ]
        
        report = ValidationReport(
            timestamp="2026-03-29T00:00:00Z",
            total_tests=2,
            passed=1,
            failed=1,
            categories={"cat1": {"total": 2, "passed": 1, "failed": 1}},
            results=results,
        )
        
        assert report.total_tests == 2
        assert report.passed == 1
        assert report.failed == 1
    
    def test_validation_report_to_dict(self) -> None:
        """Test converting report to dictionary."""
        results = [
            ValidationResult("test1", "cat1", True, 1.0, 1.0, 0.01),
        ]
        
        report = ValidationReport(
            timestamp="2026-03-29T00:00:00Z",
            total_tests=1,
            passed=1,
            failed=0,
            categories={"cat1": {"total": 1, "passed": 1, "failed": 0}},
            results=results,
        )
        
        d = report.to_dict()
        
        assert "summary" in d
        assert d["summary"]["total_tests"] == 1
        assert d["summary"]["passed"] == 1
        assert d["summary"]["failed"] == 0
        assert "pass_rate" in d["summary"]