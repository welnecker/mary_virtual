from __future__ import annotations

from copy import deepcopy
from typing import Any

from .normalization import normalizar_mary_profile, utc_now_iso


def registrar_imagem_aprovada(
    profile: dict[str, Any],
    *,
    image_id: str,
    image_url: str,
    purpose: str,
    summary: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    updated = normalizar_mary_profile(profile)
    item = {
        "image_id": str(image_id or "").strip(),
        "image_url": str(image_url or "").strip(),
        "purpose": str(purpose or "").strip(),
        "summary": str(summary or "").strip(),
        "metadata": deepcopy(metadata or {}),
        "approved_at": utc_now_iso(),
    }
    visual = updated["visual_memory"]
    visual["approved_images"].append(item)
    visual.setdefault("mary_images_shown", []).append(deepcopy(item))
    visual["last_generated_image_id"] = item["image_id"]
    visual["last_generated_image_summary"] = item["summary"]
    visual["last_mary_image_id"] = item["image_id"]
    visual["last_mary_image_path"] = item["image_url"]
    updated["updated_at"] = utc_now_iso()
    return updated


def marcar_mary_revelada(
    profile: dict[str, Any],
    *,
    image_id: str,
) -> dict[str, Any]:
    normalized_id = str(image_id or "").strip()
    if not normalized_id:
        raise ValueError("Informe um image_id válido.")
    updated = normalizar_mary_profile(profile)
    relationship = updated["relationship_state"]
    relationship["revealed_to_user"] = True
    relationship["user_has_seen_mary"] = True
    if not relationship.get("first_reveal_image_id"):
        relationship["first_reveal_image_id"] = normalized_id
    if not relationship.get("first_reveal_at"):
        relationship["first_reveal_at"] = utc_now_iso()
    updated["updated_at"] = utc_now_iso()
    return updated


def registrar_primeira_reacao_visual_usuario(
    profile: dict[str, Any],
    reaction: str,
) -> dict[str, Any]:
    updated = normalizar_mary_profile(profile)
    text = str(reaction or "").strip()
    relationship = updated["relationship_state"]
    if text and not relationship.get("user_first_visual_reaction"):
        relationship["user_first_visual_reaction"] = text
    updated["updated_at"] = utc_now_iso()
    return updated


def usuario_ja_viu_mary(profile: dict[str, Any]) -> bool:
    return bool(
        normalizar_mary_profile(profile)["relationship_state"].get(
            "user_has_seen_mary"
        )
    )


def usuario_viu_perfil_publico(profile: dict[str, Any]) -> bool:
    return bool(
        normalizar_mary_profile(profile)["relationship_state"].get(
            "public_profile_seen"
        )
    )


__all__ = [
    "registrar_imagem_aprovada",
    "marcar_mary_revelada",
    "registrar_primeira_reacao_visual_usuario",
    "usuario_ja_viu_mary",
    "usuario_viu_perfil_publico",
]
