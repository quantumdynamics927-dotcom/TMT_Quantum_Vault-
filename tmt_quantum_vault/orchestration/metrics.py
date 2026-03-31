"""
Coordination Metrics Tracker for Ensemble Orchestration.

This module implements metrics collection and analysis for coordination
quality, enabling benchmarkable coordination metrics.

Key Components:
- CoordinationMetricsCollector: Collects and aggregates metrics
- CoordinationAnalyzer: Analyzes coordination patterns
- MetricsExporter: Exports metrics for benchmarking
"""

from __future__ import annotations

import json
import threading
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import (
    AgentContract,
    AgentOutputSchema,
    AgentRole,
    ConflictResolutionResult,
    CoordinationMetrics,
    CoordinationTrace,
    HandoffStatus,
)


class MetricsWindow:
    """Sliding window for metrics aggregation."""

    def __init__(self, window_seconds: float = 60.0):
        """Initialize metrics window.

        Args:
            window_seconds: Window duration in seconds
        """
        self.window_seconds = window_seconds
        self._data: list[tuple[float, Any]] = []
        self._lock = threading.Lock()

    def add(self, value: Any) -> None:
        """Add value to window.

        Args:
            value: Value to add
        """
        with self._lock:
            self._data.append((time.time(), value))
            self._prune()

    def get_all(self) -> list[Any]:
        """Get all values in window.

        Returns:
            List of values
        """
        with self._lock:
            self._prune()
            return [v for _, v in self._data]

    def count(self) -> int:
        """Get count of values in window."""
        with self._lock:
            self._prune()
            return len(self._data)

    def _prune(self) -> None:
        """Remove expired values."""
        cutoff = time.time() - self.window_seconds
        self._data = [(t, v) for t, v in self._data if t > cutoff]


class CoordinationMetricsCollector:
    """Collects and aggregates coordination metrics."""

    def __init__(
        self,
        window_seconds: float = 60.0,
        history_file: Path | None = None,
    ):
        """Initialize metrics collector.

        Args:
            window_seconds: Aggregation window in seconds
            history_file: Optional file for persisting metrics
        """
        self.window_seconds = window_seconds
        self.history_file = history_file

        # Sliding windows for different metrics
        self._agreement_window = MetricsWindow(window_seconds)
        self._contradiction_window = MetricsWindow(window_seconds)
        self._delegation_window = MetricsWindow(window_seconds)
        self._recovery_window = MetricsWindow(window_seconds)
        self._resonance_window = MetricsWindow(window_seconds)
        self._task_window = MetricsWindow(window_seconds)

        # Counters
        self._total_tasks = 0
        self._completed_tasks = 0
        self._failed_tasks = 0

        # Agent utilization tracking
        self._agent_activations: dict[str, int] = defaultdict(int)
        self._agent_processing_time: dict[str, float] = defaultdict(float)

        # History
        self._metrics_history: list[CoordinationMetrics] = []
        self._lock = threading.Lock()

    # =========================================================================
    # Recording Methods
    # =========================================================================

    def record_contract_completion(self, contract: AgentContract) -> None:
        """Record contract completion.

        Args:
            contract: Completed contract
        """
        if not contract.output:
            return

        output = contract.output

        # Record confidence as agreement indicator
        self._agreement_window.add(output.confidence)

        # Record resonance
        self._resonance_window.add(output.resonance_score)

        # Record task completion
        self._task_window.add(
            {
                "success": output.status == HandoffStatus.COMPLETED,
                "duration_ms": contract.duration_ms,
                "agent": output.agent_name,
            }
        )

        # Update agent utilization
        self._agent_activations[output.agent_name] += 1
        self._agent_processing_time[output.agent_name] += output.processing_time_ms

        # Update counters
        with self._lock:
            self._total_tasks += 1
            if output.status == HandoffStatus.COMPLETED:
                self._completed_tasks += 1
            else:
                self._failed_tasks += 1

    def record_delegation(
        self,
        from_agent: AgentRole,
        to_agent: AgentRole,
        success: bool,
        depth: int = 1,
    ) -> None:
        """Record a delegation event.

        Args:
            from_agent: Source agent
            to_agent: Target agent
            success: Whether delegation succeeded
            depth: Delegation depth
        """
        self._delegation_window.add(
            {
                "from": from_agent.value,
                "to": to_agent.value,
                "success": success,
                "depth": depth,
            }
        )

    def record_recovery(
        self,
        success: bool,
        recovery_time_ms: float,
    ) -> None:
        """Record a recovery attempt.

        Args:
            success: Whether recovery succeeded
            recovery_time_ms: Recovery time in milliseconds
        """
        self._recovery_window.add(
            {
                "success": success,
                "time_ms": recovery_time_ms,
            }
        )

    def record_contradiction(
        self,
        outputs: list[AgentOutputSchema],
        resolved: bool,
    ) -> None:
        """Record a contradiction between outputs.

        Args:
            outputs: Conflicting outputs
            resolved: Whether contradiction was resolved
        """
        self._contradiction_window.add(
            {
                "agents": [o.agent_name for o in outputs],
                "resolved": resolved,
                "confidence_delta": (
                    max(o.confidence for o in outputs)
                    - min(o.confidence for o in outputs)
                ),
            }
        )

    def record_conflict_resolution(self, result: ConflictResolutionResult) -> None:
        """Record conflict resolution result.

        Args:
            result: Conflict resolution result
        """
        self._contradiction_window.add(
            {
                "strategy": result.strategy_used.value,
                "confidence": result.confidence_in_resolution,
                "time_ms": result.resolution_time_ms,
            }
        )

    def record_trace(self, trace: CoordinationTrace) -> None:
        """Record complete coordination trace.

        Args:
            trace: Coordination trace
        """
        # Record all contracts
        for contract in trace.contracts:
            self.record_contract_completion(contract)

        # Record final status
        if trace.final_status:
            success = trace.final_status == HandoffStatus.COMPLETED
            self._task_window.add(
                {
                    "success": success,
                    "duration_ms": trace.total_duration_ms,
                    "trace_id": str(trace.trace_id),
                }
            )

    # =========================================================================
    # Aggregation Methods
    # =========================================================================

    def get_metrics(self) -> CoordinationMetrics:
        """Get current coordination metrics.

        Returns:
            Coordination metrics
        """
        # Calculate agreement rate
        agreements = self._agreement_window.get_all()
        agreement_rate = sum(agreements) / len(agreements) if agreements else 0.0

        # Calculate contradiction rate
        contradictions = self._contradiction_window.get_all()
        contradiction_count = len(contradictions)
        total_outputs = len(agreements) + contradiction_count
        contradiction_rate = (
            contradiction_count / total_outputs if total_outputs > 0 else 0.0
        )

        # Calculate delegation metrics
        delegations = self._delegation_window.get_all()
        successful_delegations = sum(1 for d in delegations if d.get("success", False))
        delegation_success_rate = (
            successful_delegations / len(delegations) if delegations else 0.0
        )
        avg_delegation_depth = (
            sum(d.get("depth", 1) for d in delegations) / len(delegations)
            if delegations
            else 0.0
        )

        # Calculate recovery metrics
        recoveries = self._recovery_window.get_all()
        successful_recoveries = sum(1 for r in recoveries if r.get("success", False))
        recovery_success_rate = (
            successful_recoveries / len(recoveries) if recoveries else 0.0
        )
        avg_recovery_time = (
            sum(r.get("time_ms", 0) for r in recoveries) / len(recoveries)
            if recoveries
            else 0.0
        )

        # Calculate resonance correlation
        resonances = self._resonance_window.get_all()
        tasks = self._task_window.get_all()

        resonance_fitness_correlation = 0.0
        if resonances and tasks:
            # Simple correlation approximation
            avg_resonance = sum(resonances) / len(resonances)
            success_rate = sum(1 for t in tasks if t.get("success", False)) / len(tasks)
            resonance_fitness_correlation = avg_resonance * success_rate

        # Calculate phi alignment rate
        phi_aligned = sum(1 for r in resonances if r >= 0.618)  # PHI_INVERSE
        phi_alignment_rate = phi_aligned / len(resonances) if resonances else 0.0

        # Calculate agent utilization
        total_activations = sum(self._agent_activations.values())
        agent_utilization = {}
        if total_activations > 0:
            for agent, activations in self._agent_activations.items():
                agent_utilization[agent] = activations / total_activations

        # Calculate task metrics
        successful_tasks = sum(1 for t in tasks if t.get("success", False))
        avg_task_duration = (
            sum(t.get("duration_ms", 0) for t in tasks) / len(tasks) if tasks else 0.0
        )

        return CoordinationMetrics(
            measurement_window_seconds=self.window_seconds,
            agreement_rate=agreement_rate,
            contradiction_rate=contradiction_rate,
            consensus_time_ms=avg_task_duration,
            delegation_count=len(delegations),
            delegation_success_rate=delegation_success_rate,
            average_delegation_depth=avg_delegation_depth,
            recovery_attempts=len(recoveries),
            recovery_success_rate=recovery_success_rate,
            average_recovery_time_ms=avg_recovery_time,
            resonance_fitness_correlation=resonance_fitness_correlation,
            phi_alignment_rate=phi_alignment_rate,
            tasks_completed=successful_tasks,
            tasks_failed=len(tasks) - successful_tasks,
            average_task_duration_ms=avg_task_duration,
            agent_utilization=agent_utilization,
        )

    def get_summary(self) -> dict[str, Any]:
        """Get metrics summary.

        Returns:
            Metrics summary dictionary
        """
        metrics = self.get_metrics()

        return {
            "coordination_quality_score": metrics.coordination_quality_score,
            "agreement_rate": metrics.agreement_rate,
            "contradiction_rate": metrics.contradiction_rate,
            "delegation_success_rate": metrics.delegation_success_rate,
            "recovery_success_rate": metrics.recovery_success_rate,
            "resonance_fitness_correlation": (metrics.resonance_fitness_correlation),
            "phi_alignment_rate": metrics.phi_alignment_rate,
            "success_rate": metrics.success_rate,
            "tasks_completed": metrics.tasks_completed,
            "tasks_failed": metrics.tasks_failed,
            "agent_count": len(self._agent_activations),
            "measurement_window_seconds": self.window_seconds,
        }

    # =========================================================================
    # Persistence
    # =========================================================================

    def save_metrics(self) -> None:
        """Save current metrics to history file."""
        if not self.history_file:
            return

        metrics = self.get_metrics()

        with self._lock:
            self._metrics_history.append(metrics)

        # Write to file
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "current": metrics.model_dump(),
                        "summary": self.get_summary(),
                        "history": [
                            m.model_dump() for m in self._metrics_history[-100:]
                        ],
                    },
                    f,
                    indent=2,
                    default=str,
                )
        except (OSError, json.JSONEncodeError):
            pass

    def load_history(self) -> list[CoordinationMetrics]:
        """Load metrics history from file.

        Returns:
            List of historical metrics
        """
        if not self.history_file or not self.history_file.exists():
            return []

        try:
            with open(self.history_file, encoding="utf-8") as f:
                data = json.load(f)

            return [CoordinationMetrics(**m) for m in data.get("history", [])]
        except (OSError, json.JSONDecodeError, KeyError):
            return []


class CoordinationAnalyzer:
    """Analyzes coordination patterns and trends."""

    def __init__(self, collector: CoordinationMetricsCollector):
        """Initialize analyzer.

        Args:
            collector: Metrics collector
        """
        self.collector = collector

    def analyze_trends(self, history: list[CoordinationMetrics]) -> dict[str, Any]:
        """Analyze trends in coordination metrics.

        Args:
            history: Historical metrics

        Returns:
            Trend analysis
        """
        if len(history) < 2:
            return {"trend": "insufficient_data"}

        # Calculate trends
        recent = history[-5:] if len(history) >= 5 else history
        older = history[:-5] if len(history) > 5 else history[:-1]

        def avg(metrics_list: list[CoordinationMetrics], attr: str) -> float:
            values = [getattr(m, attr) for m in metrics_list]
            return sum(values) / len(values) if values else 0.0

        trends = {
            "agreement_rate": {
                "recent": avg(recent, "agreement_rate"),
                "older": avg(older, "agreement_rate"),
                "direction": (
                    "improving"
                    if avg(recent, "agreement_rate") > avg(older, "agreement_rate")
                    else "declining"
                ),
            },
            "coordination_quality": {
                "recent": avg(recent, "coordination_quality_score"),
                "older": avg(older, "coordination_quality_score"),
                "direction": (
                    "improving"
                    if avg(recent, "coordination_quality_score")
                    > avg(older, "coordination_quality_score")
                    else "declining"
                ),
            },
            "success_rate": {
                "recent": avg(recent, "success_rate"),
                "older": avg(older, "success_rate"),
                "direction": (
                    "improving"
                    if avg(recent, "success_rate") > avg(older, "success_rate")
                    else "declining"
                ),
            },
        }

        return {
            "trend": "available",
            "trends": trends,
            "data_points": len(history),
        }

    def identify_bottlenecks(self) -> list[dict[str, Any]]:
        """Identify coordination bottlenecks.

        Returns:
            List of bottlenecks
        """
        bottlenecks = []
        metrics = self.collector.get_metrics()

        # Check for high contradiction rate
        if metrics.contradiction_rate > 0.2:
            bottlenecks.append(
                {
                    "type": "high_contradiction",
                    "value": metrics.contradiction_rate,
                    "threshold": 0.2,
                    "recommendation": (
                        "Review agent output alignment and consensus protocols"
                    ),
                }
            )

        # Check for low delegation success
        if metrics.delegation_count > 0 and metrics.delegation_success_rate < 0.8:
            bottlenecks.append(
                {
                    "type": "low_delegation_success",
                    "value": metrics.delegation_success_rate,
                    "threshold": 0.8,
                    "recommendation": (
                        "Review handoff protocols and agent capabilities"
                    ),
                }
            )

        # Check for low recovery success
        if metrics.recovery_attempts > 0 and metrics.recovery_success_rate < 0.7:
            bottlenecks.append(
                {
                    "type": "low_recovery_success",
                    "value": metrics.recovery_success_rate,
                    "threshold": 0.7,
                    "recommendation": ("Review error handling and fallback mechanisms"),
                }
            )

        # Check for agent utilization imbalance
        if metrics.agent_utilization:
            max_util = max(metrics.agent_utilization.values())
            min_util = min(metrics.agent_utilization.values())
            if max_util > 0 and min_util / max_util < 0.3:
                bottlenecks.append(
                    {
                        "type": "utilization_imbalance",
                        "max_utilization": max_util,
                        "min_utilization": min_util,
                        "ratio": min_util / max_util,
                        "recommendation": (
                            "Review routing policies for better load distribution"
                        ),
                    }
                )

        return bottlenecks

    def generate_report(self) -> dict[str, Any]:
        """Generate comprehensive coordination report.

        Returns:
            Coordination report
        """
        metrics = self.collector.get_metrics()
        bottlenecks = self.identify_bottlenecks()
        history = self.collector.load_history()
        trends = self.analyze_trends(history)

        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "metrics": metrics.model_dump(),
            "summary": self.collector.get_summary(),
            "trends": trends,
            "bottlenecks": bottlenecks,
            "recommendations": self._generate_recommendations(metrics, bottlenecks),
        }

    def _generate_recommendations(
        self,
        metrics: CoordinationMetrics,
        bottlenecks: list[dict[str, Any]],
    ) -> list[str]:
        """Generate recommendations based on metrics.

        Args:
            metrics: Current metrics
            bottlenecks: Identified bottlenecks

        Returns:
            List of recommendations
        """
        recommendations = []

        # Based on coordination quality
        if metrics.coordination_quality_score < 0.7:
            recommendations.append(
                "Coordination quality is below target. Consider reviewing "
                "agent role assignments and routing policies."
            )

        # Based on agreement rate
        if metrics.agreement_rate < 0.8:
            recommendations.append(
                "Agent agreement rate is low. Consider implementing "
                "consensus protocols or adjusting confidence thresholds."
            )

        # Based on phi alignment
        if metrics.phi_alignment_rate < 0.6:
            recommendations.append(
                "Phi alignment rate is below optimal. Consider tuning "
                "resonance thresholds or agent selection criteria."
            )

        # Based on bottlenecks
        for bottleneck in bottlenecks:
            if "recommendation" in bottleneck:
                recommendations.append(bottleneck["recommendation"])

        if not recommendations:
            recommendations.append(
                "Coordination metrics are within acceptable ranges. "
                "Continue monitoring for trends."
            )

        return recommendations


class MetricsExporter:
    """Exports coordination metrics for benchmarking."""

    def __init__(self, output_dir: Path):
        """Initialize exporter.

        Args:
            output_dir: Output directory for exports
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_json(
        self,
        metrics: CoordinationMetrics,
        filename: str = "coordination_metrics.json",
    ) -> Path:
        """Export metrics to JSON file.

        Args:
            metrics: Metrics to export
            filename: Output filename

        Returns:
            Path to exported file
        """
        output_path = self.output_dir / filename

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(metrics.model_dump(), f, indent=2, default=str)

        return output_path

    def export_benchmark_format(
        self,
        metrics: CoordinationMetrics,
        filename: str = "coordination_benchmark.json",
    ) -> Path:
        """Export metrics in benchmark-compatible format.

        Args:
            metrics: Metrics to export
            filename: Output filename

        Returns:
            Path to exported file
        """
        output_path = self.output_dir / filename

        benchmark_data = {
            "benchmark_type": "coordination",
            "timestamp": datetime.now(UTC).isoformat(),
            "metrics": {
                "coordination_quality_score": {
                    "value": metrics.coordination_quality_score,
                    "target": 0.8,
                    "passed": metrics.coordination_quality_score >= 0.8,
                },
                "agreement_rate": {
                    "value": metrics.agreement_rate,
                    "target": 0.85,
                    "passed": metrics.agreement_rate >= 0.85,
                },
                "delegation_success_rate": {
                    "value": metrics.delegation_success_rate,
                    "target": 0.9,
                    "passed": metrics.delegation_success_rate >= 0.9,
                },
                "recovery_success_rate": {
                    "value": metrics.recovery_success_rate,
                    "target": 0.8,
                    "passed": metrics.recovery_success_rate >= 0.8,
                },
                "phi_alignment_rate": {
                    "value": metrics.phi_alignment_rate,
                    "target": 0.618,
                    "passed": metrics.phi_alignment_rate >= 0.618,
                },
                "success_rate": {
                    "value": metrics.success_rate,
                    "target": 0.95,
                    "passed": metrics.success_rate >= 0.95,
                },
            },
            "summary": {
                "total_metrics": 6,
                "passed_metrics": sum(
                    1
                    for m in [
                        metrics.coordination_quality_score >= 0.8,
                        metrics.agreement_rate >= 0.85,
                        metrics.delegation_success_rate >= 0.9,
                        metrics.recovery_success_rate >= 0.8,
                        metrics.phi_alignment_rate >= 0.618,
                        metrics.success_rate >= 0.95,
                    ]
                    if m
                ),
                "overall_passed": (
                    metrics.coordination_quality_score >= 0.8
                    and metrics.success_rate >= 0.95
                ),
            },
            "raw_metrics": metrics.model_dump(),
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(benchmark_data, f, indent=2, default=str)

        return output_path

    def export_trace(
        self,
        trace: CoordinationTrace,
        filename: str | None = None,
    ) -> Path:
        """Export coordination trace.

        Args:
            trace: Trace to export
            filename: Output filename (auto-generated if None)

        Returns:
            Path to exported file
        """
        if filename is None:
            filename = f"trace_{trace.trace_id}.json"

        output_path = self.output_dir / filename

        trace_data = {
            "trace_id": str(trace.trace_id),
            "session_id": str(trace.session_id),
            "started_at": (trace.started_at.isoformat() if trace.started_at else None),
            "completed_at": (
                trace.completed_at.isoformat() if trace.completed_at else None
            ),
            "final_status": (trace.final_status.value if trace.final_status else None),
            "final_confidence": trace.final_confidence,
            "total_duration_ms": trace.total_duration_ms,
            "decisions": [
                {
                    "decision_id": str(d.decision_id),
                    "task_id": str(d.task_id),
                    "primary_agent": d.primary_agent.value,
                    "backup_agents": [a.value for a in d.backup_agents],
                    "layer": d.layer.value,
                    "decision_confidence": d.decision_confidence,
                }
                for d in trace.decisions
            ],
            "contracts": [
                {
                    "contract_id": str(c.contract_id),
                    "task_type": c.input.task_type,
                    "objective": c.input.objective,
                    "output_status": (c.output.status.value if c.output else None),
                    "output_confidence": (c.output.confidence if c.output else None),
                }
                for c in trace.contracts
            ],
            "metrics": trace.metrics.model_dump() if trace.metrics else None,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(trace_data, f, indent=2, default=str)

        return output_path
