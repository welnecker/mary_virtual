from __future__ import annotations

from typing import Any

from relationship.profile_visibility import (
    marcar_perfil_revelado,
    registrar_primeira_reacao_visual,
    usuario_ja_viu_mary_no_perfil,
    usuario_viu_perfil_publico_no_perfil,
)
from visual.memory import registrar_imagem_aprovada_no_perfil

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
    registrar_imagem_aprovada_no_perfil(
        updated,
        image_id=image_id,
        image_url=image_url,
        purpose=purpose,
        summary=summary,
        metadata=metadata,
    )
    updated["updated_at"] = utc_now_iso()
    return updated


def marcar_mary_revelada(
    profile: dict[str, Any],
    *,
    image_id: str,
) -> dict[str, Any]:
    updated = normalizar_mary_profile(profile)
    marcar_perfil_revelado(updated, image_id=image_id)
    updated["updated_at"] = utc_now_iso()
    return updated


def registrar_primeira_reacao_visual_usuario(
    profile: dict[str, Any],
    reaction: str,
) -> dict[str, Any]:
    updated = normalizar_mary_profile(profile)
    registrar_primeira_reacao_visual(updated, reaction)
    updated["updated_at"] = utc_now_iso()
    return updated


def usuario_ja_viu_mary(profile: dict[str, Any]) -> bool:
    return usuario_ja_viu_mary_no_perfil(normalizar_mary_profile(profile))


def usuario_viu_perfil_publico(profile: dict[str, Any]) -> bool:
    return usuario_viu_perfil_publico_no_perfil(normalizar_mary_profile(profile))


__all__ = [
    "registrar_imagem_aprovada",
    "marcar_mary_revelada",
    "registrar_primeira_reacao_visual_usuario",
    "usuario_ja_viu_mary",
    "usuario_viu_perfil_publico",
]
