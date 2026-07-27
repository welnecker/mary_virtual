from __future__ import annotations

from copy import deepcopy
from functools import wraps
import json
import re
import sys
import unicodedata
from typing import Any, Callable

import streamlit as st

from repositories.scenario_session_repository import salvar_instancia_cenario
from scenarios.card_registry import obter_card
from scenarios.stories.casada_frustrada.beat_graph import (
    INITIAL_BEAT,
    obter_beat,
    proximo_beat_padrao,
)

CASADA_FRUSTRADA_RUNTIME_VERSION = "casada-frustrada-runtime-v3-preturn-progression"
SCENARIO_ID = "casada_frustrada"
_INSTALLED = False
_ORIGINAL_TITLE: Callable[..., Any] | None = None
_ACTIVE_INSTANCE_OVERRIDE: dict[str, Any] | None = None

LEGACY_BEATS = {
    "accidental_bump": "injury_check",
    "recognize_neighbor": "recognize_plaza",
    "second_encounter_in_aisle": "second_encounter",
    "cart_observation": "cart_single_guess",
    "checkout_wait": "checkout_turn",
    "phone_request": "request_phone",
    "first_private_message": "home_first_message",
    "first_message": "home_first_message",
    "seek_privacy": "seek_bathroom_privacy",
    "camera_confirmed": "camera_setup",
    "private_call_started": "camera_setup",
    "visual_escalation": "ask_remove_shirt",
    "react_to_torso": "react_torso",
    "mary_reveals_lingerie": "mary_remove_dress",
    "mutual_arousal": "guide_mutual_masturbation",
    "mutual_stimulation": "guide_mutual_masturbation",
    "user_release": "react_user_climax",
    "call_interrupted": "end_first_call",
    "after_call_message": "midnight_return",
    "midnight_call": "midnight_return",
    "confirm_motel": "name_motel",
    "arrival": "motel_reunion",
    "motel_arrival": "motel_preparation",
    "first_physical_contact": "ask_touch_butt",
    "mary_gives_pleasure": "offer_oral",
    "mary_receives_pleasure": "request_her_pleasure",
    "mary_first_orgasm": "first_orgasm",
    "penetration": "penetration_start",
    "aftercare": "post_penetration",
}

ROUTE_DEFAULT_BEAT = {
    "supermarket_encounter": "injury_check",
    "aisle_flirtation": "second_encounter",
    "phone_exchange": "request_phone",
    "messages": "home_first_message",
    "hidden_call": "camera_setup",
    "secret_meeting_plan": "midnight_return",
    "secret_meeting": "motel_preparation",
    "growing_tension": "ask_touch_butt",
    "intimacy": "offer_oral",
    "climax": "first_orgasm_build",
    "aftercare": "post_penetration",
    "future_secret": "final_departure",
}

PHYSICAL_CANON = {
    "skin": "pele clara",
    "eyes": "olhos verdes",
    "hair": "cabelos negros, longos e volumosos",
    "face": "rosto delicado com traços marcantes",
    "body": "corpo curvilíneo, cintura fina, quadris largos, bunda grande e coxas firmes",
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKD", _text(value).casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _session_instance() -> dict[str, Any] | None:
    value = st.session_state.get("scenario_instance")
    if not isinstance(value, dict) or _text(value.get("scenario_id")) != SCENARIO_ID:
        return None
    return value


def _instance() -> dict[str, Any] | None:
    if isinstance(_ACTIVE_INSTANCE_OVERRIDE, dict):
        return _ACTIVE_INSTANCE_OVERRIDE
    return _session_instance()


def _messages(limit: int = 8) -> list[dict[str, str]]:
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
            result.append({"role": role, "content": content[:900]})
    return result


def _last_assistant() -> str:
    for item in reversed(_messages(12)):
        if item["role"] == "assistant":
            return item["content"]
    return ""


def _assistant_count() -> int:
    value = st.session_state.get("messages")
    if not isinstance(value, list):
        return 0
    return sum(
        1
        for item in value
        if isinstance(item, dict) and item.get("role") == "assistant"
    )


def _sexual_state() -> dict[str, Any]:
    relationship = st.session_state.get("relationship_state")
    if not isinstance(relationship, dict):
        return {}
    sexual = relationship.get("sexual_state")
    return deepcopy(sexual) if isinstance(sexual, dict) else {}


def _scene(instance: dict[str, Any]) -> dict[str, Any]:
    value = instance.get("scene_state")
    return deepcopy(value) if isinstance(value, dict) else {}


def _resolved_candidate(value: Any) -> str:
    candidate = LEGACY_BEATS.get(_text(value), _text(value))
    return candidate if obter_beat(candidate) else ""


def _resolve_beat(scene: dict[str, Any], instance: dict[str, Any]) -> str:
    runtime = scene.get("script_runtime")
    runtime = runtime if isinstance(runtime, dict) else {}
    for candidate in (
        runtime.get("current_beat"),
        scene.get("current_beat"),
        instance.get("current_beat"),
    ):
        resolved = _resolved_candidate(candidate)
        if resolved:
            return resolved
    route = _text(scene.get("current_route") or instance.get("current_route"))
    return ROUTE_DEFAULT_BEAT.get(route, INITIAL_BEAT)


def _runtime_state(instance: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], str]:
    scene = _scene(instance)
    beat_id = _resolve_beat(scene, instance)
    runtime = scene.get("script_runtime")
    runtime = deepcopy(runtime) if isinstance(runtime, dict) else {}
    previous = _resolved_candidate(runtime.get("current_beat"))
    if previous != beat_id:
        runtime["awaiting_user"] = False
        runtime["attempts"] = 0
    runtime["current_beat"] = beat_id
    runtime.setdefault("completed", [])
    runtime.setdefault("awaiting_user", bool(_last_assistant()))
    runtime.setdefault("attempts", 0)
    runtime["version"] = CASADA_FRUSTRADA_RUNTIME_VERSION

    beat = obter_beat(beat_id) or {}
    scene["script_runtime"] = runtime
    scene["current_beat"] = beat_id
    scene["current_route"] = _text(beat.get("route")) or _text(scene.get("current_route"))
    scene["sexual_scene_phase"] = _text(beat.get("sexual_phase")) or "idle"
    scene["seduction_level"] = int(beat.get("intensity", 0) or 0)
    instance["current_beat"] = beat_id
    instance["current_route"] = scene["current_route"]
    instance["scene_state"] = scene
    return scene, runtime, beat_id


def _affirmative(text: str) -> bool:
    return any(
        term in text
        for term in (
            "sim", "claro", "pode", "vamos", "aceito", "topo", "fechado",
            "combinado", "ta bom", "tudo bem", "manda", "liga", "chama",
            "eu vou", "estarei", "anota", "pode pegar",
        )
    )


def _gate_satisfied(gate: str, user_text: str, sexual: dict[str, Any]) -> bool:
    text = _normalize(user_text)
    if not gate:
        return True
    if gate == "farewell":
        return bool(text)
    if gate == "accept_help_car":
        return _affirmative(text) or any(term in text for term in ("te ajudo", "espero", "vamos ao carro"))
    if gate == "phone_acceptance":
        return _affirmative(text) or any(char.isdigit() for char in user_text) or "meu numero" in text
    if gate == "video_acceptance":
        return _affirmative(text) or any(term in text for term in ("video", "camera", "pode chamar"))
    if gate == "shirt_acceptance":
        return _affirmative(text) or any(term in text for term in ("tirei", "sem camisa", "peitoral"))
    if gate == "pants_acceptance":
        return _affirmative(text) or any(term in text for term in ("tirei a calca", "de cueca", "so de cueca"))
    if gate == "bra_request":
        return _affirmative(text) or any(term in text for term in ("tira o sutia", "mostra os seios", "quero ver"))
    if gate == "underwear_acceptance":
        return _affirmative(text) or any(term in text for term in ("tirei a cueca", "pelado", "nu"))
    if gate == "mutual_acceptance":
        return _affirmative(text) or any(term in text for term in ("topo", "vamos", "ja comecei"))
    if gate == "user_climax":
        return bool(sexual.get("user_orgasm_done")) or any(term in text for term in ("gozei", "gozando", "gozar", "gozo"))
    if gate == "meeting_interest":
        return _affirmative(text) or any(term in text for term in ("motel", "onde", "quando"))
    if gate == "meeting_acceptance":
        return _affirmative(text) or any(term in text for term in ("meio dia", "motel status", "estarei la"))
    if gate == "arrival":
        return any(term in text for term in ("cheguei", "to aqui", "estou aqui", "na porta", "no motel"))
    if gate == "mary_orgasm_allowed":
        return bool(sexual.get("mary_orgasm_allowed"))
    if gate == "erection_confirmed":
        return _affirmative(text) or any(term in text for term in ("duro", "erecao", "pronto de novo"))
    if gate == "penetration_acceptance":
        return _affirmative(text) or any(term in text for term in ("entrei", "metendo", "dentro"))
    return _affirmative(text)


def _injury_resolved(user_text: str) -> bool:
    text = _normalize(user_text)
    resolved_phrases = (
        "ta tudo bem", "tudo bem", "to bem", "estou bem", "foi mais um susto",
        "foi um susto", "foi susto", "nao machucou", "nao me machucou",
        "nao doeu", "nao quebrou", "so ta doendo", "so doeu", "melhorando",
        "ja ta melhor", "consigo andar", "nao precisa", "vou terminar", "aguento",
    )
    return _affirmative(text) or any(term in text for term in resolved_phrases)


def _advance(instance: dict[str, Any], scene: dict[str, Any], runtime: dict[str, Any], beat_id: str) -> str:
    completed = list(runtime.get("completed") or [])
    if beat_id not in completed:
        completed.append(beat_id)
    beat = obter_beat(beat_id) or {}
    facts = list(scene.get("completed_story_facts") or [])
    for fact in beat.get("completes") or []:
        if fact not in facts:
            facts.append(fact)

    next_beat = proximo_beat_padrao(beat_id)
    runtime["completed"] = completed[-100:]
    runtime["attempts"] = 0
    runtime["awaiting_user"] = False
    scene["completed_story_facts"] = facts[-100:]

    if next_beat and obter_beat(next_beat):
        runtime["current_beat"] = next_beat
        next_data = obter_beat(next_beat) or {}
        scene["current_beat"] = next_beat
        scene["current_route"] = _text(next_data.get("route"))
        instance["current_beat"] = next_beat
        instance["current_route"] = scene["current_route"]
        return next_beat
    return beat_id


def _prepare_for_turn(user_text: str) -> dict[str, Any] | None:
    instance = _session_instance()
    if not isinstance(instance, dict):
        return None

    scene, runtime, beat_id = _runtime_state(instance)
    sexual = _sexual_state()

    if bool(runtime.get("awaiting_user")):
        beat = obter_beat(beat_id) or {}
        gate = _text(beat.get("gate"))
        attempts = int(runtime.get("attempts", 0) or 0)

        if beat_id == "injury_check":
            satisfied = _injury_resolved(user_text)
            if not satisfied and attempts >= 1:
                satisfied = True
        elif gate:
            satisfied = _gate_satisfied(gate, user_text, sexual)
        else:
            satisfied = True

        if satisfied:
            beat_id = _advance(instance, scene, runtime, beat_id)
        else:
            runtime["attempts"] = attempts + 1
            runtime["awaiting_user"] = False

    scene["script_runtime"] = runtime
    instance["scene_state"] = scene
    instance["scenario_prompt"] = ""
    st.session_state["scenario_instance"] = instance
    return instance


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


def _compact_prompt() -> str:
    instance = _instance()
    if not isinstance(instance, dict):
        return ""
    scene, runtime, beat_id = _runtime_state(instance)
    beat = obter_beat(beat_id)
    if not beat:
        return ""

    sexual = _sexual_state()
    transition = _text(beat.get("transition"))
    thought = _text(beat.get("thought"))
    payload = {
        "character": _character_payload(),
        "scene": {
            key: scene.get(key)
            for key in (
                "location", "time_context", "mary_clothing", "user_clothing",
                "position", "privacy_established", "video_call_established",
            )
            if scene.get(key) not in (None, "", False)
        },
        "script": {
            "route": beat.get("route"),
            "beat": beat_id,
            "objective": beat.get("objective"),
            "examples": list(beat.get("examples") or [])[:2],
            "avoid": list(beat.get("avoid") or [])[:5],
            "gate": beat.get("gate") or "",
            "gate_pending_attempts": int(runtime.get("attempts", 0) or 0),
            "transition": transition,
            "thought": thought,
        },
        "sexual": {
            "phase": sexual.get("scene_phase"),
            "arousal": sexual.get("arousal_level"),
            "mary_orgasm_allowed": bool(sexual.get("mary_orgasm_allowed")),
            "mary_orgasm_done": bool(sexual.get("mary_orgasm_done")),
            "user_orgasm_done": bool(sexual.get("user_orgasm_done")),
        },
        "recent": _messages(6),
    }

    formatting: list[str] = []
    if transition:
        formatting.append("Comece com a transição em uma única citação Markdown: > *texto da transição*. Ela não é fala audível.")
    if thought:
        formatting.append("Depois, escreva o pensamento privado em linha isolada exatamente como 'Pensamento de Mary: ...'. Ele não é audível.")
    formatting.append("Finalize com somente a fala direta prevista para este beat.")

    return (
        "Você é Mary, brasileira adulta de 25 anos, na história Casada Frustrada.\n"
        "O roteiro decide exatamente O QUE acontece neste turno. Você decide apenas COMO formular.\n"
        "Execute o beat atual; não abra assunto paralelo, não faça entrevista e não antecipe o próximo passo.\n"
        "Use as referências como direção lexical. Preserve a intenção, a intensidade e a ordem do roteiro.\n"
        "No máximo uma pergunta. Não invente ação, consentimento, sensação ou orgasmo do usuário.\n"
        "Fala direta é audível. Pensamento e transição não são falas.\n"
        + " ".join(formatting)
        + "\nESTADO="
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + "\nProduza somente a resposta de Mary e pare ao concluir este beat."
    )


def _after_response(instance: dict[str, Any], assistant_before: int) -> None:
    if _assistant_count() <= assistant_before:
        return
    scene, runtime, beat_id = _runtime_state(instance)
    runtime["awaiting_user"] = True
    scene["script_runtime"] = runtime
    scene["last_mary_response"] = _last_assistant()
    scene["interaction_count"] = int(scene.get("interaction_count", 0) or 0) + 1
    instance["interaction_count"] = int(instance.get("interaction_count", 0) or 0) + 1

    if not proximo_beat_padrao(beat_id):
        instance.update({
            "status": "completed", "ending_ready": True, "ending_sent": True,
            "input_locked": True, "show_return_to_menu": True,
            "ending_type": "script_completed", "ending_reason": "final_departure",
        })
        scene.update({
            "ending_ready": True, "ending_sent": True,
            "input_locked": True, "show_return_to_menu": True,
        })

    instance["scene_state"] = scene
    instance["scenario_prompt"] = ""
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
    if callable(prompt_builder) and not getattr(prompt_builder, "_casada_full_script_runtime", False):
        @wraps(prompt_builder)
        def prompt_wrapper(*args: Any, **kwargs: Any) -> str:
            if _instance() is not None:
                return _compact_prompt()
            return str(prompt_builder(*args, **kwargs) or "")
        prompt_wrapper._casada_full_script_runtime = True
        setattr(module, "montar_prompt_sistema", prompt_wrapper)

    processor = getattr(module, "processar_interacao", None)
    if callable(processor) and not getattr(processor, "_casada_full_script_runtime", False):
        @wraps(processor)
        def process_wrapper(*args: Any, **kwargs: Any) -> Any:
            global _ACTIVE_INSTANCE_OVERRIDE
            current = _session_instance()
            if not isinstance(current, dict):
                return processor(*args, **kwargs)

            prompt = kwargs.get("prompt")
            if prompt is None and args:
                prompt = args[0]
            prepared = _prepare_for_turn(_text(prompt))
            if not isinstance(prepared, dict):
                return processor(*args, **kwargs)

            assistant_before = _assistant_count()
            _ACTIVE_INSTANCE_OVERRIDE = prepared
            st.session_state["scenario_instance"] = None
            try:
                result = processor(*args, **kwargs)
            finally:
                st.session_state["scenario_instance"] = prepared
                _ACTIVE_INSTANCE_OVERRIDE = prepared

            _after_response(prepared, assistant_before)
            _ACTIVE_INSTANCE_OVERRIDE = None
            return result
        process_wrapper._casada_full_script_runtime = True
        setattr(module, "processar_interacao", process_wrapper)


def install_casada_frustrada_runtime() -> None:
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


__all__ = ["CASADA_FRUSTRADA_RUNTIME_VERSION", "install_casada_frustrada_runtime"]
