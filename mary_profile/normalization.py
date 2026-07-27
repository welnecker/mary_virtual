from __future__ import annotations

from copy import deepcopy
from typing import Any

from visual.normalization import normalizar_memoria_visual_no_perfil

from .composition import mesclar_dict_profundo
from .defaults import DEFAULT_MARY_PROFILE, MARY_PROFILE_VERSION
from .lifecycle import normalizar_ciclo_vida_perfil, utc_now_iso


def criar_mary_profile_padrao() -> dict[str, Any]:
    profile = deepcopy(DEFAULT_MARY_PROFILE)
    now = utc_now_iso()
    profile["created_at"] = now
    profile["updated_at"] = now
    return profile


def normalizar_mary_profile(profile: dict[str, Any] | None) -> dict[str, Any]:
    normalized = mesclar_dict_profundo(criar_mary_profile_padrao(), profile)
    normalizar_ciclo_vida_perfil(
        normalized,
        profile_version=MARY_PROFILE_VERSION,
    )
    normalizar_memoria_visual_no_perfil(normalized)
    return normalized


__all__ = [
    "utc_now_iso",
    "criar_mary_profile_padrao",
    "normalizar_mary_profile",
]
