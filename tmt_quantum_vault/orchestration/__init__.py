"""
Orchestration Module for TMT Quantum Vault Agent Coordination.

This module provides the core orchestration infrastructure for
multi-agent coordination, including:

- Formal agent contracts and schemas
- Inter-agent communication channels
- Context-aware routing decisions
- Execution planning and handoff management
- Conflict resolution and escalation
- Coordination metrics and tracing
- Benchmark integration
- TMT Benchmark Matrix for multi-layer evaluation

Usage:
    from tmt_quantum_vault.orchestration import (
        AgentOrchestrator,
        AgentContract,
        CoordinationTrace,
        RoutingPolicy,
        BenchmarkIntegration,
        TMTBenchmarkMatrix,
    )

    orchestrator = AgentOrchestrator(vault_path=Path("."))
    trace = orchestrator.execute(
        task_type="validation",
        objective="Validate system integrity",
    )

    # Run benchmark
    integration = BenchmarkIntegration(vault_path=Path("."))
    results = integration.run_full_benchmark()

    # Run TMT benchmark matrix
    matrix = TMTBenchmarkMatrix(vault_path=Path("."))
    runner = BenchmarkRunner(matrix)
"""

from .benchmark import (
    BenchmarkIntegration,
    OrchestrationBenchmark,
    run_orchestration_benchmark,
)
from .benchmark_matrix import (
    BENCHMARK_SCHEMA_VERSION,
    BaselineType,
    BenchmarkCategory,
    BenchmarkLayer,
    BenchmarkResult,
    BenchmarkRunner,
    BenchmarkTask,
    ExecutionMode,
    ExecutionStatus,
    FailureReason,
    StructuralStatus,
    TMTBenchmarkMatrix,
    create_benchmark_matrix,
    run_tmt_benchmark,
)
from .channel import (
    AgentBus,
    AgentChannel,
    ChannelRegistry,
    MessageQueue,
)
from .metrics import (
    CoordinationAnalyzer,
    CoordinationMetricsCollector,
    MetricsExporter,
)
from .models import (
    DEFAULT_CONFIDENCE_THRESHOLD,
    DEFAULT_ESCALATION_THRESHOLD,
    DEFAULT_RESONANCE_THRESHOLD,
    PHI,
    PHI_INVERSE,
    AgentChannelStats,
    AgentConflict,
    AgentContract,
    AgentInputSchema,
    AgentLayer,
    AgentMessage,
    AgentOutputSchema,
    AgentRole,
    ConflictResolutionRequest,
    ConflictResolutionResult,
    ConflictResolutionStrategy,
    CoordinationMetrics,
    CoordinationTrace,
    EscalationReason,
    EscalationRequest,
    EscalationResult,
    HandoffDirective,
    HandoffStatus,
    MessagePriority,
    RoutingDecision,
    RoutingPolicy,
)
from .orchestrator import (
    AgentOrchestrator,
    AgentProfile,
    ExecutionPlan,
    ExecutionPlanner,
    ExecutionStage,
    HandoffManager,
    RoutingEngine,
)
from .ablation import (
    AblationConfig,
    AblationResult,
    AblationScope,
    AblationStudy,
    AblationStudyRunner,
    AblationType,
    AGENT_ABLATIONS,
    COMBINATION_ABLATIONS,
    FEATURE_ABLATIONS,
    LAYER_ABLATIONS,
    run_ablation_study,
)

__all__ = [
    # Benchmark Matrix
    "BENCHMARK_SCHEMA_VERSION",
    "BaselineType",
    "BenchmarkCategory",
    "BenchmarkLayer",
    "BenchmarkResult",
    "BenchmarkRunner",
    "BenchmarkTask",
    "ExecutionMode",
    "ExecutionStatus",
    "FailureReason",
    "StructuralStatus",
    "TMTBenchmarkMatrix",
    "create_benchmark_matrix",
    "run_tmt_benchmark",
    # Benchmark
    "BenchmarkIntegration",
    "OrchestrationBenchmark",
    "run_orchestration_benchmark",
    # Channel
    "AgentBus",
    "AgentChannel",
    "ChannelRegistry",
    "MessageQueue",
    # Metrics
    "CoordinationAnalyzer",
    "CoordinationMetricsCollector",
    "MetricsExporter",
    # Models
    "AgentChannelStats",
    "AgentConflict",
    "AgentContract",
    "AgentInputSchema",
    "AgentLayer",
    "AgentMessage",
    "AgentOutputSchema",
    "AgentRole",
    "ConflictResolutionRequest",
    "ConflictResolutionResult",
    "ConflictResolutionStrategy",
    "CoordinationMetrics",
    "CoordinationTrace",
    "DEFAULT_CONFIDENCE_THRESHOLD",
    "DEFAULT_ESCALATION_THRESHOLD",
    "DEFAULT_RESONANCE_THRESHOLD",
    "EscalationReason",
    "EscalationRequest",
    "EscalationResult",
    "HandoffDirective",
    "HandoffStatus",
    "MessagePriority",
    "PHI",
    "PHI_INVERSE",
    "RoutingDecision",
    "RoutingPolicy",
    # Orchestrator
    "AgentOrchestrator",
    "AgentProfile",
    "ExecutionPlan",
    "ExecutionPlanner",
    "ExecutionStage",
    "HandoffManager",
    "RoutingEngine",
    # Ablation
    "AblationConfig",
    "AblationResult",
    "AblationScope",
    "AblationStudy",
    "AblationStudyRunner",
    "AblationType",
    "AGENT_ABLATIONS",
    "COMBINATION_ABLATIONS",
    "FEATURE_ABLATIONS",
    "LAYER_ABLATIONS",
    "run_ablation_study",
    # Orchestrator
    "AgentOrchestrator",
    "AgentProfile",
    "ExecutionPlan",
    "ExecutionPlanner",
    "ExecutionStage",
    "HandoffManager",
    "RoutingEngine",
]
