from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from .defaults import DEFAULT_MARY_PROFILE, MARY_PROFILE_VERSION


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _merge_dict(base: dict[str, Any], incoming: Any) -> dict[str, Any]:
    result = deepcopy(base)
    if not isinstance(incoming, dict):
        return result
    for key, value in incoming.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge_dict(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def criar_mary_profile_padrao() -> dict[str, Any]:
    profile = deepcopy(DEFAULT_MARY_PROFILE)
    now = utc_now_iso()
    profile["created_at"] = now
    profile["updated_at"] = now
    return profile


def normalizar_mary_profile(profile: dict[str, Any] | None) -> dict[str, Any]:
    normalized = _merge_dict(criar_mary_profile_padrao(), profile)
    normalized["profile_version"] = MARY_PROFILE_VERSION
    normalized["name"] = str(normalized.get("name") or "Mary").strip()
    try:
        normalized["age"] = max(18, int(normalized.get("age", 25)))
    except (TypeError, ValueError):
        normalized["age"] = 25

    visual = normalized.setdefault("visual_memory", {})
    approved = visual.get("approved_images")
    if not isinstance(approved, list):
        approved = []
        visual["approved_images"] = approved
    shown = visual.get("mary_images_shown")
    if not isinstance(shown, list):
        visual["mary_images_shown"] = list(approved)

    if not normalized.get("created_at"):
        normalized["created_at"] = utc_now_iso()
    if not normalized.get("updated_at"):
        normalized["updated_at"] = normalized["created_at"]
    return normalized


__all__ = [
    "utc_now_iso",
    "criar_mary_profile_padrao",
    "normalizar_mary_profile",
]
