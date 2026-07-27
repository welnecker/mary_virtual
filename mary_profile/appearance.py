from __future__ import annotations

from typing import Any

from visual.appearance import (
    aplicar_aparencia_variavel,
    extrair_aparencia_variavel,
    extrair_tracos_fisicos_estaveis,
)

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
    aplicar_aparencia_variavel(
        updated,
        hairstyle=hairstyle,
        clothing=clothing,
        makeup=makeup,
        accessories=accessories,
        expression=expression,
        location=location,
    )
    updated["updated_at"] = utc_now_iso()
    return updated


def obter_tracos_fisicos_estaveis(profile: dict[str, Any]) -> dict[str, str]:
    return extrair_tracos_fisicos_estaveis(normalizar_mary_profile(profile))


def obter_aparencia_variavel(profile: dict[str, Any]) -> dict[str, str]:
    return extrair_aparencia_variavel(normalizar_mary_profile(profile))


__all__ = [
    "atualizar_aparencia_variavel",
    "obter_tracos_fisicos_estaveis",
    "obter_aparencia_variavel",
]
