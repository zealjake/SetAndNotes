from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Role = Literal["main", "tc", "ambiguous", "unknown"]

_ROLE_TOKEN_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("main", re.compile(r"(?<![a-z0-9])track(?![a-z0-9])", re.IGNORECASE)),
    ("main", re.compile(r"(?<![a-z0-9])foh(?![a-z0-9])", re.IGNORECASE)),
    ("main", re.compile(r"(?<![a-z0-9])master(?![a-z0-9])", re.IGNORECASE)),
    ("main", re.compile(r"(?<![a-z0-9])l[\s._-]*r(?![a-z0-9])", re.IGNORECASE)),
    ("tc", re.compile(r"(?<![a-z0-9])tc(?![a-z0-9])", re.IGNORECASE)),
    ("tc", re.compile(r"(?<![a-z0-9])timecode(?![a-z0-9])", re.IGNORECASE)),
    ("tc", re.compile(r"(?<![a-z0-9])smpte(?![a-z0-9])", re.IGNORECASE)),
]


@dataclass(frozen=True, slots=True)
class ClassifiedMediaFile:
    role: Role
    normalized_name: str
    source_name: str
    matched_tokens: tuple[str, ...] = ()


def normalize_media_name(value: str) -> str:
    stem = Path(value).stem.lower()
    for _, pattern in _ROLE_TOKEN_PATTERNS:
        stem = pattern.sub(" ", stem)
    tokens = re.findall(r"[a-z0-9]+", stem)
    return "_".join(tokens)


def classify_media_file(value: str) -> ClassifiedMediaFile:
    lowered = Path(value).stem.lower()
    matched_main: list[str] = []
    matched_tc: list[str] = []

    for role, pattern in _ROLE_TOKEN_PATTERNS:
        if pattern.search(lowered):
            token = pattern.pattern
            if role == "main":
                matched_main.append(token)
            else:
                matched_tc.append(token)

    if matched_main and matched_tc:
        role: Role = "ambiguous"
    elif matched_main:
        role = "main"
    elif matched_tc:
        role = "tc"
    else:
        role = "unknown"

    normalized_name = normalize_media_name(value)
    return ClassifiedMediaFile(
        role=role,
        normalized_name=normalized_name,
        source_name=value,
        matched_tokens=tuple(matched_main + matched_tc),
    )
