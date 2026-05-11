"""
Ablation Study Framework for TMT Quantum Vault.

This module implements systematic ablation studies to measure the contribution
of individual components to overall orchestration performance.

Ablation Types:
1. Agent Ablation: Remove individual agents from the ensemble
2. Layer Ablation: Disable specific coordination layers
3. Feature Ablation: Disable specific features (routing, handoff, consensus)
4. Metric Ablation: Remove specific scoring components

Reference:
- Ablation studies methodology: https://arxiv.org/abs/1905.04699
- Component importance analysis: https://proceedings.neurips.cc/paper/2018
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import uuid4

from .benchmark_matrix import (
    BaselineType,
    BenchmarkResult,
    BenchmarkTask,
    ExecutionMode,
    ExecutionStatus,
    FailureReason,
    StructuralStatus,
    TMTBenchmarkMatrix,
)

logger = logging.getLogger(__name__)

# =============================================================================
# Ablation Types
# =============================================================================


class AblationType(StrEnum):
    """Types of ablation experiments."""

    AGENT = "agent"  # Remove individual agent
    LAYER = "layer"  # Disable coordination layer
    FEATURE = "feature"  # Disable specific feature
    METRIC = "metric"  # Remove scoring component
    COMBINATION = "combination"  # Multiple ablations combined


class AblationScope(StrEnum):
    """Scope of ablation impact."""

    LOCAL = "local"  # Affects single agent/operation
    GLOBAL = "global"  # Affects entire orchestration
    CASCADING = "cascading"  # Propagates through layers


@dataclass
class AblationConfig:
    """Configuration for a single ablation experiment."""

    ablation_id: str
    ablation_type: AblationType
    target: str  # Agent name, layer name, or feature name
    description: str
    scope: AblationScope = AblationScope.LOCAL
    disabled_components: list[str] = field(default_factory=list)
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "ablation_id": self.ablation_id,
            "ablation_type": self.ablation_type.value,
            "target": self.target,
            "description": self.description,
            "scope": self.scope.value,
            "disabled_components": self.disabled_components,
            "enabled": self.enabled,
            "metadata": self.metadata,
        }


@dataclass
class AblationResult:
    """Result of a single ablation experiment."""

    ablation_id: str
    baseline_type: BaselineType
    config: AblationConfig

    # Performance metrics
    orchestration_score: float = 0.0
    task_completion_score: float = 0.0
    output_quality_score: float = 0.0

    # Impact metrics (relative to baseline)
    score_delta: float = 0.0  # Change from baseline
    impact_percentage: float = 0.0  # Percentage impact

    # Structural metrics
    agents_available: int = 0
    agents_disabled: int = 0
    layers_available: int = 0
    layers_disabled: int = 0

    # Execution details
    tasks_passed: int = 0
    tasks_failed: int = 0
    tasks_total: int = 0

    # Timing
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Error info
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "ablation_id": self.ablation_id,
            "baseline_type": self.baseline_type.value,
            "config": self.config.to_dict(),
            "orchestration_score": self.orchestration_score,
            "task_completion_score": self.task_completion_score,
            "output_quality_score": self.output_quality_score,
            "score_delta": self.score_delta,
            "impact_percentage": self.impact_percentage,
            "agents_available": self.agents_available,
            "agents_disabled": self.agents_disabled,
            "layers_available": self.layers_available,
            "layers_disabled": self.layers_disabled,
            "tasks_passed": self.tasks_passed,
            "tasks_failed": self.tasks_failed,
            "tasks_total": self.tasks_total,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
            "error_message": self.error_message,
        }


@dataclass
class AblationStudy:
    """Complete ablation study with multiple experiments."""

    study_id: str
    study_name: str
    description: str
    baseline_score: float = 0.0
    results: list[AblationResult] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "study_id": self.study_id,
            "study_name": self.study_name,
            "description": self.description,
            "baseline_score": self.baseline_score,
            "results": [r.to_dict() for r in self.results],
            "summary": self.summary,
            "created_at": self.created_at.isoformat(),
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
        }


# =============================================================================
# Ablation Configurations
# =============================================================================

# Standard agent ablations (one agent removed at a time)
AGENT_ABLATIONS: list[AblationConfig] = [
    AblationConfig(
        ablation_id="ABL-AGENT-001",
        ablation_type=AblationType.AGENT,
        target="Synthesizer",
        description="Remove Synthesizer (integration center) from ensemble",
        scope=AblationScope.GLOBAL,
        disabled_components=["synthesizer"],
    ),
    AblationConfig(
        ablation_id="ABL-AGENT-002",
        ablation_type=AblationType.AGENT,
        target="Observer",
        description="Remove Observer (monitoring) from ensemble",
        scope=AblationScope.LOCAL,
        disabled_components=["observer"],
    ),
    AblationConfig(
        ablation_id="ABL-AGENT-003",
        ablation_type=AblationType.AGENT,
        target="Validator",
        description="Remove Validator (output verification) from ensemble",
        scope=AblationScope.GLOBAL,
        disabled_components=["validator"],
    ),
    AblationConfig(
        ablation_id="ABL-AGENT-004",
        ablation_type=AblationType.AGENT,
        target="Archivist",
        description="Remove Archivist (memory) from ensemble",
        scope=AblationScope.LOCAL,
        disabled_components=["archivist"],
    ),
    AblationConfig(
        ablation_id="ABL-AGENT-005",
        ablation_type=AblationType.AGENT,
        target="Strategic",
        description="Remove Strategic (planning) from ensemble",
        scope=AblationScope.LOCAL,
        disabled_components=["strategic"],
    ),
    AblationConfig(
        ablation_id="ABL-AGENT-006",
        ablation_type=AblationType.AGENT,
        target="Federation",
        description="Remove Federation (coordination) from ensemble",
        scope=AblationScope.GLOBAL,
        disabled_components=["federation"],
    ),
    AblationConfig(
        ablation_id="ABL-AGENT-007",
        ablation_type=AblationType.AGENT,
        target="Bio",
        description="Remove Bio (healing) from ensemble",
        scope=AblationScope.LOCAL,
        disabled_components=["bio"],
    ),
    AblationConfig(
        ablation_id="ABL-AGENT-008",
        ablation_type=AblationType.AGENT,
        target="BitNet",
        description="Remove BitNet (neural) from ensemble",
        scope=AblationScope.LOCAL,
        disabled_components=["bitnet"],
    ),
]

# Layer ablations (disable entire coordination layers)
LAYER_ABLATIONS: list[AblationConfig] = [
    AblationConfig(
        ablation_id="ABL-LAYER-001",
        ablation_type=AblationType.LAYER,
        target="INPUT",
        description="Disable input layer (Bio, Fractal, Visual)",
        scope=AblationScope.CASCADING,
        disabled_components=["input"],
    ),
    AblationConfig(
        ablation_id="ABL-LAYER-002",
        ablation_type=AblationType.LAYER,
        target="PROCESSING",
        description="Disable processing layer (Strategic, BitNet, Harmonic, Wormhole)",
        scope=AblationScope.CASCADING,
        disabled_components=["processing"],
    ),
    AblationConfig(
        ablation_id="ABL-LAYER-003",
        ablation_type=AblationType.LAYER,
        target="INTEGRATION",
        description="Disable integration layer (Synthesizer, Observer, Federation, Mirror)",
        scope=AblationScope.GLOBAL,
        disabled_components=["integration"],
    ),
    AblationConfig(
        ablation_id="ABL-LAYER-004",
        ablation_type=AblationType.LAYER,
        target="OUTPUT",
        description="Disable output layer (Validator, Archivist, Workflow, Auditor)",
        scope=AblationScope.LOCAL,
        disabled_components=["output"],
    ),
]

# Feature ablations (disable specific orchestration features)
FEATURE_ABLATIONS: list[AblationConfig] = [
    AblationConfig(
        ablation_id="ABL-FEAT-001",
        ablation_type=AblationType.FEATURE,
        target="routing_optimization",
        description="Disable phi-resonance routing optimization",
        scope=AblationScope.LOCAL,
        disabled_components=["phi_routing"],
    ),
    AblationConfig(
        ablation_id="ABL-FEAT-002",
        ablation_type=AblationType.FEATURE,
        target="handoff_validation",
        description="Disable handoff contract validation",
        scope=AblationScope.LOCAL,
        disabled_components=["handoff_validation"],
    ),
    AblationConfig(
        ablation_id="ABL-FEAT-003",
        ablation_type=AblationType.FEATURE,
        target="conflict_resolution",
        description="Disable automatic conflict resolution",
        scope=AblationScope.GLOBAL,
        disabled_components=["conflict_resolution"],
    ),
    AblationConfig(
        ablation_id="ABL-FEAT-004",
        ablation_type=AblationType.FEATURE,
        target="consensus_voting",
        description="Disable consensus voting mechanism",
        scope=AblationScope.GLOBAL,
        disabled_components=["consensus"],
    ),
    AblationConfig(
        ablation_id="ABL-FEAT-005",
        ablation_type=AblationType.FEATURE,
        target="recovery_fallback",
        description="Disable recovery fallback mechanisms",
        scope=AblationScope.GLOBAL,
        disabled_components=["recovery"],
    ),
    AblationConfig(
        ablation_id="ABL-FEAT-006",
        ablation_type=AblationType.FEATURE,
        target="memory_persistence",
        description="Disable Archivist memory persistence",
        scope=AblationScope.LOCAL,
        disabled_components=["memory"],
    ),
]

# Combination ablations (multiple components)
COMBINATION_ABLATIONS: list[AblationConfig] = [
    AblationConfig(
        ablation_id="ABL-COMB-001",
        ablation_type=AblationType.COMBINATION,
        target="integration_output",
        description="Disable both integration and output layers",
        scope=AblationScope.GLOBAL,
        disabled_components=["integration", "output"],
    ),
    AblationConfig(
        ablation_id="ABL-COMB-002",
        ablation_type=AblationType.COMBINATION,
        target="synthesizer_validator",
        description="Remove both Synthesizer and Validator",
        scope=AblationScope.GLOBAL,
        disabled_components=["synthesizer", "validator"],
    ),
    AblationConfig(
        ablation_id="ABL-COMB-003",
        ablation_type=AblationType.COMBINATION,
        target="memory_consensus",
        description="Disable memory and consensus features",
        scope=AblationScope.GLOBAL,
        disabled_components=["memory", "consensus"],
    ),
]

# Sierpinski/Fractal topology ablations
SIERPINSKI_ABLATIONS: list[AblationConfig] = [
    AblationConfig(
        ablation_id="ABL-SIERP-001",
        ablation_type=AblationType.FEATURE,
        target="sierpinski_topology",
        description="Disable Sierpinski fractal topology (use standard GHZ)",
        scope=AblationScope.LOCAL,
        disabled_components=["sierpinski_entanglement", "phi_phase_rotations"],
    ),
    AblationConfig(
        ablation_id="ABL-SIERP-002",
        ablation_type=AblationType.FEATURE,
        target="metatron_overlay",
        description="Disable Metatron cube geometry overlay",
        scope=AblationScope.LOCAL,
        disabled_components=["metatron_entanglement", "sefirah_phases"],
    ),
    AblationConfig(
        ablation_id="ABL-SIERP-003",
        ablation_type=AblationType.COMBINATION,
        target="fractal_agent_full",
        description="Disable Fractal agent with Sierpinski topology",
        scope=AblationScope.GLOBAL,
        disabled_components=["fractal", "sierpinski_topology", "phi_routing"],
    ),
    AblationConfig(
        ablation_id="ABL-SIERP-004",
        ablation_type=AblationType.FEATURE,
        target="phi_gating",
        description="Disable φ-gating threshold (0.618) for hardware routing",
        scope=AblationScope.GLOBAL,
        disabled_components=["phi_threshold", "resonance_filter"],
    ),
]


# =============================================================================
# Ablation Study Runner
# =============================================================================


class AblationStudyRunner:
    """
    Runner for systematic ablation studies.

    This class executes ablation experiments by:
    1. Running baseline (full orchestration)
    2. Applying each ablation configuration
    3. Running benchmark suite with ablation
    4. Comparing results to baseline
    5. Generating impact analysis
    """

    def __init__(
        self,
        vault_path: Path,
        output_dir: Path | None = None,
        execution_mode: ExecutionMode = ExecutionMode.SIMULATION,
    ):
        """Initialize ablation study runner.

        Args:
            vault_path: Path to TMT Quantum Vault
            output_dir: Directory for results (default: vault_path/ablation_results)
            execution_mode: Execution mode for benchmarks
        """
        self.vault_path = Path(vault_path)
        self.output_dir = (
            Path(output_dir) if output_dir else self.vault_path / "ablation_results"
        )
        self.execution_mode = execution_mode
        self.benchmark_matrix = TMTBenchmarkMatrix(vault_path)

        # Import orchestrator here to avoid circular imports
        from .orchestrator import AgentOrchestrator, RoutingPolicy

        self.AgentOrchestrator = AgentOrchestrator
        self.RoutingPolicy = RoutingPolicy

    def run_baseline(self) -> dict[str, Any]:
        """Run baseline (full orchestration) benchmark.

        Returns:
            Baseline results dictionary
        """
        logger.info("Running baseline benchmark...")

        policy = self.RoutingPolicy(policy_name="ablation_baseline")
        orchestrator = self.AgentOrchestrator(
            vault_path=self.vault_path,
            policy=policy,
            execution_mode=self.execution_mode,
        )

        # Run all benchmark tasks
        results = []
        for task in self.benchmark_matrix.tasks:
            result = self._run_task_with_orchestrator(task, orchestrator)
            results.append(result)

        # Calculate baseline scores
        baseline = self._calculate_scores(results, BaselineType.FULL_ORCHESTRATION)
        baseline["results"] = [r.__dict__ for r in results]

        logger.info(
            f"Baseline orchestration score: {baseline['orchestration_score']:.4f}"
        )
        return baseline

    def run_ablation(
        self,
        config: AblationConfig,
        baseline_score: float,
    ) -> AblationResult:
        """Run single ablation experiment.

        Args:
            config: Ablation configuration
            baseline_score: Baseline score for comparison

        Returns:
            Ablation result
        """
        logger.info(f"Running ablation: {config.ablation_id} - {config.description}")

        start_time = time.time()

        # Create policy with disabled components
        policy = self.RoutingPolicy(
            policy_name=f"ablation_{config.ablation_id}",
            disabled_components=config.disabled_components,
        )

        # Create orchestrator with ablation
        orchestrator = self.AgentOrchestrator(
            vault_path=self.vault_path,
            policy=policy,
            execution_mode=self.execution_mode,
        )

        # Run benchmark tasks
        results = []
        for task in self.benchmark_matrix.tasks:
            result = self._run_task_with_orchestrator(task, orchestrator)
            results.append(result)

        # Calculate scores
        scores = self._calculate_scores(results, BaselineType.ABLATED)

        duration_ms = (time.time() - start_time) * 1000

        # Calculate impact
        score_delta = scores["orchestration_score"] - baseline_score
        impact_percentage = (
            (score_delta / baseline_score * 100) if baseline_score > 0 else 0.0
        )

        # Count available/disabled
        all_agents = [
            "synthesizer",
            "observer",
            "validator",
            "archivist",
            "strategic",
            "federation",
            "bio",
            "bitnet",
            "harmonic",
            "wormhole",
            "mirror",
            "bronze",
            "fractal",
            "visual",
            "workflow",
            "auditor",
            "data",
            "stealth",
        ]
        all_layers = ["input", "processing", "integration", "output"]

        agents_disabled = len(
            [a for a in all_agents if a in config.disabled_components]
        )
        layers_disabled = len(
            [layer for layer in all_layers if layer in config.disabled_components]
        )

        return AblationResult(
            ablation_id=config.ablation_id,
            baseline_type=BaselineType.ABLATED,
            config=config,
            orchestration_score=scores["orchestration_score"],
            task_completion_score=scores["task_completion_score"],
            output_quality_score=scores["output_quality_score"],
            score_delta=score_delta,
            impact_percentage=impact_percentage,
            agents_available=len(all_agents) - agents_disabled,
            agents_disabled=agents_disabled,
            layers_available=len(all_layers) - layers_disabled,
            layers_disabled=layers_disabled,
            tasks_passed=scores["structural_passed"],
            tasks_failed=scores["structural_failed"],
            tasks_total=len(results),
            duration_ms=duration_ms,
        )

    def _run_task_with_orchestrator(
        self,
        task: BenchmarkTask,
        orchestrator: Any,
    ) -> BenchmarkResult:
        """Run single benchmark task with orchestrator."""
        start_time = time.time()

        try:
            trace = orchestrator.execute(
                task_type=task.task_type,
                objective=task.description,
                context={
                    **task.metadata,
                    "expected_agents": task.expected_agents,
                    "expected_layers": task.expected_layers,
                },
            )

            # Extract metrics from trace
            agents_involved = list({d.primary_agent.value for d in trace.decisions})
            layers_traversed = list({d.layer.value for d in trace.decisions})

            # Check structural correctness
            routing_correct = any(
                agent.lower() in [a.lower() for a in agents_involved]
                for agent in task.expected_agents
            )
            layers_correct = all(
                layer.lower() in [lyr.lower() for lyr in layers_traversed]
                for layer in task.expected_layers
            )
            contracts_valid = True
            handoffs = len(trace.decisions) - 1 if len(trace.decisions) > 1 else 0

            # Determine structural status
            if routing_correct and layers_correct:
                structural_status = StructuralStatus.PASSED
            elif routing_correct or layers_correct:
                structural_status = StructuralStatus.PARTIAL
            else:
                structural_status = StructuralStatus.FAILED

            duration_ms = (time.time() - start_time) * 1000

            return BenchmarkResult(
                task_id=task.task_id,
                baseline=BaselineType.FULL_ORCHESTRATION,
                execution_mode=self.execution_mode,
                structural_status=structural_status,
                routing_correct=routing_correct,
                layers_traversed_correct=layers_correct,
                handoffs_completed=handoffs,
                contracts_valid=contracts_valid,
                expected_agents_hit=routing_correct,
                expected_layers_hit=layers_correct,
                execution_status=ExecutionStatus.SIMULATION_ONLY,
                duration_ms=duration_ms,
                agents_involved=agents_involved,
                layers_traversed=layers_traversed,
                confidence=trace.final_confidence,
                resonance_score=getattr(trace, "average_resonance", 0.618),
                trace_id=trace.trace_id,
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return BenchmarkResult(
                task_id=task.task_id,
                baseline=BaselineType.FULL_ORCHESTRATION,
                execution_mode=self.execution_mode,
                structural_status=StructuralStatus.FAILED,
                routing_correct=False,
                layers_traversed_correct=False,
                handoffs_completed=0,
                contracts_valid=False,
                execution_status=ExecutionStatus.FAILED,
                failure_reason=FailureReason.UNKNOWN,
                failure_reason_details=str(e),
                duration_ms=duration_ms,
                error_message=str(e),
            )

    def run_study(
        self,
        study_name: str = "TMT Ablation Study",
        description: str = "Systematic ablation of TMT Quantum Vault components",
        ablation_types: list[AblationType] | None = None,
    ) -> AblationStudy:
        """Run complete ablation study.

        Args:
            study_name: Name for the study
            description: Study description
            ablation_types: Types of ablations to run (default: all)

        Returns:
            Complete ablation study with results
        """
        logger.info(f"Starting ablation study: {study_name}")

        study_id = str(uuid4())[:8]
        study = AblationStudy(
            study_id=study_id,
            study_name=study_name,
            description=description,
        )

        # Run baseline first
        baseline = self.run_baseline()
        study.baseline_score = baseline["orchestration_score"]

        # Determine which ablations to run
        if ablation_types is None:
            ablation_types = list(AblationType)

        configs = []
        if AblationType.AGENT in ablation_types:
            configs.extend(AGENT_ABLATIONS)
        if AblationType.LAYER in ablation_types:
            configs.extend(LAYER_ABLATIONS)
        if AblationType.FEATURE in ablation_types:
            configs.extend(FEATURE_ABLATIONS)
            configs.extend(
                SIERPINSKI_ABLATIONS
            )  # Include Sierpinski topology ablations
        if AblationType.COMBINATION in ablation_types:
            configs.extend(COMBINATION_ABLATIONS)

        # Run each ablation
        for config in configs:
            if not config.enabled:
                continue

            try:
                result = self.run_ablation(config, study.baseline_score)
                study.results.append(result)
            except Exception as e:
                logger.error(f"Ablation {config.ablation_id} failed: {e}")
                study.results.append(
                    AblationResult(
                        ablation_id=config.ablation_id,
                        baseline_type=BaselineType.ABLATED,
                        config=config,
                        error_message=str(e),
                    )
                )

        # Generate summary
        study.summary = self._generate_summary(study)
        study.completed_at = datetime.now(UTC)

        # Save results
        self._save_study(study)

        logger.info(f"Ablation study complete: {len(study.results)} experiments")
        return study

    def _calculate_scores(
        self,
        results: list[BenchmarkResult],
        baseline_type: BaselineType,
    ) -> dict[str, Any]:
        """Calculate aggregate scores from results."""
        if not results:
            return {
                "orchestration_score": 0.0,
                "task_completion_score": 0.0,
                "output_quality_score": 0.0,
                "structural_passed": 0,
                "structural_failed": 0,
            }

        orchestration_scores = [r.orchestration_score for r in results]
        task_scores = [r.task_completion_score for r in results]
        quality_scores = [r.output_quality_score for r in results]

        passed = sum(
            1 for r in results if r.structural_status == StructuralStatus.PASSED
        )
        failed = sum(
            1 for r in results if r.structural_status == StructuralStatus.FAILED
        )

        return {
            "orchestration_score": sum(orchestration_scores)
            / len(orchestration_scores),
            "task_completion_score": sum(task_scores) / len(task_scores),
            "output_quality_score": sum(quality_scores) / len(quality_scores),
            "structural_passed": passed,
            "structural_failed": failed,
        }

    def _generate_summary(self, study: AblationStudy) -> dict[str, Any]:
        """Generate summary statistics for study."""
        if not study.results:
            return {}

        # Group by ablation type
        by_type: dict[str, list[AblationResult]] = {}
        for result in study.results:
            atype = result.config.ablation_type.value
            if atype not in by_type:
                by_type[atype] = []
            by_type[atype].append(result)

        # Calculate statistics per type
        type_stats = {}
        for atype, results in by_type.items():
            valid_results = [r for r in results if r.error_message is None]
            if not valid_results:
                continue

            avg_impact = sum(r.impact_percentage for r in valid_results) / len(
                valid_results
            )
            avg_score = sum(r.orchestration_score for r in valid_results) / len(
                valid_results
            )

            type_stats[atype] = {
                "count": len(valid_results),
                "avg_impact_percentage": round(avg_impact, 2),
                "avg_orchestration_score": round(avg_score, 4),
                "most_impactful": max(
                    valid_results, key=lambda r: abs(r.impact_percentage)
                ).config.target,
            }

        # Find most impactful ablations
        sorted_by_impact = sorted(
            [r for r in study.results if r.error_message is None],
            key=lambda r: abs(r.impact_percentage),
            reverse=True,
        )

        return {
            "baseline_score": round(study.baseline_score, 4),
            "total_experiments": len(study.results),
            "successful_experiments": len(
                [r for r in study.results if r.error_message is None]
            ),
            "by_type": type_stats,
            "top_impact": [
                {
                    "ablation_id": r.ablation_id,
                    "target": r.config.target,
                    "impact": round(r.impact_percentage, 2),
                    "score": round(r.orchestration_score, 4),
                }
                for r in sorted_by_impact[:5]
            ],
        }

    def _save_study(self, study: AblationStudy) -> Path:
        """Save study results to file."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        filename = f"ablation_study_{study.study_id}_{timestamp}.json"
        filepath = self.output_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(study.to_dict(), f, indent=2, default=str)

        logger.info(f"Saved ablation study to: {filepath}")
        return filepath


# =============================================================================
# CLI Integration
# =============================================================================


def run_ablation_study(
    vault_path: Path,
    output_dir: Path | None = None,
    ablation_types: list[str] | None = None,
    execution_mode: str = "simulation",
) -> AblationStudy:
    """Run ablation study from CLI.

    Args:
        vault_path: Path to TMT Quantum Vault
        output_dir: Output directory for results
        ablation_types: Types of ablations to run
        execution_mode: Execution mode (simulation/live)

    Returns:
        Completed ablation study
    """
    mode = (
        ExecutionMode.SIMULATION
        if execution_mode == "simulation"
        else ExecutionMode.LIVE
    )

    types = None
    if ablation_types:
        types = [AblationType(t) for t in ablation_types]

    runner = AblationStudyRunner(
        vault_path=vault_path,
        output_dir=output_dir,
        execution_mode=mode,
    )

    return runner.run_study(ablation_types=types)
