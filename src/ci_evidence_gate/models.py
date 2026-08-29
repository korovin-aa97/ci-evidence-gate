"""Data models shared by parsing, collection, and evaluation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChangedFile:
    status: str
    path: str
    previous_path: str | None = None

    @property
    def matching_paths(self) -> tuple[str, ...]:
        if self.previous_path and self.previous_path != self.path:
            return (self.previous_path, self.path)
        return (self.path,)


@dataclass(frozen=True)
class CheckPolicy:
    id: str
    name: str
    workflow: str
    app_slug: str
    allowed_conclusions: tuple[str, ...]
    events: tuple[str, ...]
    max_age_hours: int | None


@dataclass(frozen=True)
class Surface:
    name: str
    patterns: tuple[str, ...]
    checks: tuple[str, ...]


@dataclass(frozen=True)
class Manifest:
    schema: str
    max_evidence_age_hours: int
    protected: tuple[str, ...]
    checks: tuple[CheckPolicy, ...]
    surfaces: tuple[Surface, ...]


@dataclass(frozen=True)
class Finding:
    code: str
    message: str
    check_id: str | None = None
    path: str | None = None


@dataclass(frozen=True)
class CheckResult:
    check_id: str
    expected_name: str
    state: str
    check_run_id: int | None
    check_name: str | None
    conclusion: str | None
    completed_at: str | None
    app_slug: str | None
    app_id: int | None
    workflow_path: str | None
    workflow_run_id: int | None
    run_attempt: int | None
    event: str | None
    details_url: str | None
