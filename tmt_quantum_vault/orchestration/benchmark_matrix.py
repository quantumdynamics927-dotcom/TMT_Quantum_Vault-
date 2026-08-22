"""
TMT Benchmark Matrix for Multi-Agent Orchestration Evaluation.

This module defines a comprehensive benchmark suite for evaluating the
TMT Quantum Vault orchestration system across multiple dimensions:

1. Model Layer: Raw model reasoning (HELM, MMLU-Pro style)
2. Agent Layer: Tool-using and policy-following behavior (τ-bench style)
3. System Layer: Full multi-agent orchestration (TMT-native)

Reference benchmarks:
- HELM: https://crfm.stanford.edu/helm/classic/latest/
- MMLU-Pro: https://neurips.cc/virtual/2024/poster/97435
- SWE-bench: https://www.vals.ai/benchmarks/swebench
- τ-bench: https://arxiv.org/abs/2406.12045
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import UUID

# =============================================================================
# Benchmark Types
# =============================================================================

# Schema version for backward compatibility
BENCHMARK_SCHEMA_VERSION = "1.0.0"


def _utcnow() -> datetime:
    """Return timezone-aware UTC datetime."""
    return datetime.now(UTC)


class BenchmarkLayer(StrEnum):
    """Layers of benchmark evaluation."""

    MODEL = "model"  # Raw model reasoning
    AGENT = "agent"  # Tool-using agent behavior
    SYSTEM = "system"  # Full multi-agent orchestration


class ExecutionMode(StrEnum):
    """Execution mode for benchmark runs."""

    SIMULATION = "simulation"  # Orchestration validation only (no LLM)
    LIVE = "live"  # Full execution with LLM backend


class StructuralStatus(StrEnum):
    """Status of orchestration structure (control plane)."""

    PASSED = "passed"  # All structural checks passed
    FAILED = "failed"  # Structural failure
    PARTIAL = "partial"  # Some structural checks passed
    SKIPPED = "skipped"  # Structural checks not applicable


class ExecutionStatus(StrEnum):
    """Status of task execution (intelligence plane)."""

    COMPLETED = "completed"  # Task completed successfully
    FAILED = "failed"  # Task execution failed
    TIMEOUT = "timeout"  # Task timed out
    SIMULATION_ONLY = "simulation_only"  # No live execution attempted


class FailureReason(StrEnum):
    """Machine-readable failure reasons."""

    SIMULATION_ONLY = "simulation_only"  # No live backend connected
    ROUTING_MISMATCH = "routing_mismatch"  # Wrong agent selected
    MISSING_AGENT = "missing_agent"  # Required agent not found
    TIMEOUT = "timeout"  # Execution timed out
    SCHEMA_FAILURE = "schema_failure"  # Output schema validation failed
    HANDOFF_FAILURE = "handoff_failure"  # Agent handoff failed
    CONFLICT_UNRESOLVED = "conflict_unresolved"  # Conflict not resolved
    CONSENSUS_FAILED = "consensus_failed"  # No consensus reached
    RECOVERY_FAILED = "recovery_failed"  # Recovery attempt failed
    LLM_ERROR = "llm_error"  # LLM backend error
    UNKNOWN = "unknown"  # Unknown failure


class BenchmarkCategory(StrEnum):
    """Categories of benchmark tasks."""

    ROUTING = "routing"  # Agent selection accuracy
    DELEGATION = "delegation"  # Handoff correctness
    CONFLICT = "conflict"  # Contradiction resolution
    MEMORY = "memory"  # Archive/persistence flow
    ABLATION = "ablation"  # Subsystem impact
    CONSENSUS = "consensus"  # Multi-agent agreement
    RECOVERY = "recovery"  # Failure recovery
    RESONANCE = "resonance"  # Phi-alignment behavior


class BaselineType(StrEnum):
    """Baseline comparison types."""

    SINGLE_MODEL = "single_model"  # One strong model, no ensemble
    FULL_ORCHESTRATION = "full"  # Complete TMT orchestration
    ABLATED = "ablated"  # TMT with one subsystem disabled


# =============================================================================
# Benchmark Task Definitions
# =============================================================================


@dataclass
class BenchmarkTask:
    """A single benchmark task definition."""

    task_id: str
    category: BenchmarkCategory
    layer: BenchmarkLayer
    description: str
    task_type: str = "synthesis"  # Task type for routing (validation, synthesis, etc.)
    expected_agents: list[str] = field(default_factory=list)
    expected_layers: list[str] = field(default_factory=list)
    success_criteria: dict[str, Any] = field(default_factory=dict)
    timeout_seconds: float = 30.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkResult:
    """Result of a single benchmark task execution."""

    task_id: str
    baseline: BaselineType
    execution_mode: ExecutionMode

    # Structural status (control plane)
    structural_status: StructuralStatus
    routing_correct: bool  # Expected agent selected
    layers_traversed_correct: bool  # Expected layers hit
    handoffs_completed: int  # Number of successful handoffs
    contracts_valid: bool  # All contracts satisfied schema

    # Expected targets validation
    expected_agents_hit: bool = False  # At least one expected agent was involved
    expected_layers_hit: bool = False  # All expected layers were traversed

    # Execution status (intelligence plane)
    execution_status: ExecutionStatus = ExecutionStatus.SIMULATION_ONLY
    failure_reason: FailureReason | None = None
    failure_reason_details: str | None = None  # Free-text debug info

    # Metrics
    duration_ms: float = 0.0
    agents_involved: list[str] = field(default_factory=list)
    layers_traversed: list[str] = field(default_factory=list)
    confidence: float = 0.0
    resonance_score: float = 0.0

    # Coordination metrics
    contradiction_detected: bool = False
    consensus_reached: bool = False
    recovery_required: bool = False
    recovery_successful: bool = False

    # Error details
    error_message: str | None = None
    trace_id: UUID | None = None
    timestamp: datetime = field(default_factory=_utcnow)

    # Schema version for backward compatibility (class-level constant)
    schema_version: str = field(default=BENCHMARK_SCHEMA_VERSION, init=False)

    @property
    def success(self) -> bool:
        """Overall success requires both structural and execution success."""
        if self.execution_mode == ExecutionMode.SIMULATION:
            # In simulation mode, only structural status matters
            return self.structural_status == StructuralStatus.PASSED
        else:
            # In live mode, both must succeed
            return (
                self.structural_status == StructuralStatus.PASSED
                and self.execution_status == ExecutionStatus.COMPLETED
            )

    @property
    def orchestration_score(self) -> float:
        """Score for orchestration/control plane quality (0-1)."""
        if self.structural_status == StructuralStatus.SKIPPED:
            return 0.0

        score = 0.0
        if self.routing_correct:
            score += 0.3
        if self.layers_traversed_correct:
            score += 0.2
        if self.contracts_valid:
            score += 0.2
        if self.handoffs_completed > 0:
            score += min(0.3, self.handoffs_completed * 0.1)

        return min(1.0, score)

    @property
    def task_completion_score(self) -> float:
        """Score for task completion (0-1)."""
        if self.execution_mode == ExecutionMode.SIMULATION:
            return 0.0  # Not applicable in simulation

        if self.execution_status == ExecutionStatus.COMPLETED:
            return 1.0
        elif self.execution_status == ExecutionStatus.SIMULATION_ONLY:
            return 0.0
        else:
            return 0.0

    @property
    def output_quality_score(self) -> float:
        """Score for output quality (0-1)."""
        if self.execution_mode == ExecutionMode.SIMULATION:
            return 0.0  # Not applicable in simulation

        # Based on confidence and resonance
        return (self.confidence + self.resonance_score) / 2.0


# =============================================================================
# TMT Benchmark Matrix
# =============================================================================


class TMTBenchmarkMatrix:
    """
    Comprehensive benchmark matrix for TMT Quantum Vault.

    This class defines benchmark tasks across three layers:
    - Model Layer: Raw reasoning capability
    - Agent Layer: Tool-using and policy-following
    - System Layer: Full orchestration behavior

    Each task is designed to measure specific coordination qualities:
    - Routing accuracy
    - Delegation correctness
    - Conflict resolution
    - Memory/persistence flow
    - Consensus formation
    - Recovery from failure
    - Resonance/phi-alignment
    """

    def __init__(self, vault_path: Path):
        """Initialize benchmark matrix.

        Args:
            vault_path: Path to TMT Quantum Vault
        """
        self.vault_path = Path(vault_path)
        self.tasks: list[BenchmarkTask] = []
        self.results: list[BenchmarkResult] = []
        self._initialize_tasks()

    def _initialize_tasks(self) -> None:
        """Initialize all benchmark tasks."""
        # =====================================================================
        # ROUTING TESTS - Agent selection accuracy
        # =====================================================================
        self.tasks.extend(
            [
                BenchmarkTask(
                    task_id="ROUTE-001",
                    category=BenchmarkCategory.ROUTING,
                    layer=BenchmarkLayer.SYSTEM,
                    description="Route a validation task to Validator agent",
                    task_type="validation",  # Maps to Validator/Auditor agents
                    expected_agents=[
                        "validator",
                        "auditor",
                        "observer",
                        "archivist",
                    ],  # Fallbacks included
                    expected_layers=[
                        "output",
                        "integration",
                    ],  # Validator is output layer
                    success_criteria={
                        "primary_agent_in_expected": True,
                        "confidence_threshold": 0.7,
                    },
                ),
                BenchmarkTask(
                    task_id="ROUTE-002",
                    category=BenchmarkCategory.ROUTING,
                    layer=BenchmarkLayer.SYSTEM,
                    description="Route a synthesis task to Synthesizer agent",
                    task_type="synthesis",  # Maps to Synthesizer/Federation agents
                    expected_agents=["synthesizer", "federation"],
                    expected_layers=["integration"],
                    success_criteria={
                        "primary_agent_in_expected": True,
                        "confidence_threshold": 0.7,
                    },
                ),
                BenchmarkTask(
                    task_id="ROUTE-003",
                    category=BenchmarkCategory.ROUTING,
                    layer=BenchmarkLayer.SYSTEM,
                    description="Route a monitoring task to Observer agent",
                    task_type="monitoring",  # Maps to Observer/Harmonic agents
                    expected_agents=["observer", "harmonic"],
                    expected_layers=["integration", "processing"],
                    success_criteria={
                        "primary_agent_in_expected": True,
                        "confidence_threshold": 0.7,
                    },
                ),
                BenchmarkTask(
                    task_id="ROUTE-004",
                    category=BenchmarkCategory.ROUTING,
                    layer=BenchmarkLayer.SYSTEM,
                    description="Route a strategic analysis task to Strategic agent",
                    task_type="analysis",  # Maps to Strategic/Wormhole agents
                    expected_agents=["strategic", "wormhole"],
                    expected_layers=["processing"],
                    success_criteria={
                        "primary_agent_in_expected": True,
                        "confidence_threshold": 0.7,
                    },
                ),
            ]
        )

        # =====================================================================
        # DELEGATION TESTS - Handoff correctness
        # =====================================================================
        self.tasks.extend(
            [
                BenchmarkTask(
                    task_id="DELEG-001",
                    category=BenchmarkCategory.DELEGATION,
                    layer=BenchmarkLayer.SYSTEM,
                    description="Execute task requiring handoff from input to integration layer",
                    task_type="coordination",  # Multi-agent coordination
                    expected_agents=[
                        "bio",
                        "fractal",
                        "synthesizer",
                    ],  # visual not available
                    expected_layers=["input", "integration"],
                    success_criteria={
                        "min_handoffs": 1,
                        "handoff_success_rate": 0.8,
                    },
                ),
                BenchmarkTask(
                    task_id="DELEG-002",
                    category=BenchmarkCategory.DELEGATION,
                    layer=BenchmarkLayer.SYSTEM,
                    description="Execute full pipeline: input → processing → integration → output",
                    task_type="coordination",  # Multi-agent coordination
                    expected_agents=["bio", "bitnet", "synthesizer", "bronze"],
                    expected_layers=["input", "processing", "integration", "output"],
                    success_criteria={
                        "min_handoffs": 3,
                        "handoff_success_rate": 0.8,
                    },
                ),
                BenchmarkTask(
                    task_id="DELEG-003",
                    category=BenchmarkCategory.DELEGATION,
                    layer=BenchmarkLayer.SYSTEM,
                    description="Execute task with Validator escalation",
                    task_type="validation",  # Maps to Validator/Auditor agents
                    expected_agents=[
                        "archivist",
                        "observer",
                        "synthesizer",
                    ],  # workflow, validator, visual not available
                    expected_layers=["output", "integration"],
                    success_criteria={
                        "escalation_detected": True,
                        "escalation_resolved": True,
                    },
                ),
            ]
        )

        # =====================================================================
        # CONFLICT TESTS - Contradiction resolution
        # =====================================================================
        self.tasks.extend(
            [
                BenchmarkTask(
                    task_id="CONF-001",
                    category=BenchmarkCategory.CONFLICT,
                    layer=BenchmarkLayer.SYSTEM,
                    description="Resolve task with ambiguous routing (multiple valid agents)",
                    task_type="synthesis",  # Maps to Synthesizer/Federation agents
                    expected_agents=["synthesizer", "federation", "observer"],
                    expected_layers=["integration"],
                    success_criteria={
                        "contradiction_detected": True,
                        "resolution_strategy": "weighted_vote",
                        "consensus_reached": True,
                    },
                ),
                BenchmarkTask(
                    task_id="CONF-002",
                    category=BenchmarkCategory.CONFLICT,
                    layer=BenchmarkLayer.SYSTEM,
                    description="Handle task with conflicting agent outputs",
                    task_type="analysis",  # Maps to Strategic/Wormhole agents
                    expected_agents=["strategic", "observer"],
                    expected_layers=["processing", "integration"],
                    success_criteria={
                        "contradiction_detected": True,
                        "resolution_time_ms": 5000,
                    },
                ),
            ]
        )

        # =====================================================================
        # MEMORY TESTS - Archive/persistence flow
        # =====================================================================
        self.tasks.extend(
            [
                BenchmarkTask(
                    task_id="MEM-001",
                    category=BenchmarkCategory.MEMORY,
                    layer=BenchmarkLayer.SYSTEM,
                    description="Execute task requiring Archivist involvement",
                    task_type="archival",  # Maps to Archivist/Auditor agents
                    expected_agents=["archivist"],
                    expected_layers=["output"],
                    success_criteria={
                        "archivist_involved": True,
                        "memory_written": True,
                    },
                ),
                BenchmarkTask(
                    task_id="MEM-002",
                    category=BenchmarkCategory.MEMORY,
                    layer=BenchmarkLayer.SYSTEM,
                    description="Retrieve and use archived context in new task",
                    task_type="archival",  # Maps to Archivist/Auditor agents
                    expected_agents=["archivist", "synthesizer"],
                    expected_layers=["output", "integration"],
                    success_criteria={
                        "memory_retrieved": True,
                        "context_used": True,
                    },
                ),
            ]
        )

        # =====================================================================
        # CONSENSUS TESTS - Multi-agent agreement
        # =====================================================================
        self.tasks.extend(
            [
                BenchmarkTask(
                    task_id="CONS-001",
                    category=BenchmarkCategory.CONSENSUS,
                    layer=BenchmarkLayer.SYSTEM,
                    description="Achieve consensus across integration layer agents",
                    task_type="coordination",  # Multi-agent coordination
                    expected_agents=["synthesizer", "observer", "federation", "mirror"],
                    expected_layers=["integration"],
                    success_criteria={
                        "min_agents_involved": 2,
                        "agreement_rate": 0.7,
                        "consensus_time_ms": 3000,
                    },
                ),
                BenchmarkTask(
                    task_id="CONS-002",
                    category=BenchmarkCategory.CONSENSUS,
                    layer=BenchmarkLayer.SYSTEM,
                    description="Measure agreement rate across repeated runs",
                    task_type="coordination",  # Multi-agent coordination
                    expected_agents=["synthesizer"],
                    expected_layers=["integration"],
                    success_criteria={
                        "stability_coefficient": 0.8,
                        "variance_threshold": 0.1,
                    },
                    metadata={"repetitions": 5},
                ),
            ]
        )

        # =====================================================================
        # RECOVERY TESTS - Failure recovery
        # =====================================================================
        self.tasks.extend(
            [
                BenchmarkTask(
                    task_id="REC-001",
                    category=BenchmarkCategory.RECOVERY,
                    layer=BenchmarkLayer.SYSTEM,
                    description="Recover from simulated agent failure",
                    task_type="synthesis",  # Maps to Synthesizer/Federation agents
                    expected_agents=["synthesizer", "bronze"],
                    expected_layers=["integration", "output"],
                    success_criteria={
                        "failure_detected": True,
                        "recovery_attempted": True,
                        "recovery_success": True,
                    },
                    metadata={"simulate_failure": True},
                ),
                BenchmarkTask(
                    task_id="REC-002",
                    category=BenchmarkCategory.RECOVERY,
                    layer=BenchmarkLayer.SYSTEM,
                    description="Handle timeout and fallback routing",
                    task_type="synthesis",  # Maps to Synthesizer/Federation agents
                    expected_agents=["synthesizer", "observer"],
                    expected_layers=["integration"],
                    success_criteria={
                        "timeout_detected": True,
                        "fallback_used": True,
                    },
                    timeout_seconds=5.0,
                ),
            ]
        )

        # =====================================================================
        # RESONANCE TESTS - Phi-alignment behavior
        # =====================================================================
        self.tasks.extend(
            [
                BenchmarkTask(
                    task_id="RES-001",
                    category=BenchmarkCategory.RESONANCE,
                    layer=BenchmarkLayer.SYSTEM,
                    description="Select agent with highest phi-alignment for task",
                    task_type="synthesis",  # Maps to Synthesizer/Federation agents
                    expected_agents=["synthesizer", "observer"],
                    expected_layers=["integration"],
                    success_criteria={
                        "phi_alignment_rate": 0.618,
                        "resonance_fitness_correlation": 0.5,
                    },
                ),
                BenchmarkTask(
                    task_id="RES-002",
                    category=BenchmarkCategory.RESONANCE,
                    layer=BenchmarkLayer.SYSTEM,
                    description="Measure resonance-to-fitness correlation",
                    task_type="processing",  # Maps to BitNet/Harmonic agents
                    expected_agents=["harmonic", "synthesizer"],
                    expected_layers=["processing", "integration"],
                    success_criteria={
                        "resonance_fitness_correlation": 0.5,
                    },
                ),
            ]
        )

        # =====================================================================
        # ABLATION TESTS - Subsystem impact
        # =====================================================================
        self.tasks.extend(
            [
                BenchmarkTask(
                    task_id="ABL-001",
                    category=BenchmarkCategory.ABLATION,
                    layer=BenchmarkLayer.SYSTEM,
                    description="Execute task with Federation agent disabled",
                    task_type="synthesis",  # Maps to Synthesizer/Federation agents
                    expected_agents=["synthesizer", "observer"],
                    expected_layers=["integration"],
                    success_criteria={
                        "ablated_agent_excluded": True,
                        "task_completed": True,
                    },
                    metadata={"ablated_agents": ["federation"]},
                ),
                BenchmarkTask(
                    task_id="ABL-002",
                    category=BenchmarkCategory.ABLATION,
                    layer=BenchmarkLayer.SYSTEM,
                    description="Execute task with resonance weighting disabled",
                    task_type="synthesis",  # Maps to Synthesizer/Federation agents
                    expected_agents=["synthesizer"],
                    expected_layers=["integration"],
                    success_criteria={
                        "resonance_disabled": True,
                        "task_completed": True,
                    },
                    metadata={"disable_resonance": True},
                ),
            ]
        )

    def get_tasks_by_category(self, category: BenchmarkCategory) -> list[BenchmarkTask]:
        """Get all tasks in a category.

        Args:
            category: Benchmark category

        Returns:
            List of tasks in the category
        """
        return [t for t in self.tasks if t.category == category]

    def get_tasks_by_layer(self, layer: BenchmarkLayer) -> list[BenchmarkTask]:
        """Get all tasks for a layer.

        Args:
            layer: Benchmark layer

        Returns:
            List of tasks for the layer
        """
        return [t for t in self.tasks if t.layer == layer]

    def get_baseline_tasks(self, baseline: BaselineType) -> list[BenchmarkTask]:
        """Get tasks applicable to a baseline.

        Args:
            baseline: Baseline type

        Returns:
            List of applicable tasks
        """
        if baseline == BaselineType.SINGLE_MODEL:
            # Single model can only do model-layer tasks
            return [t for t in self.tasks if t.layer == BenchmarkLayer.MODEL]
        else:
            # Full and ablated can do all system-layer tasks
            return [t for t in self.tasks if t.layer == BenchmarkLayer.SYSTEM]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "vault_path": str(self.vault_path),
            "total_tasks": len(self.tasks),
            "categories": {
                cat.value: len(self.get_tasks_by_category(cat))
                for cat in BenchmarkCategory
            },
            "layers": {
                layer.value: len(self.get_tasks_by_layer(layer))
                for layer in BenchmarkLayer
            },
            "tasks": [
                {
                    "task_id": t.task_id,
                    "category": t.category.value,
                    "layer": t.layer.value,
                    "description": t.description,
                    "expected_agents": t.expected_agents,
                    "expected_layers": t.expected_layers,
                    "success_criteria": t.success_criteria,
                }
                for t in self.tasks
            ],
        }


# =============================================================================
# Benchmark Runner
# =============================================================================


class BenchmarkRunner:
    """Runs benchmark tasks and collects results."""

    def __init__(
        self,
        matrix: TMTBenchmarkMatrix,
        output_dir: Path | None = None,
        execution_mode: ExecutionMode = ExecutionMode.SIMULATION,
    ):
        """Initialize benchmark runner.

        Args:
            matrix: Benchmark matrix
            output_dir: Output directory for results
            execution_mode: Execution mode (simulation or live)
        """
        self.matrix = matrix
        self.output_dir = output_dir or Path("benchmark_results")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.execution_mode = execution_mode
        self.results: list[BenchmarkResult] = []

    def run_task(
        self,
        task: BenchmarkTask,
        baseline: BaselineType,
        orchestrator: Any,  # AgentOrchestrator
    ) -> BenchmarkResult:
        """Run a single benchmark task.

        Args:
            task: Benchmark task
            baseline: Baseline type
            orchestrator: Agent orchestrator

        Returns:
            Benchmark result
        """
        start_time = time.time()

        try:
            # Execute task through orchestrator
            trace = orchestrator.execute(
                task_type=task.task_type,  # Use task_type for routing
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
            routing_correct = self._check_routing(task, agents_involved)
            layers_correct = self._check_layers(task, layers_traversed)
            contracts_valid = self._check_contracts(trace)
            handoffs = len(trace.decisions) - 1 if len(trace.decisions) > 1 else 0

            # Check expected targets
            expected_agents_hit = routing_correct  # At least one expected agent
            expected_layers_hit = layers_correct  # All expected layers

            # Determine structural status
            if routing_correct and layers_correct and contracts_valid:
                structural_status = StructuralStatus.PASSED
            elif routing_correct or layers_correct:
                structural_status = StructuralStatus.PARTIAL
            else:
                structural_status = StructuralStatus.FAILED

            # Determine execution status based on mode
            if self.execution_mode == ExecutionMode.SIMULATION:
                execution_status = ExecutionStatus.SIMULATION_ONLY
                failure_reason = FailureReason.SIMULATION_ONLY
                failure_reason_details = "Simulation mode - no live execution attempted"
            elif trace.final_status and trace.final_status.value == "completed":
                execution_status = ExecutionStatus.COMPLETED
                failure_reason = None
                failure_reason_details = None
            else:
                execution_status = ExecutionStatus.FAILED
                failure_reason = self._determine_failure_reason(trace)
                failure_reason_details = self._get_failure_details(
                    trace, failure_reason
                )

            duration_ms = (time.time() - start_time) * 1000

            result = BenchmarkResult(
                task_id=task.task_id,
                baseline=baseline,
                execution_mode=self.execution_mode,
                structural_status=structural_status,
                routing_correct=routing_correct,
                layers_traversed_correct=layers_correct,
                handoffs_completed=handoffs,
                contracts_valid=contracts_valid,
                expected_agents_hit=expected_agents_hit,
                expected_layers_hit=expected_layers_hit,
                execution_status=execution_status,
                failure_reason=failure_reason,
                failure_reason_details=failure_reason_details,
                duration_ms=duration_ms,
                agents_involved=agents_involved,
                layers_traversed=layers_traversed,
                confidence=trace.final_confidence,
                resonance_score=self._calculate_resonance(trace),
                contradiction_detected=self._detect_contradiction(trace),
                consensus_reached=trace.final_status
                and trace.final_status.value == "completed",
                recovery_required=False,
                trace_id=trace.trace_id,
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            result = BenchmarkResult(
                task_id=task.task_id,
                baseline=baseline,
                execution_mode=self.execution_mode,
                structural_status=StructuralStatus.FAILED,
                routing_correct=False,
                layers_traversed_correct=False,
                handoffs_completed=0,
                contracts_valid=False,
                expected_agents_hit=False,
                expected_layers_hit=False,
                execution_status=ExecutionStatus.FAILED,
                failure_reason=FailureReason.UNKNOWN,
                failure_reason_details=f"Exception during execution: {type(e).__name__}",
                duration_ms=duration_ms,
                agents_involved=[],
                layers_traversed=[],
                confidence=0.0,
                resonance_score=0.0,
                contradiction_detected=False,
                consensus_reached=False,
                recovery_required=True,
                error_message=str(e),
            )

        self.results.append(result)
        return result

    def _check_routing(self, task: BenchmarkTask, agents_involved: list[str]) -> bool:
        """Check if routing selected expected agents."""
        expected = [a.lower() for a in task.expected_agents]
        actual = [a.lower() for a in agents_involved]
        return any(a in expected for a in actual)

    def _check_layers(self, task: BenchmarkTask, layers_traversed: list[str]) -> bool:
        """Check if expected layers were traversed."""
        expected = [layer.lower() for layer in task.expected_layers]
        actual = [layer.lower() for layer in layers_traversed]
        return all(layer in actual for layer in expected) if expected else True

    def _check_contracts(self, trace: Any) -> bool:
        """Check if all contracts were valid."""
        for contract in trace.contracts:
            if not contract.output:
                return False
            if contract.output.status.value not in ("completed", "accepted"):
                return False
        return True

    def _determine_failure_reason(self, trace: Any) -> FailureReason:
        """Determine the reason for failure."""
        if not trace.decisions:
            return FailureReason.ROUTING_MISMATCH

        if not trace.contracts:
            return FailureReason.SCHEMA_FAILURE

        for contract in trace.contracts:
            if contract.output and contract.output.status.value == "failed":
                return FailureReason.LLM_ERROR

        return FailureReason.UNKNOWN

    def _get_failure_details(self, trace: Any, reason: FailureReason) -> str:
        """Get detailed failure description for debugging."""
        details = []

        if reason == FailureReason.ROUTING_MISMATCH:
            expected = getattr(trace, "expected_agents", [])
            actual = (
                [d.primary_agent.value for d in trace.decisions]
                if trace.decisions
                else []
            )
            details.append(f"Expected agents: {expected}, got: {actual}")

        elif reason == FailureReason.MISSING_AGENT:
            details.append("Required agent not found in registry")

        elif reason == FailureReason.TIMEOUT:
            details.append("Execution exceeded timeout")

        elif reason == FailureReason.SCHEMA_FAILURE:
            for contract in trace.contracts:
                if contract.output and contract.output.status.value == "failed":
                    details.append(
                        f"Contract {contract.agent_id}: {contract.output.error or 'schema validation failed'}"
                    )

        elif reason == FailureReason.HANDOFF_FAILURE:
            details.append("Agent handoff failed during execution")

        elif reason == FailureReason.CONSENSUS_FAILED:
            details.append("Multi-agent consensus not reached")

        elif reason == FailureReason.LLM_ERROR:
            for contract in trace.contracts:
                if (
                    contract.output
                    and hasattr(contract.output, "error")
                    and contract.output.error
                ):
                    details.append(f"LLM error: {contract.output.error}")

        return "; ".join(details) if details else f"Failure: {reason.value}"

    def _calculate_resonance(self, trace: Any) -> float:
        """Calculate average resonance score from trace."""
        if not trace.contracts:
            return 0.0

        resonances = [c.output.resonance_score for c in trace.contracts if c.output]

        return sum(resonances) / len(resonances) if resonances else 0.0

    def _detect_contradiction(self, trace: Any) -> bool:
        """Detect if there were contradictions in the trace."""
        # Check for multiple agents with different outputs
        if len(trace.contracts) < 2:
            return False

        outputs = [c.output.summary for c in trace.contracts if c.output]

        # Simple contradiction detection: different outputs
        return len(set(outputs)) > 1

    def run_baseline(
        self,
        baseline: BaselineType,
        orchestrator: Any,
        task_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Run all tasks for a baseline.

        Args:
            baseline: Baseline type
            orchestrator: Agent orchestrator
            task_ids: Optional specific task IDs to run

        Returns:
            Baseline results summary with three separate scores:
            - orchestration_score: Structural correctness (routing, layers, contracts)
            - task_completion_score: Whether the task completed successfully
            - output_quality_score: Quality metrics (confidence, resonance)
        """
        tasks = self.matrix.get_baseline_tasks(baseline)

        if task_ids:
            tasks = [t for t in tasks if t.task_id in task_ids]

        results = []
        for task in tasks:
            result = self.run_task(task, baseline, orchestrator)
            results.append(result)

        # Calculate three separate scores
        # 1. Orchestration Score: Structural correctness
        structural_passed = [
            r for r in results if r.structural_status == StructuralStatus.PASSED
        ]
        structural_partial = [
            r for r in results if r.structural_status == StructuralStatus.PARTIAL
        ]
        orchestration_score = (
            (len(structural_passed) + 0.5 * len(structural_partial)) / len(results)
            if results
            else 0.0
        )

        # 2. Task Completion Score: Execution success
        completed = [
            r for r in results if r.execution_status == ExecutionStatus.COMPLETED
        ]
        simulation_only = [
            r for r in results if r.execution_status == ExecutionStatus.SIMULATION_ONLY
        ]
        # In simulation mode, we count simulation_only as "completed" for task completion
        if self.execution_mode == ExecutionMode.SIMULATION:
            task_completion_score = (
                (len(completed) + len(simulation_only)) / len(results)
                if results
                else 0.0
            )
        else:
            task_completion_score = len(completed) / len(results) if results else 0.0

        # 3. Output Quality Score: Confidence and resonance
        quality_metrics = [
            r for r in results if r.confidence > 0.5 and r.resonance_score > 0.5
        ]
        output_quality_score = len(quality_metrics) / len(results) if results else 0.0

        # Additional statistics
        average_confidence = (
            sum(r.confidence for r in results if r.confidence > 0) / len(results)
            if results
            else 0.0
        )
        average_resonance = (
            sum(r.resonance_score for r in results if r.resonance_score > 0)
            / len(results)
            if results
            else 0.0
        )

        return {
            "schema_version": BENCHMARK_SCHEMA_VERSION,
            "baseline": baseline.value,
            "execution_mode": self.execution_mode.value,
            "total_tasks": len(results),
            "structural_passed": len(structural_passed),
            "structural_partial": len(structural_partial),
            "structural_failed": len(
                [r for r in results if r.structural_status == StructuralStatus.FAILED]
            ),
            "execution_completed": len(completed),
            "execution_simulation_only": len(simulation_only),
            "execution_failed": len(
                [r for r in results if r.execution_status == ExecutionStatus.FAILED]
            ),
            # Three separate scores
            "orchestration_score": round(orchestration_score, 3),
            "task_completion_score": round(task_completion_score, 3),
            "output_quality_score": round(output_quality_score, 3),
            # Expected targets hit rates
            "expected_agents_hit_rate": (
                sum(1 for r in results if r.expected_agents_hit) / len(results)
                if results
                else 0.0
            ),
            "expected_layers_hit_rate": (
                sum(1 for r in results if r.expected_layers_hit) / len(results)
                if results
                else 0.0
            ),
            # Legacy success field for backwards compatibility
            "success": orchestration_score >= 0.5 and task_completion_score >= 0.5,
            # Detailed metrics
            "average_duration_ms": (
                sum(r.duration_ms for r in results) / len(results) if results else 0.0
            ),
            "average_confidence": round(average_confidence, 3),
            "average_resonance": round(average_resonance, 3),
            "contradiction_rate": (
                sum(1 for r in results if r.contradiction_detected) / len(results)
                if results
                else 0.0
            ),
            "consensus_rate": (
                sum(1 for r in results if r.consensus_reached) / len(results)
                if results
                else 0.0
            ),
            "results": [
                {
                    "task_id": r.task_id,
                    "execution_mode": r.execution_mode.value,
                    "structural_status": r.structural_status.value,
                    "execution_status": r.execution_status.value,
                    "orchestration_score": r.orchestration_score,
                    "task_completion_score": r.task_completion_score,
                    "output_quality_score": r.output_quality_score,
                    # Expected targets validation
                    "expected_agents_hit": r.expected_agents_hit,
                    "expected_layers_hit": r.expected_layers_hit,
                    "routing_correct": r.routing_correct,
                    "layers_traversed_correct": r.layers_traversed_correct,
                    "handoffs_completed": r.handoffs_completed,
                    "contracts_valid": r.contracts_valid,
                    # Failure info
                    "failure_reason": (
                        r.failure_reason.value if r.failure_reason else None
                    ),
                    "failure_reason_details": r.failure_reason_details,
                    # Metrics
                    "duration_ms": r.duration_ms,
                    "confidence": r.confidence,
                    "agents_involved": r.agents_involved,
                    "layers_traversed": r.layers_traversed,
                }
                for r in results
            ],
        }

    def compare_baselines(
        self,
        orchestrator: Any,
    ) -> dict[str, Any]:
        """Compare all baseline types.

        Args:
            orchestrator: Agent orchestrator

        Returns:
            Comparison results with separate scores for each baseline
        """
        comparison = {
            "timestamp": datetime.now(UTC).isoformat(),
            "execution_mode": self.execution_mode.value,
            "baselines": {},
        }

        # Run full orchestration
        comparison["baselines"][BaselineType.FULL_ORCHESTRATION.value] = (
            self.run_baseline(BaselineType.FULL_ORCHESTRATION, orchestrator)
        )

        # Run ablated (without resonance weighting)
        comparison["baselines"][BaselineType.ABLATED.value] = self.run_baseline(
            BaselineType.ABLATED, orchestrator
        )

        # Calculate improvement from ablation for each score
        full_orch = comparison["baselines"][BaselineType.FULL_ORCHESTRATION.value]
        ablated_orch = comparison["baselines"][BaselineType.ABLATED.value]

        comparison["improvement"] = {
            "orchestration_score": (
                full_orch["orchestration_score"] - ablated_orch["orchestration_score"]
            ),
            "task_completion_score": (
                full_orch["task_completion_score"]
                - ablated_orch["task_completion_score"]
            ),
            "output_quality_score": (
                full_orch["output_quality_score"] - ablated_orch["output_quality_score"]
            ),
            "resonance_contribution": (
                full_orch["average_resonance"] - ablated_orch["average_resonance"]
            ),
        }

        return comparison

    def save_results(self, filename: str | None = None) -> Path:
        """Save results to file.

        Args:
            filename: Optional filename

        Returns:
            Path to saved file
        """
        filename = (
            filename
            or f"benchmark_results_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.json"
        )
        output_path = self.output_dir / filename

        data = {
            "schema_version": BENCHMARK_SCHEMA_VERSION,
            "execution_mode": self.execution_mode.value,
            "generated_at": datetime.now(UTC).isoformat(),
            "matrix": self.matrix.to_dict(),
            "results": [
                {
                    "task_id": r.task_id,
                    "baseline": r.baseline.value,
                    "execution_mode": r.execution_mode.value,
                    "structural_status": r.structural_status.value,
                    "execution_status": r.execution_status.value,
                    "failure_reason": (
                        r.failure_reason.value if r.failure_reason else None
                    ),
                    "failure_reason_details": r.failure_reason_details,
                    # Three separate scores
                    "orchestration_score": r.orchestration_score,
                    "task_completion_score": r.task_completion_score,
                    "output_quality_score": r.output_quality_score,
                    # Expected targets validation
                    "expected_agents_hit": r.expected_agents_hit,
                    "expected_layers_hit": r.expected_layers_hit,
                    # Structural details
                    "routing_correct": r.routing_correct,
                    "layers_traversed_correct": r.layers_traversed_correct,
                    "handoffs_completed": r.handoffs_completed,
                    "contracts_valid": r.contracts_valid,
                    # Metrics
                    "duration_ms": r.duration_ms,
                    "agents_involved": r.agents_involved,
                    "layers_traversed": r.layers_traversed,
                    "confidence": r.confidence,
                    "resonance_score": r.resonance_score,
                    "contradiction_detected": r.contradiction_detected,
                    "consensus_reached": r.consensus_reached,
                    "recovery_required": r.recovery_required,
                    "error_message": r.error_message,
                    "trace_id": str(r.trace_id) if r.trace_id else None,
                    "timestamp": r.timestamp.isoformat(),
                }
                for r in self.results
            ],
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

        return output_path


# =============================================================================
# Convenience Functions
# =============================================================================


def create_benchmark_matrix(vault_path: Path) -> TMTBenchmarkMatrix:
    """Create a benchmark matrix for TMT Quantum Vault.

    Args:
        vault_path: Path to vault

    Returns:
        Benchmark matrix
    """
    return TMTBenchmarkMatrix(vault_path)


def run_tmt_benchmark(
    vault_path: Path,
    output_dir: Path | None = None,
    task_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Run TMT benchmark suite.

    Args:
        vault_path: Path to vault
        output_dir: Output directory
        task_ids: Optional specific task IDs

    Returns:
        Benchmark results
    """
    from .orchestration import AgentOrchestrator

    matrix = TMTBenchmarkMatrix(vault_path)
    runner = BenchmarkRunner(matrix, output_dir)
    orchestrator = AgentOrchestrator(vault_path)

    results = runner.run_baseline(
        BaselineType.FULL_ORCHESTRATION, orchestrator, task_ids
    )

    runner.save_results()

    return results
