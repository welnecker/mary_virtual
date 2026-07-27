from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def registrar_imagem_aprovada_no_perfil(
    profile: dict[str, Any],
    *,
    image_id: str,
    image_url: str,
    purpose: str,
    summary: str,
    metadata: dict[str, Any] | None = None,
    approved_at: str | None = None,
) -> dict[str, Any]:
    item = {
        "image_id": str(image_id or "").strip(),
        "image_url": str(image_url or "").strip(),
        "purpose": str(purpose or "").strip(),
        "summary": str(summary or "").strip(),
        "metadata": deepcopy(metadata or {}),
        "approved_at": str(approved_at or utc_now_iso()).strip(),
    }
    visual = profile["visual_memory"]
    visual["approved_images"].append(item)
    visual.setdefault("mary_images_shown", []).append(deepcopy(item))
    visual["last_generated_image_id"] = item["image_id"]
    visual["last_generated_image_summary"] = item["summary"]
    visual["last_mary_image_id"] = item["image_id"]
    visual["last_mary_image_path"] = item["image_url"]
    return profile


__all__ = [
    "registrar_imagem_aprovada_no_perfil",
]
