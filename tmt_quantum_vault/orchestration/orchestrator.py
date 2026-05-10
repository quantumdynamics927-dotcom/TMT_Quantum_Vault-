"""
Agent Orchestrator for Ensemble Coordination.

This module implements the central orchestration kernel that coordinates
multi-agent execution, handles routing decisions, and manages the
coordination lifecycle.

Key Components:
- AgentOrchestrator: Central routing and dispatch logic
- RoutingEngine: Context-aware agent selection
- ExecutionPlanner: Parallel/sequential execution planning
- HandoffManager: Agent-to-agent handoff coordination
"""

from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from .channel import AgentBus, AgentChannel, ChannelRegistry
from .models import (
    AgentConflict,
    AgentContract,
    AgentInputSchema,
    AgentLayer,
    AgentMessage,
    AgentOutputSchema,
    AgentRole,
    ConflictResolutionResult,
    ConflictResolutionStrategy,
    CoordinationMetrics,
    CoordinationTrace,
    EscalationReason,
    EscalationResult,
    HandoffDirective,
    HandoffStatus,
    MessagePriority,
    RoutingDecision,
    RoutingPolicy,
)
from .queue_monitor import (
    KingstonQueueMonitor,
    PreflightResult,
    create_hardware_evidence_entry,
    preflight_check,
)

logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

PHI = 1.618033988749895
PHI_INVERSE = 1.0 / PHI

# Execution modes
class ExecutionMode(StrEnum):
    """Execution mode for agent tasks."""
    SIMULATION = "simulation"
    LIVE = "live"
    HYBRID = "hybrid"  # Simulation with selective live routing

# Default routing weights
DEFAULT_ROUTING_WEIGHTS = {
    "fitness": 0.30,
    "role_match": 0.25,
    "load_balance": 0.20,
    "phi_alignment": 0.15,
    "resonance": 0.10,
}

# Layer progression sequence
DEFAULT_LAYER_SEQUENCE = [
    AgentLayer.INPUT,
    AgentLayer.PROCESSING,
    AgentLayer.INTEGRATION,
    AgentLayer.OUTPUT,
]

# Role-to-layer mapping
ROLE_LAYER_MAP = {
    AgentRole.BIO: AgentLayer.INPUT,
    AgentRole.FRACTAL: AgentLayer.INPUT,
    AgentRole.VISUAL: AgentLayer.INPUT,
    AgentRole.STRATEGIC: AgentLayer.PROCESSING,
    AgentRole.BITNET: AgentLayer.PROCESSING,
    AgentRole.HARMONIC: AgentLayer.PROCESSING,
    AgentRole.WORMHOLE: AgentLayer.PROCESSING,
    AgentRole.SYNTHESIZER: AgentLayer.INTEGRATION,
    AgentRole.OBSERVER: AgentLayer.INTEGRATION,
    AgentRole.FEDERATION: AgentLayer.INTEGRATION,
    AgentRole.MIRROR: AgentLayer.INTEGRATION,
    AgentRole.BRONZE: AgentLayer.OUTPUT,
    AgentRole.WORKFLOW: AgentLayer.OUTPUT,
    AgentRole.STEALTH: AgentLayer.OUTPUT,
    AgentRole.VALIDATOR: AgentLayer.OUTPUT,
    AgentRole.ARCHIVIST: AgentLayer.OUTPUT,
    AgentRole.AUDITOR: AgentLayer.OUTPUT,
}

# Task type to role mapping
# Maps task types to agent roles that can handle them.
# Roles are listed in priority order. Fallback to synthesizer if none available.
TASK_ROLE_ROUTING = {
    # Validation tasks - use observer (monitoring) or archivist (records) as fallback
    "validation": [AgentRole.VALIDATOR, AgentRole.AUDITOR, AgentRole.OBSERVER, AgentRole.ARCHIVIST],
    # Synthesis tasks - primary integration agents
    "synthesis": [AgentRole.SYNTHESIZER, AgentRole.FEDERATION, AgentRole.MIRROR],
    # Analysis tasks - use observer as fallback for strategic
    "analysis": [AgentRole.STRATEGIC, AgentRole.WORMHOLE, AgentRole.OBSERVER],
    # Monitoring tasks - use observer (available) or bitnet as fallback
    "monitoring": [AgentRole.OBSERVER, AgentRole.HARMONIC, AgentRole.BITNET],
    # Coordination tasks - use synthesizer as fallback for federation
    "coordination": [AgentRole.FEDERATION, AgentRole.WORKFLOW, AgentRole.SYNTHESIZER],
    # Archival tasks - use archivist (available) or observer as fallback
    "archival": [AgentRole.ARCHIVIST, AgentRole.AUDITOR, AgentRole.OBSERVER],
    # Protection tasks - use bronze (available) or stealth
    "protection": [AgentRole.BRONZE, AgentRole.STEALTH],
    # Processing tasks - use bitnet (available) or fractal as fallback
    "processing": [AgentRole.BITNET, AgentRole.HARMONIC, AgentRole.FRACTAL],
    # Visualization tasks - use fractal (available) or mirror as fallback
    "visualization": [AgentRole.VISUAL, AgentRole.FRACTAL, AgentRole.MIRROR],
    # Biological tasks - use bio (available) or mirror as fallback
    "biological": [AgentRole.BIO, AgentRole.MIRROR],
    # Strategic tasks - use wormhole (available) or observer as fallback
    "strategic": [AgentRole.STRATEGIC, AgentRole.WORMHOLE, AgentRole.OBSERVER],
}


# =============================================================================
# Agent Profile
# =============================================================================


class AgentProfile:
    """Profile of an agent for orchestration decisions."""

    def __init__(
        self,
        agent_id: int,
        agent_name: str,
        agent_role: AgentRole,
        fitness: float,
        phi_score: float,
        resonance_frequency: float,
        specialization: str,
        conscious_dna: str = "",
    ):
        """Initialize agent profile.

        Args:
            agent_id: Unique agent identifier
            agent_name: Human-readable name
            agent_role: Functional role
            fitness: Fitness score (0-1)
            phi_score: Phi alignment score
            resonance_frequency: Resonance frequency in Hz
            specialization: Specialization description
            conscious_dna: DNA sequence
        """
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.agent_role = agent_role
        self.fitness = fitness
        self.phi_score = phi_score
        self.resonance_frequency = resonance_frequency
        self.specialization = specialization
        self.conscious_dna = conscious_dna

        # Dynamic state
        self.current_load = 0
        self.total_tasks_completed = 0
        self.total_tasks_failed = 0
        self.last_activity: datetime | None = None

        # Computed properties
        self.layer = ROLE_LAYER_MAP.get(agent_role, AgentLayer.PROCESSING)

    @property
    def availability(self) -> float:
        """Get availability score (0-1)."""
        # Simple availability based on load
        max_load = 5
        return max(0.0, 1.0 - (self.current_load / max_load))

    @property
    def phi_alignment(self) -> float:
        """Get phi alignment score (0-1)."""
        # Distance from ideal phi inverse
        deviation = abs(self.phi_score - PHI_INVERSE)
        return max(0.0, 1.0 - (deviation / PHI_INVERSE))

    @property
    def success_rate(self) -> float:
        """Get success rate (0-1)."""
        total = self.total_tasks_completed + self.total_tasks_failed
        if total == 0:
            return 1.0
        return self.total_tasks_completed / total

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "agent_role": self.agent_role.value,
            "fitness": self.fitness,
            "phi_score": self.phi_score,
            "resonance_frequency": self.resonance_frequency,
            "specialization": self.specialization,
            "layer": self.layer.value,
            "current_load": self.current_load,
            "availability": self.availability,
            "phi_alignment": self.phi_alignment,
            "success_rate": self.success_rate,
        }


# =============================================================================
# Routing Engine
# =============================================================================


class RoutingEngine:
    """Context-aware agent selection engine."""

    def __init__(
        self,
        policy: RoutingPolicy | None = None,
        weights: dict[str, float] | None = None,
    ):
        """Initialize routing engine.

        Args:
            policy: Routing policy
            weights: Routing factor weights
        """
        self.policy = policy or RoutingPolicy(policy_name="default")
        self.weights = {**DEFAULT_ROUTING_WEIGHTS, **(weights or {})}
        self._agent_profiles: dict[int, AgentProfile] = {}

    def register_agent(self, profile: AgentProfile) -> None:
        """Register an agent profile.

        Args:
            profile: Agent profile to register
        """
        self._agent_profiles[profile.agent_id] = profile

    def unregister_agent(self, agent_id: int) -> AgentProfile | None:
        """Unregister an agent.

        Args:
            agent_id: Agent ID to unregister

        Returns:
            Removed profile or None
        """
        return self._agent_profiles.pop(agent_id, None)

    def get_profile(self, agent_id: int) -> AgentProfile | None:
        """Get agent profile.

        Args:
            agent_id: Agent ID

        Returns:
            Profile or None
        """
        return self._agent_profiles.get(agent_id)

    def _is_disabled(self, component: str) -> bool:
        """Check if a component is disabled.

        Args:
            component: Component name (agent role or layer name)

        Returns:
            True if disabled
        """
        disabled = self.policy.disabled_components
        return component.lower() in [d.lower() for d in disabled]

    def get_profiles_by_role(self, role: AgentRole) -> list[AgentProfile]:
        """Get all profiles for a role.

        Args:
            role: Agent role

        Returns:
            List of profiles
        """
        return [p for p in self._agent_profiles.values() if p.agent_role == role]

    def get_profiles_by_layer(self, layer: AgentLayer) -> list[AgentProfile]:
        """Get all profiles for a layer.

        Args:
            layer: Agent layer

        Returns:
            List of profiles
        """
        return [p for p in self._agent_profiles.values() if p.layer == layer]

    def route(
        self,
        task_type: str,
        context: dict[str, Any] | None = None,
        preferred_agents: list[AgentRole] | None = None,
        excluded_agents: list[AgentRole] | None = None,
    ) -> RoutingDecision:
        """Make a routing decision.

        Args:
            task_type: Type of task
            context: Task context
            preferred_agents: Preferred agent roles
            excluded_agents: Excluded agent roles

        Returns:
            Routing decision
        """
        context = context or {}
        excluded_agents = excluded_agents or []
        preferred_agents = preferred_agents or []

        # Get candidate roles based on task type
        task_roles = TASK_ROLE_ROUTING.get(task_type, [AgentRole.SYNTHESIZER])

        # If preferred_agents is provided, use those directly (for DELEG tasks)
        # Otherwise, filter by task_roles
        if preferred_agents:
            candidate_roles = list(preferred_agents)
        else:
            candidate_roles = task_roles

        # Filter by excluded
        candidate_roles = [r for r in candidate_roles if r not in excluded_agents]

        # Filter by ablation (disabled components)
        candidate_roles = [r for r in candidate_roles if not self._is_disabled(r.value)]

        if not candidate_roles:
            candidate_roles = [AgentRole.SYNTHESIZER]  # Default fallback

        # Get candidate profiles
        candidates = []
        for role in candidate_roles:
            candidates.extend(self.get_profiles_by_role(role))

        # Filter out disabled agents
        candidates = [p for p in candidates if not self._is_disabled(p.agent_role.value)]

        if not candidates:
            # Fallback to any available agent (excluding disabled)
            candidates = [
                p for p in self._agent_profiles.values()
                if not self._is_disabled(p.agent_role.value)
            ]

        # Score candidates
        scored_candidates = []
        for profile in candidates:
            score = self._calculate_score(profile, task_type, context)
            scored_candidates.append((profile, score))

        # Sort by score
        scored_candidates.sort(key=lambda x: x[1], reverse=True)

        # Select primary and backups
        primary = scored_candidates[0][0] if scored_candidates else None
        backups = (
            [p for p, _ in scored_candidates[1:4]] if len(scored_candidates) > 1 else []
        )

        if not primary:
            raise RuntimeError("No agents available for routing")

        # Calculate routing factors
        routing_factors = self._get_routing_factors(primary, task_type, context)

        return RoutingDecision(
            task_id=uuid4(),
            primary_agent=primary.agent_role,
            primary_reason=(
                f"Best match for {task_type} " f"(score: {scored_candidates[0][1]:.3f})"
            ),
            backup_agents=[b.agent_role for b in backups],
            routing_factors=routing_factors,
            layer=primary.layer,
            estimated_complexity=context.get("complexity", 0.5),
            parallel_execution=context.get("parallel", False),
            decision_confidence=scored_candidates[0][1],
            alternative_routes_considered=len(scored_candidates) - 1,
        )

    def _calculate_score(
        self,
        profile: AgentProfile,
        task_type: str,
        context: dict[str, Any],
    ) -> float:
        """Calculate routing score for a profile.

        Args:
            profile: Agent profile
            task_type: Task type
            context: Task context

        Returns:
            Routing score (0-1)
        """
        factors = self._get_routing_factors(profile, task_type, context)

        total_score = 0.0
        for factor_name, factor_value in factors.items():
            weight = self.weights.get(factor_name, 0.1)
            total_score += weight * factor_value

        return min(1.0, total_score)

    def _get_routing_factors(
        self,
        profile: AgentProfile,
        task_type: str,
        context: dict[str, Any],
    ) -> dict[str, float]:
        """Get routing factors for a profile.

        Args:
            profile: Agent profile
            task_type: Task type
            context: Task context

        Returns:
            Dictionary of factor values
        """
        # Fitness factor
        fitness_factor = profile.fitness

        # Role match factor
        task_roles = TASK_ROLE_ROUTING.get(task_type, [])
        role_match = 1.0 if profile.agent_role in task_roles else 0.3

        # Load balance factor
        load_factor = profile.availability

        # Phi alignment factor
        phi_factor = profile.phi_alignment

        # Resonance factor
        resonance_factor = profile.resonance_frequency / 1000.0  # Normalize
        resonance_factor = min(1.0, resonance_factor)

        # Success rate factor
        success_factor = profile.success_rate

        return {
            "fitness": fitness_factor,
            "role_match": role_match,
            "load_balance": load_factor,
            "phi_alignment": phi_factor,
            "resonance": resonance_factor,
            "success_rate": success_factor,
        }


# =============================================================================
# Execution Planner
# =============================================================================


class ExecutionPlan:
    """Execution plan for a multi-agent task."""

    def __init__(
        self,
        plan_id: UUID,
        task_id: UUID,
        stages: list[ExecutionStage],
    ):
        """Initialize execution plan.

        Args:
            plan_id: Unique plan ID
            task_id: Task ID
            stages: Execution stages
        """
        self.plan_id = plan_id
        self.task_id = task_id
        self.stages = stages
        self.current_stage_index = 0
        self.started_at: datetime | None = None
        self.completed_at: datetime | None = None

    @property
    def current_stage(self) -> ExecutionStage | None:
        """Get current execution stage."""
        if self.current_stage_index < len(self.stages):
            return self.stages[self.current_stage_index]
        return None

    @property
    def is_complete(self) -> bool:
        """Check if plan is complete."""
        return self.current_stage_index >= len(self.stages)

    def advance(self) -> ExecutionStage | None:
        """Advance to next stage.

        Returns:
            Next stage or None if complete
        """
        self.current_stage_index += 1
        return self.current_stage

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "plan_id": str(self.plan_id),
            "task_id": str(self.task_id),
            "stages": [s.to_dict() for s in self.stages],
            "current_stage_index": self.current_stage_index,
            "is_complete": self.is_complete,
        }


class ExecutionStage:
    """Single stage of execution."""

    def __init__(
        self,
        stage_id: UUID,
        layer: AgentLayer,
        agents: list[AgentRole],
        parallel: bool = False,
        dependencies: list[UUID] | None = None,
    ):
        """Initialize execution stage.

        Args:
            stage_id: Unique stage ID
            layer: Agent layer
            agents: Agents to execute
            parallel: Whether to execute in parallel
            dependencies: IDs of stages that must complete first
        """
        self.stage_id = stage_id
        self.layer = layer
        self.agents = agents
        self.parallel = parallel
        self.dependencies = dependencies or []

        self.status: HandoffStatus = HandoffStatus.PENDING
        self.results: dict[AgentRole, AgentOutputSchema] = {}
        self.started_at: datetime | None = None
        self.completed_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "stage_id": str(self.stage_id),
            "layer": self.layer.value,
            "agents": [a.value for a in self.agents],
            "parallel": self.parallel,
            "dependencies": [str(d) for d in self.dependencies],
            "status": self.status.value,
        }


class ExecutionPlanner:
    """Plans parallel/sequential execution of agents."""

    def __init__(
        self,
        routing_engine: RoutingEngine,
        layer_sequence: list[AgentLayer] | None = None,
    ):
        """Initialize execution planner.

        Args:
            routing_engine: Routing engine for agent selection
            layer_sequence: Layer execution sequence
        """
        self.routing_engine = routing_engine
        self.layer_sequence = layer_sequence or DEFAULT_LAYER_SEQUENCE

    def plan(
        self,
        task_type: str,
        context: dict[str, Any],
        parallel_layers: bool = False,
    ) -> ExecutionPlan:
        """Create execution plan.

        Args:
            task_type: Type of task
            context: Task context
            parallel_layers: Whether to execute layers in parallel

        Returns:
            Execution plan
        """
        plan_id = uuid4()
        task_id = uuid4()
        stages = []

        # Check if context specifies expected_agents for DELEG tasks
        expected_agents = context.get("expected_agents", [])
        expected_layers = context.get("expected_layers", [])

        # For DELEG tasks with expected layers, create stages for all expected layers
        if expected_layers and expected_agents:
            # Convert expected_layers to AgentLayer enums
            layer_map = {
                "input": AgentLayer.INPUT,
                "processing": AgentLayer.PROCESSING,
                "integration": AgentLayer.INTEGRATION,
                "output": AgentLayer.OUTPUT,
            }
            target_layers = [layer_map.get(layer_name.lower(), layer_name) for layer_name in expected_layers if layer_name.lower() in layer_map]

            for layer in target_layers:
                profiles = self.routing_engine.get_profiles_by_layer(layer)
                if not profiles:
                    continue

                # Get agents for this layer - match expected_agents to this layer's profiles
                layer_agents = [
                    p.agent_role
                    for p in profiles
                    if p.agent_role.value in [a.lower() for a in expected_agents]
                ]

                # If no expected agents match this layer, use task_roles
                if not layer_agents:
                    task_roles = TASK_ROLE_ROUTING.get(task_type, [])
                    layer_agents = [
                        p.agent_role
                        for p in profiles
                        if p.agent_role in task_roles
                    ]

                # If still no agents, use all layer agents
                if not layer_agents:
                    layer_agents = [p.agent_role for p in profiles[:2]]

                stage = ExecutionStage(
                    stage_id=uuid4(),
                    layer=layer,
                    agents=layer_agents,
                    parallel=parallel_layers,
                )
                stages.append(stage)
        else:
            # Standard execution: create stage for each layer
            for layer in self.layer_sequence:
                profiles = self.routing_engine.get_profiles_by_layer(layer)

                if not profiles:
                    continue

                # Select agents for this layer
                task_roles = TASK_ROLE_ROUTING.get(task_type, [])
                layer_agents = [
                    p.agent_role
                    for p in profiles
                    if p.agent_role in task_roles or not task_roles
                ]

                if not layer_agents:
                    # Use all layer agents if no specific match
                    layer_agents = [p.agent_role for p in profiles[:2]]

                stage = ExecutionStage(
                    stage_id=uuid4(),
                    layer=layer,
                    agents=layer_agents,
                    parallel=parallel_layers,
                )
                stages.append(stage)

        # Set up dependencies for sequential execution
        if not parallel_layers:
            for i, stage in enumerate(stages):
                if i > 0:
                    stage.dependencies = [stages[i - 1].stage_id]

        return ExecutionPlan(
            plan_id=plan_id,
            task_id=task_id,
            stages=stages,
        )


# =============================================================================
# Handoff Manager
# =============================================================================


class HandoffManager:
    """Manages agent-to-agent handoffs."""

    def __init__(self, bus: AgentBus):
        """Initialize handoff manager.

        Args:
            bus: Agent communication bus
        """
        self._bus = bus
        self._pending_handoffs: dict[UUID, HandoffDirective] = {}
        self._handoff_history: list[tuple[HandoffDirective, HandoffStatus]] = []

    def initiate_handoff(
        self,
        from_agent: AgentRole,
        to_agent: AgentRole,
        reason: str,
        context: dict[str, Any],
        trace_id: UUID,
        priority: MessagePriority = MessagePriority.NORMAL,
    ) -> HandoffDirective:
        """Initiate a handoff.

        Args:
            from_agent: Source agent
            to_agent: Target agent
            reason: Handoff reason
            context: Context to preserve
            trace_id: Trace ID
            priority: Message priority

        Returns:
            Handoff directive
        """
        directive = HandoffDirective(
            target_agent=to_agent,
            reason=reason,
            context_to_preserve=list(context.keys()),
            modifications=context,
            urgency=priority,
        )

        # Create handoff message
        message = AgentMessage(
            sender_agent=from_agent,
            sender_id=0,  # Will be filled by channel
            recipient_agent=to_agent,
            message_type="delegation",
            payload={
                "directive": directive.model_dump(),
                "reason": reason,
            },
            priority=priority,
            trace_id=trace_id,
        )

        self._bus.send(message)
        self._pending_handoffs[directive.target_agent] = directive

        return directive

    def complete_handoff(
        self,
        directive: HandoffDirective,
        status: HandoffStatus,
    ) -> None:
        """Complete a handoff.

        Args:
            directive: Handoff directive
            status: Completion status
        """
        if directive in self._pending_handoffs.values():
            self._handoff_history.append((directive, status))
            self._pending_handoffs.pop(directive.target_agent, None)

    def get_pending_handoffs(self) -> list[HandoffDirective]:
        """Get all pending handoffs.

        Returns:
            List of pending directives
        """
        return list(self._pending_handoffs.values())

    def get_handoff_stats(self) -> dict[str, Any]:
        """Get handoff statistics.

        Returns:
            Handoff statistics
        """
        total = len(self._handoff_history)
        if total == 0:
            return {
                "total_handoffs": 0,
                "success_rate": 0.0,
                "pending_count": len(self._pending_handoffs),
            }

        successful = sum(
            1
            for _, status in self._handoff_history
            if status == HandoffStatus.COMPLETED
        )

        return {
            "total_handoffs": total,
            "success_rate": successful / total,
            "pending_count": len(self._pending_handoffs),
        }


# =============================================================================
# Agent Orchestrator
# =============================================================================


class AgentOrchestrator:
    """Central orchestration kernel for multi-agent coordination."""

    def __init__(
        self,
        vault_path: Path,
        policy: RoutingPolicy | None = None,
        execution_mode: ExecutionMode = ExecutionMode.SIMULATION,
    ):
        """Initialize agent orchestrator.

        Args:
            vault_path: Path to TMT Quantum Vault
            policy: Routing policy
            execution_mode: Execution mode (simulation, live, hybrid)
        """
        self.vault_path = Path(vault_path)
        self.policy = policy or RoutingPolicy(policy_name="default")
        self.execution_mode = execution_mode

        # Core components
        self._registry = ChannelRegistry()
        self._bus = AgentBus(self._registry)
        self._routing_engine = RoutingEngine(policy=self.policy)
        self._execution_planner = ExecutionPlanner(self._routing_engine)
        self._handoff_manager = HandoffManager(self._bus)

        # Queue monitor for live execution (lazy loaded)
        self._queue_monitor: KingstonQueueMonitor | None = None

        # State
        self._profiles: dict[int, AgentProfile] = {}
        self._active_traces: dict[UUID, CoordinationTrace] = {}
        self._metrics = CoordinationMetrics()

        # Load agents
        self._load_agents()

    # =========================================================================
    # Agent Loading
    # =========================================================================

    def _load_agents(self) -> None:
        """Load all agents from vault."""
        agent_dirs = [
            d
            for d in self.vault_path.iterdir()
            if d.is_dir() and d.name.startswith("Agent_")
        ]

        for agent_dir in agent_dirs:
            profile = self._load_agent_profile(agent_dir)
            if profile:
                self._register_agent(profile)

    def _load_agent_profile(self, agent_dir: Path) -> AgentProfile | None:
        """Load agent profile from directory.

        Args:
            agent_dir: Agent directory

        Returns:
            Agent profile or None
        """
        dna_file = agent_dir / "conscious_dna.json"
        if not dna_file.exists():
            return None

        try:
            with open(dna_file, encoding="utf-8") as f:
                dna_data = json.load(f)

            # Map specialization to role
            role = self._specialization_to_role(dna_data.get("dna_specialization", ""))

            return AgentProfile(
                agent_id=dna_data.get("dna_agent_id", 0),
                agent_name=dna_data.get("dna_agent_name", "Unknown"),
                agent_role=role,
                fitness=dna_data.get("fitness", 0.0),
                phi_score=dna_data.get("phi_score", 0.0),
                resonance_frequency=dna_data.get("resonance_frequency", 0.0),
                specialization=dna_data.get("dna_specialization", ""),
                conscious_dna=dna_data.get("conscious_dna", ""),
            )
        except (json.JSONDecodeError, KeyError):
            return None

    def _specialization_to_role(self, specialization: str) -> AgentRole:
        """Map specialization to agent role.

        Args:
            specialization: Specialization string

        Returns:
            Agent role
        """
        mapping = {
            "knowledge fusion": AgentRole.SYNTHESIZER,
            "resonance monitoring": AgentRole.OBSERVER,
            "integrity verification": AgentRole.VALIDATOR,
            "strategic analysis": AgentRole.STRATEGIC,
            "resonance tuning": AgentRole.HARMONIC,
            "network coordination": AgentRole.FEDERATION,
            "process automation": AgentRole.WORKFLOW,
            "memory-persistence": AgentRole.ARCHIVIST,
            "governance & compliance": AgentRole.AUDITOR,
            "protection & justice": AgentRole.BRONZE,
            "wisdom & knowledge": AgentRole.BITNET,
            "consciousness evolution": AgentRole.WORMHOLE,
            "divine love": AgentRole.MIRROR,
            "healing": AgentRole.BIO,
            "beauty & harmony": AgentRole.FRACTAL,
            "pattern recognition": AgentRole.VISUAL,
            "quantum bridge": AgentRole.STEALTH,
        }

        specialization_lower = specialization.lower()
        for key, role in mapping.items():
            if key in specialization_lower:
                return role

        return AgentRole.SYNTHESIZER

    def _register_agent(self, profile: AgentProfile) -> None:
        """Register an agent.

        Args:
            profile: Agent profile
        """
        self._profiles[profile.agent_id] = profile
        self._routing_engine.register_agent(profile)

        # Create channel
        channel = AgentChannel(
            agent_id=profile.agent_id,
            agent_name=profile.agent_name,
            agent_role=profile.agent_role,
        )
        self._bus.register_channel(channel)

    # =========================================================================
    # Task Execution
    # =========================================================================

    def execute(
        self,
        task_type: str,
        objective: str,
        context: dict[str, Any] | None = None,
        preferred_agents: list[AgentRole] | list[str] | None = None,
        execution_mode: ExecutionMode | None = None,
    ) -> CoordinationTrace:
        """Execute a multi-agent task.

        Args:
            task_type: Type of task
            objective: Task objective
            context: Task context
            preferred_agents: Preferred agent roles (AgentRole or str)
            execution_mode: Override execution mode (optional, defaults to self.execution_mode)

        Returns:
            Coordination trace
        """
        context = context or {}
        trace_id = uuid4()
        session_id = uuid4()

        # Use provided execution_mode or fall back to instance default
        effective_execution_mode = execution_mode or self.execution_mode

        # Convert string agent names to AgentRole if needed
        parsed_agents: list[AgentRole] | None = None
        if preferred_agents:
            parsed_agents = []
            for agent in preferred_agents:
                if isinstance(agent, str):
                    # Try to match string to AgentRole
                    try:
                        parsed_agents.append(AgentRole(agent))
                    except ValueError:
                        # Try uppercase match
                        try:
                            parsed_agents.append(AgentRole(agent.upper()))
                        except ValueError:
                            logger.warning(f"Unknown agent role: {agent}, skipping")
                else:
                    parsed_agents.append(agent)

        # Create trace
        trace = CoordinationTrace(
            trace_id=trace_id,
            session_id=session_id,
        )

        self._active_traces[trace_id] = trace

        try:
            # Create execution plan
            plan = self._execution_planner.plan(
                task_type=task_type,
                context=context,
            )

            # Execute stages
            while not plan.is_complete:
                stage = plan.current_stage
                if not stage:
                    break

                stage.started_at = datetime.now(UTC)
                stage.status = HandoffStatus.PENDING

                # Execute stage agents
                for agent_role in stage.agents:
                    routing_decision = self._routing_engine.route(
                        task_type=task_type,
                        context=context,
                        preferred_agents=[agent_role],
                    )
                    trace.add_decision(routing_decision)

                    # Create contract
                    contract = self._create_contract(
                        task_type=task_type,
                        objective=objective,
                        context=context,
                        routing_decision=routing_decision,
                        trace_id=trace_id,
                    )
                    trace.add_contract(contract)

                    # Execute agent (simulated for now)
                    output = self._execute_agent(
                        profile=self._routing_engine.get_profile(
                            self._get_agent_id_by_role(agent_role)
                        ),
                        contract=contract,
                        execution_mode=effective_execution_mode,
                    )

                    if output:
                        contract.output = output
                        contract.completed_at = datetime.now(UTC)
                        stage.results[agent_role] = output

                stage.completed_at = datetime.now(UTC)
                stage.status = HandoffStatus.COMPLETED
                plan.advance()

            # Finalize trace
            final_confidence = self._calculate_final_confidence(trace)
            trace.finalize(
                status=HandoffStatus.COMPLETED,
                confidence=final_confidence,
            )

            # Update metrics
            self._update_metrics(trace)

        except Exception:
            logger.exception("Orchestration execution failed")
            trace.finalize(
                status=HandoffStatus.FAILED,
                confidence=0.0,
            )

        return trace

    def _create_contract(
        self,
        task_type: str,
        objective: str,
        context: dict[str, Any],
        routing_decision: RoutingDecision,
        trace_id: UUID,
    ) -> AgentContract:
        """Create agent contract."""
        input_schema = AgentInputSchema(
            task_type=task_type,
            objective=objective,
            context=context,
            preferred_agents=[routing_decision.primary_agent],
        )

        return AgentContract(
            trace_id=trace_id,
            input=input_schema,
        )

    def _get_queue_monitor(self) -> KingstonQueueMonitor:
        """Get or create the queue monitor for live execution.

        Returns:
            KingstonQueueMonitor instance
        """
        if self._queue_monitor is None:
            self._queue_monitor = KingstonQueueMonitor()
        return self._queue_monitor

    def _execute_agent(
        self,
        profile: AgentProfile | None,
        contract: AgentContract,
        circuit: Any | None = None,
        execution_mode: ExecutionMode | None = None,
    ) -> AgentOutputSchema | None:
        """Execute a single agent with three-lane routing.

        Three-Lane Routing Strategy:
        1. SIMULATION mode: Fast, free, always available
        2. LIVE mode with quantum: Route to ibm_kingston if resonance >= 0.618
        3. LIVE mode with LLM: Route to Ollama for synthesis tasks

        Args:
            profile: Agent profile
            contract: Agent contract
            circuit: Optional quantum circuit for hardware execution
            execution_mode: Override execution mode (optional)

        Returns:
            Agent output or None
        """
        if not profile:
            return None

        # Use provided execution_mode or fall back to instance default
        effective_mode = execution_mode or self.execution_mode

        # Update agent state
        profile.current_load += 1
        profile.last_activity = datetime.now(UTC)
        start_time = time.time()

        try:
            # ── Lane 1: Simulation (always fast, free) ──────────────────────
            if effective_mode == ExecutionMode.SIMULATION:
                return self._simulate_agent(profile, contract, start_time)

            # ── Lane 2: Quantum tasks → ibm_kingston (if resonance + budget) ──
            if circuit is not None and self._requires_quantum_execution(contract):
                preflight = preflight_check(circuit)

                if preflight.ready_for_hardware:
                    monitor = self._get_queue_monitor()
                    if monitor.should_route_live(preflight.phi_score):
                        result = self._run_on_kingston(
                            profile, contract, circuit, preflight
                        )
                        if result:
                            return result
                        # Fall through to Lane 3 on failure

            # ── Lane 3: LLM tasks / fallback → Ollama or Synthesizer ─────────
            if self._is_llm_task(profile.agent_role, contract):
                result = self._run_on_ollama(profile, contract)
                if result:
                    return result

            # ── Fallback: Simulation ──────────────────────────────────────────
            return self._simulate_agent(profile, contract, start_time)

        except Exception as e:
            logger.error(f"Agent execution failed: {e}", exc_info=True)
            return self._create_error_output(profile, contract, str(e), start_time)

        finally:
            profile.current_load -= 1
            profile.total_tasks_completed += 1

    def _requires_quantum_execution(self, contract: AgentContract) -> bool:
        """Check if contract requires quantum execution.

        Args:
            contract: Agent contract

        Returns:
            True if quantum execution required
        """
        task_type = contract.input.task_type.lower()
        quantum_types = {
            "quantum", "circuit", "entanglement", "superposition",
            "teleportation", "qrng", "bell_state", "grover", "shor",
        }
        return any(qt in task_type for qt in quantum_types)

    def _is_llm_task(
        self, agent_role: AgentRole, contract: AgentContract
    ) -> bool:
        """Check if task should be routed to LLM.

        Args:
            agent_role: Agent role
            contract: Agent contract

        Returns:
            True if LLM routing appropriate
        """
        llm_roles = {
            AgentRole.SYNTHESIZER,
            AgentRole.STRATEGIC,
            AgentRole.OBSERVER,
            AgentRole.MIRROR,
        }
        return agent_role in llm_roles

    def _simulate_agent(
        self,
        profile: AgentProfile,
        contract: AgentContract,
        start_time: float,
    ) -> AgentOutputSchema:
        """Simulate agent execution.

        Args:
            profile: Agent profile
            contract: Agent contract
            start_time: Execution start time

        Returns:
            Simulated agent output
        """
        return AgentOutputSchema(
            task_id=contract.input.task_id,
            agent_id=profile.agent_id,
            agent_name=profile.agent_name,
            agent_role=profile.agent_role,
            result={"status": "simulated", "mode": "simulation"},
            summary=f"Simulated by {profile.agent_name}",
            confidence=profile.fitness,
            resonance_score=profile.phi_alignment,
            fitness_contribution=profile.fitness * 0.1,
            status=HandoffStatus.COMPLETED,
            processing_time_ms=(time.time() - start_time) * 1000,
        )

    def _run_on_kingston(
        self,
        profile: AgentProfile,
        contract: AgentContract,
        circuit: Any,
        preflight: PreflightResult,
    ) -> AgentOutputSchema | None:
        """Run task on ibm_kingston backend.

        Args:
            profile: Agent profile
            contract: Agent contract
            circuit: Quantum circuit
            preflight: Pre-flight check result

        Returns:
            Agent output or None on failure
        """
        try:
            from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
            from qiskit_ibm_runtime.options import SamplerOptions

            monitor = self._get_queue_monitor()
            service = QiskitRuntimeService(channel="ibm_quantum")
            backend = service.backend("ibm_kingston")

            # Configure sampler
            options = SamplerOptions(default_shots=1024)
            sampler = SamplerV2(backend, options=options)

            # Run job
            job = sampler.run([circuit])
            result = job.result()

            # Record usage (estimate based on job time)
            usage_minutes = 0.5  # Conservative estimate
            monitor.record_usage(usage_minutes)

            # Create evidence entry
            evidence = create_hardware_evidence_entry(
                {"fidelity": preflight.fidelity},
                preflight.phi_score,
                monitor,
            )

            return AgentOutputSchema(
                task_id=contract.input.task_id,
                agent_id=profile.agent_id,
                agent_name=profile.agent_name,
                agent_role=profile.agent_role,
                result={
                    "status": "completed",
                    "backend": "ibm_kingston",
                    "counts": result[0].data.meas.get_counts(),
                },
                summary=f"Executed on ibm_kingston by {profile.agent_name}",
                confidence=preflight.fidelity,
                resonance_score=preflight.phi_score,
                fitness_contribution=profile.fitness * 0.1,
                status=HandoffStatus.COMPLETED,
                evidence=evidence,
            )

        except ImportError:
            logger.warning("qiskit-ibm-runtime not installed, falling back to simulation")
            return None
        except Exception as e:
            logger.warning(f"IBM Quantum execution failed: {e}")
            return None

    def _run_on_ollama(
        self,
        profile: AgentProfile,
        contract: AgentContract,
    ) -> AgentOutputSchema | None:
        """Run task on local Ollama instance.

        Args:
            profile: Agent profile
            contract: Agent contract

        Returns:
            Agent output or None on failure
        """
        try:
            from tmt_quantum_vault.ollama_api import is_available, run

            if not is_available():
                logger.debug("Ollama not available, falling back to simulation")
                return None

            # Build prompt from contract
            prompt = self._build_prompt(profile, contract)

            # Run on Ollama with local model
            response = run(
                model="qwen2.5:1.5b",  # Local mini model
                prompt=prompt,
                num_predict=512,
                temperature=0.7,
            )

            # Parse structured JSON response
            parsed_result = self._parse_llm_response(response.response)

            # Calculate resonance score based on response quality
            resonance_score = self._calculate_resonance_score(
                parsed_result, profile.phi_alignment
            )

            return AgentOutputSchema(
                task_id=contract.input.task_id,
                agent_id=profile.agent_id,
                agent_name=profile.agent_name,
                agent_role=profile.agent_role,
                result={
                    "status": "completed",
                    "backend": "ollama_local",
                    "response": response.response,
                    "parsed": parsed_result,
                },
                summary=parsed_result.get("summary", f"Processed by {profile.agent_name} via Ollama"),
                confidence=parsed_result.get("confidence", 0.82),
                resonance_score=resonance_score,
                fitness_contribution=profile.fitness * 0.1,
                status=HandoffStatus.COMPLETED,
            )

        except ImportError:
            logger.debug("Ollama API not available, falling back to simulation")
            return None
        except Exception as e:
            logger.warning(f"Ollama execution failed: {e}")
            return None

    def _parse_llm_response(self, response: str) -> dict[str, Any]:
        """Parse LLM response to extract structured fields.

        Args:
            response: Raw LLM response string

        Returns:
            Parsed result dictionary
        """
        import json
        import re

        # Try to extract JSON from response
        json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group())
                return {
                    "summary": parsed.get("summary", response[:200]),
                    "analysis": parsed.get("analysis", ""),
                    "recommendations": parsed.get("recommendations", []),
                    "confidence": float(parsed.get("confidence", 0.82)),
                    "resonance_notes": parsed.get("resonance_notes", ""),
                    "next_agent": parsed.get("next_agent"),
                }
            except (json.JSONDecodeError, ValueError):
                pass

        # Fallback: use raw response as summary
        return {
            "summary": response[:200] if len(response) > 200 else response,
            "analysis": "",
            "recommendations": [],
            "confidence": 0.75,  # Lower confidence for unstructured response
            "resonance_notes": "",
            "next_agent": None,
        }

    def _calculate_resonance_score(
        self, parsed_result: dict[str, Any], base_phi: float
    ) -> float:
        """Calculate resonance score based on response quality.

        Args:
            parsed_result: Parsed LLM response
            base_phi: Base phi alignment from agent profile

        Returns:
            Resonance score (0-1)
        """
        score = base_phi  # Start with base phi alignment

        # Boost for structured response
        if parsed_result.get("summary") and len(parsed_result["summary"]) > 10:
            score += 0.05

        if parsed_result.get("analysis") and len(parsed_result["analysis"]) > 10:
            score += 0.05

        if parsed_result.get("recommendations") and len(parsed_result["recommendations"]) > 0:
            score += 0.05

        if parsed_result.get("resonance_notes") and len(parsed_result["resonance_notes"]) > 10:
            score += 0.05

        # Boost for high confidence
        confidence = parsed_result.get("confidence", 0.75)
        if confidence >= 0.85:
            score += 0.05

        # Cap at 1.0
        return min(1.0, score)

    def _build_prompt(
        self, profile: AgentProfile, contract: AgentContract
    ) -> str:
        """Build prompt for LLM execution.

        Args:
            profile: Agent profile
            contract: Agent contract

        Returns:
            Formatted prompt string
        """
        return f"""You are {profile.agent_name}, a {profile.agent_role.value} agent.
Specialization: {profile.specialization}
Fitness: {profile.fitness:.3f}
Phi Alignment: {profile.phi_alignment:.3f}

Task: {contract.input.objective}
Context: {contract.input.context}

Respond in structured JSON format with the following fields:
{{
  "summary": "Brief summary of the response (max 100 words)",
  "analysis": "Key insights or findings",
  "recommendations": ["List of actionable recommendations"],
  "confidence": 0.85,
  "resonance_notes": "How this relates to phi-alignment",
  "next_agent": "suggested next agent role or null"
}}

Keep the response concise and focused. Provide only valid JSON."""

    def _create_error_output(
        self,
        profile: AgentProfile,
        contract: AgentContract,
        error_message: str,
        start_time: float,
    ) -> AgentOutputSchema:
        """Create an error output for failed execution.

        Args:
            profile: Agent profile
            contract: Agent contract
            error_message: Error message
            start_time: Execution start time

        Returns:
            Error agent output
        """
        return AgentOutputSchema(
            task_id=contract.input.task_id,
            agent_id=profile.agent_id,
            agent_name=profile.agent_name,
            agent_role=profile.agent_role,
            result={"status": "error", "error": error_message},
            summary=f"Error: {error_message}",
            confidence=0.0,
            resonance_score=0.0,
            fitness_contribution=0.0,
            status=HandoffStatus.FAILED,
            errors=[error_message],
            processing_time_ms=(time.time() - start_time) * 1000,
        )

    def _get_agent_id_by_role(self, role: AgentRole) -> int:
        """Get agent ID by role.

        Args:
            role: Agent role

        Returns:
            Agent ID or 0
        """
        for profile in self._profiles.values():
            if profile.agent_role == role:
                return profile.agent_id
        return 0

    def _calculate_final_confidence(self, trace: CoordinationTrace) -> float:
        """Calculate final confidence from trace.

        Args:
            trace: Coordination trace

        Returns:
            Final confidence score
        """
        if not trace.contracts:
            return 0.0

        confidences = [c.output.confidence for c in trace.contracts if c.output]

        if not confidences:
            return 0.0

        return sum(confidences) / len(confidences)

    def _update_metrics(self, trace: CoordinationTrace) -> None:
        """Update coordination metrics from trace.

        Args:
            trace: Completed coordination trace
        """
        self._metrics.tasks_completed += 1
        self._metrics.measured_at = datetime.now(UTC)
        # Note: success_rate is a computed property, no need to set it

    # =========================================================================
    # Conflict Resolution
    # =========================================================================

    def resolve_conflict(
        self,
        conflict: AgentConflict,
        strategy: ConflictResolutionStrategy | None = None,
    ) -> ConflictResolutionResult:
        """Resolve a conflict between agent outputs.

        Args:
            conflict: Agent conflict
            strategy: Resolution strategy

        Returns:
            Resolution result
        """
        strategy = strategy or self.policy.default_conflict_strategy

        if strategy == ConflictResolutionStrategy.HIGHEST_CONFIDENCE:
            return self._resolve_by_confidence(conflict)
        elif strategy == ConflictResolutionStrategy.HIGHEST_FITNESS:
            return self._resolve_by_fitness(conflict)
        elif strategy == ConflictResolutionStrategy.WEIGHTED_VOTE:
            return self._resolve_by_weighted_vote(conflict)
        elif strategy == ConflictResolutionStrategy.PHI_ALIGNMENT:
            return self._resolve_by_phi(conflict)
        else:
            return self._resolve_by_confidence(conflict)

    def _resolve_by_confidence(
        self, conflict: AgentConflict
    ) -> ConflictResolutionResult:
        """Resolve by highest confidence."""
        best = max(conflict.agent_outputs, key=lambda o: o.confidence)

        return ConflictResolutionResult(
            request_id=uuid4(),
            conflict_id=conflict.conflict_id,
            winning_output=best,
            strategy_used=ConflictResolutionStrategy.HIGHEST_CONFIDENCE,
            resolution_reason=f"Highest confidence: {best.confidence:.3f}",
            resolution_time_ms=conflict.resolution_time_ms,
            confidence_in_resolution=best.confidence,
        )

    def _resolve_by_fitness(self, conflict: AgentConflict) -> ConflictResolutionResult:
        """Resolve by highest fitness contribution."""
        best = max(conflict.agent_outputs, key=lambda o: o.fitness_contribution)

        return ConflictResolutionResult(
            request_id=uuid4(),
            conflict_id=conflict.conflict_id,
            winning_output=best,
            strategy_used=ConflictResolutionStrategy.HIGHEST_FITNESS,
            resolution_reason=(f"Highest fitness: {best.fitness_contribution:.3f}"),
            resolution_time_ms=conflict.resolution_time_ms,
            confidence_in_resolution=best.fitness_contribution,
        )

    def _resolve_by_weighted_vote(
        self, conflict: AgentConflict
    ) -> ConflictResolutionResult:
        """Resolve by weighted vote."""
        # Weight by confidence * fitness
        vote_distribution = {}
        for output in conflict.agent_outputs:
            weight = output.confidence * output.fitness_contribution
            vote_distribution[output.agent_name] = weight

        best = max(
            conflict.agent_outputs, key=lambda o: vote_distribution[o.agent_name]
        )

        return ConflictResolutionResult(
            request_id=uuid4(),
            conflict_id=conflict.conflict_id,
            winning_output=best,
            strategy_used=ConflictResolutionStrategy.WEIGHTED_VOTE,
            resolution_reason=f"Weighted vote winner: {best.agent_name}",
            resolution_time_ms=conflict.resolution_time_ms,
            confidence_in_resolution=vote_distribution[best.agent_name],
            vote_distribution=vote_distribution,
        )

    def _resolve_by_phi(self, conflict: AgentConflict) -> ConflictResolutionResult:
        """Resolve by phi alignment."""
        best = max(conflict.agent_outputs, key=lambda o: o.resonance_score)

        return ConflictResolutionResult(
            request_id=uuid4(),
            conflict_id=conflict.conflict_id,
            winning_output=best,
            strategy_used=ConflictResolutionStrategy.PHI_ALIGNMENT,
            resolution_reason=(f"Best phi alignment: {best.resonance_score:.3f}"),
            resolution_time_ms=conflict.resolution_time_ms,
            confidence_in_resolution=best.resonance_score,
        )

    # =========================================================================
    # Escalation
    # =========================================================================

    def escalate(
        self,
        reason: EscalationReason,
        current_agent: AgentRole,
        current_confidence: float,
        trace_id: UUID,
        context: dict[str, Any] | None = None,
    ) -> EscalationResult:
        """Escalate a decision.

        Args:
            reason: Escalation reason
            current_agent: Current agent
            current_confidence: Current confidence
            trace_id: Trace ID
            context: Additional context

        Returns:
            Escalation result
        """
        # Determine escalation target
        current_layer = ROLE_LAYER_MAP.get(current_agent, AgentLayer.PROCESSING)

        # Escalate to next layer
        layer_index = DEFAULT_LAYER_SEQUENCE.index(current_layer)
        if layer_index < len(DEFAULT_LAYER_SEQUENCE) - 1:
            target_layer = DEFAULT_LAYER_SEQUENCE[layer_index + 1]
        else:
            target_layer = AgentLayer.INTEGRATION  # Max escalation

        # Get target agent
        target_profiles = self._routing_engine.get_profiles_by_layer(target_layer)
        target_agent = (
            target_profiles[0].agent_role if target_profiles else AgentRole.SYNTHESIZER
        )

        return EscalationResult(
            escalation_id=uuid4(),
            escalated_to=target_agent,
            decision="review_required",
            rationale=(
                f"Escalated from {current_agent.value} " f"due to {reason.value}"
            ),
            final_confidence=current_confidence * 0.9,  # Penalty
            requires_action=True,
            action_required="Review and approve escalated decision",
        )

    # =========================================================================
    # Status and Metrics
    # =========================================================================

    def get_status(self) -> dict[str, Any]:
        """Get orchestrator status.

        Returns:
            Status dictionary
        """
        return {
            "vault_path": str(self.vault_path),
            "policy": self.policy.policy_name,
            "agents_registered": len(self._profiles),
            "active_traces": len(self._active_traces),
            "bus_stats": self._bus.get_stats(),
            "handoff_stats": self._handoff_manager.get_handoff_stats(),
            "metrics": self._metrics.model_dump(mode="json"),
        }

    def get_metrics(self) -> CoordinationMetrics:
        """Get coordination metrics.

        Returns:
            Coordination metrics
        """
        return self._metrics

    def get_agent_profiles(self) -> list[dict[str, Any]]:
        """Get all agent profiles.

        Returns:
            List of profile dictionaries
        """
        return [p.to_dict() for p in self._profiles.values()]

    def get_trace(self, trace_id: UUID) -> CoordinationTrace | None:
        """Get coordination trace by ID.

        Args:
            trace_id: Trace ID

        Returns:
            Trace or None
        """
        return self._active_traces.get(trace_id)
