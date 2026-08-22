"""
Agent Communication Channel for Inter-Agent Messaging.

This module implements the communication bus that enables agents to
exchange messages, coordinate tasks, and maintain communication state.

Key Components:
- AgentChannel: Communication bus for message routing
- ChannelRegistry: Registry of active agent channels
- MessageQueue: Priority-based message queue with TTL
"""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from .models import (
    AgentChannelStats,
    AgentMessage,
    AgentRole,
    MessagePriority,
)

logger = logging.getLogger(__name__)


class MessageQueue:
    """Priority-based message queue with TTL support."""

    def __init__(self, max_size: int = 1000):
        """Initialize message queue.

        Args:
            max_size: Maximum queue size before dropping lowest priority
        """
        self._queue: list[AgentMessage] = []
        self._max_size = max_size
        self._lock = threading.Lock()

        # Priority ordering (higher value = higher priority)
        self._priority_order = {
            MessagePriority.CRITICAL: 4,
            MessagePriority.HIGH: 3,
            MessagePriority.NORMAL: 2,
            MessagePriority.LOW: 1,
        }

    def enqueue(self, message: AgentMessage) -> bool:
        """Add message to queue.

        Args:
            message: Message to enqueue

        Returns:
            True if enqueued, False if dropped
        """
        with self._lock:
            # Check TTL
            if self._is_expired(message):
                return False

            # Insert in priority order
            inserted = False
            for i, existing in enumerate(self._queue):
                if self._compare_priority(message, existing) > 0:
                    self._queue.insert(i, message)
                    inserted = True
                    break

            if not inserted:
                self._queue.append(message)

            # Enforce max size
            if len(self._queue) > self._max_size:
                self._queue.pop()  # Remove lowest priority

            return True

    def dequeue(self) -> AgentMessage | None:
        """Get next message from queue.

        Returns:
            Next message or None if empty
        """
        with self._lock:
            # Remove expired messages
            self._queue = [m for m in self._queue if not self._is_expired(m)]

            if self._queue:
                return self._queue.pop(0)
            return None

    def peek(self) -> AgentMessage | None:
        """Peek at next message without removing.

        Returns:
            Next message or None if empty
        """
        with self._lock:
            if self._queue:
                return self._queue[0]
            return None

    def size(self) -> int:
        """Get current queue size."""
        with self._lock:
            return len(self._queue)

    def clear(self) -> int:
        """Clear all messages from queue.

        Returns:
            Number of messages cleared
        """
        with self._lock:
            count = len(self._queue)
            self._queue.clear()
            return count

    def _is_expired(self, message: AgentMessage) -> bool:
        """Check if message has expired."""
        expiry = message.timestamp + timedelta(seconds=message.ttl_seconds)
        return datetime.now(UTC) > expiry

    def _compare_priority(self, a: AgentMessage, b: AgentMessage) -> int:
        """Compare message priorities.

        Returns:
            Positive if a > b, negative if a < b, 0 if equal
        """
        return self._priority_order[a.priority] - self._priority_order[b.priority]


class AgentChannel:
    """Communication channel for a single agent."""

    def __init__(
        self,
        agent_id: int,
        agent_name: str,
        agent_role: AgentRole,
        max_queue_size: int = 100,
    ):
        """Initialize agent channel.

        Args:
            agent_id: Unique agent identifier
            agent_name: Human-readable agent name
            agent_role: Agent's functional role
            max_queue_size: Maximum messages in queue
        """
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.agent_role = agent_role

        self._inbox = MessageQueue(max_size=max_queue_size)
        self._outbox: list[AgentMessage] = []
        self._pending_responses: dict[UUID, AgentMessage] = {}

        # Statistics
        self._stats = AgentChannelStats(
            agent_id=agent_id,
            agent_name=agent_name,
        )

        # Callbacks
        self._message_handlers: dict[str, Callable[[AgentMessage], None]] = {}
        self._lock = threading.Lock()

    # =========================================================================
    # Message Sending
    # =========================================================================

    def send(
        self,
        recipient: AgentRole | None,
        message_type: str,
        payload: dict[str, Any],
        *,
        priority: MessagePriority = MessagePriority.NORMAL,
        requires_response: bool = False,
        response_deadline_seconds: float | None = None,
        trace_id: UUID | None = None,
        correlation_id: UUID | None = None,
    ) -> AgentMessage:
        """Create and queue a message for sending.

        Args:
            recipient: Target agent role (None for broadcast)
            message_type: Type of message
            payload: Message content
            priority: Message priority
            requires_response: Whether response is required
            response_deadline_seconds: Deadline for response
            trace_id: Trace ID for correlation
            correlation_id: Correlation ID for request-response matching

        Returns:
            Created message
        """
        message = AgentMessage(
            sender_agent=self.agent_role,
            sender_id=self.agent_id,
            recipient_agent=recipient,
            message_type=message_type,
            payload=payload,
            priority=priority,
            requires_response=requires_response,
            response_deadline=(
                datetime.now(UTC) + timedelta(seconds=response_deadline_seconds)
                if response_deadline_seconds
                else None
            ),
            trace_id=trace_id or uuid4(),
            correlation_id=correlation_id,
        )

        with self._lock:
            self._outbox.append(message)
            self._stats.messages_sent += 1

            if requires_response:
                self._pending_responses[message.message_id] = message

        return message

    def broadcast(
        self,
        message_type: str,
        payload: dict[str, Any],
        *,
        priority: MessagePriority = MessagePriority.NORMAL,
        trace_id: UUID | None = None,
    ) -> AgentMessage:
        """Broadcast message to all agents.

        Args:
            message_type: Type of message
            payload: Message content
            priority: Message priority
            trace_id: Trace ID for correlation

        Returns:
            Created broadcast message
        """
        return self.send(
            recipient=None,
            message_type=message_type,
            payload=payload,
            priority=priority,
            trace_id=trace_id,
        )

    def respond(
        self,
        original_message: AgentMessage,
        payload: dict[str, Any],
        *,
        priority: MessagePriority | None = None,
    ) -> AgentMessage:
        """Respond to a received message.

        Args:
            original_message: Message to respond to
            payload: Response content
            priority: Response priority (defaults to original priority)

        Returns:
            Response message
        """
        return self.send(
            recipient=original_message.sender_agent,
            message_type="response",
            payload=payload,
            priority=priority or original_message.priority,
            trace_id=original_message.trace_id,
            correlation_id=original_message.message_id,
        )

    # =========================================================================
    # Message Receiving
    # =========================================================================

    def receive(self) -> AgentMessage | None:
        """Get next message from inbox.

        Returns:
            Next message or None if empty
        """
        message = self._inbox.dequeue()
        if message:
            with self._lock:
                self._stats.messages_received += 1
            self._handle_message(message)
        return message

    def deliver(self, message: AgentMessage) -> bool:
        """Deliver message to this channel's inbox.

        Args:
            message: Message to deliver

        Returns:
            True if delivered, False if rejected
        """
        # Check if message is for this agent
        if message.recipient_agent and message.recipient_agent != self.agent_role:
            return False

        result = self._inbox.enqueue(message)
        if result:
            with self._lock:
                self._stats.messages_pending = self._inbox.size()
        return result

    def _handle_message(self, message: AgentMessage) -> None:
        """Handle received message."""
        handler = self._message_handlers.get(message.message_type)
        if handler:
            try:
                handler(message)
            except Exception as e:
                logger.error(
                    f"Handler error for message type {message.message_type}: {e}"
                )

    # =========================================================================
    # Handler Registration
    # =========================================================================

    def on_message(
        self,
        message_type: str,
        handler: Callable[[AgentMessage], None],
    ) -> None:
        """Register handler for message type.

        Args:
            message_type: Message type to handle
            handler: Handler function
        """
        self._message_handlers[message_type] = handler

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> AgentChannelStats:
        """Get channel statistics."""
        with self._lock:
            self._stats.messages_pending = self._inbox.size()
            return self._stats.model_copy()

    def record_success(
        self,
        confidence: float,
        resonance: float,
        processing_time_ms: float,
    ) -> None:
        """Record successful processing."""
        with self._lock:
            self._stats.total_processing_time_ms += processing_time_ms

            # Update rolling averages
            n = self._stats.messages_received
            if n > 0:
                self._stats.average_confidence = (
                    self._stats.average_confidence * (n - 1) + confidence
                ) / n
                self._stats.average_resonance = (
                    self._stats.average_resonance * (n - 1) + resonance
                ) / n
                self._stats.average_response_time_ms = (
                    self._stats.total_processing_time_ms / n
                )

            # Update success rate
            total = self._stats.messages_received
            if total > 0:
                self._stats.success_rate = (
                    self._stats.success_rate * (total - 1) + 1.0
                ) / total

    def record_error(self) -> None:
        """Record processing error."""
        with self._lock:
            total = self._stats.messages_received
            if total > 0:
                self._stats.error_rate = (self._stats.error_rate * (total - 1)) / total

    # =========================================================================
    # Pending Responses
    # =========================================================================

    def check_pending_responses(self) -> list[AgentMessage]:
        """Check for timed-out pending responses.

        Returns:
            List of timed-out messages
        """
        timed_out = []
        with self._lock:
            expired_ids = []
            for msg_id, msg in self._pending_responses.items():
                if msg.response_deadline and datetime.now(UTC) > msg.response_deadline:
                    timed_out.append(msg)
                    expired_ids.append(msg_id)

            for msg_id in expired_ids:
                del self._pending_responses[msg_id]

        return timed_out

    def clear_outbox(self) -> list[AgentMessage]:
        """Clear and return all outbox messages.

        Returns:
            List of messages to send
        """
        with self._lock:
            messages = self._outbox.copy()
            self._outbox.clear()
            return messages


class ChannelRegistry:
    """Registry of active agent channels."""

    def __init__(self):
        """Initialize channel registry."""
        self._channels: dict[int, AgentChannel] = {}
        self._role_index: dict[AgentRole, list[int]] = defaultdict(list)
        self._lock = threading.Lock()

    def register(self, channel: AgentChannel) -> None:
        """Register an agent channel.

        Args:
            channel: Channel to register
        """
        with self._lock:
            self._channels[channel.agent_id] = channel
            if channel.agent_id not in self._role_index[channel.agent_role]:
                self._role_index[channel.agent_role].append(channel.agent_id)

    def unregister(self, agent_id: int) -> AgentChannel | None:
        """Unregister an agent channel.

        Args:
            agent_id: ID of channel to unregister

        Returns:
            Unregistered channel or None
        """
        with self._lock:
            channel = self._channels.pop(agent_id, None)
            if channel:
                self._role_index[channel.agent_role].remove(agent_id)
            return channel

    def get(self, agent_id: int) -> AgentChannel | None:
        """Get channel by agent ID.

        Args:
            agent_id: Agent ID

        Returns:
            Channel or None
        """
        return self._channels.get(agent_id)

    def get_by_role(self, role: AgentRole) -> list[AgentChannel]:
        """Get all channels for a role.

        Args:
            role: Agent role

        Returns:
            List of channels
        """
        with self._lock:
            agent_ids = self._role_index.get(role, [])
            return [self._channels[aid] for aid in agent_ids if aid in self._channels]

    def get_all(self) -> list[AgentChannel]:
        """Get all registered channels.

        Returns:
            List of all channels
        """
        return list(self._channels.values())

    def broadcast(
        self,
        message: AgentMessage,
        exclude_sender: bool = True,
    ) -> int:
        """Broadcast message to all channels.

        Args:
            message: Message to broadcast
            exclude_sender: Whether to exclude sender

        Returns:
            Number of channels delivered to
        """
        delivered = 0
        for channel in self.get_all():
            if exclude_sender and channel.agent_id == message.sender_id:
                continue
            if channel.deliver(message):
                delivered += 1
        return delivered

    def route_to_role(self, message: AgentMessage, role: AgentRole) -> int:
        """Route message to all agents with a specific role.

        Args:
            message: Message to route
            role: Target role

        Returns:
            Number of channels delivered to
        """
        delivered = 0
        for channel in self.get_by_role(role):
            if channel.deliver(message):
                delivered += 1
        return delivered

    def get_aggregate_stats(self) -> dict[str, Any]:
        """Get aggregate statistics across all channels.

        Returns:
            Aggregate statistics
        """
        all_stats = [ch.get_stats() for ch in self.get_all()]

        if not all_stats:
            return {
                "total_agents": 0,
                "total_messages_sent": 0,
                "total_messages_received": 0,
                "total_pending": 0,
                "average_success_rate": 0.0,
                "average_confidence": 0.0,
                "average_resonance": 0.0,
            }

        return {
            "total_agents": len(all_stats),
            "total_messages_sent": sum(s.messages_sent for s in all_stats),
            "total_messages_received": sum(s.messages_received for s in all_stats),
            "total_pending": sum(s.messages_pending for s in all_stats),
            "average_success_rate": sum(s.success_rate for s in all_stats)
            / len(all_stats),
            "average_confidence": sum(s.average_confidence for s in all_stats)
            / len(all_stats),
            "average_resonance": sum(s.average_resonance for s in all_stats)
            / len(all_stats),
        }


class AgentBus:
    """Central communication bus for all agent channels."""

    def __init__(self, registry: ChannelRegistry | None = None):
        """Initialize agent bus.

        Args:
            registry: Channel registry (created if not provided)
        """
        self._registry = registry or ChannelRegistry()
        self._message_log: list[AgentMessage] = []
        self._max_log_size = 10000
        self._lock = threading.Lock()

    @property
    def registry(self) -> ChannelRegistry:
        """Get channel registry."""
        return self._registry

    def register_channel(self, channel: AgentChannel) -> None:
        """Register a channel with the bus."""
        self._registry.register(channel)

    def send(self, message: AgentMessage) -> int:
        """Send message through the bus.

        Args:
            message: Message to send

        Returns:
            Number of recipients
        """
        # Log message
        with self._lock:
            self._message_log.append(message)
            if len(self._message_log) > self._max_log_size:
                self._message_log = self._message_log[-self._max_log_size :]

        # Route message
        if message.recipient_agent:
            return self._registry.route_to_role(message, message.recipient_agent)
        else:
            return self._registry.broadcast(message)

    def process_outboxes(self) -> int:
        """Process all channel outboxes and route messages.

        Returns:
            Total messages processed
        """
        total_processed = 0
        for channel in self._registry.get_all():
            messages = channel.clear_outbox()
            for message in messages:
                self.send(message)
                total_processed += 1
        return total_processed

    def get_message_log(
        self,
        trace_id: UUID | None = None,
        sender_role: AgentRole | None = None,
        message_type: str | None = None,
        limit: int = 100,
    ) -> list[AgentMessage]:
        """Get filtered message log.

        Args:
            trace_id: Filter by trace ID
            sender_role: Filter by sender role
            message_type: Filter by message type
            limit: Maximum messages to return

        Returns:
            Filtered message log
        """
        with self._lock:
            messages = self._message_log.copy()

        if trace_id:
            messages = [m for m in messages if m.trace_id == trace_id]
        if sender_role:
            messages = [m for m in messages if m.sender_agent == sender_role]
        if message_type:
            messages = [m for m in messages if m.message_type == message_type]

        return messages[-limit:]

    def get_stats(self) -> dict[str, Any]:
        """Get bus statistics."""
        return {
            "registry": self._registry.get_aggregate_stats(),
            "message_log_size": len(self._message_log),
        }
