from __future__ import annotations

import re
import secrets
import socket
from typing import Any


def slugify_web_note_username(username: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", username.strip().lower())
    slug = slug.strip("-")
    return slug or "user"


def _unique_slug(base_slug: str, used_slugs: set[str]) -> str:
    if base_slug not in used_slugs:
        return base_slug
    index = 2
    while f"{base_slug}-{index}" in used_slugs:
        index += 1
    return f"{base_slug}-{index}"


def create_web_note_user(username: str, existing_slugs: set[str] | None = None) -> dict[str, Any]:
    used_slugs = set(existing_slugs or set())
    slug = _unique_slug(slugify_web_note_username(username), used_slugs)
    return {
        "username": username.strip(),
        "token": secrets.token_urlsafe(18),
        "slug": slug,
        "enabled": True,
    }


def ensure_web_note_user_token(user: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(user)
    if not normalized.get("token"):
        normalized["token"] = secrets.token_urlsafe(18)
    normalized["username"] = str(normalized.get("username", "")).strip()
    normalized["enabled"] = bool(normalized.get("enabled", True))
    if not normalized.get("slug"):
        normalized["slug"] = slugify_web_note_username(normalized["username"])
    return normalized


def normalize_web_note_users(users: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized_users: list[dict[str, Any]] = []
    used_slugs: set[str] = set()
    for user in users:
        normalized = ensure_web_note_user_token(user)
        preferred_slug = str(normalized.get("slug", "")).strip()
        if not preferred_slug or preferred_slug == slugify_web_note_username(str(user.get("username", ""))):
            preferred_slug = slugify_web_note_username(normalized["username"])
        normalized["slug"] = _unique_slug(preferred_slug, used_slugs)
        used_slugs.add(normalized["slug"])
        normalized_users.append(normalized)
    return normalized_users


def set_web_note_user_enabled(user: dict[str, Any], enabled: bool) -> dict[str, Any]:
    normalized = dict(user)
    normalized["enabled"] = bool(enabled)
    return normalized


def build_web_note_url(host: str, port: int, slug: str) -> str:
    return f"http://{host}:{port}/notes/u/{slug}"


def build_copy_all_web_note_links_text(users: list[dict[str, Any]], *, host: str, port: int) -> str:
    blocks: list[str] = []
    for user in users:
        username = str(user.get("username", "")).strip()
        slug = str(user.get("slug", "")).strip()
        if not username or not slug:
            continue
        blocks.append(f"{username}\n{build_web_note_url(host, port, slug)}")
    return "\n\n".join(blocks)


def detect_web_note_host() -> str:
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("8.8.8.8", 80))
        host = probe.getsockname()[0]
    except OSError:
        host = "127.0.0.1"
    finally:
        probe.close()
    return host
