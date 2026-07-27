from __future__ import annotations

from copy import deepcopy
from functools import wraps
import json
import sys
from typing import Any, Callable

import streamlit as st

from repositories.scenario_session_repository import salvar_instancia_cenario
from scenarios.card_registry import obter_card
from scenarios.stories.casada_frustrada.refusal_lock import detectar_trava_psicologica
from scenarios.stories.casada_frustrada.story_director import dirigir_turno


CASADA_FRUSTRADA_SCRIPT_RUNTIME_VERSION = (
    "casada-frustrada-script-runtime-v9-locked-screenplay"
)
SCENARIO_ID = "casada_frustrada"
_STORY_STATE_SESSION_KEY = "casada_frustrada_story_state"
_MEMORY_SESSION_KEY = "casada_frustrada_canonical_memory"
_DIRECTION_SESSION_KEY = "casada_frustrada_last_story_direction"
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
    if not isinstance(value, dict) or _text(value.get("scenario_id")) != SCENARIO_ID:
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


def _open_beat_before_resolution(instance: dict[str, Any]) -> str:
    scene = instance.get("scene_state")
    scene = scene if isinstance(scene, dict) else {}
    return _text(scene.get("current_beat") or instance.get("current_beat"))


def _build_prompt() -> str:
    instance = _instance()
    if not isinstance(instance, dict):
        return ""

    messages = _messages(120)
    open_beat = _open_beat_before_resolution(instance)
    refusal_lock = detectar_trava_psicologica(messages=messages, open_beat=open_beat)
    direction = dirigir_turno(
        instance=instance,
        messages=messages,
        story_state_value=st.session_state.get(_STORY_STATE_SESSION_KEY),
    )

    if refusal_lock:
        direction["psychological_lock"] = refusal_lock
        direction["objective"] = refusal_lock["final_direction"]
        direction["gate"] = ""
        direction["avoid"] = [
            "Não negociar.",
            "Não oferecer outra chance.",
            "Não fazer nova pergunta.",
            "Não reabrir o roteiro.",
        ]

    st.session_state[_STORY_STATE_SESSION_KEY] = direction.get("story_state", {})
    st.session_state[_MEMORY_SESSION_KEY] = deepcopy(instance.get("story_memory", {}))
    st.session_state[_DIRECTION_SESSION_KEY] = deepcopy(direction)

    gate = _text(direction.get("gate"))
    streak = _question_streak()
    question_allowed = False if refusal_lock else bool(gate) or streak < 2
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
                "A trava psicológica encerra a interação sem nova pergunta."
                if refusal_lock
                else "A ação atual depende de confirmação concreta do usuário."
                if gate
                else "Evitar nova pergunta automática depois de duas respostas interrogativas."
                if not question_allowed
                else "Pergunta permitida apenas quando necessária ao beat atual."
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
                "'Pensamento de Mary:'. Pode aparecer antes, entre ou depois das falas, exatamente "
                "quando surgir na lógica do turno."
            ),
            "forbidden_narration": (
                "Não escrever ponte, rubrica, descrição externa nem narração em terceira pessoa."
            ),
        },
        "recent": messages[-12:],
    }

    refusal_instruction = (
        "psychological_lock está ativo. Produza uma única despedida emocional e definitiva, "
        "seguindo final_direction. Não negocie, não ameace dano e não ofereça continuação.\n"
        if refusal_lock
        else ""
    )

    return (
        "Você interpreta Mary, brasileira adulta de 25 anos, na história Casada Frustrada.\n"
        "Responda primeiro ao sentido imediato da fala do usuário, mas sem abandonar o roteiro.\n"
        "story_direction é a única autoridade narrativa.\n"
        "screenplay_lock.current_beat é o único movimento disponível neste turno.\n"
        "Execute somente screenplay_lock.mandatory_objective. A forma verbal pode ser natural, "
        "mas a ação, roupa, posição, contato e consequência devem corresponder exatamente a esse beat.\n"
        "screenplay_lock.next_beat_locked e next_objective_locked estão PROIBIDOS neste turno. "
        "Não antecipe, não misture e não substitua o beat atual por uma sensualidade genérica.\n"
        "Não escolha atos a partir do restante da história: o roteiro completo não é um cardápio.\n"
        "Nunca invente roupa retirada, toque, posição, consentimento, prazer ou orgasmo não confirmados.\n"
        "Nunca repita algo já registrado em screenplay_execution, canonical_story_memory ou "
        "confirmed_visual_state.\n"
        + refusal_instruction
        + "Quando question_allowed=false, termine sem interrogação.\n"
        "Use 1 a 3 parágrafos curtos. Não escreva narração em terceira pessoa.\n"
        "ESTADO="
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + "\nProduza apenas a próxima resposta natural de Mary."
    )


def _mark_completed(
    instance: dict[str, Any],
    scene: dict[str, Any],
    *,
    ending_type: str,
    ending_reason: str,
) -> None:
    instance.update({
        "status": "completed",
        "ending_ready": True,
        "ending_sent": True,
        "ending_forced": True,
        "input_locked": True,
        "show_return_to_menu": True,
        "ending_type": ending_type,
        "ending_reason": ending_reason,
        "requires_new_paid_cycle": True,
    })
    scene.update({
        "ending_ready": True,
        "ending_sent": True,
        "ending_forced": True,
        "input_locked": True,
        "show_return_to_menu": True,
        "requires_new_paid_cycle": True,
    })


def _after_response(instance: dict[str, Any], assistant_before: int) -> None:
    if _assistant_count() <= assistant_before:
        return
    scene = instance.get("scene_state")
    scene = deepcopy(scene) if isinstance(scene, dict) else {}
    scene["last_mary_response"] = _last_assistant()
    scene["interaction_count"] = int(scene.get("interaction_count", 0) or 0) + 1
    instance["interaction_count"] = int(instance.get("interaction_count", 0) or 0) + 1

    direction = st.session_state.get(_DIRECTION_SESSION_KEY)
    direction = direction if isinstance(direction, dict) else {}
    refusal_lock = direction.get("psychological_lock")
    if isinstance(refusal_lock, dict) and refusal_lock.get("input_locked_after_response"):
        _mark_completed(
            instance,
            scene,
            ending_type=_text(refusal_lock.get("ending_type")) or "psychological_refusal_lock",
            ending_reason=_text(refusal_lock.get("ending_reason")) or "user_refusal",
        )
        scene["psychological_lock"] = deepcopy(refusal_lock)
    elif _text(instance.get("current_beat")) == "final_departure":
        _mark_completed(
            instance,
            scene,
            ending_type="script_completed",
            ending_reason="final_departure",
        )

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
