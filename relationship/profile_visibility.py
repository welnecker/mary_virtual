from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any


DEFAULT_PROFILE_VISIBILITY_STATE: dict[str, Any] = {
    "revealed_to_user": False,
    "first_reveal_image_id": "",
    "first_reveal_at": "",
    "user_has_seen_mary": False,
    "user_first_visual_reaction": "",
    "public_profile_seen": False,
    "public_profile_seen_at": "",
    "private_details_revealed": {"tattoo": False},
    "private_details_revealed_at": {"tattoo": ""},
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def criar_estado_visibilidade_perfil_padrao() -> dict[str, Any]:
    return deepcopy(DEFAULT_PROFILE_VISIBILITY_STATE)


def marcar_perfil_revelado(
    profile: dict[str, Any],
    *,
    image_id: str,
    revealed_at: str | None = None,
) -> dict[str, Any]:
    normalized_id = str(image_id or "").strip()
    if not normalized_id:
        raise ValueError("Informe um image_id válido.")

    relationship = profile["relationship_state"]
    relationship["revealed_to_user"] = True
    relationship["user_has_seen_mary"] = True
    if not relationship.get("first_reveal_image_id"):
        relationship["first_reveal_image_id"] = normalized_id
    if not relationship.get("first_reveal_at"):
        relationship["first_reveal_at"] = str(revealed_at or utc_now_iso()).strip()
    return profile


def registrar_primeira_reacao_visual(
    profile: dict[str, Any],
    reaction: str,
) -> dict[str, Any]:
    text = str(reaction or "").strip()
    relationship = profile["relationship_state"]
    if text and not relationship.get("user_first_visual_reaction"):
        relationship["user_first_visual_reaction"] = text
    return profile


def usuario_ja_viu_mary_no_perfil(profile: dict[str, Any]) -> bool:
    return bool(profile["relationship_state"].get("user_has_seen_mary"))


def usuario_viu_perfil_publico_no_perfil(profile: dict[str, Any]) -> bool:
    return bool(profile["relationship_state"].get("public_profile_seen"))


__all__ = [
    "DEFAULT_PROFILE_VISIBILITY_STATE",
    "criar_estado_visibilidade_perfil_padrao",
    "marcar_perfil_revelado",
    "registrar_primeira_reacao_visual",
    "usuario_ja_viu_mary_no_perfil",
    "usuario_viu_perfil_publico_no_perfil",
]
