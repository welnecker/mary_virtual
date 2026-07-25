from __future__ import annotations

from copy import deepcopy
from functools import wraps
import sys
from typing import Any, Callable

import streamlit as st

import relationship.scenario_director as director
from scenarios.card_registry import obter_card


SCENARIO_BRIDGE_INTEGRATION_VERSION = "scenario-bridge-v2-direct-state-reencounter"
_INSTALLED = False
_ORIGINAL_TITLE: Callable[..., Any] | None = None

_RULES = """
PONTES NARRATIVAS ENTRE CENAS
- Retorne também: scene_resolution, bridge_recommended, bridge_target_route,
  bridge_target_beat, bridge_context e bridge_reason.
- scene_resolution: active, scene_closed, stalled_farewell ou definitive_ending.
- scene_closed e stalled_farewell não encerram a história quando ainda existe uma
  continuação plausível no card.
- Recomende uma ponte quando a cena local terminou ou ficou presa em despedidas
  equivalentes e continuar no mesmo instante apenas repetiria o encerramento.
- A decisão é semântica: use histórico, estado e situação; nunca palavras fixas,
  regex ou número obrigatório de turnos.
- bridge_context descreve uma possibilidade curta de reencontro, não uma frase pronta.
""".strip()


def _text(value: Any) -> str:
    return str(value or "").strip()


def _truth(value: Any) -> bool:
    return value is True or _text(value).lower() in {"true", "1", "sim", "yes"}


def _option(scenario_id: str, route: str) -> dict[str, Any]:
    card = obter_card(scenario_id)
    transitions = card.get("transitions") if isinstance(card, dict) else {}
    bridges = transitions.get("bridges") if isinstance(transitions, dict) else {}
    options = bridges.get("options") if isinstance(bridges, dict) else {}
    value = options.get(route) if isinstance(options, dict) else {}
    return deepcopy(value) if isinstance(value, dict) else {}


def _install_contract() -> None:
    prompt = _text(getattr(director, "DIRECTOR_SYSTEM_PROMPT", ""))
    if "PONTES NARRATIVAS ENTRE CENAS" not in prompt:
        prompt = prompt + "\n\n" + _RULES
        director.DIRECTOR_SYSTEM_PROMPT = prompt
        canonical = getattr(director, "_canonical", None)
        if canonical is not None:
            canonical.DIRECTOR_SYSTEM_PROMPT = prompt

    current = director.normalizar_analise_diretor
    if getattr(current, "_mary_bridge_fields", False):
        return

    @wraps(current)
    def normalizer(analysis: dict[str, Any] | None, *, scene_state: dict[str, Any] | None):
        raw = analysis if isinstance(analysis, dict) else {}
        result = current(raw, scene_state=scene_state)
        for key in (
            "scene_resolution", "bridge_target_route", "bridge_target_beat",
            "bridge_context", "bridge_reason",
        ):
            result[key] = _text(raw.get(key))
        result["bridge_recommended"] = _truth(raw.get("bridge_recommended"))
        return result

    normalizer._mary_bridge_fields = True  # type: ignore[attr-defined]
    director.normalizar_analise_diretor = normalizer
    canonical = getattr(director, "_canonical", None)
    if canonical is not None:
        canonical.normalizar_analise_diretor = normalizer


def _wrap_apply(original: Callable[..., Any]) -> Callable[..., Any]:
    if getattr(original, "_mary_bridge_apply", False):
        return original

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
        analysis = kwargs.get("analise")
        if analysis is None and len(args) > 1:
            analysis = args[1]
        analysis = analysis if isinstance(analysis, dict) else {}
        state = original(*args, **kwargs)
        state = deepcopy(state) if isinstance(state, dict) else {}

        resolution = _text(analysis.get("scene_resolution"))
        if (
            not _truth(analysis.get("bridge_recommended"))
            or _truth(analysis.get("story_ending_signal"))
            or resolution not in {"scene_closed", "stalled_farewell"}
        ):
            return state

        scenario_id = _text(
            analysis.get("_scenario_id")
            or st.session_state.get("selected_scenario_id")
        )
        source_route = _text(state.get("current_route"))
        option = _option(scenario_id, source_route)
        if not option:
            return state

        target_route = _text(option.get("target_route"))
        target_beat = _text(option.get("target_beat"))
        if not target_route:
            return state

        context = _text(analysis.get("bridge_context"))
        possibilities = option.get("possibilities")
        if not context and isinstance(possibilities, list) and possibilities:
            context = _text(possibilities[0])

        state["previous_route"] = source_route
        state["current_route"] = target_route
        state["current_beat"] = target_beat

        card = obter_card(scenario_id)
        routes = card.get("routes") if isinstance(card, dict) else {}
        target_data = routes.get(target_route) if isinstance(routes, dict) else {}
        if isinstance(target_data, dict) and _text(target_data.get("phase")):
            state["current_phase"] = _text(target_data.get("phase"))

        state["bridge_pending"] = {
            "target_route": target_route,
            "target_beat": target_beat,
            "context": context,
            "armed_interaction": int(state.get("interaction_number", 0) or 0),
        }
        state["ending_ready"] = False
        state["ending_sent"] = False
        state["ending_reason"] = ""
        state["ending_type"] = ""
        state["user_disengaged"] = False
        return state

    wrapper._mary_bridge_apply = True  # type: ignore[attr-defined]
    return wrapper


def _pending_bridge(scene_state: Any = None) -> dict[str, Any]:
    scene = scene_state if isinstance(scene_state, dict) else None
    if scene is None:
        instance = st.session_state.get("scenario_instance")
        scene = instance.get("scene_state") if isinstance(instance, dict) else {}
    bridge = scene.get("bridge_pending") if isinstance(scene, dict) else {}
    if not isinstance(bridge, dict):
        return {}
    armed = int(bridge.get("armed_interaction", 0) or 0)
    current = int(scene.get("interaction_number", 0) or 0)
    return deepcopy(bridge) if not armed or not current or armed == current else {}


def _wrap_direction(original: Callable[..., Any]) -> Callable[..., Any]:
    if getattr(original, "_mary_bridge_direction", False):
        return original

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> str:
        base = _text(original(*args, **kwargs))
        scene_state = kwargs.get("scene_state")
        bridge = _pending_bridge(scene_state)
        if not bridge:
            return base
        extra = (
            "[PONTE NARRATIVA — USAR UMA VEZ]\n"
            "A cena anterior terminou, mas a história continua. Abra com uma ponte "
            "temporal curta em primeira pessoa, estabeleça somente o novo ponto de "
            "encontro e emende imediatamente uma fala de Mary. Não repita a despedida, "
            "não resuma o que ocorreu e não alongue a narração.\n"
            f"Possibilidade adaptável, não literal: {_text(bridge.get('context'))}\n"
            f"Rota retomada: {_text(bridge.get('target_route'))}; "
            f"beat: {_text(bridge.get('target_beat'))}."
        )
        return "\n\n".join(part for part in (base, extra) if part)

    wrapper._mary_bridge_direction = True  # type: ignore[attr-defined]
    return wrapper


def aplicar_pontes_narrativas() -> None:
    _install_contract()
    main = sys.modules.get("__main__")
    if main is None:
        return
    apply_fn = getattr(main, "aplicar_analise_ao_estado", None)
    if callable(apply_fn):
        main.aplicar_analise_ao_estado = _wrap_apply(apply_fn)
    direction_fn = getattr(main, "montar_direcao_narrativa", None)
    if callable(direction_fn):
        main.montar_direcao_narrativa = _wrap_direction(direction_fn)


def install_scenario_bridge_integration() -> None:
    global _INSTALLED, _ORIGINAL_TITLE
    if _INSTALLED:
        return
    _install_contract()
    _ORIGINAL_TITLE = st.title

    @wraps(_ORIGINAL_TITLE)
    def patched_title(*args: Any, **kwargs: Any) -> Any:
        aplicar_pontes_narrativas()
        assert _ORIGINAL_TITLE is not None
        return _ORIGINAL_TITLE(*args, **kwargs)

    st.title = patched_title
    _INSTALLED = True


__all__ = [
    "SCENARIO_BRIDGE_INTEGRATION_VERSION",
    "aplicar_pontes_narrativas",
    "install_scenario_bridge_integration",
]
