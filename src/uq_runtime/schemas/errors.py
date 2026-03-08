"""Public error types for capability and runtime mismatches."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class AgentUQError(Exception):
    """Base error carrying actionable metadata."""

    message: str
    provider: str | None = None
    transport: str | None = None
    model: str | None = None
    requested_params: dict[str, Any] | None = None
    observed_capability: dict[str, Any] | None = None
    remediation: str | None = None

    def __str__(self) -> str:
        detail = [self.message]
        if self.provider or self.model:
            detail.append(
                f"provider={self.provider or 'unknown'} transport={self.transport or 'unknown'} model={self.model or 'unknown'}"
            )
        if self.requested_params:
            detail.append(f"requested={self.requested_params}")
        if self.observed_capability:
            detail.append(f"observed={self.observed_capability}")
        if self.remediation:
            detail.append(f"remediation={self.remediation}")
        return " | ".join(detail)


class LogprobsNotRequestedError(AgentUQError):
    pass


class SelectedTokenLogprobsUnavailableError(AgentUQError):
    pass


class TopKLogprobsUnavailableError(AgentUQError):
    pass


class ProviderDroppedRequestedParameterError(AgentUQError):
    pass


class ModelCapabilityUnknownProbeRequired(AgentUQError):
    pass


class UnsupportedForCanonicalModeError(AgentUQError):
    pass


class CapabilityProbeFailedError(AgentUQError):
    pass

