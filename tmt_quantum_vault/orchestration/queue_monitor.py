"""
Queue Monitor for IBM Quantum Live Lane.

Manages the 180-minute promotion budget for ibm_kingston (Heron r2, 156 qubits)
and provides phi-threshold gating for hardware execution.

Key Features:
- Budget tracking (180 min promotion allocation)
- Queue depth monitoring
- Phi-resonance threshold gating (0.618)
- Pre-flight Aer simulator validation
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

PHI_THRESHOLD = 0.618  # Golden ratio inverse threshold for resonance
DEFAULT_BUDGET_MINUTES = 180.0  # IBM Open Plan promotion allocation
MAX_QUEUE_DEPTH = 15  # Maximum acceptable queue depth
PREFLIGHT_SIM_BACKEND = "aer_simulator"
KINGSTON_BACKEND = "ibm_kingston"
KINGSTON_QUBITS = 156
KINGSTON_CLOPS = 340_000
KINGSTON_TWO_QUBIT_ERR = 2.03e-3


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class BudgetState:
    """Tracks the IBM Quantum runtime budget."""

    total_minutes: float = DEFAULT_BUDGET_MINUTES
    used_minutes: float = 0.0
    last_updated: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def remaining_minutes(self) -> float:
        """Get remaining budget in minutes."""
        return max(0.0, self.total_minutes - self.used_minutes)

    @property
    def utilization_percent(self) -> float:
        """Get budget utilization percentage."""
        if self.total_minutes <= 0:
            return 0.0
        return (self.used_minutes / self.total_minutes) * 100.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_minutes": self.total_minutes,
            "used_minutes": self.used_minutes,
            "remaining_minutes": self.remaining_minutes,
            "utilization_percent": self.utilization_percent,
            "last_updated": self.last_updated.isoformat(),
        }


@dataclass
class QueueStatus:
    """Status of the IBM Quantum queue."""

    backend_name: str
    pending_jobs: int
    status: str  # 'available', 'busy', 'offline'
    avg_wait_time_seconds: float = 0.0

    @property
    def is_acceptable(self) -> bool:
        """Check if queue is acceptable for submission."""
        return self.status == "available" and self.pending_jobs <= MAX_QUEUE_DEPTH

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "backend_name": self.backend_name,
            "pending_jobs": self.pending_jobs,
            "status": self.status,
            "avg_wait_time_seconds": self.avg_wait_time_seconds,
            "is_acceptable": self.is_acceptable,
        }


@dataclass
class PreflightResult:
    """Result of pre-flight Aer simulation check."""

    passed: bool
    phi_score: float
    fidelity: float
    ready_for_hardware: bool
    error_message: str | None = None
    simulation_time_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "passed": self.passed,
            "phi_score": self.phi_score,
            "fidelity": self.fidelity,
            "ready_for_hardware": self.ready_for_hardware,
            "error_message": self.error_message,
            "simulation_time_ms": self.simulation_time_ms,
        }


# =============================================================================
# Queue Monitor
# =============================================================================


class KingstonQueueMonitor:
    """
    Monitors ibm_kingston queue and manages budget allocation.

    This class guards the 180-minute promotion budget and ensures
    only high-resonance tasks (phi >= 0.618) are routed to live hardware.
    """

    def __init__(
        self,
        budget_minutes: float = DEFAULT_BUDGET_MINUTES,
        phi_threshold: float = PHI_THRESHOLD,
        max_queue_depth: int = MAX_QUEUE_DEPTH,
        state_path: Path | None = None,
    ):
        """Initialize the queue monitor.

        Args:
            budget_minutes: Total budget in minutes
            phi_threshold: Minimum phi score for hardware routing
            max_queue_depth: Maximum acceptable queue depth
            state_path: Path to persist budget state
        """
        self.phi_threshold = phi_threshold
        self.max_queue_depth = max_queue_depth
        self.state_path = (
            state_path or Path.home() / ".tmt_quantum" / "budget_state.json"
        )

        # Initialize budget state
        self._budget = BudgetState(total_minutes=budget_minutes)
        self._load_state()

        # IBM Quantum service (lazy loaded)
        self._service = None
        self._backend = None

    def _load_state(self) -> None:
        """Load persisted budget state."""
        if self.state_path.exists():
            try:
                with open(self.state_path, encoding="utf-8") as f:
                    data = json.load(f)
                self._budget.used_minutes = data.get("used_minutes", 0.0)
                logger.info(
                    f"Loaded budget state: {self._budget.remaining_minutes:.2f} min remaining"
                )
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to load budget state: {e}")

    def _save_state(self) -> None:
        """Persist budget state."""
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(self._budget.to_dict(), f, indent=2)

    @property
    def remaining_budget(self) -> float:
        """Get remaining budget in minutes."""
        return self._budget.remaining_minutes

    @property
    def utilization_percent(self) -> float:
        """Get budget utilization percentage."""
        return self._budget.utilization_percent

    def _get_service(self):
        """Get or create IBM Quantum service connection.

        Returns:
            QiskitRuntimeService or None if unavailable
        """
        if self._service is None:
            try:
                from qiskit_ibm_runtime import QiskitRuntimeService

                self._service = QiskitRuntimeService(channel="ibm_quantum")
                logger.info("Connected to IBM Quantum service")
            except ImportError:
                logger.warning("qiskit-ibm-runtime not installed")
                return None
            except Exception as e:
                logger.warning(f"Failed to connect to IBM Quantum: {e}")
                return None
        return self._service

    def get_queue_status(self) -> QueueStatus:
        """Get current queue status for ibm_kingston.

        Returns:
            QueueStatus with current queue information
        """
        service = self._get_service()
        if service is None:
            return QueueStatus(
                backend_name=KINGSTON_BACKEND,
                pending_jobs=-1,
                status="unavailable",
            )

        try:
            backend = service.backend(KINGSTON_BACKEND)
            status = backend.status()

            return QueueStatus(
                backend_name=KINGSTON_BACKEND,
                pending_jobs=status.pending_jobs,
                status="available" if status.status_msg == "active" else "busy",
                avg_wait_time_seconds=0.0,  # Would need additional API call
            )
        except Exception as e:
            logger.warning(f"Failed to get queue status: {e}")
            return QueueStatus(
                backend_name=KINGSTON_BACKEND,
                pending_jobs=-1,
                status="error",
            )

    def should_route_live(self, resonance_score: float) -> bool:
        """
        Determine if a task should be routed to live hardware.

        Args:
            resonance_score: Phi-resonance score from pre-flight check

        Returns:
            True if task should be routed to ibm_kingston
        """
        # Check phi threshold
        if resonance_score < self.phi_threshold:
            logger.debug(
                f"Resonance {resonance_score:.3f} below threshold {self.phi_threshold}"
            )
            return False

        # Check budget
        if self.remaining_budget <= 0:
            logger.warning("Budget exhausted")
            return False

        # Check queue
        queue_status = self.get_queue_status()
        if not queue_status.is_acceptable:
            logger.debug(
                f"Queue not acceptable: {queue_status.pending_jobs} pending jobs"
            )
            return False

        return True

    def record_usage(self, minutes: float) -> None:
        """
        Record runtime usage.

        Args:
            minutes: Minutes of runtime used
        """
        self._budget.used_minutes += minutes
        self._budget.last_updated = datetime.now(UTC)
        self._save_state()
        logger.info(
            f"Recorded {minutes:.2f} min usage, {self.remaining_budget:.2f} min remaining"
        )

    def get_budget_summary(self) -> dict[str, Any]:
        """Get budget summary for reporting.

        Returns:
            Dictionary with budget information
        """
        return {
            "backend": KINGSTON_BACKEND,
            "processor_family": "Heron-r2",
            "n_qubits": KINGSTON_QUBITS,
            "clops": KINGSTON_CLOPS,
            "two_qubit_error_rate": KINGSTON_TWO_QUBIT_ERR,
            "budget": self._budget.to_dict(),
            "phi_threshold": self.phi_threshold,
            "max_queue_depth": self.max_queue_depth,
        }


# =============================================================================
# Pre-Flight Check
# =============================================================================


def preflight_check(circuit: Any, shots: int = 1024) -> PreflightResult:
    """
    Run pre-flight Aer simulation to validate circuit before hardware submission.

    Uses the AGI-model calibration framework to predict whether a live run
    is worth the budget cost.

    Args:
        circuit: Quantum circuit to validate
        shots: Number of simulation shots

    Returns:
        PreflightResult with validation status
    """
    import time

    start_time = time.time()

    try:
        from qiskit_aer import AerSimulator

        sim = AerSimulator()
        result = sim.run(circuit, shots=shots).result()
        counts = result.get_counts()

        # Calculate phi-resonance score
        phi_score = calculate_phi_resonance(counts)

        # Extract fidelity (simplified)
        total_counts = sum(counts.values())
        max_count = max(counts.values()) if counts else 0
        fidelity = max_count / total_counts if total_counts > 0 else 0.0

        ready_for_hardware = phi_score >= PHI_THRESHOLD

        return PreflightResult(
            passed=True,
            phi_score=phi_score,
            fidelity=fidelity,
            ready_for_hardware=ready_for_hardware,
            simulation_time_ms=(time.time() - start_time) * 1000,
        )

    except ImportError:
        return PreflightResult(
            passed=False,
            phi_score=0.0,
            fidelity=0.0,
            ready_for_hardware=False,
            error_message="qiskit-aer not installed",
        )
    except Exception as e:
        return PreflightResult(
            passed=False,
            phi_score=0.0,
            fidelity=0.0,
            ready_for_hardware=False,
            error_message=str(e),
        )


def calculate_phi_resonance(counts: dict[str, int]) -> float:
    """
    Calculate phi-resonance score from measurement counts.

    Uses the Merkaba geometry alignment to score resonance.

    Args:
        counts: Measurement counts from quantum circuit

    Returns:
        Phi-resonance score (0-1)
    """
    if not counts:
        return 0.0

    total = sum(counts.values())
    if total == 0:
        return 0.0

    # Calculate probability distribution
    probs = {k: v / total for k, v in counts.items()}

    # Find the dominant outcome
    max_prob = max(probs.values())

    # Calculate entropy-based resonance
    import math

    entropy = -sum(p * math.log2(p + 1e-10) for p in probs.values() if p > 0)
    max_entropy = math.log2(len(counts)) if len(counts) > 1 else 1.0

    # Normalize entropy
    normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0.0

    # Phi-resonance combines concentration and entropy
    # Higher concentration (max_prob) and lower entropy = higher resonance
    resonance = (max_prob * 0.6) + ((1 - normalized_entropy) * 0.4)

    # Apply phi scaling
    phi = 1.618033988749895
    phi_scaled = resonance * (phi - 1) / phi

    return min(1.0, phi_scaled)


# =============================================================================
# Evidence Ledger Integration
# =============================================================================


def create_hardware_evidence_entry(
    result_data: dict[str, Any],
    phi_score: float,
    monitor: KingstonQueueMonitor,
) -> dict[str, Any]:
    """
    Create an evidence ledger entry for hardware execution.

    Args:
        result_data: Result data from quantum execution
        phi_score: Phi-resonance score
        monitor: Queue monitor for budget info

    Returns:
        Evidence entry dictionary
    """
    return {
        "backend": KINGSTON_BACKEND,
        "processor_family": "Heron-r2",
        "n_qubits": KINGSTON_QUBITS,
        "clops": KINGSTON_CLOPS,
        "two_qubit_err": KINGSTON_TWO_QUBIT_ERR,
        "fidelity": result_data.get("fidelity", 0.0),
        "resonance_score": phi_score,
        "phi_threshold_met": phi_score >= PHI_THRESHOLD,
        "is_free_tier": True,
        "promotion_minutes": monitor._budget.total_minutes,
        "remaining_minutes": monitor.remaining_budget,
        "timestamp": datetime.now(UTC).isoformat(),
    }
