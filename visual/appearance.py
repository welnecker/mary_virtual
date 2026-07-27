from __future__ import annotations

from typing import Any


VARIABLE_APPEARANCE_KEYS = (
    "hairstyle",
    "clothing",
    "makeup",
    "accessories",
    "expression",
    "location",
)


def aplicar_aparencia_variavel(
    profile: dict[str, Any],
    *,
    hairstyle: str | None = None,
    clothing: str | None = None,
    makeup: str | None = None,
    accessories: str | None = None,
    expression: str | None = None,
    location: str | None = None,
) -> dict[str, Any]:
    variable = profile["physical_profile"]["variable_traits"]
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
    return profile


def extrair_tracos_fisicos_estaveis(profile: dict[str, Any]) -> dict[str, str]:
    traits = profile["physical_profile"]["stable_traits"]
    return {
        str(key): str(value)
        for key, value in traits.items()
        if str(value).strip()
    }


def extrair_aparencia_variavel(profile: dict[str, Any]) -> dict[str, str]:
    traits = profile["physical_profile"]["variable_traits"]
    return {
        str(key): str(value)
        for key, value in traits.items()
        if str(value).strip()
    }


__all__ = [
    "VARIABLE_APPEARANCE_KEYS",
    "aplicar_aparencia_variavel",
    "extrair_tracos_fisicos_estaveis",
    "extrair_aparencia_variavel",
]
