"""Fail-closed policy evaluation over immutable Git and GitHub API facts."""

from __future__ import annotations

import datetime as dt
import hashlib
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .errors import InvalidEvaluation
from .git import changed_files, read_file_at, validate_commit, validate_manifest_path
from .github import EvidenceProvider, workflow_run_id
from .manifest import parse_manifest
from .models import CheckPolicy, CheckResult, Finding
from .patterns import matches

RECEIPT_SCHEMA = "ci-evidence-receipt/v1"
TOOL_VERSION = "0.1.1"


def _parse_time(value: object, context: str) -> dt.datetime:
    if not isinstance(value, str):
        raise InvalidEvaluation(f"{context} has no timestamp")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InvalidEvaluation(f"{context} has an invalid timestamp") from exc
    if parsed.tzinfo is None:
        raise InvalidEvaluation(f"{context} timestamp has no timezone")
    return parsed.astimezone(dt.UTC)


def _optional_int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _candidate_result(
    policy: CheckPolicy,
    item: dict[str, Any],
    run: dict[str, Any],
    state: str,
) -> CheckResult:
    app = item.get("app") if isinstance(item.get("app"), dict) else {}
    return CheckResult(
        check_id=policy.id,
        expected_name=policy.name,
        state=state,
        check_run_id=_optional_int(item.get("id")),
        check_name=item.get("name") if isinstance(item.get("name"), str) else None,
        conclusion=item.get("conclusion")
        if isinstance(item.get("conclusion"), str)
        else None,
        completed_at=item.get("completed_at")
        if isinstance(item.get("completed_at"), str)
        else None,
        app_slug=app.get("slug") if isinstance(app.get("slug"), str) else None,
        app_id=_optional_int(app.get("id")),
        workflow_path=run.get("path") if isinstance(run.get("path"), str) else None,
        workflow_run_id=_optional_int(run.get("id")),
        run_attempt=_optional_int(run.get("run_attempt")),
        event=run.get("event") if isinstance(run.get("event"), str) else None,
        details_url=item.get("details_url")
        if isinstance(item.get("details_url"), str)
        else None,
    )


def _missing_result(policy: CheckPolicy) -> CheckResult:
    return CheckResult(
        check_id=policy.id,
        expected_name=policy.name,
        state="missing",
        check_run_id=None,
        check_name=None,
        conclusion=None,
        completed_at=None,
        app_slug=None,
        app_id=None,
        workflow_path=None,
        workflow_run_id=None,
        run_attempt=None,
        event=None,
        details_url=None,
    )


def verify_check(
    policy: CheckPolicy,
    runs: list[dict[str, Any]],
    provider: EvidenceProvider,
    head_sha: str,
    now: dt.datetime,
    default_max_age: int,
) -> tuple[CheckResult, tuple[Finding, ...], bool]:
    same_name = [item for item in runs if item.get("name") == policy.name]
    identity_matches: list[tuple[dict[str, Any], dict[str, Any]]] = []
    workflow_cache: dict[int, dict[str, Any]] = {}
    for item in same_name:
        app = item.get("app") if isinstance(item.get("app"), dict) else {}
        if item.get("head_sha") != head_sha or app.get("slug") != policy.app_slug:
            continue
        run_id = workflow_run_id(item.get("details_url"))
        if run_id is None:
            continue
        if run_id not in workflow_cache:
            workflow_cache[run_id] = provider.workflow_run(run_id)
        run = workflow_cache[run_id]
        if (
            run.get("id") != run_id
            or run.get("head_sha") != head_sha
            or run.get("path") != policy.workflow
            or run.get("event") not in policy.events
        ):
            continue
        attempt = run.get("run_attempt")
        if not isinstance(attempt, int) or isinstance(attempt, bool) or attempt < 1:
            raise InvalidEvaluation(f"workflow run {run_id} has an invalid run_attempt")
        identity_matches.append((item, run))

    if not identity_matches:
        observed = sorted(
            {
                str((item.get("app") or {}).get("slug"))
                for item in same_name
                if isinstance(item.get("app"), dict)
            }
        )
        detail = f"; observed app slugs: {', '.join(observed)}" if observed else ""
        return (
            _missing_result(policy),
            (
                Finding(
                    code="required-check-missing",
                    message=(
                        f"No {policy.name!r} check from {policy.app_slug!r} and "
                        f"{policy.workflow!r} was found for the exact head SHA{detail}."
                    ),
                    check_id=policy.id,
                ),
            ),
            False,
        )

    highest_attempt = max(int(run["run_attempt"]) for _, run in identity_matches)
    latest = [
        (item, run)
        for item, run in identity_matches
        if run["run_attempt"] == highest_attempt
    ]
    if len(latest) != 1:
        raise InvalidEvaluation(
            f"check {policy.id!r} is ambiguous: {len(latest)} matching runs at attempt {highest_attempt}"
        )
    item, run = latest[0]
    result = _candidate_result(policy, item, run, "observed")
    findings: list[Finding] = []
    if item.get("status") != "completed":
        findings.append(
            Finding(
                code="required-check-incomplete",
                message=f"Required check {policy.name!r} is {item.get('status')!r}, not completed.",
                check_id=policy.id,
            )
        )
    if item.get("conclusion") not in policy.allowed_conclusions:
        findings.append(
            Finding(
                code="required-check-conclusion",
                message=(
                    f"Required check {policy.name!r} concluded {item.get('conclusion')!r}; "
                    f"allowed: {', '.join(policy.allowed_conclusions)}."
                ),
                check_id=policy.id,
            )
        )
    if item.get("status") != "completed":
        return result, tuple(findings), False
    completed = _parse_time(item.get("completed_at"), f"check {policy.id}")
    if completed > now + dt.timedelta(minutes=5):
        raise InvalidEvaluation(f"check {policy.id!r} completed in the future")
    max_age = policy.max_age_hours or default_max_age
    if now - completed > dt.timedelta(hours=max_age):
        findings.append(
            Finding(
                code="required-check-stale",
                message=f"Required check {policy.name!r} is older than {max_age} hours.",
                check_id=policy.id,
            )
        )
    return result, tuple(findings), not findings


def evaluate(
    *,
    workspace: Path,
    repository: str,
    base_sha: str,
    head_sha: str,
    manifest_path: str,
    provider: EvidenceProvider,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    evaluation_time = (now or dt.datetime.now(dt.UTC)).astimezone(dt.UTC)
    workspace = workspace.resolve()
    base_sha = validate_commit(workspace, base_sha, "base-sha")
    head_sha = validate_commit(workspace, head_sha, "head-sha")
    manifest_path = validate_manifest_path(manifest_path)
    raw_manifest = read_file_at(workspace, base_sha, manifest_path)
    manifest = parse_manifest(raw_manifest)
    changes = changed_files(workspace, base_sha, head_sha)
    all_paths = tuple(
        sorted({path for change in changes for path in change.matching_paths})
    )

    protected_patterns = tuple(dict.fromkeys((manifest_path, *manifest.protected)))
    protected_paths = tuple(
        path for path in all_paths if matches(path, protected_patterns)
    )
    covered_paths: set[str] = set()
    matched_surfaces: list[dict[str, Any]] = []
    required_ids: set[str] = set()
    for surface in manifest.surfaces:
        surface_paths = tuple(
            path for path in all_paths if matches(path, surface.patterns)
        )
        if surface_paths:
            covered_paths.update(surface_paths)
            required_ids.update(surface.checks)
            matched_surfaces.append(
                {
                    "name": surface.name,
                    "changed_files": list(surface_paths),
                    "required_checks": list(surface.checks),
                }
            )
    uncovered = tuple(sorted(set(all_paths) - covered_paths))

    findings: list[Finding] = []
    invalid = False
    if protected_paths:
        invalid = True
        for path in protected_paths:
            findings.append(
                Finding(
                    code="protected-policy-change",
                    message=f"Protected policy or verifier path changed: {path}",
                    path=path,
                )
            )
    for path in uncovered:
        findings.append(
            Finding(
                code="uncovered-file",
                message=f"No declared surface covers changed path: {path}",
                path=path,
            )
        )

    check_runs = provider.check_runs(head_sha)
    check_policies = {item.id: item for item in manifest.checks}
    check_results: list[CheckResult] = []
    all_checks_passed = True
    for check_id in sorted(required_ids):
        result, check_findings, passed = verify_check(
            check_policies[check_id],
            check_runs,
            provider,
            head_sha,
            evaluation_time,
            manifest.max_evidence_age_hours,
        )
        check_results.append(result)
        findings.extend(check_findings)
        all_checks_passed = all_checks_passed and passed

    if invalid:
        verdict = "invalid"
    elif uncovered or not all_checks_passed:
        verdict = "insufficient"
    else:
        verdict = "sufficient"

    return {
        "schema": RECEIPT_SCHEMA,
        "tool": {"name": "ci-evidence-gate", "version": TOOL_VERSION},
        "evaluated_at": evaluation_time.isoformat().replace("+00:00", "Z"),
        "repository": repository,
        "subject": {"base_sha": base_sha, "head_sha": head_sha},
        "policy": {
            "schema": manifest.schema,
            "source_ref": base_sha,
            "path": manifest_path,
            "sha256": hashlib.sha256(raw_manifest).hexdigest(),
            "protected_patterns": list(protected_patterns),
        },
        "changed_files": [asdict(item) for item in changes],
        "matched_surfaces": matched_surfaces,
        "required_checks": sorted(required_ids),
        "check_evidence": [asdict(item) for item in check_results],
        "uncovered_files": list(uncovered),
        "protected_changes": list(protected_paths),
        "findings": [asdict(item) for item in findings],
        "verdict": verdict,
    }
