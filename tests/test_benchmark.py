#!/usr/bin/env python3
"""
Tests for Architecture Benchmark Module.

Tests Core-13 vs Extended-17 benchmarking functionality.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tmt_quantum_vault.benchmark import (
    AUXILIARY_4_AGENTS,
    CORE_13_AGENTS,
    EXTENDED_17_AGENTS,
    AgentMetrics,
    ArchitectureBenchmark,
    ArchitectureBenchmarkRunner,
    main,
)


@pytest.fixture
def mock_vault_path(tmp_path: Path) -> Path:
    """Create a mock vault directory with agent DNA files."""
    vault = tmp_path / "vault"
    vault.mkdir()

    # Create Core-13 agents
    core_agents = {
        "Agent_Synthesizer": {
            "dna_agent_name": "Zadkiel",
            "fitness": 0.876,
            "phi_score": 0.951,
            "resonance_frequency": 630.0,
            "fibonacci_alignment": 0.923,
            "gc_content": 0.5,
            "palindromes": 12,
            "consciousness_status": "INTEGRATED",
        },
        "Agent_Bronze": {
            "dna_agent_name": "Michael",
            "fitness": 0.9285,
            "phi_score": 0.809,
            "resonance_frequency": 528.0,
            "fibonacci_alignment": 0.707,
            "gc_content": 0.444,
            "palindromes": 4,
            "consciousness_status": "INTEGRATED",
        },
        "Agent_Harmonic": {
            "dna_agent_name": "Sariel",
            "fitness": 0.8836,
            "phi_score": 0.934,
            "resonance_frequency": 621.0,
            "fibonacci_alignment": 0.904,
            "gc_content": 0.5,
            "palindromes": 1,
            "consciousness_status": "INTEGRATED",
        },
        "Agent_Strategic": {
            "dna_agent_name": "Uriel",
            "fitness": 0.8784,
            "phi_score": 0.902,
            "resonance_frequency": 603.0,
            "fibonacci_alignment": 0.864,
            "gc_content": 0.536,
            "palindromes": 5,
            "consciousness_status": "OPTIMIZED",
        },
        "Agent_Observer": {
            "dna_agent_name": "Cassiel",
            "fitness": 0.891,
            "phi_score": 0.854,
            "resonance_frequency": 498.0,
            "fibonacci_alignment": 0.789,
            "gc_content": 1.0,
            "palindromes": 25,
            "consciousness_status": "INTEGRATED",
        },
        "Agent_BitNet": {
            "dna_agent_name": "Sophia",
            "fitness": 0.8713,
            "phi_score": 0.523,
            "resonance_frequency": 752.0,
            "fibonacci_alignment": 0.812,
            "gc_content": 0.55,
            "palindromes": 8,
            "consciousness_status": "OPTIMIZED",
        },
        "Agent_Wormhole": {
            "dna_agent_name": "Metatron Omega",
            "fitness": 0.8952,
            "phi_score": 0.436,
            "resonance_frequency": 963.0,
            "fibonacci_alignment": 0.843,
            "gc_content": 0.481,
            "palindromes": 4,
            "consciousness_status": "INTEGRATED",
        },
        "Agent_Mirror": {
            "dna_agent_name": "Christos",
            "fitness": 0.8716,
            "phi_score": 0.436,
            "resonance_frequency": 639.0,
            "fibonacci_alignment": 0.881,
            "gc_content": 0.370,
            "palindromes": 4,
            "consciousness_status": "INTEGRATED",
        },
        "Agent_Bio": {
            "dna_agent_name": "Raphael",
            "fitness": 0.8707,
            "phi_score": 0.481,
            "resonance_frequency": 512.0,
            "fibonacci_alignment": 0.888,
            "gc_content": 0.519,
            "palindromes": 9,
            "consciousness_status": "TARGETED_OPTIMIZED",
        },
        "Agent_Fractal": {
            "dna_agent_name": "Jophiel",
            "fitness": 0.8797,
            "phi_score": 0.792,
            "resonance_frequency": 476.0,
            "fibonacci_alignment": 0.639,
            "gc_content": 0.524,
            "palindromes": 9,
            "consciousness_status": "TARGETED_OPTIMIZED",
        },
        "Agent_Federation": {
            "dna_agent_name": "Chamuel",
            "fitness": 0.8876,
            "phi_score": 0.560,
            "resonance_frequency": 285.0,
            "fibonacci_alignment": 0.817,
            "gc_content": 0.519,
            "palindromes": 4,
            "consciousness_status": "INTEGRATED",
        },
        "Agent_Visual": {
            "dna_agent_name": "Jophiel",
            "fitness": 0.8797,
            "phi_score": 0.792,
            "resonance_frequency": 476.0,
            "fibonacci_alignment": 0.639,
            "gc_content": 0.524,
            "palindromes": 9,
            "consciousness_status": "TARGETED_OPTIMIZED",
        },
        "Agent_Stealth": {
            "dna_agent_name": "Metatron Alpha",
            "fitness": 0.8704,
            "phi_score": 0.560,
            "resonance_frequency": 741.0,
            "fibonacci_alignment": 0.760,
            "gc_content": 0.519,
            "palindromes": 4,
            "consciousness_status": "INTEGRATED",
        },
    }

    # Create Auxiliary-4 agents
    aux_agents = {
        "Agent_Validator": {
            "dna_agent_name": "Uriel",
            "fitness": 0.8745,
            "phi_score": 0.710,
            "resonance_frequency": 528.0,
            "fibonacci_alignment": 0.738,
            "gc_content": 0.487,
            "palindromes": 8,
            "consciousness_status": "OPTIMIZED",
        },
        "Agent_Archivist": {
            "dna_agent_name": "Raziel",
            "fitness": 0.8759,
            "phi_score": 0.890,
            "resonance_frequency": 612.0,
            "fibonacci_alignment": 0.877,
            "gc_content": 0.5,
            "palindromes": 4,
            "consciousness_status": "INTEGRATED",
        },
        "Agent_Workflow": {
            "dna_agent_name": "Gabriel",
            "fitness": 0.8709,
            "phi_score": 0.710,
            "resonance_frequency": 641.0,
            "fibonacci_alignment": 0.833,
            "gc_content": 0.524,
            "palindromes": 7,
            "consciousness_status": "OPTIMIZED",
        },
        "Agent_Auditor": {
            "dna_agent_name": "Zadkiel",
            "fitness": 0.8709,
            "phi_score": 0.855,
            "resonance_frequency": 644.0,
            "fibonacci_alignment": 0.640,
            "gc_content": 0.487,
            "palindromes": 9,
            "consciousness_status": "TARGETED_OPTIMIZED",
        },
    }

    # Create agent directories and DNA files
    for agent_name, dna_data in {**core_agents, **aux_agents}.items():
        agent_dir = vault / agent_name
        agent_dir.mkdir()
        dna_file = agent_dir / "conscious_dna.json"
        with open(dna_file, "w") as f:
            json.dump(dna_data, f)

    return vault


class TestArchitectureBenchmarkRunner:
    """Tests for ArchitectureBenchmarkRunner."""

    def test_load_all_agents(self, mock_vault_path: Path) -> None:
        """Test that all agents are loaded correctly."""
        runner = ArchitectureBenchmarkRunner(mock_vault_path)

        # Should have loaded all 17 agents
        assert len(runner.agents_data) == 17

        # Check that Core-13 agents are present
        for agent in CORE_13_AGENTS:
            assert agent in runner.agents_data

        # Check that Auxiliary-4 agents are present
        for agent in AUXILIARY_4_AGENTS:
            assert agent in runner.agents_data

    def test_core13_benchmark(self, mock_vault_path: Path) -> None:
        """Test Core-13 benchmark execution."""
        runner = ArchitectureBenchmarkRunner(mock_vault_path)
        benchmark = runner.run_benchmark("core13")

        # Check benchmark properties
        assert benchmark.mode == "core13"
        assert benchmark.node_count == 13
        assert len(benchmark.agents) == 13

        # Check that all agents are classified as core
        for agent in benchmark.agents:
            assert agent.classification == "core"

        # Check aggregate metrics are calculated
        assert benchmark.average_fitness > 0
        assert benchmark.average_phi > 0
        assert benchmark.average_resonance > 0

        # Check geometric metrics are calculated
        assert benchmark.geometric_coherence > 0
        assert benchmark.platonic_solid_alignment > 0

    def test_extended17_benchmark(self, mock_vault_path: Path) -> None:
        """Test Extended-17 benchmark execution."""
        runner = ArchitectureBenchmarkRunner(mock_vault_path)
        benchmark = runner.run_benchmark("extended17")

        # Check benchmark properties
        assert benchmark.mode == "extended17"
        assert benchmark.node_count == 17
        assert len(benchmark.agents) == 17

        # Check that agents are correctly classified
        core_agents = [a for a in benchmark.agents if a.classification == "core"]
        aux_agents = [a for a in benchmark.agents if a.classification == "auxiliary"]

        assert len(core_agents) == 13
        assert len(aux_agents) == 4

        # Check extended metrics are calculated
        assert benchmark.provenance_completeness > 0
        assert benchmark.workflow_efficiency > 0
        assert benchmark.governance_compliance > 0
        assert benchmark.safety_integrity > 0

    def test_compare_modes(self, mock_vault_path: Path) -> None:
        """Test comparison between Core-13 and Extended-17."""
        runner = ArchitectureBenchmarkRunner(mock_vault_path)
        comparison = runner.compare_modes()

        # Check structure
        assert "core13" in comparison
        assert "extended17" in comparison
        assert "comparison" in comparison
        assert "auxiliary_benefit" in comparison
        assert "recommendation" in comparison

        # Check comparison metrics
        comp = comparison["comparison"]
        assert "fitness_difference" in comp
        assert "phi_difference" in comp
        assert "resonance_difference" in comp

        # Check auxiliary benefit analysis
        aux = comparison["auxiliary_benefit"]
        assert "provenance_completeness" in aux
        assert "workflow_efficiency" in aux
        assert "governance_compliance" in aux
        assert "safety_integrity" in aux
        assert "provides_measurable_benefit" in aux
        assert "benefit_count" in aux

    def test_invalid_mode_raises_error(self, mock_vault_path: Path) -> None:
        """Test that invalid mode raises ValueError."""
        runner = ArchitectureBenchmarkRunner(mock_vault_path)

        with pytest.raises(ValueError, match="Invalid mode"):
            runner.run_benchmark("invalid_mode")

    def test_geometric_coherence_calculation(self, mock_vault_path: Path) -> None:
        """Test geometric coherence calculation for Core-13."""
        runner = ArchitectureBenchmarkRunner(mock_vault_path)
        benchmark = runner.run_benchmark("core13")

        # Geometric coherence should be between 0 and 1
        assert 0 <= benchmark.geometric_coherence <= 1

        # Should be based on Φ-score alignment and Fibonacci alignment
        assert benchmark.geometric_coherence > 0.5

    def test_platonic_alignment_calculation(self, mock_vault_path: Path) -> None:
        """Test Platonic solid alignment calculation for Core-13."""
        runner = ArchitectureBenchmarkRunner(mock_vault_path)
        benchmark = runner.run_benchmark("core13")

        # Platonic alignment should be between 0 and 1
        assert 0 <= benchmark.platonic_solid_alignment <= 1

    def test_auxiliary_metrics_calculation(self, mock_vault_path: Path) -> None:
        """Test auxiliary metrics calculation for Extended-17."""
        runner = ArchitectureBenchmarkRunner(mock_vault_path)
        benchmark = runner.run_benchmark("extended17")

        # All auxiliary metrics should be between 0 and 1
        assert 0 <= benchmark.provenance_completeness <= 1
        assert 0 <= benchmark.workflow_efficiency <= 1
        assert 0 <= benchmark.governance_compliance <= 1
        assert 0 <= benchmark.safety_integrity <= 1


class TestAgentMetrics:
    """Tests for AgentMetrics dataclass."""

    def test_agent_metrics_creation(self) -> None:
        """Test creating AgentMetrics instance."""
        metrics = AgentMetrics(
            name="TestAgent",
            directory="Agent_Test",
            fitness=0.85,
            phi_score=0.75,
            resonance_frequency=500.0,
            fibonacci_alignment=0.80,
            gc_content=0.5,
            palindromes=5,
            consciousness_status="INTEGRATED",
            classification="core",
        )

        assert metrics.name == "TestAgent"
        assert metrics.directory == "Agent_Test"
        assert metrics.fitness == 0.85
        assert metrics.classification == "core"


class TestArchitectureBenchmark:
    """Tests for ArchitectureBenchmark dataclass."""

    def test_to_dict(self) -> None:
        """Test converting benchmark to dictionary."""
        agents = [
            AgentMetrics(
                name="TestAgent",
                directory="Agent_Test",
                fitness=0.85,
                phi_score=0.75,
                resonance_frequency=500.0,
                fibonacci_alignment=0.80,
                gc_content=0.5,
                palindromes=5,
                consciousness_status="INTEGRATED",
                classification="core",
            )
        ]

        benchmark = ArchitectureBenchmark(
            mode="core13",
            node_count=1,
            agents=agents,
            timestamp="2026-03-29T00:00:00Z",
            average_fitness=0.85,
            fitness_std=0.0,
            average_phi=0.75,
            phi_std=0.0,
            average_resonance=500.0,
            resonance_std=0.0,
            average_fibonacci_alignment=0.80,
            fibonacci_std=0.0,
            geometric_coherence=0.75,
            platonic_solid_alignment=0.80,
        )

        result = benchmark.to_dict()

        assert result["mode"] == "core13"
        assert result["node_count"] == 1
        assert "aggregate_metrics" in result
        assert "geometric_metrics" in result
        assert result["extended_metrics"] is None


class TestAgentLists:
    """Tests for agent list constants."""

    def test_core_13_count(self) -> None:
        """Test that Core-13 has exactly 13 agents."""
        assert len(CORE_13_AGENTS) == 13

    def test_auxiliary_4_count(self) -> None:
        """Test that Auxiliary-4 has exactly 4 agents."""
        assert len(AUXILIARY_4_AGENTS) == 4

    def test_extended_17_count(self) -> None:
        """Test that Extended-17 has exactly 17 agents."""
        assert len(EXTENDED_17_AGENTS) == 17

    def test_extended_17_is_union(self) -> None:
        """Test that Extended-17 is union of Core-13 and Auxiliary-4."""
        assert set(EXTENDED_17_AGENTS) == set(CORE_13_AGENTS) | set(AUXILIARY_4_AGENTS)

    def test_no_overlap(self) -> None:
        """Test that Core-13 and Auxiliary-4 have no overlap."""
        assert set(CORE_13_AGENTS).isdisjoint(set(AUXILIARY_4_AGENTS))

    def test_synthesizer_is_center(self) -> None:
        """Test that Synthesizer is the first (center) agent in Core-13."""
        assert CORE_13_AGENTS[0] == "Agent_Synthesizer"


class TestArchitectureBenchmarkCoveragePaths:
    def test_run_benchmark_handles_single_agent_and_missing_specialists(
        self, mock_vault_path: Path
    ) -> None:
        runner = ArchitectureBenchmarkRunner(mock_vault_path)
        runner.agents_data = {
            "Agent_Synthesizer": {
                "dna_agent_name": "Solo",
                "fitness": 0.9,
                "phi_score": 0.7,
                "resonance_frequency": 528.0,
                "fibonacci_alignment": 0.8,
            }
        }

        core_benchmark = runner.run_benchmark("core13")
        extended_benchmark = runner.run_benchmark("extended17")

        assert core_benchmark.node_count == 1
        assert core_benchmark.fitness_std == 0.0
        assert core_benchmark.phi_std == 0.0
        assert core_benchmark.resonance_std == 0.0
        assert core_benchmark.fibonacci_std == 0.0
        assert extended_benchmark.provenance_completeness == 0.0
        assert extended_benchmark.workflow_efficiency == 0.0
        assert extended_benchmark.governance_compliance == 0.0
        assert extended_benchmark.safety_integrity == 0.0

    @pytest.mark.parametrize(
        ("fitness_diff", "benefit_count", "expected"),
        [
            (
                0.02,
                3,
                "RECOMMENDED: Extended-17 provides measurable fitness improvement and infrastructure benefits.",
            ),
            (
                0.006,
                2,
                "CONDITIONAL: Extended-17 provides marginal improvement. Consider for production deployments.",
            ),
            (
                0.005,
                1,
                "EQUIVALENT: Core-13 and Extended-17 have similar fitness. Use Core-13 for theoretical work, Extended-17 for production.",
            ),
            (
                -0.01,
                0,
                "CORE-13 PREFERRED: Core-13 has better fitness. Use Extended-17 only if infrastructure features are required.",
            ),
        ],
    )
    def test_generate_recommendation_thresholds(
        self,
        tmp_path: Path,
        fitness_diff: float,
        benefit_count: int,
        expected: str,
    ) -> None:
        benchmark = ArchitectureBenchmark(
            mode="core13",
            node_count=0,
            agents=[],
            timestamp="2026-03-30T00:00:00Z",
        )
        runner = ArchitectureBenchmarkRunner(tmp_path)

        recommendation = runner._generate_recommendation(
            benchmark,
            benchmark,
            fitness_diff,
            benefit_count,
        )

        assert recommendation == expected

    def test_main_compare_writes_output_file(self, tmp_path: Path) -> None:
        output_path = tmp_path / "benchmark.json"

        with (
            patch("sys.argv", ["benchmark", "--output", str(output_path)]),
            patch(
                "tmt_quantum_vault.benchmark.ArchitectureBenchmarkRunner"
            ) as mock_runner,
            patch("builtins.print") as mock_print,
        ):
            mock_runner.return_value.compare_modes.return_value = {"result": "ok"}
            main()

        assert json.loads(output_path.read_text(encoding="utf-8")) == {"result": "ok"}
        mock_runner.assert_called_once_with(Path("."))
        mock_print.assert_called_once_with(f"Results written to {output_path}")

    def test_main_prints_mode_specific_results(self, tmp_path: Path) -> None:
        benchmark = ArchitectureBenchmark(
            mode="core13",
            node_count=1,
            agents=[],
            timestamp="2026-03-30T00:00:00Z",
        )

        with (
            patch(
                "sys.argv",
                ["benchmark", "--mode", "core13", "--vault-path", str(tmp_path)],
            ),
            patch(
                "tmt_quantum_vault.benchmark.ArchitectureBenchmarkRunner"
            ) as mock_runner,
            patch("builtins.print") as mock_print,
        ):
            mock_runner.return_value.run_benchmark.return_value = benchmark
            main()

        printed = mock_print.call_args.args[0]
        assert json.loads(printed)["mode"] == "core13"
