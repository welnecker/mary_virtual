from __future__ import annotations

from pathlib import Path
from typing import Any

from identity.public_profile import (
    aplicar_atualizacoes_perfil_publico,
    montar_perfil_publico,
)
from relationship.profile_visibility import marcar_perfil_publico_como_visto

from .defaults import DEFAULT_PUBLIC_PROFILE_IMAGE_PATH
from .normalization import normalizar_mary_profile, utc_now_iso


def obter_perfil_publico(profile: dict[str, Any] | None = None) -> dict[str, Any]:
    normalized = normalizar_mary_profile(profile)
    return montar_perfil_publico(normalized)


def obter_caminho_imagem_publica(profile: dict[str, Any] | None = None) -> str:
    public = obter_perfil_publico(profile)
    return str(
        public.get("profile_image_path") or DEFAULT_PUBLIC_PROFILE_IMAGE_PATH
    ).strip()


def imagem_publica_existe(profile: dict[str, Any] | None = None) -> bool:
    path = obter_caminho_imagem_publica(profile)
    return bool(path and Path(path).is_file())


def marcar_perfil_publico_visto(profile: dict[str, Any]) -> dict[str, Any]:
    updated = normalizar_mary_profile(profile)
    marcar_perfil_publico_como_visto(updated, seen_at=utc_now_iso())
    updated["updated_at"] = utc_now_iso()
    return updated


def atualizar_perfil_publico(
    profile: dict[str, Any],
    *,
    headline: str | None = None,
    bio: str | None = None,
    profile_image_path: str | None = None,
    image_alt_text: str | None = None,
) -> dict[str, Any]:
    updated = normalizar_mary_profile(profile)
    aplicar_atualizacoes_perfil_publico(
        updated,
        headline=headline,
        bio=bio,
        profile_image_path=profile_image_path,
        image_alt_text=image_alt_text,
    )
    updated["updated_at"] = utc_now_iso()
    return updated


__all__ = [
    "obter_perfil_publico",
    "obter_caminho_imagem_publica",
    "imagem_publica_existe",
    "marcar_perfil_publico_visto",
    "atualizar_perfil_publico",
]
