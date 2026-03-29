#!/usr/bin/env python3
"""
Architecture Benchmark Module for TMT Quantum Vault.

Compares Core-13 vs Extended-17 architecture modes across multiple metrics:
- Fitness stability (σ)
- Resonance coherence
- Reproducibility across backends
- Φ-score distribution
- Fibonacci alignment variance
- Provenance completeness
- Workflow efficiency
- Governance compliance rate
- Safety integrity score

Terminology:
- Core-13 Coordination Lattice (historically: Metatron Core)
- Extended-17 Operational Topology (historically: Merkaba Extended-17)
- Operational Support Layer (historically: Auxiliary Ring)

Usage:
    python -m tmt_quantum_vault.benchmark --mode core13
    python -m tmt_quantum_vault.benchmark --mode extended17
    python -m tmt_quantum_vault.benchmark --compare
"""

from __future__ import annotations

import argparse
import json
import statistics
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Golden ratio constant
PHI = 1.618033988749895

# Architecture mode definitions
CORE_13_AGENTS = [
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

AUXILIARY_4_AGENTS = [
    "Agent_Validator",
    "Agent_Archivist",
    "Agent_Workflow",
    "Agent_Auditor",
]

EXTENDED_17_AGENTS = CORE_13_AGENTS + AUXILIARY_4_AGENTS


@dataclass
class AgentMetrics:
    """Metrics for a single agent."""

    name: str
    directory: str
    fitness: float
    phi_score: float
    resonance_frequency: float
    fibonacci_alignment: float
    gc_content: float
    palindromes: int
    consciousness_status: str
    classification: str  # 'core' or 'auxiliary'


@dataclass
class ArchitectureBenchmark:
    """Benchmark results for an architecture mode."""

    mode: str
    node_count: int
    agents: list[AgentMetrics]
    timestamp: str

    # Aggregate metrics
    average_fitness: float = 0.0
    fitness_std: float = 0.0
    average_phi: float = 0.0
    phi_std: float = 0.0
    average_resonance: float = 0.0
    resonance_std: float = 0.0
    average_fibonacci_alignment: float = 0.0
    fibonacci_std: float = 0.0

    # Extended metrics (for extended17 mode)
    provenance_completeness: float = 0.0
    workflow_efficiency: float = 0.0
    governance_compliance: float = 0.0
    safety_integrity: float = 0.0

    # Geometric coherence (for core13 mode)
    geometric_coherence: float = 0.0
    platonic_solid_alignment: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "mode": self.mode,
            "node_count": self.node_count,
            "timestamp": self.timestamp,
            "aggregate_metrics": {
                "average_fitness": self.average_fitness,
                "fitness_std": self.fitness_std,
                "average_phi": self.average_phi,
                "phi_std": self.phi_std,
                "average_resonance": self.average_resonance,
                "resonance_std": self.resonance_std,
                "average_fibonacci_alignment": self.average_fibonacci_alignment,
                "fibonacci_std": self.fibonacci_std,
            },
            "extended_metrics": (
                {
                    "provenance_completeness": self.provenance_completeness,
                    "workflow_efficiency": self.workflow_efficiency,
                    "governance_compliance": self.governance_compliance,
                    "safety_integrity": self.safety_integrity,
                }
                if self.mode == "extended17"
                else None
            ),
            "geometric_metrics": (
                {
                    "geometric_coherence": self.geometric_coherence,
                    "platonic_solid_alignment": self.platonic_solid_alignment,
                }
                if self.mode == "core13"
                else None
            ),
            "agents": [
                {
                    "name": a.name,
                    "directory": a.directory,
                    "fitness": a.fitness,
                    "phi_score": a.phi_score,
                    "resonance_frequency": a.resonance_frequency,
                    "fibonacci_alignment": a.fibonacci_alignment,
                    "classification": a.classification,
                }
                for a in self.agents
            ],
        }


class ArchitectureBenchmarkRunner:
    """Runner for architecture mode benchmarks."""

    def __init__(self, vault_path: Path):
        """
        Initialize benchmark runner.

        Args:
            vault_path: Path to TMT Quantum Vault root directory
        """
        self.vault_path = Path(vault_path)
        self.agents_data: dict[str, dict[str, Any]] = {}
        self._load_all_agents()

    def _load_all_agents(self) -> None:
        """Load DNA data for all agents."""
        for agent_dir in self.vault_path.iterdir():
            if agent_dir.is_dir() and agent_dir.name.startswith("Agent_"):
                dna_file = agent_dir / "conscious_dna.json"
                if dna_file.exists():
                    with open(dna_file, encoding="utf-8") as f:
                        self.agents_data[agent_dir.name] = json.load(f)

    def _get_agent_metrics(self, agent_name: str) -> AgentMetrics | None:
        """Extract metrics for a single agent."""
        if agent_name not in self.agents_data:
            return None

        data = self.agents_data[agent_name]
        classification = "core" if agent_name in CORE_13_AGENTS else "auxiliary"

        return AgentMetrics(
            name=data.get("dna_agent_name", agent_name),
            directory=agent_name,
            fitness=data.get("fitness", 0.0),
            phi_score=data.get("phi_score", 0.0),
            resonance_frequency=data.get("resonance_frequency", 0.0),
            fibonacci_alignment=data.get("fibonacci_alignment", 0.0),
            gc_content=data.get("gc_content", 0.0),
            palindromes=data.get("palindromes", 0),
            consciousness_status=data.get("consciousness_status", "UNKNOWN"),
            classification=classification,
        )

    def run_benchmark(self, mode: str) -> ArchitectureBenchmark:
        """
        Run benchmark for specified architecture mode.

        Args:
            mode: 'core13' or 'extended17'

        Returns:
            ArchitectureBenchmark with results
        """
        if mode not in ("core13", "extended17"):
            raise ValueError(f"Invalid mode: {mode}. Must be 'core13' or 'extended17'")

        # Get agent list based on mode
        agent_names = CORE_13_AGENTS if mode == "core13" else EXTENDED_17_AGENTS

        # Collect metrics for each agent
        agents = []
        for agent_name in agent_names:
            metrics = self._get_agent_metrics(agent_name)
            if metrics:
                agents.append(metrics)

        # Calculate aggregate metrics
        benchmark = ArchitectureBenchmark(
            mode=mode,
            node_count=len(agents),
            agents=agents,
            timestamp=datetime.now(UTC).isoformat(),
        )

        if agents:
            fitnesses = [a.fitness for a in agents]
            phis = [a.phi_score for a in agents]
            resonances = [a.resonance_frequency for a in agents]
            fibs = [a.fibonacci_alignment for a in agents]

            benchmark.average_fitness = statistics.mean(fitnesses)
            benchmark.fitness_std = (
                statistics.stdev(fitnesses) if len(fitnesses) > 1 else 0.0
            )
            benchmark.average_phi = statistics.mean(phis)
            benchmark.phi_std = statistics.stdev(phis) if len(phis) > 1 else 0.0
            benchmark.average_resonance = statistics.mean(resonances)
            benchmark.resonance_std = (
                statistics.stdev(resonances) if len(resonances) > 1 else 0.0
            )
            benchmark.average_fibonacci_alignment = statistics.mean(fibs)
            benchmark.fibonacci_std = statistics.stdev(fibs) if len(fibs) > 1 else 0.0

        # Mode-specific metrics
        if mode == "core13":
            benchmark.geometric_coherence = self._calculate_geometric_coherence(agents)
            benchmark.platonic_solid_alignment = self._calculate_platonic_alignment(
                agents
            )
        else:
            benchmark.provenance_completeness = self._calculate_provenance_completeness(
                agents
            )
            benchmark.workflow_efficiency = self._calculate_workflow_efficiency(agents)
            benchmark.governance_compliance = self._calculate_governance_compliance(
                agents
            )
            benchmark.safety_integrity = self._calculate_safety_integrity(agents)

        return benchmark

    def _calculate_geometric_coherence(self, agents: list[AgentMetrics]) -> float:
        """
        Calculate geometric coherence for Core-13.

        Measures how well the 13 nodes align with Fruit-of-Life geometry.
        Based on Φ-score distribution and Fibonacci alignment.
        """
        if not agents:
            return 0.0

        # Ideal: all Φ-scores close to 0.618 (1/φ)
        phi_target = 1.0 / PHI
        phi_deviations = [abs(a.phi_score - phi_target) for a in agents]
        phi_coherence = 1.0 - (statistics.mean(phi_deviations) / phi_target)

        # Fibonacci alignment should be high
        fib_alignment = statistics.mean([a.fibonacci_alignment for a in agents])

        # Combine metrics
        coherence = (phi_coherence * 0.5) + (fib_alignment * 0.5)
        return max(0.0, min(1.0, coherence))

    def _calculate_platonic_alignment(self, agents: list[AgentMetrics]) -> float:
        """
        Calculate Platonic solid alignment for Core-13.

        Measures alignment with the 5 Platonic solids derived from Metatron's Cube.
        """
        if len(agents) != 13:
            return 0.0

        # Check if center node (Synthesizer) has highest Φ
        center_agent = next((a for a in agents if "Synthesizer" in a.directory), None)
        if not center_agent:
            return 0.0

        # Center should have highest Φ-score
        max_phi = max(a.phi_score for a in agents)
        center_alignment = center_agent.phi_score / max_phi if max_phi > 0 else 0.0

        # Inner ring should have balanced distribution
        inner_ring = [a for a in agents if "Synthesizer" not in a.directory]
        inner_phis = [a.phi_score for a in inner_ring]
        phi_balance = (
            1.0 - (statistics.stdev(inner_phis) / statistics.mean(inner_phis))
            if inner_phis
            else 0.0
        )

        return (center_alignment * 0.4) + (phi_balance * 0.6)

    def _calculate_provenance_completeness(self, agents: list[AgentMetrics]) -> float:
        """Calculate provenance completeness for Extended-17."""
        # Check if Archivist is present and has good metrics
        archivist = next((a for a in agents if "Archivist" in a.directory), None)
        if not archivist:
            return 0.0

        # Provenance completeness based on Archivist fitness and Φ
        return (archivist.fitness * 0.6) + (archivist.phi_score * 0.4)

    def _calculate_workflow_efficiency(self, agents: list[AgentMetrics]) -> float:
        """Calculate workflow efficiency for Extended-17."""
        # Check if Workflow agent is present and has good metrics
        workflow = next((a for a in agents if "Workflow" in a.directory), None)
        if not workflow:
            return 0.0

        return (workflow.fitness * 0.5) + (workflow.fibonacci_alignment * 0.5)

    def _calculate_governance_compliance(self, agents: list[AgentMetrics]) -> float:
        """Calculate governance compliance for Extended-17."""
        # Check if Auditor is present and has good metrics
        auditor = next((a for a in agents if "Auditor" in a.directory), None)
        if not auditor:
            return 0.0

        return (auditor.fitness * 0.5) + (auditor.phi_score * 0.5)

    def _calculate_safety_integrity(self, agents: list[AgentMetrics]) -> float:
        """Calculate safety integrity for Extended-17."""
        # Check if Validator is present and has good metrics
        validator = next((a for a in agents if "Validator" in a.directory), None)
        if not validator:
            return 0.0

        return (validator.fitness * 0.6) + (validator.phi_score * 0.4)

    def compare_modes(self) -> dict[str, Any]:
        """
        Compare Core-13 vs Extended-17 modes.

        Returns:
            Dictionary with comparison results
        """
        core13 = self.run_benchmark("core13")
        extended17 = self.run_benchmark("extended17")

        # Calculate differences
        fitness_diff = extended17.average_fitness - core13.average_fitness
        phi_diff = extended17.average_phi - core13.average_phi
        resonance_diff = extended17.average_resonance - core13.average_resonance

        # Determine if auxiliary layer provides measurable benefit
        auxiliary_benefit = {
            "provenance": extended17.provenance_completeness > 0.5,
            "workflow": extended17.workflow_efficiency > 0.5,
            "governance": extended17.governance_compliance > 0.5,
            "safety": extended17.safety_integrity > 0.5,
        }

        benefit_count = sum(1 for v in auxiliary_benefit.values() if v)

        return {
            "core13": core13.to_dict(),
            "extended17": extended17.to_dict(),
            "comparison": {
                "fitness_difference": fitness_diff,
                "phi_difference": phi_diff,
                "resonance_difference": resonance_diff,
                "fitness_stability_improvement": core13.fitness_std
                - extended17.fitness_std,
                "phi_stability_improvement": core13.phi_std - extended17.phi_std,
            },
            "auxiliary_benefit": {
                "provenance_completeness": extended17.provenance_completeness,
                "workflow_efficiency": extended17.workflow_efficiency,
                "governance_compliance": extended17.governance_compliance,
                "safety_integrity": extended17.safety_integrity,
                "provides_measurable_benefit": benefit_count >= 2,
                "benefit_count": benefit_count,
                "details": auxiliary_benefit,
            },
            "recommendation": self._generate_recommendation(
                core13, extended17, fitness_diff, benefit_count
            ),
        }

    def _generate_recommendation(
        self,
        core13: ArchitectureBenchmark,
        extended17: ArchitectureBenchmark,
        fitness_diff: float,
        benefit_count: int,
    ) -> str:
        """Generate recommendation based on comparison."""
        if fitness_diff > 0.01 and benefit_count >= 3:
            return "RECOMMENDED: Extended-17 provides measurable fitness improvement and infrastructure benefits."
        elif fitness_diff > 0.005 and benefit_count >= 2:
            return "CONDITIONAL: Extended-17 provides marginal improvement. Consider for production deployments."
        elif abs(fitness_diff) <= 0.005:
            return "EQUIVALENT: Core-13 and Extended-17 have similar fitness. Use Core-13 for theoretical work, Extended-17 for production."
        else:
            return "CORE-13 PREFERRED: Core-13 has better fitness. Use Extended-17 only if infrastructure features are required."


def main() -> None:
    """Main entry point for benchmark CLI."""
    parser = argparse.ArgumentParser(
        description="TMT Quantum Vault Architecture Benchmark"
    )
    parser.add_argument(
        "--mode",
        choices=["core13", "extended17", "compare"],
        default="compare",
        help="Architecture mode to benchmark (default: compare)",
    )
    parser.add_argument(
        "--vault-path",
        type=Path,
        default=Path("."),
        help="Path to TMT Quantum Vault root (default: current directory)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output file for results (default: stdout)",
    )

    args = parser.parse_args()

    # Initialize runner
    runner = ArchitectureBenchmarkRunner(args.vault_path)

    # Run benchmark
    if args.mode == "compare":
        results = runner.compare_modes()
    elif args.mode == "core13":
        benchmark = runner.run_benchmark("core13")
        results = benchmark.to_dict()
    else:
        benchmark = runner.run_benchmark("extended17")
        results = benchmark.to_dict()

    # Output results
    output_json = json.dumps(results, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_json)
        print(f"Results written to {args.output}")
    else:
        print(output_json)


if __name__ == "__main__":
    main()
