from __future__ import annotations

from copy import deepcopy
from functools import wraps
from typing import Any, Callable

from scenarios.card import montar_contexto_card, normalizar_card_package
from scenarios.stories.casada_frustrada.card import obter_card as obter_card_casada
from scenarios.stories.vizinha_porta_trancada.card import obter_card as obter_card_vizinha


CARD_REGISTRY_VERSION = "scenario-card-registry-v1-two-independent-marys"
CardLoader = Callable[[], dict[str, Any]]

CARD_LOADERS: dict[str, CardLoader] = {
    "casada_frustrada": obter_card_casada,
    "vizinha_porta_trancada": obter_card_vizinha,
}


def obter_card(scenario_id: str) -> dict[str, Any]:
    loader = CARD_LOADERS.get(str(scenario_id or "").strip())
    if not callable(loader):
        return {}
    return normalizar_card_package(loader())


def enriquecer_config_com_card(config: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(config) if isinstance(config, dict) else {}
    scenario_id = str(result.get("scenario_id") or "").strip()
    card = obter_card(scenario_id)
    if not card:
        return result

    result["card_package"] = card
    result["character_profile"] = deepcopy(card["character"])
    result["psychology_profile"] = deepcopy(card["psychology"])
    result["voice_profile"] = deepcopy(card["voice"])
    result["transition_policy"] = deepcopy(card["transitions"])
    result["screenplay_policy"] = deepcopy(card["screenplay"])
    result["shared_engines"] = deepcopy(card["shared_engines"])
    return result


def _wrap_config_loader(loader: Callable[[], dict[str, Any]]) -> Callable[[], dict[str, Any]]:
    if getattr(loader, "_mary_card_config_wrapped", False):
        return loader

    @wraps(loader)
    def wrapper() -> dict[str, Any]:
        return enriquecer_config_com_card(loader())

    wrapper._mary_card_config_wrapped = True  # type: ignore[attr-defined]
    return wrapper


def instalar_cards_no_registry(registry_module: Any) -> None:
    loaders_map = getattr(registry_module, "SCENARIO_LOADERS", None)
    if isinstance(loaders_map, dict):
        for scenario_id, card_loader in CARD_LOADERS.items():
            loaders = loaders_map.get(scenario_id)
            if not isinstance(loaders, dict):
                continue
            config_loader = loaders.get("config_loader")
            if callable(config_loader):
                loaders["config_loader"] = _wrap_config_loader(config_loader)
            loaders["card_loader"] = card_loader

    original_prompt = getattr(registry_module, "montar_prompt_cenario", None)
    if not callable(original_prompt) or getattr(
        original_prompt, "_mary_card_prompt_wrapped", False
    ):
        return

    @wraps(original_prompt)
    def prompt_wrapper(*, config: dict[str, Any]) -> str:
        enriched = enriquecer_config_com_card(config)
        base = str(original_prompt(config=enriched) or "").strip()
        card = enriched.get("card_package")
        card_context = montar_contexto_card(card) if isinstance(card, dict) else ""
        return "\n\n".join(part for part in (base, card_context) if part)

    prompt_wrapper._mary_card_prompt_wrapped = True  # type: ignore[attr-defined]
    registry_module.montar_prompt_cenario = prompt_wrapper


__all__ = [
    "CARD_LOADERS",
    "CARD_REGISTRY_VERSION",
    "enriquecer_config_com_card",
    "instalar_cards_no_registry",
    "obter_card",
]
