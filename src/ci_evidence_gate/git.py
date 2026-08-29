"""Read immutable policy and changed paths from the local Git object database."""

from __future__ import annotations

import os
import re
import shutil

# Git is invoked without a shell and only with validated refs/paths.
import subprocess  # nosec B404
from pathlib import Path

from .errors import InvalidEvaluation
from .models import ChangedFile

FULL_SHA_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")


def _git(workspace: Path, *arguments: str, text: bool = True) -> str | bytes:
    environment = os.environ.copy()
    # Repository-local configuration is needed for ordinary Git operation, but
    # machine-global includes must not make the verdict host-dependent.
    environment["GIT_CONFIG_NOSYSTEM"] = "1"
    environment["GIT_CONFIG_GLOBAL"] = os.devnull
    executable = shutil.which("git")
    if not executable:
        raise InvalidEvaluation("git executable was not found on PATH")
    try:
        # No shell is used; every ref/path supplied by the caller is validated.
        result = subprocess.run(  # nosec B603
            [executable, *arguments],
            cwd=workspace,
            check=True,
            capture_output=True,
            text=text,
            env=environment,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = ""
        if isinstance(exc, subprocess.CalledProcessError) and exc.stderr:
            detail = (
                exc.stderr
                if isinstance(exc.stderr, str)
                else exc.stderr.decode("utf-8", "replace")
            )
        raise InvalidEvaluation(f"git command failed: {detail.strip() or exc}") from exc
    return result.stdout


def validate_commit(workspace: Path, sha: str, label: str) -> str:
    if not FULL_SHA_RE.fullmatch(sha):
        raise InvalidEvaluation(
            f"{label} must be a full lowercase hexadecimal commit SHA"
        )
    resolved = str(
        _git(workspace, "rev-parse", "--verify", f"{sha}^{{commit}}")
    ).strip()
    if resolved != sha:
        raise InvalidEvaluation(
            f"{label} resolved to {resolved}, not the requested exact SHA"
        )
    return resolved


def validate_manifest_path(path: str) -> str:
    candidate = Path(path)
    if (
        not path
        or candidate.is_absolute()
        or ".." in candidate.parts
        or "\x00" in path
        or "\\" in path
    ):
        raise InvalidEvaluation(
            "manifest path must be a safe repository-relative POSIX path"
        )
    return candidate.as_posix()


def read_file_at(workspace: Path, ref: str, path: str) -> bytes:
    path = validate_manifest_path(path)
    output = _git(workspace, "show", f"{ref}:{path}", text=False)
    if not isinstance(output, bytes):
        raise InvalidEvaluation("git returned text while reading manifest bytes")
    return output


def changed_files(
    workspace: Path, base_sha: str, head_sha: str
) -> tuple[ChangedFile, ...]:
    output = _git(
        workspace,
        "diff",
        "--name-status",
        "-z",
        "--find-renames",
        f"{base_sha}...{head_sha}",
        text=False,
    )
    if not isinstance(output, bytes):
        raise InvalidEvaluation("git returned text for a binary name-status request")
    fields = output.split(b"\0")
    if fields and fields[-1] == b"":
        fields.pop()
    result: list[ChangedFile] = []
    index = 0
    while index < len(fields):
        status = fields[index].decode("ascii", "strict")
        index += 1
        kind = status[:1]
        if kind in {"R", "C"}:
            if index + 1 >= len(fields):
                raise InvalidEvaluation("git returned a truncated rename/copy record")
            previous = fields[index].decode("utf-8", "surrogateescape")
            path = fields[index + 1].decode("utf-8", "surrogateescape")
            index += 2
            result.append(ChangedFile(status=status, path=path, previous_path=previous))
        else:
            if index >= len(fields):
                raise InvalidEvaluation("git returned a truncated changed-file record")
            path = fields[index].decode("utf-8", "surrogateescape")
            index += 1
            result.append(ChangedFile(status=status, path=path))
    return tuple(result)
