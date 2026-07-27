from __future__ import annotations

from copy import deepcopy
from typing import Any


def montar_perfil_publico(profile: dict[str, Any]) -> dict[str, Any]:
    public = deepcopy(profile.get("public_profile", {}))
    public.setdefault("display_name", profile.get("name", "Mary"))
    public.setdefault("age", profile.get("age", 25))
    public.setdefault("public_status", public.get("headline", ""))
    public.setdefault("short_bio", public.get("bio", ""))
    public.setdefault("long_bio", public.get("bio", ""))
    public.setdefault("occupation", "companhia virtual")
    public.setdefault("city", "online")
    public.setdefault("interests", [])
    public.setdefault(
        "personality_traits",
        list(profile.get("personality", {}).get("core_traits", [])),
    )
    public.setdefault("open_to", ["conversa adulta", "provocação", "intimidade"])
    public.setdefault("identity", deepcopy(profile.get("identity", {})))
    public.setdefault("image_id", "mary_public_profile_blurred_v1")
    return public


def aplicar_atualizacoes_perfil_publico(
    profile: dict[str, Any],
    *,
    headline: str | None = None,
    bio: str | None = None,
    profile_image_path: str | None = None,
    image_alt_text: str | None = None,
) -> dict[str, Any]:
    public = profile["public_profile"]
    for key, value in {
        "headline": headline,
        "bio": bio,
        "profile_image_path": profile_image_path,
        "image_alt_text": image_alt_text,
    }.items():
        if value is not None:
            public[key] = str(value).strip()
    return profile


__all__ = [
    "montar_perfil_publico",
    "aplicar_atualizacoes_perfil_publico",
]
