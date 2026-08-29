"""Read-only GitHub REST evidence collection."""

from __future__ import annotations

import json
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Protocol

from .errors import ApiError, InvalidEvaluation

RUN_JOB_URL_RE = re.compile(
    r"/actions/runs/(?P<run_id>[0-9]+)/job/(?P<job_id>[0-9]+)(?:$|[/?#])"
)
CHECK_RUN_URL_RE = re.compile(r"/check-runs/(?P<check_run_id>[0-9]+)(?:$|[/?#])")
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
MAX_RESPONSE_BYTES = 10 * 1024 * 1024


class EvidenceProvider(Protocol):
    def check_runs(self, head_sha: str) -> list[dict[str, Any]]: ...
    def workflow_run(self, run_id: int) -> dict[str, Any]: ...
    def workflow_job(self, job_id: int) -> dict[str, Any]: ...


def _origin(url: str) -> tuple[str, str, int]:
    parsed = urllib.parse.urlparse(url)
    try:
        port = parsed.port or 443
    except ValueError as exc:
        raise InvalidEvaluation("api-url contains an invalid port") from exc
    return parsed.scheme.lower(), (parsed.hostname or "").lower(), port


class _SameOriginRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Follow GitHub redirects without forwarding the token to another origin."""

    def __init__(self, allowed_origin: tuple[str, str, int]) -> None:
        super().__init__()
        self.allowed_origin = allowed_origin

    def redirect_request(
        self,
        request: urllib.request.Request,
        response: Any,
        code: int,
        message: str,
        headers: Any,
        new_url: str,
    ) -> urllib.request.Request | None:
        redirected = super().redirect_request(
            request, response, code, message, headers, new_url
        )
        if (
            redirected is not None
            and _origin(redirected.full_url) != self.allowed_origin
        ):
            raise urllib.error.HTTPError(
                redirected.full_url,
                code,
                "cross-origin API redirect rejected",
                headers,
                response,
            )
        return redirected


@dataclass
class GitHubClient:
    repository: str
    token: str
    api_url: str = "https://api.github.com"
    api_version: str = "2022-11-28"
    timeout_seconds: int = 20
    _opener: urllib.request.OpenerDirector = field(init=False, repr=False)
    _workflow_run_cache: dict[int, dict[str, Any]] = field(
        init=False, default_factory=dict, repr=False
    )
    _workflow_job_cache: dict[int, dict[str, Any]] = field(
        init=False, default_factory=dict, repr=False
    )

    def __post_init__(self) -> None:
        if not REPOSITORY_RE.fullmatch(self.repository):
            raise InvalidEvaluation("repository must be OWNER/NAME")
        parsed = urllib.parse.urlparse(self.api_url)
        if (
            parsed.scheme != "https"
            or not parsed.netloc
            or parsed.username
            or parsed.password
            or parsed.params
            or parsed.query
            or parsed.fragment
        ):
            raise InvalidEvaluation(
                "api-url must be an HTTPS API base URL without credentials, query, or fragment"
            )
        origin = _origin(self.api_url)
        self.api_url = self.api_url.rstrip("/")
        if not self.token:
            raise InvalidEvaluation(
                "a token with actions:read and checks:read is required"
            )
        self._opener = urllib.request.build_opener(
            _SameOriginRedirectHandler(origin),
            urllib.request.HTTPSHandler(context=ssl.create_default_context()),
        )

    def _get(self, path: str, query: dict[str, str] | None = None) -> dict[str, Any]:
        url = f"{self.api_url}{path}"
        if query:
            url += "?" + urllib.parse.urlencode(query)
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "User-Agent": "ci-evidence-gate/0.1.3",
                "X-GitHub-Api-Version": self.api_version,
            },
        )
        try:
            # api_url is validated as a credential-free HTTPS origin above.
            with self._opener.open(  # nosec B310
                request,
                timeout=self.timeout_seconds,
            ) as response:
                payload = response.read(MAX_RESPONSE_BYTES + 1)
                if len(payload) > MAX_RESPONSE_BYTES:
                    raise ApiError(
                        f"GitHub API response exceeded {MAX_RESPONSE_BYTES} bytes for {path}"
                    )
        except urllib.error.HTTPError as exc:
            body = exc.read(512).decode("utf-8", "replace")
            rate_limit = ""
            remaining = exc.headers.get("X-RateLimit-Remaining")
            retry_after = exc.headers.get("Retry-After")
            reset = exc.headers.get("X-RateLimit-Reset")
            if exc.code in {403, 429} and (remaining == "0" or retry_after):
                hints = []
                if retry_after:
                    hints.append(f"retry-after={retry_after}s")
                if reset:
                    hints.append(f"reset={reset}")
                rate_limit = "; rate limit exceeded"
                if hints:
                    rate_limit += " (" + ", ".join(hints) + ")"
            raise ApiError(
                f"GitHub API returned HTTP {exc.code} for {path}{rate_limit}: {body}"
            ) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ApiError(f"GitHub API request failed for {path}: {exc}") from exc
        try:
            value = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ApiError(f"GitHub API returned invalid JSON for {path}") from exc
        if not isinstance(value, dict):
            raise ApiError(f"GitHub API returned an unexpected payload for {path}")
        return value

    def check_runs(self, head_sha: str) -> list[dict[str, Any]]:
        owner, repository = (
            urllib.parse.quote(part, safe="") for part in self.repository.split("/", 1)
        )
        encoded_sha = urllib.parse.quote(head_sha, safe="")
        collected: list[dict[str, Any]] = []
        for page in range(1, 11):
            payload = self._get(
                f"/repos/{owner}/{repository}/commits/{encoded_sha}/check-runs",
                {"filter": "all", "per_page": "100", "page": str(page)},
            )
            items = payload.get("check_runs")
            if not isinstance(items, list) or not all(
                isinstance(item, dict) for item in items
            ):
                raise ApiError("check-runs response is missing check_runs[]")
            collected.extend(items)
            if len(items) < 100:
                return collected
        raise ApiError(
            "more than 1000 check runs matched the commit; narrow the CI configuration"
        )

    def workflow_run(self, run_id: int) -> dict[str, Any]:
        owner, repository = (
            urllib.parse.quote(part, safe="") for part in self.repository.split("/", 1)
        )
        if run_id not in self._workflow_run_cache:
            self._workflow_run_cache[run_id] = self._get(
                f"/repos/{owner}/{repository}/actions/runs/{run_id}"
            )
        return self._workflow_run_cache[run_id]

    def workflow_job(self, job_id: int) -> dict[str, Any]:
        owner, repository = (
            urllib.parse.quote(part, safe="") for part in self.repository.split("/", 1)
        )
        if job_id not in self._workflow_job_cache:
            self._workflow_job_cache[job_id] = self._get(
                f"/repos/{owner}/{repository}/actions/jobs/{job_id}"
            )
        return self._workflow_job_cache[job_id]


@dataclass
class FixtureProvider:
    """Offline evidence used only by tests and the local demo."""

    payload: dict[str, Any]

    def __post_init__(self) -> None:
        if self.payload.get("schema") != "ci-evidence-fixture/v1":
            raise InvalidEvaluation("fixture schema must be ci-evidence-fixture/v1")

    def check_runs(self, head_sha: str) -> list[dict[str, Any]]:
        items = self.payload.get("check_runs")
        if not isinstance(items, list) or not all(
            isinstance(item, dict) for item in items
        ):
            raise InvalidEvaluation("fixture check_runs must be an array of objects")
        return list(items)

    def workflow_run(self, run_id: int) -> dict[str, Any]:
        runs = self.payload.get("workflow_runs")
        if not isinstance(runs, dict):
            raise InvalidEvaluation("fixture workflow_runs must be an object")
        result = runs.get(str(run_id))
        if not isinstance(result, dict):
            raise InvalidEvaluation(f"fixture has no workflow run {run_id}")
        return result

    def workflow_job(self, job_id: int) -> dict[str, Any]:
        jobs = self.payload.get("workflow_jobs")
        if not isinstance(jobs, dict):
            raise InvalidEvaluation("fixture workflow_jobs must be an object")
        result = jobs.get(str(job_id))
        if not isinstance(result, dict):
            raise InvalidEvaluation(f"fixture has no workflow job {job_id}")
        return result


def workflow_job_reference(details_url: object) -> tuple[int, int] | None:
    if not isinstance(details_url, str):
        return None
    match = RUN_JOB_URL_RE.search(details_url)
    if not match:
        return None
    return int(match.group("run_id")), int(match.group("job_id"))


def workflow_run_id(details_url: object) -> int | None:
    reference = workflow_job_reference(details_url)
    return reference[0] if reference else None


def check_run_id(check_run_url: object) -> int | None:
    if not isinstance(check_run_url, str):
        return None
    match = CHECK_RUN_URL_RE.search(check_run_url)
    return int(match.group("check_run_id")) if match else None
