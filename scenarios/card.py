from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable


CARD_CONTRACT_VERSION = "scenario-card-v1-isolated-character"
CardLoader = Callable[[], dict[str, Any]]

_REQUIRED_SECTIONS = {
    "scenario_id",
    "character",
    "psychology",
    "voice",
    "routes",
    "screenplay",
    "transitions",
}


def _dict(value: Any) -> dict[str, Any]:
    return deepcopy(value) if isinstance(value, dict) else {}


def _text(value: Any) -> str:
    return str(value or "").strip()


def normalizar_card_package(value: dict[str, Any] | None) -> dict[str, Any]:
    card = _dict(value)
    missing = _REQUIRED_SECTIONS - set(card)
    if missing:
        raise ValueError(
            "Pacote de card incompleto: " + ", ".join(sorted(missing))
        )

    scenario_id = _text(card.get("scenario_id"))
    if not scenario_id:
        raise ValueError("scenario_id do card não pode ficar vazio.")

    result = {
        "card_contract_version": CARD_CONTRACT_VERSION,
        "scenario_id": scenario_id,
        "character": _dict(card.get("character")),
        "psychology": _dict(card.get("psychology")),
        "voice": _dict(card.get("voice")),
        "routes": _dict(card.get("routes")),
        "screenplay": _dict(card.get("screenplay")),
        "transitions": _dict(card.get("transitions")),
        "shared_engines": _dict(card.get("shared_engines")),
        "prompt_policy": _dict(card.get("prompt_policy")),
    }
    return result


def montar_contexto_card(card: dict[str, Any] | None) -> str:
    package = normalizar_card_package(card)
    character = package["character"]
    psychology = package["psychology"]
    voice = package["voice"]
    policy = package["prompt_policy"]

    return f"""
PERSONAGEM EXCLUSIVA DESTE CARD

Este card possui uma versão própria e independente de Mary. Não importe humor,
segurança, vulgaridade, carência, timidez, sarcasmo, ritmo ou forma de seduzir de
outro card.

IDENTIDADE DRAMÁTICA
{character}

PERFIL PSICOLÓGICO
{psychology}

VOZ DESTA MARY
{voice}

POLÍTICA DO CARD
{policy}

REGRAS DE ISOLAMENTO
- Os traços deste card vencem traços comportamentais globais incompatíveis.
- O roteiro, as rotas e as transições pertencem somente a este card.
- Métricas emocionais globais são sinais técnicos; não redefinem a personagem.
- O motor sexual compartilhado controla mecânica corporal, não personalidade.
- Nenhuma experiência vivida por outra Mary deve ser presumida nesta história.
""".strip()


__all__ = [
    "CARD_CONTRACT_VERSION",
    "CardLoader",
    "montar_contexto_card",
    "normalizar_card_package",
]
