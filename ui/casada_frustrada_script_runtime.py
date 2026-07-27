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
from ui.casada_frustrada_canonical_prompt import (
    build_route_compass,
    question_policy,
)


CASADA_FRUSTRADA_SCRIPT_RUNTIME_VERSION = (
    "casada-frustrada-script-runtime-v6-full-route-calibration"
)
SCENARIO_ID = "casada_frustrada"
_INSTALLED = False
_ORIGINAL_TITLE: Callable[..., Any] | None = None
_ACTIVE_INSTANCE: dict[str, Any] | None = None


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

QUICK_BEATS = {
    "injury_check",
    "recognize_plaza",
    "first_farewell",
    "checkout_turn",
    "open_trunk",
    "car_farewell",
    "camera_setup",
    "end_first_call",
    "midnight_return",
    "motel_preparation",
    "motel_reunion",
    "final_departure",
}

CALL_ROUTE = "hidden_call"



def _text(value: Any) -> str:
    return str(value or "").strip()



def _normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKD", _text(value).casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()



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
    for item in reversed(_messages(16)):
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



def _question_streak() -> int:
    assistants = [
        item["content"]
        for item in _messages(12)
        if item.get("role") == "assistant"
    ]
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



def _scene(instance: dict[str, Any]) -> dict[str, Any]:
    value = instance.get("scene_state")
    return deepcopy(value) if isinstance(value, dict) else {}



def _valid_beat(value: Any) -> str:
    candidate = LEGACY_BEATS.get(_text(value), _text(value))
    return candidate if obter_beat(candidate) else ""



def _resolve_current_beat(scene: dict[str, Any], instance: dict[str, Any]) -> str:
    runtime = scene.get("script_runtime")
    runtime = runtime if isinstance(runtime, dict) else {}
    for value in (
        runtime.get("current_beat"),
        scene.get("current_beat"),
        instance.get("current_beat"),
    ):
        beat_id = _valid_beat(value)
        if beat_id:
            return beat_id
    route = _text(scene.get("current_route") or instance.get("current_route"))
    return ROUTE_DEFAULT_BEAT.get(route, INITIAL_BEAT)



def _runtime(instance: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], str]:
    scene = _scene(instance)
    beat_id = _resolve_current_beat(scene, instance)
    runtime = scene.get("script_runtime")
    runtime = deepcopy(runtime) if isinstance(runtime, dict) else {}
    previous = _valid_beat(runtime.get("current_beat"))
    if previous != beat_id:
        runtime["turns_in_beat"] = 0
        runtime["soft_hold"] = False
        runtime["pace_correction"] = False
    runtime.setdefault("completed", [])
    runtime.setdefault("last_emitted_beat", "")
    runtime.setdefault("turns_in_beat", 0)
    runtime.setdefault("soft_hold", False)
    runtime.setdefault("gate_attempts", 0)
    runtime.setdefault("pace_correction", False)
    runtime["current_beat"] = beat_id
    runtime["version"] = CASADA_FRUSTRADA_SCRIPT_RUNTIME_VERSION

    beat = obter_beat(beat_id) or {}
    route = _text(beat.get("route")) or _text(scene.get("current_route"))
    scene["script_runtime"] = runtime
    scene["current_beat"] = beat_id
    scene["current_route"] = route
    scene["sexual_scene_phase"] = _text(beat.get("sexual_phase")) or "idle"
    scene["seduction_level"] = int(beat.get("intensity", 0) or 0)
    instance["current_beat"] = beat_id
    instance["current_route"] = route
    instance["scene_state"] = scene
    return scene, runtime, beat_id



def _affirmative(text: str) -> bool:
    normalized = _normalize(text)
    return any(
        term in normalized
        for term in (
            "sim", "claro", "pode", "vamos", "aceito", "topo", "fechado",
            "combinado", "ta bom", "tudo bem", "manda", "liga", "chama",
            "eu vou", "estarei", "anota", "pode pegar", "quero", "beleza",
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



def _advance(
    instance: dict[str, Any],
    scene: dict[str, Any],
    runtime: dict[str, Any],
    beat_id: str,
) -> str:
    completed = list(runtime.get("completed") or [])
    if beat_id not in completed:
        completed.append(beat_id)
    beat = obter_beat(beat_id) or {}
    facts = list(scene.get("completed_story_facts") or [])
    for fact in beat.get("completes") or []:
        if fact not in facts:
            facts.append(fact)

    next_beat = proximo_beat_padrao(beat_id)
    runtime["completed"] = completed[-120:]
    runtime["last_emitted_beat"] = ""
    runtime["turns_in_beat"] = 0
    runtime["soft_hold"] = False
    runtime["pace_correction"] = False
    runtime["gate_attempts"] = 0
    scene["completed_story_facts"] = facts[-120:]

    if next_beat and obter_beat(next_beat):
        next_data = obter_beat(next_beat) or {}
        runtime["current_beat"] = next_beat
        scene["current_beat"] = next_beat
        scene["current_route"] = _text(next_data.get("route"))
        instance["current_beat"] = next_beat
        instance["current_route"] = scene["current_route"]
        return next_beat
    return beat_id



def _user_requests_slowdown(user_text: str) -> bool:
    text = _normalize(user_text)
    return any(
        marker in text
        for marker in (
            "calma", "devagar", "muito rapido", "indo rapido", "vamos com calma",
            "ta rapido", "esta rapido", "nao precisa correr",
        )
    )



def _user_deserves_breath(user_text: str, route: str, beat_id: str, turns_in_beat: int) -> bool:
    if route == CALL_ROUTE:
        return False
    if beat_id in QUICK_BEATS or turns_in_beat >= 1:
        return False
    text = _text(user_text)
    normalized = _normalize(text)
    if not normalized:
        return False
    asks_something = "?" in text or any(
        normalized.startswith(prefix)
        for prefix in ("como ", "por que ", "porque ", "e voce", "e vc", "ah e", "serio")
    )
    offers_material = len(normalized.split()) >= 9 and not _affirmative(text)
    playful = any(marker in normalized for marker in ("rsrs", "kkk", "brincando", "safado", "bobo"))
    return asks_something or offers_material or playful



def _history_overshot_messages_route(route: str) -> bool:
    if route != "messages":
        return False
    history = " ".join(_normalize(item["content"]) for item in _messages(12))
    explicit_markers = (
        "penetrar", "penetracao", "gozar dentro", "pau dentro", "xoxota",
        "clitoris", "chupar", "masturbar", "meter", "foder",
    )
    return any(marker in history for marker in explicit_markers)



def _consume_user_reply(instance: dict[str, Any], user_text: str) -> None:
    scene, runtime, beat_id = _runtime(instance)
    beat = obter_beat(beat_id) or {}
    route = _text(beat.get("route"))
    gate = _text(beat.get("gate"))
    emitted = _text(runtime.get("last_emitted_beat")) == beat_id or bool(_last_assistant())
    if not emitted:
        instance["scene_state"] = scene
        return

    turns = int(runtime.get("turns_in_beat", 0) or 0)
    if _user_requests_slowdown(user_text):
        runtime["pace_correction"] = True
        runtime["soft_hold"] = True
    elif gate:
        if _gate_satisfied(gate, user_text, _sexual_state()):
            _advance(instance, scene, runtime, beat_id)
        else:
            runtime["gate_attempts"] = int(runtime.get("gate_attempts", 0) or 0) + 1
            runtime["soft_hold"] = True
    elif route == CALL_ROUTE:
        # Na chamada, cada reação concluída abre o próximo marco. Material rico do
        # usuário não pode manter Mary perguntando indefinidamente no mesmo ponto.
        _advance(instance, scene, runtime, beat_id)
    elif _user_deserves_breath(user_text, route, beat_id, turns):
        runtime["soft_hold"] = True
    else:
        _advance(instance, scene, runtime, beat_id)

    scene["script_runtime"] = runtime
    instance["scene_state"] = scene



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
    scene, runtime, beat_id = _runtime(instance)
    beat = obter_beat(beat_id)
    if not beat:
        return ""

    route = _text(beat.get("route"))
    first_turn = int(runtime.get("turns_in_beat", 0) or 0) == 0
    transition = _text(beat.get("transition")) if first_turn else ""
    thought = _text(beat.get("thought")) if first_turn else ""
    gate = _text(beat.get("gate"))
    streak = _question_streak()
    q_policy = question_policy(route, streak, gate)
    overshot = _history_overshot_messages_route(route)
    sexual = _sexual_state()

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
        "screenplay": {
            "current_route": route,
            "full_route_compass": build_route_compass(route, beat_id),
            "current_milestone": {
                "beat": beat_id,
                "purpose": _text(beat.get("objective")),
                "lexical_seed_not_template": list(beat.get("examples") or [])[:1],
                "avoid": list(beat.get("avoid") or [])[:5],
                "gate": gate,
                "turns_here": int(runtime.get("turns_in_beat", 0) or 0),
                "soft_hold": bool(runtime.get("soft_hold")),
            },
            "pace_correction": bool(runtime.get("pace_correction")),
            "history_overshot_current_route": overshot,
            "transition": transition,
            "thought_seed": thought,
        },
        "question_control": q_policy,
        "sexual": {
            "phase": sexual.get("scene_phase"),
            "arousal": sexual.get("arousal_level"),
            "mary_orgasm_allowed": bool(sexual.get("mary_orgasm_allowed")),
            "mary_orgasm_done": bool(sexual.get("mary_orgasm_done")),
            "user_orgasm_done": bool(sexual.get("user_orgasm_done")),
        },
        "recent": _messages(8),
    }

    return (
        "Você interpreta Mary, brasileira adulta de 25 anos, na história Casada Frustrada.\n"
        "Leia primeiro a fala atual do usuário e responda ao sentido dela. O roteiro orienta a direção, não fornece texto para recitar.\n"
        "Você recebe o mapa completo da rota atual: use-o para saber de onde veio, onde está e como a cena deve terminar. Não execute todo o mapa; realize apenas o movimento atual.\n"
        "Na chamada, não substitua a sequência concreta por fantasia hipotética interminável. Reaja ao que foi confirmado e avance para o próximo marco visual ou corporal.\n"
        "Não crie uma pergunta por hábito. Respeite question_control: quando question_allowed=false, a resposta deve terminar em afirmação, reação ou ação de Mary, sem interrogação.\n"
        "Perguntas na chamada existem somente para decisões concretas do roteiro: aceitar vídeo, mostrar roupa/corpo, iniciar ato ou confirmar encontro.\n"
        "Se pace_correction=true, reconheça que acelerou, reduza a intensidade e reancore a cena no marco atual sem pedir nova validação.\n"
        "Se history_overshot_current_route=true, o histórico avançou sexualmente além dos fatos concretos: não continue a fantasia. Volte com naturalidade à privacidade, atração e proposta de vídeo previstas.\n"
        "As sementes lexicais não são modelos de resposta. Não copie nem parafraseie mecanicamente. Preserve a personalidade, a hesitação e a criatividade de Mary.\n"
        "Use 1 a 3 parágrafos curtos. Não invente ação, consentimento, sensação, fala ou orgasmo do usuário.\n"
        "Transição e pensamento não são falas audíveis; use-os apenas quando fornecidos e somente na entrada do marco.\n"
        "ESTADO="
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + "\nProduza apenas a próxima resposta natural de Mary."
    )



def _after_response(instance: dict[str, Any], assistant_before: int) -> None:
    if _assistant_count() <= assistant_before:
        return
    scene, runtime, beat_id = _runtime(instance)
    runtime["last_emitted_beat"] = beat_id
    runtime["turns_in_beat"] = int(runtime.get("turns_in_beat", 0) or 0) + 1
    runtime["soft_hold"] = False
    runtime["pace_correction"] = False
    runtime["gate_attempts"] = 0
    scene["script_runtime"] = runtime
    scene["last_mary_response"] = _last_assistant()
    scene["interaction_count"] = int(scene.get("interaction_count", 0) or 0) + 1
    instance["interaction_count"] = int(instance.get("interaction_count", 0) or 0) + 1

    if not proximo_beat_padrao(beat_id):
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
    if callable(prompt_builder) and not getattr(
        prompt_builder,
        "_casada_full_route_runtime",
        False,
    ):
        @wraps(prompt_builder)
        def prompt_wrapper(*args: Any, **kwargs: Any) -> str:
            if _instance() is not None:
                return _compact_prompt()
            return str(prompt_builder(*args, **kwargs) or "")

        prompt_wrapper._casada_full_route_runtime = True  # type: ignore[attr-defined]
        setattr(module, "montar_prompt_sistema", prompt_wrapper)

    processor = getattr(module, "processar_interacao", None)
    if callable(processor) and not getattr(
        processor,
        "_casada_full_route_runtime",
        False,
    ):
        @wraps(processor)
        def process_wrapper(*args: Any, **kwargs: Any) -> Any:
            global _ACTIVE_INSTANCE
            current = _session_instance()
            if not isinstance(current, dict):
                return processor(*args, **kwargs)

            prompt = kwargs.get("prompt")
            if prompt is None and args:
                prompt = args[0]

            _consume_user_reply(current, _text(prompt))
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

        process_wrapper._casada_full_route_runtime = True  # type: ignore[attr-defined]
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
