from __future__ import annotations

from copy import deepcopy
from functools import wraps
import re
import sys
import unicodedata
from typing import Any, Callable

import streamlit as st

import relationship.scenario_director as director
from scenarios.card_registry import obter_card


SCENARIO_BRIDGE_INTEGRATION_VERSION = "scenario-bridge-v3-two-step-farewell"
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
- A ponte nunca aparece na mesma resposta que reconhece a despedida. Primeiro Mary
  encerra brevemente a cena; somente na interação seguinte ocorre o salto de tempo.
- Valeu, tchau, até e beleza, quando usados sozinhos ou como encerramento curto, são
  sinais de despedida. Interprete-os dentro do histórico, sem transformar ocorrências
  casuais dessas palavras no meio da conversa em encerramento automático.
- A decisão principal continua semântica: use histórico, estado e situação; não dependa
  de uma frase exata, regex obrigatória ou número rígido de turnos.
- bridge_context descreve uma possibilidade curta de reencontro, não uma frase pronta.
""".strip()

_FAREWELL_EXACT = {
    "valeu",
    "tchau",
    "ate",
    "ate mais",
    "ate logo",
    "beleza",
    "falou",
    "fui",
    "obrigado",
    "obrigada",
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _truth(value: Any) -> bool:
    return value is True or _text(value).lower() in {"true", "1", "sim", "yes"}


def _normalize(value: Any) -> str:
    text = _text(value).lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _farewell_signal(value: Any) -> bool:
    """Reconhece despedidas curtas sem classificar uma frase comum como encerramento."""
    text = _normalize(value)
    if not text or "?" in _text(value):
        return False
    if text in _FAREWELL_EXACT:
        return True

    words = text.split()
    if len(words) > 6:
        return False

    # "beleza" só vale como despedida quando aparece sozinha. As demais formas
    # aceitam complementos breves, como "valeu mesmo" ou "tchau, até mais".
    return any(
        text.startswith(prefix + " ")
        for prefix in ("valeu", "tchau", "ate", "falou", "obrigado", "obrigada")
    )


def _mary_already_closed_scene(scene: dict[str, Any]) -> bool:
    if bool(scene.get("scene_closing_signal")):
        return True
    last_analysis = scene.get("last_director_analysis")
    if isinstance(last_analysis, dict) and (
        _truth(last_analysis.get("scene_closing_signal"))
        or _text(last_analysis.get("scene_resolution"))
        in {"scene_closed", "stalled_farewell"}
    ):
        return True

    text = _normalize(scene.get("last_mary_response"))
    if not text:
        return False
    markers = (
        "tchau",
        "ate mais",
        "ate logo",
        "boas compras",
        "vou continuar minhas compras",
        "vou te deixar",
        "a gente se esbarra",
        "quem sabe a gente nao se esbarra",
    )
    return any(marker in text for marker in markers)


def _option(scenario_id: str, route: str) -> dict[str, Any]:
    card = obter_card(scenario_id)
    transitions = card.get("transitions") if isinstance(card, dict) else {}
    bridges = transitions.get("bridges") if isinstance(transitions, dict) else {}
    options = bridges.get("options") if isinstance(bridges, dict) else {}
    value = options.get(route) if isinstance(options, dict) else {}
    return deepcopy(value) if isinstance(value, dict) else {}


def _target_phase(scenario_id: str, target_route: str) -> str:
    card = obter_card(scenario_id)
    routes = card.get("routes") if isinstance(card, dict) else {}
    target = routes.get(target_route) if isinstance(routes, dict) else {}
    return _text(target.get("phase")) if isinstance(target, dict) else ""


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
    def normalizer(
        analysis: dict[str, Any] | None,
        *,
        scene_state: dict[str, Any] | None,
    ) -> dict[str, Any]:
        raw = analysis if isinstance(analysis, dict) else {}
        result = current(raw, scene_state=scene_state)
        for key in (
            "scene_resolution",
            "bridge_target_route",
            "bridge_target_beat",
            "bridge_context",
            "bridge_reason",
        ):
            result[key] = _text(raw.get(key))
        result["bridge_recommended"] = _truth(raw.get("bridge_recommended"))
        return result

    normalizer._mary_bridge_fields = True  # type: ignore[attr-defined]
    director.normalizar_analise_diretor = normalizer
    canonical = getattr(director, "_canonical", None)
    if canonical is not None:
        canonical.normalizar_analise_diretor = normalizer


def _activate_existing_bridge(
    *,
    state: dict[str, Any],
    existing: dict[str, Any],
    analysis: dict[str, Any],
    scenario_id: str,
) -> dict[str, Any]:
    if _truth(analysis.get("story_ending_signal")):
        state.pop("bridge_pending", None)
        state.pop("farewell_ack_only_interaction", None)
        return state

    current = int(state.get("interaction_number", 0) or 0)
    activate_at = int(existing.get("activate_interaction", 0) or 0)
    if not current or not activate_at or current < activate_at:
        state["bridge_pending"] = deepcopy(existing)
        return state

    target_route = _text(existing.get("target_route"))
    target_beat = _text(existing.get("target_beat"))
    if target_route:
        state["previous_route"] = _text(existing.get("source_route"))
        state["current_route"] = target_route
        state["current_beat"] = target_beat
        phase = _target_phase(scenario_id, target_route)
        if phase:
            state["current_phase"] = phase

    active = deepcopy(existing)
    active["status"] = "active"
    state["bridge_pending"] = active
    state["ending_ready"] = False
    state["ending_sent"] = False
    state["ending_reason"] = ""
    state["ending_type"] = ""
    state["user_disengaged"] = False
    return state


def _wrap_apply(original: Callable[..., Any]) -> Callable[..., Any]:
    if getattr(original, "_mary_bridge_apply", False):
        return original

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
        input_scene = kwargs.get("scene_state")
        if input_scene is None and args:
            input_scene = args[0]
        input_scene = input_scene if isinstance(input_scene, dict) else {}
        source_route = _text(input_scene.get("current_route"))
        existing = input_scene.get("bridge_pending")
        existing = deepcopy(existing) if isinstance(existing, dict) else {}

        analysis = kwargs.get("analise")
        if analysis is None and len(args) > 1:
            analysis = args[1]
        analysis = analysis if isinstance(analysis, dict) else {}

        state = original(*args, **kwargs)
        state = deepcopy(state) if isinstance(state, dict) else {}
        scenario_id = _text(
            analysis.get("_scenario_id")
            or state.get("scenario_id")
            or st.session_state.get("selected_scenario_id")
        )

        if existing:
            return _activate_existing_bridge(
                state=state,
                existing=existing,
                analysis=analysis,
                scenario_id=scenario_id,
            )

        resolution = _text(analysis.get("scene_resolution"))
        semantic_bridge = (
            _truth(analysis.get("bridge_recommended"))
            and resolution in {"scene_closed", "stalled_farewell"}
        )
        user_farewell = _farewell_signal(
            analysis.get("user_action") or state.get("last_user_action")
        )
        contextual_farewell = user_farewell and _mary_already_closed_scene(input_scene)

        if (
            _truth(analysis.get("story_ending_signal"))
            or not (semantic_bridge or contextual_farewell)
        ):
            return state

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

        current = int(state.get("interaction_number", 0) or 0)
        state["bridge_pending"] = {
            "source_route": source_route,
            "target_route": target_route,
            "target_beat": target_beat,
            "context": context,
            "armed_interaction": current,
            "activate_interaction": current + 1,
            "status": "armed",
            "reason": _text(analysis.get("bridge_reason"))
            or ("short_farewell_after_scene_closure" if contextual_farewell else "semantic_scene_bridge"),
        }
        state["farewell_ack_only_interaction"] = current
        state["ending_ready"] = False
        state["ending_sent"] = False
        state["ending_reason"] = ""
        state["ending_type"] = ""
        state["user_disengaged"] = False
        return state

    wrapper._mary_bridge_apply = True  # type: ignore[attr-defined]
    return wrapper


def _bridge_stage(scene_state: Any = None) -> tuple[str, dict[str, Any]]:
    scene = scene_state if isinstance(scene_state, dict) else None
    if scene is None:
        instance = st.session_state.get("scenario_instance")
        scene = instance.get("scene_state") if isinstance(instance, dict) else {}
    if not isinstance(scene, dict):
        return "", {}

    current = int(scene.get("interaction_number", 0) or 0)
    ack_at = int(scene.get("farewell_ack_only_interaction", 0) or 0)
    bridge = scene.get("bridge_pending")
    bridge = deepcopy(bridge) if isinstance(bridge, dict) else {}

    if current and ack_at == current:
        return "ack", bridge
    if not bridge:
        return "", {}

    activate_at = int(bridge.get("activate_interaction", 0) or 0)
    if current and activate_at == current:
        return "bridge", bridge
    return "", {}


def _wrap_direction(original: Callable[..., Any]) -> Callable[..., Any]:
    if getattr(original, "_mary_bridge_direction", False):
        return original

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> str:
        base = _text(original(*args, **kwargs))
        stage, bridge = _bridge_stage(kwargs.get("scene_state"))
        if stage == "ack":
            extra = (
                "[ENCERRAMENTO DA CENA — SEM PONTE NESTE TURNO]\n"
                "O usuário se despediu. Mary responde apenas com um encerramento curto e "
                "natural, de no máximo uma frase. Não cobre que ele falou pouco, não faça "
                "novo comentário, não reinicie assunto e não introduza reencontro, salto de "
                "tempo ou ponte nesta resposta."
            )
            return "\n\n".join(part for part in (base, extra) if part)

        if stage != "bridge":
            return base

        extra = (
            "[PONTE NARRATIVA — USAR UMA VEZ]\n"
            "A despedida anterior já foi respondida e a cena terminou. Não responda, "
            "agradeça nem comente novamente palavras como valeu, tchau, até ou beleza. "
            "Comece diretamente com uma ponte temporal curta em primeira pessoa, estabeleça "
            "somente o novo ponto de encontro e emende imediatamente uma fala viva de Mary. "
            "Não resuma a conversa anterior e não alongue a narração.\n"
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
