"""Strict parser for ci-evidence-manifest/v1."""

from __future__ import annotations

import re
import tomllib

from .errors import InvalidEvaluation
from .models import CheckPolicy, Manifest, Surface
from .patterns import compile_pattern

MANIFEST_SCHEMA = "ci-evidence-manifest/v1"
ALLOWED_CONCLUSIONS = {"success", "neutral"}
ALLOWED_EVENTS = {"pull_request", "pull_request_target", "merge_group", "push"}
ID_RE = re.compile(r"^[a-z][a-z0-9-]{0,63}$")


def _only_keys(value: dict[str, object], allowed: set[str], context: str) -> None:
    unknown = set(value) - allowed
    if unknown:
        raise InvalidEvaluation(f"unknown {context} keys: {', '.join(sorted(unknown))}")


def _strings(value: object, context: str, *, nonempty: bool = True) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise InvalidEvaluation(f"{context} must be an array of strings")
    result = tuple(value)
    if nonempty and not result:
        raise InvalidEvaluation(f"{context} must not be empty")
    if any(not item for item in result):
        raise InvalidEvaluation(f"{context} contains an empty value")
    return result


def parse_manifest(raw: bytes) -> Manifest:
    try:
        data = tomllib.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise InvalidEvaluation(f"manifest is not valid UTF-8 TOML: {exc}") from exc
    if not isinstance(data, dict):
        raise InvalidEvaluation("manifest root must be a table")
    _only_keys(data, {"schema", "policy", "checks", "surfaces"}, "manifest")

    schema = data.get("schema")
    if schema != MANIFEST_SCHEMA:
        raise InvalidEvaluation(f"manifest schema must be {MANIFEST_SCHEMA!r}")

    policy = data.get("policy")
    if not isinstance(policy, dict):
        raise InvalidEvaluation("manifest requires a [policy] table")
    _only_keys(policy, {"max_evidence_age_hours", "protected"}, "policy")
    max_age = policy.get("max_evidence_age_hours", 24)
    if (
        not isinstance(max_age, int)
        or isinstance(max_age, bool)
        or not 1 <= max_age <= 720
    ):
        raise InvalidEvaluation(
            "policy.max_evidence_age_hours must be an integer from 1 to 720"
        )
    protected = _strings(policy.get("protected", []), "policy.protected")
    for pattern in protected:
        compile_pattern(pattern)

    raw_checks = data.get("checks")
    if not isinstance(raw_checks, list) or not raw_checks:
        raise InvalidEvaluation("manifest requires at least one [[checks]] table")
    checks: list[CheckPolicy] = []
    check_ids: set[str] = set()
    for index, item in enumerate(raw_checks):
        context = f"checks[{index}]"
        if not isinstance(item, dict):
            raise InvalidEvaluation(f"{context} must be a table")
        _only_keys(
            item,
            {
                "id",
                "name",
                "workflow",
                "app_slug",
                "allowed_conclusions",
                "events",
                "max_age_hours",
            },
            context,
        )
        check_id = item.get("id")
        name = item.get("name")
        workflow = item.get("workflow")
        app_slug = item.get("app_slug", "github-actions")
        if not isinstance(check_id, str) or not ID_RE.fullmatch(check_id):
            raise InvalidEvaluation(f"{context}.id must match {ID_RE.pattern}")
        if check_id in check_ids:
            raise InvalidEvaluation(f"duplicate check id: {check_id}")
        check_ids.add(check_id)
        if not isinstance(name, str) or not name.strip() or "\n" in name:
            raise InvalidEvaluation(f"{context}.name must be a non-empty single line")
        if (
            not isinstance(workflow, str)
            or not workflow.startswith(".github/workflows/")
            or not workflow.endswith((".yml", ".yaml"))
            or ".." in workflow.split("/")
        ):
            raise InvalidEvaluation(f"{context}.workflow must be a safe workflow path")
        if not isinstance(app_slug, str) or not app_slug:
            raise InvalidEvaluation(f"{context}.app_slug must be a string")
        conclusions = _strings(
            item.get("allowed_conclusions", ["success"]),
            f"{context}.allowed_conclusions",
        )
        if not set(conclusions) <= ALLOWED_CONCLUSIONS:
            raise InvalidEvaluation(
                f"{context}.allowed_conclusions may contain only {sorted(ALLOWED_CONCLUSIONS)}"
            )
        events = _strings(item.get("events", ["pull_request"]), f"{context}.events")
        if not set(events) <= ALLOWED_EVENTS:
            raise InvalidEvaluation(f"{context}.events contains an unsupported event")
        item_max_age = item.get("max_age_hours")
        if item_max_age is not None and (
            not isinstance(item_max_age, int)
            or isinstance(item_max_age, bool)
            or not 1 <= item_max_age <= 720
        ):
            raise InvalidEvaluation(f"{context}.max_age_hours must be from 1 to 720")
        checks.append(
            CheckPolicy(
                id=check_id,
                name=name,
                workflow=workflow,
                app_slug=app_slug,
                allowed_conclusions=conclusions,
                events=events,
                max_age_hours=item_max_age,
            )
        )

    raw_surfaces = data.get("surfaces")
    if not isinstance(raw_surfaces, list) or not raw_surfaces:
        raise InvalidEvaluation("manifest requires at least one [[surfaces]] table")
    surfaces: list[Surface] = []
    surface_names: set[str] = set()
    for index, item in enumerate(raw_surfaces):
        context = f"surfaces[{index}]"
        if not isinstance(item, dict):
            raise InvalidEvaluation(f"{context} must be a table")
        _only_keys(item, {"name", "patterns", "checks"}, context)
        name = item.get("name")
        if not isinstance(name, str) or not ID_RE.fullmatch(name):
            raise InvalidEvaluation(f"{context}.name must match {ID_RE.pattern}")
        if name in surface_names:
            raise InvalidEvaluation(f"duplicate surface name: {name}")
        surface_names.add(name)
        patterns = _strings(item.get("patterns"), f"{context}.patterns")
        required = _strings(item.get("checks"), f"{context}.checks")
        unknown = set(required) - check_ids
        if unknown:
            raise InvalidEvaluation(
                f"{context}.checks references unknown ids: {', '.join(sorted(unknown))}"
            )
        for pattern in patterns:
            compile_pattern(pattern)
        surfaces.append(Surface(name=name, patterns=patterns, checks=required))

    return Manifest(
        schema=schema,
        max_evidence_age_hours=max_age,
        protected=protected,
        checks=tuple(checks),
        surfaces=tuple(surfaces),
    )
