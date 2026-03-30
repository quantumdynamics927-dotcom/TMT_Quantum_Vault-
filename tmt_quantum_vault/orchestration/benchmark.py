"""
Benchmark Integration for Orchestration.

This module integrates orchestration metrics with the existing
benchmark framework, enabling coordination quality benchmarking.

Key Components:
- OrchestrationBenchmark: Benchmark runner for coordination
- BenchmarkIntegration: Integration with existing benchmark system
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .metrics import CoordinationAnalyzer, CoordinationMetricsCollector, MetricsExporter
from .models import (
    CoordinationMetrics,
    HandoffStatus,
    RoutingPolicy,
)
from .orchestrator import AgentOrchestrator


class OrchestrationBenchmark:
    """Benchmark runner for orchestration coordination."""

    def __init__(
        self,
        orchestrator: AgentOrchestrator,
        output_dir: Path | None = None,
    ):
        """Initialize orchestration benchmark.

        Args:
            orchestrator: Agent orchestrator
            output_dir: Output directory for results
        """
        self.orchestrator = orchestrator
        self.output_dir = output_dir or Path("benchmark_results")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.collector = CoordinationMetricsCollector(
            window_seconds=300.0,
            history_file=self.output_dir / "coordination_history.json",
        )
        self.analyzer = CoordinationAnalyzer(self.collector)
        self.exporter = MetricsExporter(self.output_dir)

    def run_benchmark(
        self,
        task_types: list[str] | None = None,
        iterations: int = 10,
        parallel_tasks: bool = False,
    ) -> dict[str, Any]:
        """Run orchestration benchmark.

        Args:
            task_types: Task types to benchmark
            iterations: Number of iterations per task type
            parallel_tasks: Whether to run tasks in parallel

        Returns:
            Benchmark results
        """
        task_types = task_types or [
            "validation",
            "synthesis",
            "analysis",
            "coordination",
            "monitoring",
        ]

        benchmark_id = uuid4()
        start_time = time.time()

        results = {
            "benchmark_id": str(benchmark_id),
            "started_at": datetime.now(UTC).isoformat(),
            "configuration": {
                "task_types": task_types,
                "iterations": iterations,
                "parallel_tasks": parallel_tasks,
            },
            "task_results": {},
            "traces": [],
        }

        # Run benchmark for each task type
        for task_type in task_types:
            task_results = self._benchmark_task_type(
                task_type=task_type,
                iterations=iterations,
            )
            results["task_results"][task_type] = task_results

            # Collect traces
            for trace in task_results.get("traces", []):
                results["traces"].append(trace)

        # Calculate aggregate metrics
        end_time = time.time()
        metrics = self.collector.get_metrics()

        results["completed_at"] = datetime.now(UTC).isoformat()
        results["duration_seconds"] = end_time - start_time
        results["metrics"] = metrics.model_dump(mode="json")
        results["summary"] = self._create_summary(metrics, results)

        # Export results
        self._export_results(results)

        return results

    def _benchmark_task_type(
        self,
        task_type: str,
        iterations: int,
    ) -> dict[str, Any]:
        """Benchmark a single task type.

        Args:
            task_type: Task type to benchmark
            iterations: Number of iterations

        Returns:
            Task type results
        """
        results = {
            "task_type": task_type,
            "iterations": iterations,
            "successful": 0,
            "failed": 0,
            "traces": [],
            "latencies_ms": [],
            "confidences": [],
        }

        for i in range(iterations):
            try:
                # Execute task
                trace = self.orchestrator.execute(
                    task_type=task_type,
                    objective=f"Benchmark {task_type} iteration {i+1}",
                    context={"benchmark": True, "iteration": i + 1},
                )

                # Record results
                results["traces"].append(
                    {
                        "trace_id": str(trace.trace_id),
                        "status": (
                            trace.final_status.value
                            if trace.final_status
                            else "unknown"
                        ),
                        "confidence": trace.final_confidence,
                        "duration_ms": trace.total_duration_ms,
                    }
                )

                # Update collector
                self.collector.record_trace(trace)

                # Update counters
                if trace.final_status == HandoffStatus.COMPLETED:
                    results["successful"] += 1
                else:
                    results["failed"] += 1

                results["latencies_ms"].append(trace.total_duration_ms)
                results["confidences"].append(trace.final_confidence)

            except Exception as e:
                results["failed"] += 1
                results["traces"].append(
                    {
                        "trace_id": None,
                        "status": "error",
                        "error": str(e),
                    }
                )

        # Calculate statistics
        if results["latencies_ms"]:
            results["avg_latency_ms"] = sum(results["latencies_ms"]) / len(
                results["latencies_ms"]
            )
            results["min_latency_ms"] = min(results["latencies_ms"])
            results["max_latency_ms"] = max(results["latencies_ms"])

        if results["confidences"]:
            results["avg_confidence"] = sum(results["confidences"]) / len(
                results["confidences"]
            )

        results["success_rate"] = (
            results["successful"] / iterations if iterations > 0 else 0.0
        )

        return results

    def _create_summary(
        self,
        metrics: CoordinationMetrics,
        results: dict[str, Any],
    ) -> dict[str, Any]:
        """Create benchmark summary.

        Args:
            metrics: Coordination metrics
            results: Full results

        Returns:
            Summary dictionary
        """
        # Calculate overall success rate
        total_successful = sum(
            r.get("successful", 0) for r in results.get("task_results", {}).values()
        )
        total_failed = sum(
            r.get("failed", 0) for r in results.get("task_results", {}).values()
        )
        total_tasks = total_successful + total_failed

        # Determine pass/fail
        passed = (
            metrics.coordination_quality_score >= 0.8
            and metrics.success_rate >= 0.95
            and metrics.agreement_rate >= 0.85
        )

        return {
            "passed": passed,
            "coordination_quality_score": metrics.coordination_quality_score,
            "success_rate": metrics.success_rate,
            "agreement_rate": metrics.agreement_rate,
            "total_tasks": total_tasks,
            "successful_tasks": total_successful,
            "failed_tasks": total_failed,
            "overall_success_rate": (
                total_successful / total_tasks if total_tasks > 0 else 0.0
            ),
            "recommendations": self.analyzer._generate_recommendations(
                metrics,
                self.analyzer.identify_bottlenecks(),
            ),
        }

    def _export_results(self, results: dict[str, Any]) -> None:
        """Export benchmark results.

        Args:
            results: Results to export
        """
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")

        # Export full results
        results_path = self.output_dir / f"orchestration_benchmark_{timestamp}.json"
        with open(results_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, default=str)

        # Export metrics in benchmark format
        metrics = CoordinationMetrics(**results.get("metrics", {}))
        self.exporter.export_benchmark_format(
            metrics,
            filename=f"coordination_benchmark_{timestamp}.json",
        )

        # Save collector history
        self.collector.save_metrics()


class BenchmarkIntegration:
    """Integration with existing benchmark system."""

    def __init__(
        self,
        vault_path: Path,
        benchmark_output_dir: Path | None = None,
    ):
        """Initialize benchmark integration.

        Args:
            vault_path: Path to TMT Quantum Vault
            benchmark_output_dir: Output directory for benchmarks
        """
        self.vault_path = Path(vault_path)
        self.benchmark_output_dir = (
            benchmark_output_dir or self.vault_path / "benchmark_results"
        )

        # Create orchestrator with default policy
        self.policy = RoutingPolicy(
            policy_name="benchmark_default",
            confidence_threshold=0.7,
            resonance_threshold=0.618,
            escalation_threshold=0.5,
        )

        self.orchestrator = AgentOrchestrator(
            vault_path=self.vault_path,
            policy=self.policy,
        )

        self.benchmark = OrchestrationBenchmark(
            orchestrator=self.orchestrator,
            output_dir=self.benchmark_output_dir,
        )

    def run_full_benchmark(
        self,
        iterations_per_task: int = 10,
    ) -> dict[str, Any]:
        """Run full orchestration benchmark suite.

        Args:
            iterations_per_task: Iterations per task type

        Returns:
            Full benchmark results
        """
        return self.benchmark.run_benchmark(
            iterations=iterations_per_task,
        )

    def run_targeted_benchmark(
        self,
        task_types: list[str],
        iterations: int = 5,
    ) -> dict[str, Any]:
        """Run targeted benchmark for specific task types.

        Args:
            task_types: Task types to benchmark
            iterations: Iterations per task type

        Returns:
            Targeted benchmark results
        """
        return self.benchmark.run_benchmark(
            task_types=task_types,
            iterations=iterations,
        )

    def get_orchestrator_status(self) -> dict[str, Any]:
        """Get orchestrator status.

        Returns:
            Orchestrator status
        """
        return self.orchestrator.get_status()

    def get_agent_profiles(self) -> list[dict[str, Any]]:
        """Get all agent profiles.

        Returns:
            List of agent profiles
        """
        return self.orchestrator.get_agent_profiles()

    def generate_coordination_report(self) -> dict[str, Any]:
        """Generate coordination analysis report.

        Returns:
            Coordination report
        """
        return self.benchmark.analyzer.generate_report()


def run_orchestration_benchmark(
    vault_path: Path,
    output_dir: Path | None = None,
    iterations: int = 10,
) -> dict[str, Any]:
    """Convenience function to run orchestration benchmark.

    Args:
        vault_path: Path to TMT Quantum Vault
        output_dir: Output directory
        iterations: Iterations per task type

    Returns:
        Benchmark results
    """
    integration = BenchmarkIntegration(
        vault_path=vault_path,
        benchmark_output_dir=output_dir,
    )

    return integration.run_full_benchmark(iterations_per_task=iterations)
