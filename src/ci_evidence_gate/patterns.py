"""A small, documented subset of GitHub-style glob matching."""

from __future__ import annotations

import functools
import re

from .errors import InvalidEvaluation


@functools.lru_cache(maxsize=512)
def compile_pattern(pattern: str) -> re.Pattern[str]:
    if not pattern or pattern.startswith("/") or "\x00" in pattern:
        raise InvalidEvaluation(f"unsafe or empty path pattern: {pattern!r}")
    if pattern.startswith("!"):
        raise InvalidEvaluation("negative path patterns are not supported in v1")

    pieces: list[str] = ["^"]
    index = 0
    while index < len(pattern):
        char = pattern[index]
        if char == "*":
            if index + 1 < len(pattern) and pattern[index + 1] == "*":
                index += 2
                if index < len(pattern) and pattern[index] == "/":
                    pieces.append("(?:.*/)?")
                    index += 1
                else:
                    pieces.append(".*")
                continue
            pieces.append("[^/]*")
        elif char == "?":
            pieces.append("[^/]")
        elif char == "[":
            raise InvalidEvaluation(
                "character classes are not supported in v1 patterns"
            )
        else:
            pieces.append(re.escape(char))
        index += 1
    pieces.append("$")
    return re.compile("".join(pieces))


def matches(path: str, patterns: tuple[str, ...]) -> bool:
    return any(compile_pattern(pattern).match(path) for pattern in patterns)
