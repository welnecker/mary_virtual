from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from relationship.profile_visibility import marcar_perfil_publico_como_visto

from .defaults import DEFAULT_PUBLIC_PROFILE_IMAGE_PATH
from .normalization import normalizar_mary_profile, utc_now_iso


def obter_perfil_publico(profile: dict[str, Any] | None = None) -> dict[str, Any]:
    normalized = normalizar_mary_profile(profile)
    public = deepcopy(normalized.get("public_profile", {}))
    public.setdefault("display_name", normalized.get("name", "Mary"))
    public.setdefault("age", normalized.get("age", 25))
    public.setdefault("public_status", public.get("headline", ""))
    public.setdefault("short_bio", public.get("bio", ""))
    public.setdefault("long_bio", public.get("bio", ""))
    public.setdefault("occupation", "companhia virtual")
    public.setdefault("city", "online")
    public.setdefault("interests", [])
    public.setdefault(
        "personality_traits",
        list(normalized.get("personality", {}).get("core_traits", [])),
    )
    public.setdefault("open_to", ["conversa adulta", "provocação", "intimidade"])
    public.setdefault("identity", deepcopy(normalized.get("identity", {})))
    public.setdefault("image_id", "mary_public_profile_blurred_v1")
    return public


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
    public = updated["public_profile"]
    for key, value in {
        "headline": headline,
        "bio": bio,
        "profile_image_path": profile_image_path,
        "image_alt_text": image_alt_text,
    }.items():
        if value is not None:
            public[key] = str(value).strip()
    updated["updated_at"] = utc_now_iso()
    return updated


__all__ = [
    "obter_perfil_publico",
    "obter_caminho_imagem_publica",
    "imagem_publica_existe",
    "marcar_perfil_publico_visto",
    "atualizar_perfil_publico",
]
