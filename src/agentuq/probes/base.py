"""Probe protocol definitions."""

from __future__ import annotations

from typing import Protocol


class CapabilityProbe(Protocol):
    def probe(self, model: str, **kwargs: object) -> dict:
        ...

