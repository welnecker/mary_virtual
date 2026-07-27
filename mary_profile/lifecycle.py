from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalizar_ciclo_vida_perfil(
    profile: dict[str, Any],
    *,
    profile_version: str,
) -> dict[str, Any]:
    profile["profile_version"] = str(profile_version or "").strip()
    profile["name"] = str(profile.get("name") or "Mary").strip()

    try:
        profile["age"] = max(18, int(profile.get("age", 25)))
    except (TypeError, ValueError):
        profile["age"] = 25

    if not profile.get("created_at"):
        profile["created_at"] = utc_now_iso()
    if not profile.get("updated_at"):
        profile["updated_at"] = profile["created_at"]
    return profile


__all__ = [
    "utc_now_iso",
    "normalizar_ciclo_vida_perfil",
]
