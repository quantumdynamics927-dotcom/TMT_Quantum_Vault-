"""
Orchestration Models for TMT Quantum Vault Agent Coordination.

This module defines formal contracts, schemas, and message types for
ensemble agent orchestration, enabling traceable multi-agent coordination.

Key Components:
- AgentContract: Input/output schema for agent invocations
- AgentMessage: Inter-agent communication protocol
- RoutingDecision: Context-aware agent selection
- CoordinationMetrics: Measurable coordination quality indicators
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

# =============================================================================
# Helper Functions
# =============================================================================


def utcnow() -> datetime:
    """Return timezone-aware UTC datetime."""
    return datetime.now(UTC)


# =============================================================================
# Constants
# =============================================================================

PHI = 1.618033988749895
PHI_INVERSE = 1.0 / PHI  # ≈ 0.618

# Coordination thresholds
DEFAULT_CONFIDENCE_THRESHOLD = 0.7
DEFAULT_RESONANCE_THRESHOLD = 0.618
DEFAULT_ESCALATION_THRESHOLD = 0.5


# =============================================================================
# Enums
# =============================================================================


class AgentLayer(StrEnum):
    """Hierarchical layer assignment for agents."""

    INPUT = "input"
    PROCESSING = "processing"
    INTEGRATION = "integration"
    OUTPUT = "output"


class AgentRole(StrEnum):
    """Functional role classification for routing decisions."""

    SYNTHESIZER = "synthesizer"
    OBSERVER = "observer"
    VALIDATOR = "validator"
    STRATEGIC = "strategic"
    HARMONIC = "harmonic"
    FEDERATION = "federation"
    WORKFLOW = "workflow"
    ARCHIVIST = "archivist"
    AUDITOR = "auditor"
    BRONZE = "bronze"
    BITNET = "bitnet"
    WORMHOLE = "wormhole"
    MIRROR = "mirror"
    BIO = "bio"
    FRACTAL = "fractal"
    VISUAL = "visual"
    STEALTH = "stealth"


class MessagePriority(StrEnum):
    """Priority levels for inter-agent messages."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class HandoffStatus(StrEnum):
    """Status of agent handoff operations."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    COMPLETED = "completed"
    ESCALATED = "escalated"
    FAILED = "failed"


class ConflictResolutionStrategy(StrEnum):
    """Strategies for resolving agent output conflicts."""

    WEIGHTED_VOTE = "weighted_vote"
    HIGHEST_CONFIDENCE = "highest_confidence"
    HIGHEST_FITNESS = "highest_fitness"
    CONSENSUS = "consensus"
    ARBITRATOR = "arbitrator"
    PHI_ALIGNMENT = "phi_alignment"


class EscalationReason(StrEnum):
    """Reasons for escalating decisions up the coordination hierarchy."""

    LOW_CONFIDENCE = "low_confidence"
    CONFLICT = "conflict"
    TIMEOUT = "timeout"
    ERROR = "error"
    POLICY_VIOLATION = "policy_violation"
    STAKEHOLDER_REQUEST = "stakeholder_request"


# =============================================================================
# Agent Contract Schema
# =============================================================================


class AgentInputSchema(BaseModel):
    """Input schema for agent invocation."""

    model_config = ConfigDict(extra="forbid")

    task_id: UUID = Field(default_factory=uuid4)
    task_type: str = Field(..., min_length=1)
    objective: str = Field(..., min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)
    constraints: dict[str, Any] = Field(default_factory=dict)
    priority: MessagePriority = Field(default=MessagePriority.NORMAL)
    timeout_seconds: float = Field(default=30.0, ge=1.0, le=3600.0)

    # Routing hints
    preferred_agents: list[AgentRole] = Field(default_factory=list)
    excluded_agents: list[AgentRole] = Field(default_factory=list)
    required_capabilities: list[str] = Field(default_factory=list)


class AgentOutputSchema(BaseModel):
    """Output schema for agent results."""

    model_config = ConfigDict(extra="allow")

    task_id: UUID
    agent_id: int
    agent_name: str
    agent_role: AgentRole

    # Core output
    result: Any = None
    summary: str = Field(..., min_length=1)

    # Quality metrics
    confidence: float = Field(..., ge=0.0, le=1.0)
    resonance_score: float = Field(..., ge=0.0, le=1.0)
    fitness_contribution: float = Field(default=0.0, ge=0.0, le=1.0)

    # Status
    status: HandoffStatus
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    # Metadata
    processing_time_ms: float = Field(default=0.0, ge=0.0)
    timestamp: datetime = Field(default_factory=utcnow)

    # Hardware provenance (for quantum execution)
    evidence: dict[str, Any] | None = None

    # Handoff
    handoff: HandoffDirective | None = None


class HandoffDirective(BaseModel):
    """Directive for handing off to next agent in pipeline."""

    model_config = ConfigDict(extra="forbid")

    target_agent: AgentRole
    reason: str = Field(..., min_length=1)
    context_to_preserve: list[str] = Field(default_factory=list)
    modifications: dict[str, Any] = Field(default_factory=dict)
    urgency: MessagePriority = Field(default=MessagePriority.NORMAL)


class AgentContract(BaseModel):
    """Complete contract for agent invocation and response."""

    model_config = ConfigDict(extra="forbid")

    contract_id: UUID = Field(default_factory=uuid4)
    version: str = Field(default="1.0.0")

    # Input/Output
    input: AgentInputSchema
    output: AgentOutputSchema | None = None

    # Contract lifecycle
    created_at: datetime = Field(default_factory=utcnow)
    completed_at: datetime | None = None

    # Trace
    trace_id: UUID = Field(default_factory=uuid4)
    parent_contract_id: UUID | None = None

    @property
    def is_complete(self) -> bool:
        return self.output is not None and self.completed_at is not None

    @property
    def duration_ms(self) -> float:
        if self.completed_at and self.created_at:
            return (self.completed_at - self.created_at).total_seconds() * 1000
        return 0.0


# =============================================================================
# Inter-Agent Messaging
# =============================================================================


class AgentMessage(BaseModel):
    """Message for inter-agent communication."""

    model_config = ConfigDict(extra="forbid")

    message_id: UUID = Field(default_factory=uuid4)

    # Routing
    sender_agent: AgentRole
    sender_id: int
    recipient_agent: AgentRole | None = None  # None = broadcast
    recipient_id: int | None = None

    # Content
    message_type: Literal[
        "request",
        "response",
        "notification",
        "query",
        "broadcast",
        "escalation",
        "delegation",
    ]
    payload: dict[str, Any] = Field(default_factory=dict)

    # Metadata
    priority: MessagePriority = Field(default=MessagePriority.NORMAL)
    requires_response: bool = Field(default=False)
    response_deadline: datetime | None = None
    correlation_id: UUID | None = None  # For request-response matching

    # Trace
    trace_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=utcnow)
    ttl_seconds: float = Field(default=300.0, ge=1.0)


class AgentChannelStats(BaseModel):
    """Statistics for an agent communication channel."""

    agent_id: int
    agent_name: str

    # Message counts
    messages_sent: int = 0
    messages_received: int = 0
    messages_pending: int = 0

    # Timing
    average_response_time_ms: float = 0.0
    total_processing_time_ms: float = 0.0

    # Quality
    success_rate: float = 0.0
    error_rate: float = 0.0
    average_confidence: float = 0.0
    average_resonance: float = 0.0


# =============================================================================
# Routing and Decision
# =============================================================================


class RoutingDecision(BaseModel):
    """Decision about which agent(s) should handle a task."""

    model_config = ConfigDict(extra="forbid")

    decision_id: UUID = Field(default_factory=uuid4)
    task_id: UUID

    # Selected agents
    primary_agent: AgentRole
    primary_reason: str
    backup_agents: list[AgentRole] = Field(default_factory=list)

    # Routing factors
    routing_factors: dict[str, float] = Field(default_factory=dict)
    # Examples: {"fitness": 0.85, "role_match": 0.9, "load_balance": 0.7}

    # Context
    layer: AgentLayer
    estimated_complexity: float = Field(default=0.5, ge=0.0, le=1.0)
    parallel_execution: bool = Field(default=False)

    # Confidence
    decision_confidence: float = Field(..., ge=0.0, le=1.0)
    alternative_routes_considered: int = Field(default=0)

    # Timestamps
    timestamp: datetime = Field(default_factory=utcnow)


class RoutingPolicy(BaseModel):
    """Policy for routing decisions."""

    model_config = ConfigDict(extra="forbid")

    policy_name: str
    version: str = Field(default="1.0.0")

    # Role-based routing
    role_routing: dict[str, list[AgentRole]] = Field(default_factory=dict)
    # Example: {"validation": [AgentRole.VALIDATOR, AgentRole.AUDITOR]}

    # Layer progression
    layer_sequence: list[AgentLayer] = Field(
        default=[
            AgentLayer.INPUT,
            AgentLayer.PROCESSING,
            AgentLayer.INTEGRATION,
            AgentLayer.OUTPUT,
        ]
    )

    # Thresholds
    confidence_threshold: float = Field(default=DEFAULT_CONFIDENCE_THRESHOLD)
    resonance_threshold: float = Field(default=DEFAULT_RESONANCE_THRESHOLD)
    escalation_threshold: float = Field(default=DEFAULT_ESCALATION_THRESHOLD)

    # Conflict resolution
    default_conflict_strategy: ConflictResolutionStrategy = Field(
        default=ConflictResolutionStrategy.WEIGHTED_VOTE
    )

    # Load balancing
    max_concurrent_tasks_per_agent: int = Field(default=5)
    agent_weight_by_fitness: bool = Field(default=True)

    # Ablation support - components to disable
    disabled_components: list[str] = Field(default_factory=list)
    # Example: ["synthesizer", "validator", "integration", "consensus"]


# =============================================================================
# Coordination Metrics
# =============================================================================


class CoordinationMetrics(BaseModel):
    """Measurable coordination quality indicators."""

    model_config = ConfigDict(extra="allow")

    # Session identification
    session_id: UUID = Field(default_factory=uuid4)
    measurement_window_seconds: float = Field(default=60.0)

    # Agreement metrics
    agreement_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    # Percentage of agent outputs that agree within tolerance

    contradiction_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    # Percentage of agent outputs that contradict each other

    consensus_time_ms: float = Field(default=0.0, ge=0.0)
    # Average time to reach consensus

    # Delegation metrics
    delegation_count: int = 0
    delegation_success_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    average_delegation_depth: float = Field(default=0.0, ge=0.0)

    # Recovery metrics
    recovery_attempts: int = 0
    recovery_success_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    average_recovery_time_ms: float = Field(default=0.0, ge=0.0)

    # Resonance correlation
    resonance_fitness_correlation: float = Field(default=0.0, ge=-1.0, le=1.0)
    # Correlation between resonance scores and fitness outcomes

    phi_alignment_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    # Percentage of decisions aligned with phi threshold

    # Throughput
    tasks_completed: int = 0
    tasks_failed: int = 0
    average_task_duration_ms: float = Field(default=0.0, ge=0.0)

    # Agent utilization
    agent_utilization: dict[str, float] = Field(default_factory=dict)
    # Agent name -> utilization percentage

    # Timestamps
    measured_at: datetime = Field(default_factory=utcnow)

    @property
    def success_rate(self) -> float:
        total = self.tasks_completed + self.tasks_failed
        if total == 0:
            return 0.0
        return self.tasks_completed / total

    @property
    def coordination_quality_score(self) -> float:
        """Composite score for coordination quality (0-1)."""
        weights = {
            "agreement": 0.25,
            "delegation_success": 0.15,
            "recovery_success": 0.15,
            "resonance_correlation": 0.20,
            "phi_alignment": 0.15,
            "success_rate": 0.10,
        }

        return (
            weights["agreement"] * self.agreement_rate
            + weights["delegation_success"] * self.delegation_success_rate
            + weights["recovery_success"] * self.recovery_success_rate
            + weights["resonance_correlation"]
            * max(0, self.resonance_fitness_correlation)
            + weights["phi_alignment"] * self.phi_alignment_rate
            + weights["success_rate"] * self.success_rate
        )


class CoordinationTrace(BaseModel):
    """Traceable decision path for multi-agent runs."""

    model_config = ConfigDict(extra="allow")

    trace_id: UUID = Field(default_factory=uuid4)
    session_id: UUID

    # Decision sequence
    decisions: list[RoutingDecision] = Field(default_factory=list)
    messages: list[AgentMessage] = Field(default_factory=list)
    contracts: list[AgentContract] = Field(default_factory=list)

    # Outcome
    final_status: HandoffStatus | None = None
    final_confidence: float = Field(default=0.0)
    total_duration_ms: float = Field(default=0.0)

    # Metrics snapshot
    metrics: CoordinationMetrics | None = None

    # Timestamps
    started_at: datetime = Field(default_factory=utcnow)
    completed_at: datetime | None = None

    def add_decision(self, decision: RoutingDecision) -> None:
        self.decisions.append(decision)

    def add_message(self, message: AgentMessage) -> None:
        self.messages.append(message)

    def add_contract(self, contract: AgentContract) -> None:
        self.contracts.append(contract)

    def finalize(self, status: HandoffStatus, confidence: float) -> None:
        self.final_status = status
        self.final_confidence = confidence
        self.completed_at = datetime.now(UTC)
        if self.started_at:
            self.total_duration_ms = (
                self.completed_at - self.started_at
            ).total_seconds() * 1000


# =============================================================================
# Conflict Resolution
# =============================================================================


class AgentConflict(BaseModel):
    """Represents a conflict between agent outputs."""

    model_config = ConfigDict(extra="forbid")

    conflict_id: UUID = Field(default_factory=uuid4)
    trace_id: UUID

    # Conflicting agents
    agent_outputs: list[AgentOutputSchema] = Field(..., min_length=2)

    # Conflict details
    conflict_type: Literal[
        "value_mismatch",
        "confidence_divergence",
        "resonance_interference",
        "policy_violation",
        "timeout_conflict",
    ]
    severity: Literal["low", "medium", "high", "critical"]

    # Resolution
    resolution_strategy: ConflictResolutionStrategy
    resolution_result: AgentOutputSchema | None = None
    resolution_reason: str | None = None

    # Timestamps
    detected_at: datetime = Field(default_factory=utcnow)
    resolved_at: datetime | None = None

    @property
    def is_resolved(self) -> bool:
        return self.resolution_result is not None and self.resolved_at is not None

    @property
    def resolution_time_ms(self) -> float:
        if self.resolved_at:
            return (self.resolved_at - self.detected_at).total_seconds() * 1000
        return 0.0


class ConflictResolutionRequest(BaseModel):
    """Request to resolve a conflict between agents."""

    model_config = ConfigDict(extra="forbid")

    request_id: UUID = Field(default_factory=uuid4)
    conflict: AgentConflict

    # Resolution preferences
    preferred_strategy: ConflictResolutionStrategy | None = None
    arbitrator_agent: AgentRole | None = None  # For ARBITRATOR strategy

    # Constraints
    max_resolution_time_ms: float = Field(default=5000.0)
    require_consensus: bool = Field(default=False)
    min_confidence_threshold: float = Field(default=DEFAULT_CONFIDENCE_THRESHOLD)


class ConflictResolutionResult(BaseModel):
    """Result of conflict resolution."""

    model_config = ConfigDict(extra="allow")

    request_id: UUID
    conflict_id: UUID

    # Resolution
    winning_output: AgentOutputSchema
    strategy_used: ConflictResolutionStrategy
    resolution_reason: str

    # Metrics
    resolution_time_ms: float
    confidence_in_resolution: float = Field(..., ge=0.0, le=1.0)

    # Voting details (if applicable)
    vote_distribution: dict[str, float] | None = None
    # Agent name -> vote weight

    # Timestamp
    timestamp: datetime = Field(default_factory=utcnow)


# =============================================================================
# Escalation
# =============================================================================


class EscalationRequest(BaseModel):
    """Request to escalate a decision up the hierarchy."""

    model_config = ConfigDict(extra="forbid")

    escalation_id: UUID = Field(default_factory=uuid4)
    trace_id: UUID

    # Escalation details
    reason: EscalationReason
    description: str = Field(..., min_length=1)

    # Context
    current_agent: AgentRole
    current_confidence: float
    target_layer: AgentLayer

    # Supporting data
    supporting_outputs: list[AgentOutputSchema] = Field(default_factory=list)
    context_data: dict[str, Any] = Field(default_factory=dict)

    # Timestamps
    created_at: datetime = Field(default_factory=utcnow)
    resolved_at: datetime | None = None


class EscalationResult(BaseModel):
    """Result of an escalation."""

    model_config = ConfigDict(extra="forbid")

    escalation_id: UUID

    # Resolution
    escalated_to: AgentRole
    decision: str
    rationale: str

    # Outcome
    final_confidence: float = Field(..., ge=0.0, le=1.0)
    requires_action: bool = False
    action_required: str | None = None

    # Timestamps
    resolved_at: datetime = Field(default_factory=utcnow)
