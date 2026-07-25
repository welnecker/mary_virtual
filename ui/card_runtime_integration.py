from __future__ import annotations

from copy import deepcopy
from functools import wraps
import re
import sys
import unicodedata
from typing import Any, Callable

import streamlit as st

import scenarios.service as scenario_service
import ui.scenario_menu as scenario_menu
from scenarios.card_registry import obter_card
from scenarios.card_runtime import (
    aplicar_restricoes_card,
    montar_janela_roteiro,
    rota_permite_sexualidade,
)


CARD_RUNTIME_INTEGRATION_VERSION = (
    "card-runtime-integration-v5-two-step-dialogue-bridge"
)
_RECENT_MESSAGES_LIMIT = 20
_INSTALLED = False
_ORIGINAL_TITLE: Callable[..., Any] | None = None

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


def _normalize(value: Any) -> str:
    text = _text(value).lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _is_short_farewell(value: Any) -> bool:
    original = _text(value)
    text = _normalize(value)
    if not text or "?" in original:
        return False
    if text in _FAREWELL_EXACT:
        return True
    words = text.split()
    if len(words) > 6:
        return False
    return any(
        text.startswith(prefix + " ")
        for prefix in ("valeu", "tchau", "ate", "falou", "obrigado", "obrigada")
    )


def _instance() -> dict[str, Any] | None:
    value = st.session_state.get("scenario_instance")
    return value if isinstance(value, dict) else None


def _context() -> tuple[str, str]:
    instance = _instance()
    if not isinstance(instance, dict):
        return "", ""
    scene = instance.get("scene_state")
    if not isinstance(scene, dict):
        scene = {}
    return (
        _text(instance.get("scenario_id")),
        _text(instance.get("current_route") or scene.get("current_route")),
    )


def _valid_messages(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    result: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        role = _text(item.get("role"))
        content = _text(item.get("content"))
        if role in {"user", "assistant"} and content:
            result.append({"role": role, "content": content})
    return result


def _cache_recent_messages() -> None:
    """Mantém recorte recente apenas em memória.

    A interação e a sessão já são persistidas pelo fluxo principal. Fazer uma nova
    gravação completa aqui duplicava consultas e atualizações no Google Sheets após
    cada resposta. O recorte em memória será incluído na próxima persistência normal.
    """
    instance = _instance()
    if not isinstance(instance, dict):
        return
    messages = _valid_messages(st.session_state.get("messages"))[-_RECENT_MESSAGES_LIMIT:]
    progress = instance.get("story_progress")
    if not isinstance(progress, dict):
        progress = {}
    progress = deepcopy(progress)
    progress["recent_messages"] = messages
    progress["recent_messages_session_id"] = _text(
        instance.get("scenario_session_id")
    )
    instance["story_progress"] = progress
    st.session_state["scenario_instance"] = instance


def _fallback_messages(instance: dict[str, Any], messages: Any) -> list[dict[str, str]]:
    current = _valid_messages(messages)
    if current:
        return current[-_RECENT_MESSAGES_LIMIT:]
    progress = instance.get("story_progress")
    if isinstance(progress, dict):
        stored_session = _text(progress.get("recent_messages_session_id"))
        current_session = _text(instance.get("scenario_session_id"))
        if not stored_session or stored_session == current_session:
            restored = _valid_messages(progress.get("recent_messages"))
            if restored:
                return restored[-_RECENT_MESSAGES_LIMIT:]
    scene = instance.get("scene_state")
    if isinstance(scene, dict):
        restored = _valid_messages(scene.get("continuation_context"))
        if restored:
            return restored[-_RECENT_MESSAGES_LIMIT:]
    return []


def _sanitize_scene_state(scenario_id: str, route: str) -> None:
    instance = _instance()
    if not isinstance(instance, dict):
        return
    scene = instance.get("scene_state")
    if not isinstance(scene, dict):
        scene = {}
    scene = deepcopy(scene)
    if not rota_permite_sexualidade(obter_card(scenario_id), route):
        scene["sexual_scene_phase"] = "idle"
        scene["sexual_voice_mode"] = "natural"
        scene["seduction_level"] = min(int(scene.get("seduction_level", 0) or 0), 1)
        sexual = scene.get("sexual_state")
        if isinstance(sexual, dict):
            sexual = deepcopy(sexual)
            sexual.update(
                {
                    "scene_phase": "idle",
                    "arousal_level": 0.0,
                    "stimulation_turns": 0,
                    "mary_pre_orgasm": False,
                    "mary_orgasm_allowed": False,
                    "mary_orgasm_done": False,
                    "user_orgasm_pending": False,
                    "user_orgasm_done": False,
                    "aftercare_required": False,
                }
            )
            scene["sexual_state"] = sexual
    instance["scene_state"] = scene
    instance["current_route"] = route
    st.session_state["scenario_instance"] = instance


def _bridge_option(scenario_id: str, route: str) -> dict[str, Any]:
    card = obter_card(scenario_id)
    transitions = card.get("transitions") if isinstance(card, dict) else {}
    bridges = transitions.get("bridges") if isinstance(transitions, dict) else {}
    options = bridges.get("options") if isinstance(bridges, dict) else {}
    option = options.get(route) if isinstance(options, dict) else {}
    return deepcopy(option) if isinstance(option, dict) else {}


def _arm_or_activate_bridge(prompt: Any) -> tuple[str, str]:
    """Retorna o contexto atualizado depois de tratar a ponte em dois tempos.

    1) despedida curta arma a ponte e exige apenas encerramento naquele turno;
    2) o primeiro turno posterior que não seja nova despedida ativa o reencontro.
    """
    instance = _instance()
    if not isinstance(instance, dict):
        return "", ""
    scenario_id = _text(instance.get("scenario_id"))
    scene = instance.get("scene_state")
    if not isinstance(scene, dict):
        scene = {}
    scene = deepcopy(scene)
    route = _text(instance.get("current_route") or scene.get("current_route"))
    user_farewell = _is_short_farewell(prompt)
    pending = scene.get("dialogue_bridge")
    pending = deepcopy(pending) if isinstance(pending, dict) else {}

    scene["farewell_ack_only_this_turn"] = False
    scene["dialogue_bridge_active_this_turn"] = False

    if pending.get("status") == "armed":
        if user_farewell:
            scene["farewell_ack_only_this_turn"] = True
        else:
            target_route = _text(pending.get("target_route"))
            target_beat = _text(pending.get("target_beat"))
            if target_route:
                scene["previous_route"] = route
                scene["current_route"] = target_route
                scene["current_beat"] = target_beat
                scene["dialogue_bridge_active_this_turn"] = True
                scene["dialogue_bridge"] = {
                    **pending,
                    "status": "active",
                }
                scene["ending_ready"] = False
                scene["ending_sent"] = False
                scene["ending_reason"] = ""
                scene["ending_type"] = ""
                scene["user_disengaged"] = False
                instance["current_route"] = target_route
                if target_beat:
                    instance["current_beat"] = target_beat
                route = target_route
    elif user_farewell and scenario_id == "casada_frustrada":
        option = _bridge_option(scenario_id, route)
        target_route = _text(option.get("target_route"))
        if target_route:
            possibilities = option.get("possibilities")
            context = ""
            if isinstance(possibilities, list) and possibilities:
                context = _text(possibilities[0])
            scene["dialogue_bridge"] = {
                "status": "armed",
                "source_route": route,
                "target_route": target_route,
                "target_beat": _text(option.get("target_beat")),
                "context": context,
            }
            scene["farewell_ack_only_this_turn"] = True
            scene["ending_ready"] = False
            scene["ending_sent"] = False
            scene["user_disengaged"] = False

    instance["scene_state"] = scene
    st.session_state["scenario_instance"] = instance
    return scenario_id, route


def _bridge_prompt_block() -> str:
    instance = _instance()
    if not isinstance(instance, dict):
        return ""
    scene = instance.get("scene_state")
    if not isinstance(scene, dict):
        return ""
    if bool(scene.get("farewell_ack_only_this_turn")):
        return (
            "[ENCERRAMENTO DE CENA — SEM REENCONTRO NESTA RESPOSTA]\n"
            "O usuário encerrou a conversa atual. Mary responde somente com uma frase "
            "curta e natural de despedida. Não acrescente ajuda, novo assunto, promessa, "
            "pergunta, salto temporal ou reencontro. A ponte fica reservada para o próximo "
            "turno que não seja outra despedida."
        )
    if not bool(scene.get("dialogue_bridge_active_this_turn")):
        return ""
    bridge = scene.get("dialogue_bridge")
    bridge = bridge if isinstance(bridge, dict) else {}
    return (
        "[PONTE LÓGICA DE DIÁLOGO — USAR AGORA UMA ÚNICA VEZ]\n"
        "A despedida anterior já terminou e não deve ser respondida novamente. Comece "
        "diretamente com uma passagem curta de tempo ou mudança natural de ponto dentro "
        "do mesmo universo da história. Em seguida, Mary reencontra o usuário e fala algo "
        "novo que retoma a progressão do roteiro. Não recapitule a despedida, não diga "
        "'valeu', 'tchau' ou 'até', e não explique a transição.\n"
        f"Possibilidade adaptável: {_text(bridge.get('context'))}\n"
        f"Nova rota: {_text(bridge.get('target_route'))}; "
        f"beat: {_text(bridge.get('target_beat'))}."
    )


def _patch_prompt_builder(module: Any) -> None:
    original = getattr(module, "montar_prompt_sistema", None)
    if not callable(original) or getattr(original, "_mary_card_runtime_wrapped", False):
        return

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> str:
        scenario_id, route = _context()
        if not scenario_id or not route:
            return str(original(*args, **kwargs) or "")
        aligned = dict(kwargs)
        aligned.update(
            aplicar_restricoes_card(
                scenario_id=scenario_id,
                route=route,
                mary_profile=aligned.get("mary_profile"),
                relationship_state=aligned.get("relationship_state"),
                sexual_state=aligned.get("sexual_state"),
                turn_intent=aligned.get("turn_intent"),
                turn_direction=aligned.get("turn_direction"),
            )
        )
        aligned["include_voice_examples"] = False
        return str(original(*args, **aligned) or "")

    wrapper._mary_card_runtime_wrapped = True  # type: ignore[attr-defined]
    setattr(module, "montar_prompt_sistema", wrapper)


def _patch_narrative_direction(module: Any) -> None:
    original = getattr(module, "montar_direcao_narrativa", None)
    if not callable(original) or getattr(original, "_mary_card_narrative_wrapped", False):
        return

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> str:
        base = str(original(*args, **kwargs) or "").strip()
        scenario_id, route = _context()
        screenplay = montar_janela_roteiro(scenario_id, route) if scenario_id and route else ""
        bridge = _bridge_prompt_block()
        return "\n\n".join(part for part in (base, screenplay, bridge) if part)

    wrapper._mary_card_narrative_wrapped = True  # type: ignore[attr-defined]
    setattr(module, "montar_direcao_narrativa", wrapper)


def _patch_process_interaction(module: Any) -> None:
    original = getattr(module, "processar_interacao", None)
    if not callable(original) or getattr(original, "_mary_card_process_wrapped", False):
        return

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        prompt = kwargs.get("prompt")
        if prompt is None and args:
            prompt = args[0]
        scenario_id, route = _arm_or_activate_bridge(prompt)
        if not scenario_id or not route:
            scenario_id, route = _context()
        if scenario_id and route:
            _sanitize_scene_state(scenario_id, route)
            relationship = st.session_state.get("relationship_state")
            sexual = relationship.get("sexual_state") if isinstance(relationship, dict) else {}
            constrained = aplicar_restricoes_card(
                scenario_id=scenario_id,
                route=route,
                mary_profile=st.session_state.get("mary_profile"),
                relationship_state=relationship,
                sexual_state=sexual,
                turn_intent=(relationship or {}).get("current_turn_intent")
                if isinstance(relationship, dict)
                else {},
                turn_direction=(relationship or {}).get("current_turn_direction")
                if isinstance(relationship, dict)
                else {},
            )
            st.session_state["relationship_state"] = constrained["relationship_state"]
        result = original(*args, **kwargs)
        _cache_recent_messages()
        return result

    wrapper._mary_card_process_wrapped = True  # type: ignore[attr-defined]
    setattr(module, "processar_interacao", wrapper)


def _wrap_continue(original: Callable[..., Any]) -> Callable[..., Any]:
    if getattr(original, "_mary_card_continue_wrapped", False):
        return original

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        result = original(*args, **kwargs)
        if not isinstance(result, tuple) or len(result) < 2:
            return result
        instance, messages = result[0], result[1]
        if not isinstance(instance, dict):
            return result
        return instance, _fallback_messages(instance, messages)

    wrapper._mary_card_continue_wrapped = True  # type: ignore[attr-defined]
    return wrapper


def _patch_continue(module: Any) -> None:
    service_current = scenario_service.continuar_cenario_para_usuario
    service_wrapped = _wrap_continue(service_current)
    scenario_service.continuar_cenario_para_usuario = service_wrapped

    menu_current = scenario_menu.continuar_cenario_para_usuario
    if menu_current is service_current or menu_current is service_wrapped:
        menu_wrapped = service_wrapped
    else:
        menu_wrapped = _wrap_continue(menu_current)
    scenario_menu.continuar_cenario_para_usuario = menu_wrapped

    current_main = getattr(module, "continuar_cenario_para_usuario", None)
    if callable(current_main):
        setattr(module, "continuar_cenario_para_usuario", _wrap_continue(current_main))


def aplicar_card_runtime() -> None:
    module = sys.modules.get("__main__")
    if module is None:
        return
    _patch_prompt_builder(module)
    _patch_narrative_direction(module)
    _patch_process_interaction(module)
    _patch_continue(module)


def install_card_runtime_integration() -> None:
    global _INSTALLED, _ORIGINAL_TITLE
    if _INSTALLED:
        return
    _ORIGINAL_TITLE = st.title

    @wraps(_ORIGINAL_TITLE)
    def patched_title(*args: Any, **kwargs: Any) -> Any:
        aplicar_card_runtime()
        assert _ORIGINAL_TITLE is not None
        return _ORIGINAL_TITLE(*args, **kwargs)

    st.title = patched_title
    _INSTALLED = True


__all__ = [
    "CARD_RUNTIME_INTEGRATION_VERSION",
    "aplicar_card_runtime",
    "install_card_runtime_integration",
]
