from __future__ import annotations

from typing import Any


def normalizar_memoria_visual_no_perfil(profile: dict[str, Any]) -> dict[str, Any]:
    visual = profile.setdefault("visual_memory", {})

    approved = visual.get("approved_images")
    if not isinstance(approved, list):
        approved = []
        visual["approved_images"] = approved

    shown = visual.get("mary_images_shown")
    if not isinstance(shown, list):
        visual["mary_images_shown"] = list(approved)

    return profile


__all__ = ["normalizar_memoria_visual_no_perfil"]
