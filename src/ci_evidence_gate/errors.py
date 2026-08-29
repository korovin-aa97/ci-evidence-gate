"""Typed, user-safe failures for CI Evidence Gate."""

from __future__ import annotations


class GateError(Exception):
    """Base class for expected evaluation failures."""


class InvalidEvaluation(GateError):
    """The gate cannot produce trustworthy evidence."""


class ApiError(InvalidEvaluation):
    """GitHub evidence could not be retrieved or authenticated."""
