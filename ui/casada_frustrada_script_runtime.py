from __future__ import annotations

from copy import deepcopy
from functools import wraps
import json
import re
import sys
from typing import Any, Callable

import streamlit as st

from repositories.scenario_session_repository import salvar_instancia_cenario
from scenarios.card_registry import obter_card
from scenarios.stories.casada_frustrada.story_director import dirigir_turno


CASADA_FRUSTRADA_SCRIPT_RUNTIME_VERSION = (
    "casada-frustrada-script-runtime-v7-logical-bridge"
)
SCENARIO_ID = "casada_frustrada"
_STORY_STATE_SESSION_KEY = "casada_frustrada_story_state"
_MEMORY_SESSION_KEY = "casada_frustrada_canonical_memory"
_INSTALLED = False
_ORIGINAL_TITLE: Callable[..., Any] | None = None
_ACTIVE_INSTANCE: dict[str, Any] | None = None

PHYSICAL_CANON = {
    "skin": "pele clara",
    "eyes": "olhos verdes",
    "hair": "cabelos negros, longos e volumosos",
    "face": "rosto delicado com traços marcantes",
    "body": "corpo curvilíneo, cintura fina, quadris largos, bunda grande e coxas firmes",
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _session_instance() -> dict[str, Any] | None:
    value = st.session_state.get("scenario_instance")
    if not isinstance(value, dict):
        return None
    if _text(value.get("scenario_id")) != SCENARIO_ID:
        return None
    return value


def _instance() -> dict[str, Any] | None:
    if isinstance(_ACTIVE_INSTANCE, dict):
        return _ACTIVE_INSTANCE
    return _session_instance()


def _messages(limit: int = 100) -> list[dict[str, str]]:
    value = st.session_state.get("messages")
    if not isinstance(value, list):
        return []
    result: list[dict[str, str]] = []
    for item in value[-limit:]:
        if not isinstance(item, dict):
            continue
        role = _text(item.get("role"))
        content = _text(item.get("content"))
        if role in {"user", "assistant"} and content:
            result.append({"role": role, "content": content[:4000]})
    return result


def _last_assistant() -> str:
    for item in reversed(_messages(30)):
        if item["role"] == "assistant":
            return item["content"]
    return ""


def _assistant_count() -> int:
    return sum(1 for item in _messages(500) if item["role"] == "assistant")


def _question_streak() -> int:
    assistants = [item["content"] for item in _messages(16) if item["role"] == "assistant"]
    streak = 0
    for content in reversed(assistants):
        if "?" not in content:
            break
        streak += 1
    return streak


def _sexual_state() -> dict[str, Any]:
    relationship = st.session_state.get("relationship_state")
    if not isinstance(relationship, dict):
        return {}
    sexual = relationship.get("sexual_state")
    return deepcopy(sexual) if isinstance(sexual, dict) else {}


def _character_payload() -> dict[str, Any]:
    card = obter_card(SCENARIO_ID) or {}
    character = card.get("character") if isinstance(card.get("character"), dict) else {}
    psychology = card.get("psychology") if isinstance(card.get("psychology"), dict) else {}
    voice = card.get("voice") if isinstance(card.get("voice"), dict) else {}
    return {
        "physical": PHYSICAL_CANON,
        "psychology": {
            "core": list(character.get("core_traits") or [])[:5],
            "latent": list(character.get("latent_traits") or [])[:4],
            "contradictions": list(character.get("contradictions") or [])[:3],
            "route_expression": psychology.get("route_expression", {}),
        },
        "voice": {
            "register": voice.get("default_register", "popular, íntimo e direto"),
            "humor": voice.get("humor", "contextual"),
        },
    }


def _build_prompt() -> str:
    instance = _instance()
    if not isinstance(instance, dict):
        return ""

    messages = _messages(100)
    direction = dirigir_turno(
        instance=instance,
        messages=messages,
        story_state_value=st.session_state.get(_STORY_STATE_SESSION_KEY),
    )
    st.session_state[_STORY_STATE_SESSION_KEY] = direction.get("story_state", {})
    st.session_state[_MEMORY_SESSION_KEY] = deepcopy(instance.get("story_memory", {}))

    gate = _text(direction.get("gate"))
    streak = _question_streak()
    question_allowed = bool(gate) or streak < 2
    sexual = _sexual_state()
    scene = instance.get("scene_state")
    scene = scene if isinstance(scene, dict) else {}

    payload = {
        "character": _character_payload(),
        "scene": {
            key: scene.get(key)
            for key in (
                "location",
                "time_context",
                "mary_clothing",
                "user_clothing",
                "position",
                "privacy_established",
                "video_call_established",
            )
            if scene.get(key) not in (None, "", False)
        },
        "story_direction": direction,
        "question_control": {
            "recent_question_streak": streak,
            "question_allowed": question_allowed,
            "reason": (
                "A única função aberta depende de uma decisão concreta do usuário."
                if gate
                else "Evitar nova pergunta automática depois de duas respostas interrogativas."
                if not question_allowed
                else "Pergunta opcional; responder primeiro ao usuário."
            ),
        },
        "sexual": {
            "phase": sexual.get("scene_phase"),
            "arousal": sexual.get("arousal_level"),
            "mary_orgasm_allowed": bool(sexual.get("mary_orgasm_allowed")),
            "mary_orgasm_done": bool(sexual.get("mary_orgasm_done")),
            "user_orgasm_done": bool(sexual.get("user_orgasm_done")),
        },
        "output_contract": {
            "speech": "Fala audível de Mary em texto normal, sem rótulo.",
            "thought": (
                "Pensamento privado é opcional, dinâmico, em primeira pessoa e iniciado por "
                "'Pensamento de Mary:'. Pode aparecer antes, entre ou depois das falas, no ponto "
                "em que ocorre mentalmente; nunca em posição fixa."
            ),
            "forbidden_narration": (
                "Não escrever ponte, rubrica, descrição externa nem narração em terceira pessoa."
            ),
        },
        "recent": messages[-12:],
    }

    return (
        "Você interpreta Mary, brasileira adulta de 25 anos, na história Casada Frustrada.\n"
        "Responda primeiro ao sentido da fala atual do usuário.\n"
        "story_direction é a única autoridade narrativa deste turno. Ela já conciliou memória "
        "canônica, fatos visuais, beat_graph.py e immersive_screenplay.py.\n"
        "Não existe milestone paralelo, cursor oculto ou checklist de um beat por turno.\n"
        "Use objective como função aberta, não como frase obrigatória. O trecho do roteiro fornece "
        "direção dramática; não o recite nem execute vários movimentos futuros.\n"
        "Nunca repita como primeira vez algo registrado em canonical_story_memory ou "
        "confirmed_visual_state.\n"
        "Na chamada, reaja ao que está visualmente confirmado. Não peça novamente uma ação já "
        "cumprida e não invente uma ação ainda não confirmada pelo usuário.\n"
        "Quando question_allowed=false, termine em afirmação ou reação, sem interrogação.\n"
        "Use 1 a 3 parágrafos curtos. Não invente fala, consentimento, sensação ou ação do usuário.\n"
        "ESTADO="
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + "\nProduza apenas a próxima resposta natural de Mary."
    )


def _after_response(instance: dict[str, Any], assistant_before: int) -> None:
    if _assistant_count() <= assistant_before:
        return
    scene = instance.get("scene_state")
    scene = deepcopy(scene) if isinstance(scene, dict) else {}
    scene["last_mary_response"] = _last_assistant()
    scene["interaction_count"] = int(scene.get("interaction_count", 0) or 0) + 1
    instance["interaction_count"] = int(instance.get("interaction_count", 0) or 0) + 1

    if _text(instance.get("current_beat")) == "final_departure":
        instance.update({
            "status": "completed",
            "ending_ready": True,
            "ending_sent": True,
            "input_locked": True,
            "show_return_to_menu": True,
            "ending_type": "script_completed",
            "ending_reason": "final_departure",
        })
        scene.update({
            "ending_ready": True,
            "ending_sent": True,
            "input_locked": True,
            "show_return_to_menu": True,
        })

    instance["scene_state"] = scene
    instance["scenario_prompt"] = ""
    memory = st.session_state.get(_MEMORY_SESSION_KEY)
    if isinstance(memory, dict):
        instance["story_memory"] = deepcopy(memory)
    st.session_state["scenario_instance"] = instance
    try:
        salvar_instancia_cenario(instance, houve_interacao=True)
    except Exception:
        pass


def _patch_main() -> None:
    module = sys.modules.get("__main__")
    if module is None:
        return

    prompt_builder = getattr(module, "montar_prompt_sistema", None)
    if callable(prompt_builder) and not getattr(prompt_builder, "_casada_logical_bridge", False):
        @wraps(prompt_builder)
        def prompt_wrapper(*args: Any, **kwargs: Any) -> str:
            if _instance() is not None:
                return _build_prompt()
            return str(prompt_builder(*args, **kwargs) or "")

        prompt_wrapper._casada_logical_bridge = True  # type: ignore[attr-defined]
        setattr(module, "montar_prompt_sistema", prompt_wrapper)

    processor = getattr(module, "processar_interacao", None)
    if callable(processor) and not getattr(processor, "_casada_logical_bridge", False):
        @wraps(processor)
        def process_wrapper(*args: Any, **kwargs: Any) -> Any:
            global _ACTIVE_INSTANCE
            current = _session_instance()
            if not isinstance(current, dict):
                return processor(*args, **kwargs)

            current["scenario_prompt"] = ""
            st.session_state["scenario_instance"] = current
            assistant_before = _assistant_count()
            _ACTIVE_INSTANCE = current
            st.session_state["scenario_instance"] = None
            try:
                result = processor(*args, **kwargs)
            finally:
                st.session_state["scenario_instance"] = current
                _ACTIVE_INSTANCE = current

            _after_response(current, assistant_before)
            _ACTIVE_INSTANCE = None
            return result

        process_wrapper._casada_logical_bridge = True  # type: ignore[attr-defined]
        setattr(module, "processar_interacao", process_wrapper)


def install_casada_frustrada_script_runtime() -> None:
    global _INSTALLED, _ORIGINAL_TITLE
    if _INSTALLED:
        return
    _patch_main()
    _ORIGINAL_TITLE = st.title

    @wraps(_ORIGINAL_TITLE)
    def patched_title(*args: Any, **kwargs: Any) -> Any:
        _patch_main()
        assert _ORIGINAL_TITLE is not None
        return _ORIGINAL_TITLE(*args, **kwargs)

    st.title = patched_title
    _INSTALLED = True


__all__ = [
    "CASADA_FRUSTRADA_SCRIPT_RUNTIME_VERSION",
    "install_casada_frustrada_script_runtime",
]
