"""Custom exceptions for TMT Quantum Vault."""

from __future__ import annotations


class VaultError(Exception):
    """Base exception for all TMT Quantum Vault errors."""

    pass


class RoutingError(VaultError):
    """Raised when agent routing fails."""

    pass


class ChannelError(VaultError):
    """Raised when agent communication channel operations fail."""

    pass


class ValidationError(VaultError):
    """Raised when data validation fails."""

    pass


class ConfigurationError(VaultError):
    """Raised when configuration is invalid or missing."""

    pass


class AgentError(VaultError):
    """Raised when an agent operation fails."""

    pass


class OrchestrationError(VaultError):
    """Raised when orchestration execution fails."""

    pass
