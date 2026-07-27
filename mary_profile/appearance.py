from __future__ import annotations

from typing import Any

from .normalization import normalizar_mary_profile, utc_now_iso


def atualizar_aparencia_variavel(
    profile: dict[str, Any],
    *,
    hairstyle: str | None = None,
    clothing: str | None = None,
    makeup: str | None = None,
    accessories: str | None = None,
    expression: str | None = None,
    location: str | None = None,
) -> dict[str, Any]:
    updated = normalizar_mary_profile(profile)
    variable = updated["physical_profile"]["variable_traits"]
    for key, value in {
        "hairstyle": hairstyle,
        "clothing": clothing,
        "makeup": makeup,
        "accessories": accessories,
        "expression": expression,
        "location": location,
    }.items():
        if value is not None:
            variable[key] = str(value).strip()
    updated["updated_at"] = utc_now_iso()
    return updated


def obter_tracos_fisicos_estaveis(profile: dict[str, Any]) -> dict[str, str]:
    traits = normalizar_mary_profile(profile)["physical_profile"]["stable_traits"]
    return {
        str(key): str(value)
        for key, value in traits.items()
        if str(value).strip()
    }


def obter_aparencia_variavel(profile: dict[str, Any]) -> dict[str, str]:
    traits = normalizar_mary_profile(profile)["physical_profile"]["variable_traits"]
    return {
        str(key): str(value)
        for key, value in traits.items()
        if str(value).strip()
    }


__all__ = [
    "atualizar_aparencia_variavel",
    "obter_tracos_fisicos_estaveis",
    "obter_aparencia_variavel",
]
