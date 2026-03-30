from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from tmt_quantum_vault.orchestration.benchmark import OrchestrationBenchmark
from tmt_quantum_vault.orchestration.benchmark_matrix import (
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
)
from tmt_quantum_vault.orchestration.channel import AgentChannel, ChannelRegistry
from tmt_quantum_vault.orchestration.metrics import (
    CoordinationAnalyzer,
    CoordinationMetricsCollector,
    MetricsExporter,
)
from tmt_quantum_vault.orchestration.models import (
    AgentConflict,
    AgentContract,
    AgentInputSchema,
    AgentLayer,
    AgentOutputSchema,
    AgentRole,
    ConflictResolutionStrategy,
    CoordinationMetrics,
    CoordinationTrace,
    EscalationReason,
    HandoffStatus,
    RoutingDecision,
)
from tmt_quantum_vault.orchestration.orchestrator import AgentOrchestrator, AgentProfile


def make_output(
    *,
    agent_id: int = 1,
    agent_name: str = "Agent One",
    agent_role: AgentRole = AgentRole.SYNTHESIZER,
    summary: str = "processed",
    confidence: float = 0.9,
    resonance_score: float = 0.7,
    fitness_contribution: float = 0.5,
    status: HandoffStatus = HandoffStatus.COMPLETED,
    **extra: object,
) -> AgentOutputSchema:
    return AgentOutputSchema(
        task_id=uuid4(),
        agent_id=agent_id,
        agent_name=agent_name,
        agent_role=agent_role,
        result={"ok": True},
        summary=summary,
        confidence=confidence,
        resonance_score=resonance_score,
        fitness_contribution=fitness_contribution,
        status=status,
        processing_time_ms=12.5,
        **extra,
    )


def make_contract(output: AgentOutputSchema | None = None) -> AgentContract:
    contract = AgentContract(
        input=AgentInputSchema(task_type="analysis", objective="Inspect state")
    )
    contract.output = output
    if output is not None:
        contract.completed_at = contract.created_at + timedelta(milliseconds=25)
    return contract


def make_decision(
    *,
    primary_agent: AgentRole = AgentRole.SYNTHESIZER,
    layer: AgentLayer = AgentLayer.INTEGRATION,
) -> RoutingDecision:
    return RoutingDecision(
        task_id=uuid4(),
        primary_agent=primary_agent,
        primary_reason="test route",
        layer=layer,
        decision_confidence=0.91,
    )


def make_trace(
    *,
    decisions: list[RoutingDecision] | None = None,
    contracts: list[AgentContract] | None = None,
    final_status: HandoffStatus | None = HandoffStatus.COMPLETED,
    final_confidence: float = 0.8,
    total_duration_ms: float = 42.0,
) -> CoordinationTrace:
    return CoordinationTrace(
        session_id=uuid4(),
        decisions=decisions or [],
        contracts=contracts or [],
        final_status=final_status,
        final_confidence=final_confidence,
        total_duration_ms=total_duration_ms,
        completed_at=datetime(2025, 1, 1, tzinfo=UTC),
    )


def make_metrics(
    *,
    agreement_rate: float = 0.8,
    contradiction_rate: float = 0.1,
    delegation_count: int = 0,
    delegation_success_rate: float = 1.0,
    recovery_attempts: int = 0,
    recovery_success_rate: float = 1.0,
    resonance_fitness_correlation: float = 0.7,
    phi_alignment_rate: float = 0.8,
    tasks_completed: int = 10,
    tasks_failed: int = 0,
    agent_utilization: dict[str, float] | None = None,
) -> CoordinationMetrics:
    return CoordinationMetrics(
        agreement_rate=agreement_rate,
        contradiction_rate=contradiction_rate,
        delegation_count=delegation_count,
        delegation_success_rate=delegation_success_rate,
        recovery_attempts=recovery_attempts,
        recovery_success_rate=recovery_success_rate,
        resonance_fitness_correlation=resonance_fitness_correlation,
        phi_alignment_rate=phi_alignment_rate,
        tasks_completed=tasks_completed,
        tasks_failed=tasks_failed,
        agent_utilization=agent_utilization or {},
    )


def test_channel_registry_aggregate_stats() -> None:
    registry = ChannelRegistry()
    assert registry.get_aggregate_stats()["total_agents"] == 0

    channel = AgentChannel(
        agent_id=1,
        agent_name="Validator",
        agent_role=AgentRole.VALIDATOR,
    )
    registry.register(channel)

    message = channel.send(
        recipient=AgentRole.VALIDATOR,
        message_type="request",
        payload={"task": "validate"},
        requires_response=True,
        response_deadline_seconds=0.01,
    )
    delivered = channel.deliver(message)
    assert delivered is True
    assert channel.receive() is not None

    channel.record_success(confidence=0.8, resonance=0.7, processing_time_ms=10.0)
    stats = registry.get_aggregate_stats()

    assert stats["total_agents"] == 1
    assert stats["total_messages_sent"] == 1
    assert stats["total_messages_received"] == 1
    assert stats["average_success_rate"] == pytest.approx(1.0)
    assert stats["average_confidence"] == pytest.approx(0.8)
    assert stats["average_resonance"] == pytest.approx(0.7)


@pytest.mark.parametrize(
    ("strategy", "expected_agent"),
    [
        (ConflictResolutionStrategy.HIGHEST_CONFIDENCE, "High Confidence"),
        (ConflictResolutionStrategy.HIGHEST_FITNESS, "High Fitness"),
        (ConflictResolutionStrategy.WEIGHTED_VOTE, "High Fitness"),
        (ConflictResolutionStrategy.PHI_ALIGNMENT, "High Fitness"),
        (ConflictResolutionStrategy.CONSENSUS, "High Confidence"),
    ],
)
def test_orchestrator_conflict_resolution_strategies_select_expected_output(
    tmp_path: Path,
    strategy: ConflictResolutionStrategy,
    expected_agent: str,
) -> None:
    orchestrator = AgentOrchestrator(tmp_path)
    conflict = AgentConflict(
        trace_id=uuid4(),
        agent_outputs=[
            make_output(
                agent_name="High Confidence",
                confidence=0.95,
                fitness_contribution=0.4,
                resonance_score=0.6,
            ),
            make_output(
                agent_id=2,
                agent_name="High Fitness",
                agent_role=AgentRole.OBSERVER,
                confidence=0.5,
                fitness_contribution=0.9,
                resonance_score=0.95,
            ),
        ],
        conflict_type="value_mismatch",
        severity="high",
        resolution_strategy=ConflictResolutionStrategy.WEIGHTED_VOTE,
    )

    result = orchestrator.resolve_conflict(conflict, strategy=strategy)

    assert result.winning_output.agent_name == expected_agent
    assert result.strategy_used in {
        strategy,
        ConflictResolutionStrategy.HIGHEST_CONFIDENCE,
    }


def test_orchestrator_escalate_uses_next_layer_agent_or_synthesizer_fallback(
    tmp_path: Path,
) -> None:
    orchestrator = AgentOrchestrator(tmp_path)
    fallback_orchestrator = AgentOrchestrator(tmp_path)
    orchestrator._register_agent(
        AgentProfile(
            agent_id=7,
            agent_name="Observer",
            agent_role=AgentRole.OBSERVER,
            fitness=0.9,
            phi_score=0.62,
            resonance_frequency=528.0,
            specialization="resonance monitoring",
        )
    )

    escalated = orchestrator.escalate(
        reason=EscalationReason.LOW_CONFIDENCE,
        current_agent=AgentRole.STRATEGIC,
        current_confidence=0.8,
        trace_id=uuid4(),
    )
    fallback = orchestrator.escalate(
        reason=EscalationReason.ERROR,
        current_agent=AgentRole.VALIDATOR,
        current_confidence=0.5,
        trace_id=uuid4(),
    )
    default_target = fallback_orchestrator.escalate(
        reason=EscalationReason.ERROR,
        current_agent=AgentRole.VALIDATOR,
        current_confidence=0.5,
        trace_id=uuid4(),
    )

    assert escalated.escalated_to == AgentRole.OBSERVER
    assert escalated.final_confidence == pytest.approx(0.72)
    assert fallback.escalated_to == AgentRole.OBSERVER
    assert default_target.escalated_to == AgentRole.SYNTHESIZER


def test_coordination_analyzer_reports_trends_bottlenecks_and_recommendations() -> None:
    collector = CoordinationMetricsCollector()
    analyzer = CoordinationAnalyzer(collector)
    history = [
        make_metrics(
            agreement_rate=0.4,
            tasks_completed=4,
            tasks_failed=6,
            resonance_fitness_correlation=0.3,
            phi_alignment_rate=0.4,
        ),
        make_metrics(
            agreement_rate=0.5,
            tasks_completed=5,
            tasks_failed=5,
            resonance_fitness_correlation=0.35,
            phi_alignment_rate=0.45,
        ),
        make_metrics(
            agreement_rate=0.9,
            tasks_completed=9,
            tasks_failed=1,
            resonance_fitness_correlation=0.6,
            phi_alignment_rate=0.8,
        ),
    ]
    collector.get_metrics = lambda: make_metrics(
        agreement_rate=0.6,
        contradiction_rate=0.25,
        delegation_count=2,
        delegation_success_rate=0.5,
        recovery_attempts=1,
        recovery_success_rate=0.4,
        resonance_fitness_correlation=0.4,
        phi_alignment_rate=0.5,
        tasks_completed=7,
        tasks_failed=3,
        agent_utilization={"A": 1.0, "B": 0.2},
    )

    insufficient = analyzer.analyze_trends(history[:1])
    trends = analyzer.analyze_trends(history)
    bottlenecks = analyzer.identify_bottlenecks()
    recommendations = analyzer._generate_recommendations(
        collector.get_metrics(), bottlenecks
    )

    assert insufficient == {"trend": "insufficient_data"}
    assert trends["trend"] == "available"
    assert trends["trends"]["agreement_rate"]["direction"] == "improving"
    assert {b["type"] for b in bottlenecks} == {
        "high_contradiction",
        "low_delegation_success",
        "low_recovery_success",
        "utilization_imbalance",
    }
    assert any("Coordination quality is below target" in rec for rec in recommendations)
    assert any("Review handoff protocols" in rec for rec in recommendations)


def test_metrics_exporter_writes_json_and_benchmark_formats(tmp_path: Path) -> None:
    exporter = MetricsExporter(tmp_path)
    metrics = make_metrics(
        agreement_rate=0.9,
        delegation_count=3,
        delegation_success_rate=1.0,
        recovery_attempts=1,
        recovery_success_rate=1.0,
        phi_alignment_rate=0.7,
        tasks_completed=19,
        tasks_failed=1,
    )

    json_path = exporter.export_json(metrics, filename="metrics.json")
    benchmark_path = exporter.export_benchmark_format(
        metrics, filename="benchmark.json"
    )

    assert json_path.read_text(encoding="utf-8")
    assert benchmark_path.read_text(encoding="utf-8")


class DummyOrchestrator:
    def __init__(self, traces: list[CoordinationTrace | Exception]):
        self._traces = traces
        self.calls: list[tuple[str, str, dict[str, object]]] = []

    def execute(self, task_type: str, objective: str, context: dict[str, object]):
        self.calls.append((task_type, objective, context))
        outcome = self._traces.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def test_orchestration_benchmark_task_execution(tmp_path: Path) -> None:
    orchestrator = DummyOrchestrator(
        [
            make_trace(
                final_status=HandoffStatus.COMPLETED,
                final_confidence=0.9,
                total_duration_ms=50.0,
            ),
            RuntimeError("boom"),
        ]
    )
    benchmark = OrchestrationBenchmark(orchestrator, output_dir=tmp_path)

    task_results = benchmark._benchmark_task_type("analysis", iterations=2)
    summary = benchmark._create_summary(
        make_metrics(
            agreement_rate=0.86,
            delegation_success_rate=0.9,
            recovery_success_rate=0.9,
            resonance_fitness_correlation=0.8,
            phi_alignment_rate=0.7,
            tasks_completed=19,
            tasks_failed=0,
        ),
        {"task_results": {"analysis": task_results}},
    )

    assert task_results["successful"] == 1
    assert task_results["failed"] == 1
    assert task_results["avg_latency_ms"] == pytest.approx(50.0)
    assert task_results["avg_confidence"] == pytest.approx(0.9)
    assert task_results["success_rate"] == pytest.approx(0.5)
    assert summary["passed"] is True
    assert summary["overall_success_rate"] == pytest.approx(0.5)


def test_benchmark_result_properties_reflect_execution_mode_and_scores() -> None:
    simulation = BenchmarkResult(
        task_id="SIM-1",
        baseline=BaselineType.FULL_ORCHESTRATION,
        execution_mode=ExecutionMode.SIMULATION,
        structural_status=StructuralStatus.PASSED,
        routing_correct=True,
        layers_traversed_correct=True,
        handoffs_completed=2,
        contracts_valid=True,
        confidence=0.8,
        resonance_score=0.6,
    )
    live = BenchmarkResult(
        task_id="LIVE-1",
        baseline=BaselineType.FULL_ORCHESTRATION,
        execution_mode=ExecutionMode.LIVE,
        structural_status=StructuralStatus.PASSED,
        routing_correct=True,
        layers_traversed_correct=True,
        handoffs_completed=4,
        contracts_valid=True,
        execution_status=ExecutionStatus.COMPLETED,
        confidence=0.8,
        resonance_score=0.6,
    )

    assert simulation.success is True
    assert simulation.task_completion_score == 0.0
    assert simulation.output_quality_score == 0.0
    assert live.success is True
    assert live.orchestration_score == 1.0
    assert live.task_completion_score == 1.0
    assert live.output_quality_score == pytest.approx(0.7)


def test_benchmark_runner_helpers_cover_failure_and_resonance_paths(
    tmp_path: Path,
) -> None:
    matrix = TMTBenchmarkMatrix(tmp_path)
    runner = BenchmarkRunner(
        matrix, output_dir=tmp_path, execution_mode=ExecutionMode.LIVE
    )
    task = BenchmarkTask(
        task_id="ROUTE-TEST",
        category=BenchmarkCategory.ROUTING,
        layer=BenchmarkLayer.SYSTEM,
        description="Route the task",
        expected_agents=["validator"],
        expected_layers=["integration"],
    )

    failed_output = make_output(
        agent_name="Validator",
        agent_role=AgentRole.VALIDATOR,
        summary="schema error",
        confidence=0.4,
        resonance_score=0.2,
        status=HandoffStatus.FAILED,
        error="bad schema",
    )
    contrasting_output = make_output(
        agent_id=2,
        agent_name="Observer",
        agent_role=AgentRole.OBSERVER,
        summary="different answer",
        confidence=0.8,
        resonance_score=0.9,
    )
    trace = make_trace(
        decisions=[make_decision(primary_agent=AgentRole.VALIDATOR)],
        contracts=[make_contract(failed_output), make_contract(contrasting_output)],
        final_status=HandoffStatus.FAILED,
    )
    trace.expected_agents = ["validator"]

    assert runner._check_routing(task, ["validator"]) is True
    assert runner._check_layers(task, ["integration"]) is True
    assert runner._check_contracts(trace) is False
    assert runner._determine_failure_reason(make_trace(decisions=[], contracts=[])) == (
        FailureReason.ROUTING_MISMATCH
    )
    assert runner._determine_failure_reason(trace) == FailureReason.LLM_ERROR
    assert "Expected agents" in runner._get_failure_details(
        trace, FailureReason.ROUTING_MISMATCH
    )
    assert "LLM error: bad schema" in runner._get_failure_details(
        trace, FailureReason.LLM_ERROR
    )
    assert runner._calculate_resonance(trace) == pytest.approx(0.55)
    assert runner._detect_contradiction(trace) is True


def test_benchmark_runner_compare_baselines_reports_improvements(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = BenchmarkRunner(TMTBenchmarkMatrix(tmp_path), output_dir=tmp_path)

    def fake_run_baseline(
        baseline: BaselineType, orchestrator: object
    ) -> dict[str, float]:
        return (
            {
                "orchestration_score": 0.9,
                "task_completion_score": 0.8,
                "output_quality_score": 0.7,
                "average_resonance": 0.6,
            }
            if baseline == BaselineType.FULL_ORCHESTRATION
            else {
                "orchestration_score": 0.7,
                "task_completion_score": 0.5,
                "output_quality_score": 0.3,
                "average_resonance": 0.2,
            }
        )

    monkeypatch.setattr(runner, "run_baseline", fake_run_baseline)

    comparison = runner.compare_baselines(orchestrator=object())

    assert comparison["baselines"][BaselineType.FULL_ORCHESTRATION.value][
        "orchestration_score"
    ] == pytest.approx(0.9)
    assert comparison["improvement"] == {
        "orchestration_score": pytest.approx(0.2),
        "task_completion_score": pytest.approx(0.3),
        "output_quality_score": pytest.approx(0.4),
        "resonance_contribution": pytest.approx(0.4),
    }
