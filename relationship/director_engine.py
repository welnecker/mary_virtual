from __future__ import annotations

from copy import deepcopy
from typing import Any

from relationship.initiative_engine import (
    TOPIC_DIRECTION_BOUNDARY,
    TOPIC_DIRECTION_CURRENT,
    TOPIC_DIRECTION_EMOTIONAL,
    TOPIC_DIRECTION_NEW_TOPIC,
    TOPIC_DIRECTION_PERSONAL,
    TOPIC_DIRECTION_RELATIONSHIP,
    TOPIC_DIRECTION_ROMANTIC,
    TOPIC_DIRECTION_SEXUAL,
    TURN_MODE_CHANGE_TOPIC,
    TURN_MODE_INCREASE_INTIMACY,
    TURN_MODE_INITIATE_FLIRT,
    TURN_MODE_INITIATE_SEXUAL_SCENE,
    TURN_MODE_INITIATE_SEXUAL_TENSION,
    TURN_MODE_RESPOND,
    TURN_MODE_SEEK_AFFECTION,
    TURN_MODE_SET_BOUNDARY,
    TURN_MODE_SHARE,
    TURN_MODE_SHOW_IRRITATION,
    TURN_MODE_SLOW_DOWN,
    TURN_MODE_TEASE,
    criar_intencao_turno_padrao,
    normalizar_estado_interno_mary,
)


EXPERIENCE_MODE_NATURAL = "natural_conversation"
EXPERIENCE_MODE_PERSONAL_SHARE = "personal_share"
EXPERIENCE_MODE_UNEXPECTED_CONFESSION = "unexpected_confession"
EXPERIENCE_MODE_PLAYFUL_CHALLENGE = "playful_challenge"
EXPERIENCE_MODE_PRIVATE_JOKE = "private_joke"
EXPERIENCE_MODE_MEMORY_CALLBACK = "memory_callback"
EXPERIENCE_MODE_UNFINISHED_REVEAL = "unfinished_reveal"
EXPERIENCE_MODE_EMOTIONAL_REVERSAL = "emotional_reversal"
EXPERIENCE_MODE_GENTLE_PROVOCATION = "gentle_provocation"
EXPERIENCE_MODE_BOLD_PROVOCATION = "bold_provocation"
EXPERIENCE_MODE_ROMANTIC_ESCALATION = "romantic_escalation"
EXPERIENCE_MODE_SEXUAL_TENSION = "sexual_tension"
EXPERIENCE_MODE_SEXUAL_INITIATIVE = "sexual_initiative"
EXPERIENCE_MODE_SEEK_AFFECTION = "seek_affection"
EXPERIENCE_MODE_SHOW_JEALOUSY = "show_jealousy"
EXPERIENCE_MODE_SHOW_VULNERABILITY = "show_vulnerability"
EXPERIENCE_MODE_SET_BOUNDARY = "set_boundary"
EXPERIENCE_MODE_CREATE_SHARED_PLAN = "create_shared_plan"
EXPERIENCE_MODE_CONTINUE_SHARED_FANTASY = "continue_shared_fantasy"
EXPERIENCE_MODE_SURPRISE_TOPIC = "surprise_topic"
EXPERIENCE_MODE_HUMOR_BREAK = "humor_break"
EXPERIENCE_MODE_AFTERCARE = "aftercare"
EXPERIENCE_MODE_FRUSTRATION = "frustration"

VOICE_REGISTER_NATURAL = "natural"
VOICE_REGISTER_PLAYFUL = "playful"
VOICE_REGISTER_WARM = "warm"
VOICE_REGISTER_ROMANTIC = "romantic"
VOICE_REGISTER_VULNERABLE = "vulnerable"
VOICE_REGISTER_TEASING = "teasing"
VOICE_REGISTER_BOLD = "bold"
VOICE_REGISTER_EXPLICIT_PLAYFUL = "explicit_playful"
VOICE_REGISTER_EXPLICIT_INTENSE = "explicit_intense"
VOICE_REGISTER_AFFECTIONATE_SEXUAL = "affectionate_sexual"
VOICE_REGISTER_IRRITATED = "irritated"
VOICE_REGISTER_BOUNDARY = "boundary"
VOICE_REGISTER_AFTERCARE = "aftercare"

THREAD_TYPE_UNFINISHED_REVEAL = "unfinished_reveal"
THREAD_TYPE_PROMISE = "promise"
THREAD_TYPE_PRIVATE_JOKE = "private_joke"
THREAD_TYPE_SHARED_PLAN = "shared_plan"
THREAD_TYPE_EMOTIONAL_QUESTION = "emotional_question"
THREAD_TYPE_ROMANTIC_TENSION = "romantic_tension"
THREAD_TYPE_SEXUAL_TENSION = "sexual_tension"
THREAD_TYPE_SHARED_FANTASY = "shared_fantasy"

THREAD_TYPES = {
    THREAD_TYPE_UNFINISHED_REVEAL,
    THREAD_TYPE_PROMISE,
    THREAD_TYPE_PRIVATE_JOKE,
    THREAD_TYPE_SHARED_PLAN,
    THREAD_TYPE_EMOTIONAL_QUESTION,
    THREAD_TYPE_ROMANTIC_TENSION,
    THREAD_TYPE_SEXUAL_TENSION,
    THREAD_TYPE_SHARED_FANTASY,
}

DEFAULT_EXPERIENCE_STATE: dict[str, Any] = {
    "current_mode": EXPERIENCE_MODE_NATURAL,
    "previous_mode": "",
    "recent_modes": [],
    "open_threads": [],
    "last_primary_intention": "",
    "last_emotional_color": "",
    "last_voice_register": "",
    "last_direction_reason": "",
    "last_user_style": "neutral",
    "repeated_function_count": 0,
}

DEFAULT_VOICE_STATE: dict[str, Any] = {
    "warmth": 0.34,
    "playfulness": 0.36,
    "boldness": 0.34,
    "vulnerability": 0.08,
    "romantic_intensity": 0.0,
    "sexual_intensity": 0.0,
    "sexual_explicitness": 0.0,
    "vulgarity": 0.12,
    "body_confidence": 0.60,
    "emotional_openness": 0.14,
    "humor": 0.30,
    "tenderness": 0.12,
    "jealousy": 0.0,
}

DEFAULT_TURN_DIRECTION: dict[str, Any] = {
    "experience_mode": EXPERIENCE_MODE_NATURAL,
    "primary_intention": "react_and_move",
    "emotional_color": "natural_presence",
    "voice_register": VOICE_REGISTER_NATURAL,
    "response_scope": "brief",
    "surprise_level": 0.15,
    "topic_direction": TOPIC_DIRECTION_CURRENT,
    "should_lead": True,
    "should_reveal_something": False,
    "should_create_pending_thread": False,
    "should_resume_thread": False,
    "open_thread_id": "",
    "callback_memory_id": "",
    "scene_seed": "",
    "body_focus_allowed": False,
    "romantic_expression_allowed": False,
    "sexual_expression_allowed": False,
    "explicit_sexual_language_allowed": False,
    "must_preserve_current_scene": False,
    "must_avoid_repetition": True,
    "must_address_user_message": True,
    "avoid_question": True,
    "user_style": "neutral",
    "pace": "advance",
    "action_choice": "react_and_move",
    "reason": "default_direction",
    "voice_state": deepcopy(DEFAULT_VOICE_STATE),
}


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def limitar_valor(
    value: Any,
    *,
    minimum: float = 0.0,
    maximum: float = 1.0,
) -> float:
    return max(minimum, min(maximum, safe_float(value, minimum)))


def normalizar_bool(value: Any, *, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "1", "sim", "s", "yes", "verdadeiro"}:
        return True
    if text in {"false", "0", "nao", "não", "n", "no", "falso", ""}:
        return False
    return default


def criar_estado_experiencia() -> dict[str, Any]:
    return deepcopy(DEFAULT_EXPERIENCE_STATE)


def criar_estado_voz() -> dict[str, Any]:
    return deepcopy(DEFAULT_VOICE_STATE)


def criar_direcao_turno_padrao() -> dict[str, Any]:
    return deepcopy(DEFAULT_TURN_DIRECTION)


def normalizar_estado_voz(value: dict[str, Any] | None) -> dict[str, Any]:
    state = criar_estado_voz()
    if isinstance(value, dict):
        state.update(value)
    for field in DEFAULT_VOICE_STATE:
        state[field] = limitar_valor(state.get(field))
    return state


def normalizar_thread(thread: Any) -> dict[str, Any]:
    if not isinstance(thread, dict):
        return {}
    thread_type = str(thread.get("type") or "").strip().lower()
    thread_id = str(thread.get("id") or "").strip()
    summary = str(thread.get("summary") or "").strip()
    if thread_type not in THREAD_TYPES or not thread_id or not summary:
        return {}
    return {
        "id": thread_id,
        "type": thread_type,
        "summary": summary,
        "created_turn": max(0, safe_int(thread.get("created_turn"))),
        "last_touched_turn": max(0, safe_int(thread.get("last_touched_turn"))),
        "urgency": limitar_valor(thread.get("urgency", 0.3)),
        "ready": normalizar_bool(thread.get("ready")),
    }


def normalizar_estado_experiencia(
    value: dict[str, Any] | None,
) -> dict[str, Any]:
    state = criar_estado_experiencia()
    if isinstance(value, dict):
        state.update(value)
    state["recent_modes"] = list(state.get("recent_modes") or [])[-5:]
    state["open_threads"] = [
        thread
        for item in list(state.get("open_threads") or [])
        if (thread := normalizar_thread(item))
    ][-8:]
    return state


def adicionar_thread_aberto(
    relationship_state: dict[str, Any],
    *,
    thread_type: str,
    summary: str,
    urgency: float = 0.3,
) -> dict[str, Any]:
    state = deepcopy(relationship_state if isinstance(relationship_state, dict) else {})
    experience = normalizar_estado_experiencia(state.get("experience_state"))
    turn = safe_int(state.get("interaction_count"))
    thread = {
        "id": f"thread_{turn}_{len(experience['open_threads']) + 1}",
        "type": thread_type if thread_type in THREAD_TYPES else THREAD_TYPE_UNFINISHED_REVEAL,
        "summary": str(summary or "").strip(),
        "created_turn": turn,
        "last_touched_turn": turn,
        "urgency": limitar_valor(urgency),
        "ready": False,
    }
    if thread["summary"]:
        experience["open_threads"].append(thread)
    state["experience_state"] = experience
    return state


def marcar_thread_pronto(
    relationship_state: dict[str, Any],
    thread_id: str,
) -> dict[str, Any]:
    state = deepcopy(relationship_state if isinstance(relationship_state, dict) else {})
    experience = normalizar_estado_experiencia(state.get("experience_state"))
    for thread in experience["open_threads"]:
        if thread.get("id") == thread_id:
            thread["ready"] = True
    state["experience_state"] = experience
    return state


def resolver_thread(
    relationship_state: dict[str, Any],
    thread_id: str,
) -> dict[str, Any]:
    state = deepcopy(relationship_state if isinstance(relationship_state, dict) else {})
    experience = normalizar_estado_experiencia(state.get("experience_state"))
    experience["open_threads"] = [
        thread
        for thread in experience["open_threads"]
        if thread.get("id") != thread_id
    ]
    state["experience_state"] = experience
    return state


def _texto_sinais(signals: dict[str, Any]) -> str:
    parts: list[str] = []
    for key, value in signals.items():
        if isinstance(value, str):
            parts.append(value)
        elif value is True:
            parts.append(key)
    return " ".join(parts).lower()


def _detectar_estilo_usuario(
    signals: dict[str, Any],
    turn_intent: dict[str, Any],
) -> str:
    text = _texto_sinais(signals)
    mode = str(turn_intent.get("turn_mode") or "").lower()

    if any(token in text for token in ("recusa", "rejeicao", "rejeição", "desconforto", "limite", "não quero", "nao quero")):
        return "refusing"
    if any(token in text for token in ("hesita", "cautela", "duvida", "dúvida", "analisa", "observa", "pergunta")) or mode == TURN_MODE_SLOW_DOWN:
        return "analytical"
    if any(token in text for token in ("sexual", "tesao", "tesão", "urgencia", "urgência", "direto", "avanca", "avança", "toque")) or mode in {
        TURN_MODE_INITIATE_SEXUAL_SCENE,
        TURN_MODE_INITIATE_SEXUAL_TENSION,
        TURN_MODE_INCREASE_INTIMACY,
    }:
        return "eager"
    if any(token in text for token in ("brinca", "humor", "ironia", "provoca", "zoa")) or mode == TURN_MODE_TEASE:
        return "playful"
    if any(token in text for token in ("carinho", "afeto", "vulnerabilidade", "tristeza", "saudade")) or mode == TURN_MODE_SEEK_AFFECTION:
        return "emotional"
    return "neutral"


def _obter_contexto_cenario(state: dict[str, Any]) -> dict[str, Any]:
    context = state.get("scenario_context")
    return context if isinstance(context, dict) else {}


def _obter_fase_sexual(state: dict[str, Any]) -> str:
    sexual = state.get("sexual_state")
    if not isinstance(sexual, dict):
        return "idle"
    return str(sexual.get("scene_phase") or "idle").strip().lower()


def _escolher_direcao(
    *,
    state: dict[str, Any],
    signals: dict[str, Any],
    turn_intent: dict[str, Any],
) -> dict[str, Any]:
    direction = criar_direcao_turno_padrao()
    user_style = _detectar_estilo_usuario(signals, turn_intent)
    scenario = _obter_contexto_cenario(state)
    phase = str(scenario.get("scenario_phase") or "").lower()
    sexual_phase = _obter_fase_sexual(state)
    sexual_level = safe_int(state.get("sexual_level", state.get("sexual_intimacy", 0)))
    interaction_count = safe_int(scenario.get("interaction_count", state.get("interaction_count", 0)))

    direction["user_style"] = user_style
    direction["must_preserve_current_scene"] = bool(scenario.get("active"))
    direction["body_focus_allowed"] = sexual_level >= 2 or sexual_phase not in {"", "idle"}
    direction["romantic_expression_allowed"] = safe_float(state.get("romantic_tension_level")) >= 0.25 or phase in {"intimacy", "climax", "aftercare", "ending"}
    direction["sexual_expression_allowed"] = sexual_level >= 2 or sexual_phase not in {"", "idle"}
    direction["explicit_sexual_language_allowed"] = sexual_level >= 3 or sexual_phase in {"active", "pre_orgasm", "orgasm", "post_orgasm", "frustration"}

    if interaction_count >= 40:
        direction["pace"] = "resolve"
        direction["response_scope"] = "brief"
    elif interaction_count >= 24:
        direction["pace"] = "advance_decisively"
    else:
        direction["pace"] = "advance"

    if user_style == "refusing":
        direction.update(
            {
                "experience_mode": EXPERIENCE_MODE_EMOTIONAL_REVERSAL,
                "primary_intention": "accept_refusal_with_personality_and_keep_door_open",
                "emotional_color": "lightly_wounded_but_self_possessed",
                "voice_register": VOICE_REGISTER_PLAYFUL,
                "topic_direction": TOPIC_DIRECTION_CURRENT,
                "should_lead": True,
                "action_choice": "reframe_without_pressure",
                "sexual_expression_allowed": False,
                "explicit_sexual_language_allowed": False,
                "avoid_question": True,
                "reason": "user_refused_or_withdrew",
            }
        )
    elif user_style == "analytical":
        direction.update(
            {
                "experience_mode": EXPERIENCE_MODE_GENTLE_PROVOCATION,
                "primary_intention": "answer_concretely_then_offer_one_safe_next_move",
                "emotional_color": "patient_with_a_hint_of_irony",
                "voice_register": VOICE_REGISTER_WARM,
                "should_lead": True,
                "action_choice": "clarify_and_move_one_step",
                "avoid_question": False,
                "reason": "user_is_cautious_or_analytical",
            }
        )
    elif user_style == "eager":
        mode = (
            EXPERIENCE_MODE_CONTINUE_SHARED_FANTASY
            if sexual_phase not in {"", "idle"}
            else EXPERIENCE_MODE_BOLD_PROVOCATION
        )
        direction.update(
            {
                "experience_mode": mode,
                "primary_intention": "match_energy_and_advance_without_micropasses",
                "emotional_color": "surprised_amused_and_desiring",
                "voice_register": (
                    VOICE_REGISTER_EXPLICIT_INTENSE
                    if direction["explicit_sexual_language_allowed"]
                    else VOICE_REGISTER_BOLD
                ),
                "topic_direction": TOPIC_DIRECTION_SEXUAL,
                "should_lead": True,
                "action_choice": "take_a_bold_coherent_action",
                "avoid_question": True,
                "surprise_level": 0.35,
                "reason": "user_is_eager",
            }
        )
    elif user_style == "playful":
        direction.update(
            {
                "experience_mode": EXPERIENCE_MODE_HUMOR_BREAK,
                "primary_intention": "return_humor_and_turn_it_into_progress",
                "emotional_color": "irreverent_and_quick",
                "voice_register": VOICE_REGISTER_PLAYFUL,
                "should_lead": True,
                "action_choice": "tease_then_move",
                "avoid_question": True,
                "surprise_level": 0.28,
                "reason": "user_is_playful",
            }
        )
    elif user_style == "emotional":
        direction.update(
            {
                "experience_mode": EXPERIENCE_MODE_SHOW_VULNERABILITY,
                "primary_intention": "respond_with_real_feeling_and_one_concrete_choice",
                "emotional_color": "warm_but_not_therapeutic",
                "voice_register": VOICE_REGISTER_VULNERABLE,
                "should_lead": True,
                "action_choice": "reveal_or_ask_for_something_real",
                "avoid_question": False,
                "reason": "user_is_emotional",
            }
        )
    else:
        direction.update(
            {
                "experience_mode": EXPERIENCE_MODE_NATURAL,
                "primary_intention": "react_with_personality_and_add_one_real_movement",
                "emotional_color": "natural_with_edge",
                "voice_register": VOICE_REGISTER_NATURAL,
                "should_lead": True,
                "action_choice": "react_and_move",
                "avoid_question": True,
                "reason": "neutral_user_style",
            }
        )

    if sexual_phase in {"active", "pre_orgasm", "orgasm", "post_orgasm", "frustration"}:
        direction["experience_mode"] = EXPERIENCE_MODE_CONTINUE_SHARED_FANTASY
        direction["must_preserve_current_scene"] = True
        direction["should_lead"] = True
        direction["avoid_question"] = True
        direction["action_choice"] = "advance_one_strong_body_or_voice_move"

    if phase in {"climax", "aftercare", "ending"} or interaction_count >= 40:
        direction["should_create_pending_thread"] = False
        direction["should_reveal_something"] = False
        direction["pace"] = "resolve"
        if phase == "aftercare":
            direction["experience_mode"] = EXPERIENCE_MODE_AFTERCARE
            direction["voice_register"] = VOICE_REGISTER_AFTERCARE
            direction["primary_intention"] = "land_the_emotion_without_restarting_the_arc"

    voice = normalizar_estado_voz(direction.get("voice_state"))
    if user_style == "eager":
        voice.update({"boldness": 0.78, "humor": 0.42, "sexual_intensity": 0.72, "sexual_explicitness": 0.68, "vulgarity": 0.38})
    elif user_style == "refusing":
        voice.update({"playfulness": 0.48, "humor": 0.44, "warmth": 0.28, "boldness": 0.40})
    elif user_style == "analytical":
        voice.update({"warmth": 0.46, "humor": 0.28, "boldness": 0.30})
    elif user_style == "playful":
        voice.update({"playfulness": 0.74, "humor": 0.72, "boldness": 0.52})
    elif user_style == "emotional":
        voice.update({"warmth": 0.62, "vulnerability": 0.42, "tenderness": 0.48})
    direction["voice_state"] = normalizar_estado_voz(voice)

    return direction


def planejar_direcao_turno(
    relationship_state: dict[str, Any] | None,
    *,
    signals: dict[str, Any] | None = None,
    turn_intent: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    state = deepcopy(relationship_state if isinstance(relationship_state, dict) else {})
    signals = signals if isinstance(signals, dict) else {}
    intent = turn_intent if isinstance(turn_intent, dict) else criar_intencao_turno_padrao()

    mary_internal = normalizar_estado_interno_mary(state.get("mary_internal_state"))
    state["mary_internal_state"] = mary_internal

    experience = normalizar_estado_experiencia(state.get("experience_state"))
    direction = _escolher_direcao(
        state=state,
        signals=signals,
        turn_intent=intent,
    )

    last_function = str(experience.get("last_primary_intention") or "")
    current_function = str(direction.get("primary_intention") or "")
    repeated = safe_int(experience.get("repeated_function_count")) + 1 if last_function == current_function else 0
    experience["repeated_function_count"] = repeated

    if repeated >= 2:
        direction["action_choice"] = "change_the_function_of_the_turn"
        direction["primary_intention"] = "break_repetition_with_a_new_concrete_move"
        direction["surprise_level"] = max(0.30, safe_float(direction.get("surprise_level")))
        direction["reason"] = "same_function_repeated"
        experience["repeated_function_count"] = 0

    experience["previous_mode"] = experience.get("current_mode", "")
    experience["current_mode"] = direction["experience_mode"]
    experience["recent_modes"] = [
        *list(experience.get("recent_modes") or []),
        direction["experience_mode"],
    ][-5:]
    experience["last_primary_intention"] = direction["primary_intention"]
    experience["last_emotional_color"] = direction["emotional_color"]
    experience["last_voice_register"] = direction["voice_register"]
    experience["last_direction_reason"] = direction["reason"]
    experience["last_user_style"] = direction["user_style"]

    state["experience_state"] = experience
    state["current_turn_direction"] = direction
    return state, direction


def sincronizar_direcao_apos_resposta(
    relationship_state: dict[str, Any] | None,
    *,
    turn_direction: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state = deepcopy(relationship_state if isinstance(relationship_state, dict) else {})
    direction = turn_direction if isinstance(turn_direction, dict) else state.get("current_turn_direction")
    if not isinstance(direction, dict):
        direction = criar_direcao_turno_padrao()
    state["last_turn_direction"] = deepcopy(direction)
    state["current_turn_direction"] = {}
    return state


def montar_contexto_direcao(
    relationship_state: dict[str, Any] | None,
    turn_direction: dict[str, Any] | None = None,
) -> str:
    state = relationship_state if isinstance(relationship_state, dict) else {}
    direction = turn_direction if isinstance(turn_direction, dict) else state.get("current_turn_direction")
    if not isinstance(direction, dict):
        direction = criar_direcao_turno_padrao()

    compact = {
        "user_style": direction.get("user_style", "neutral"),
        "pace": direction.get("pace", "advance"),
        "goal": direction.get("primary_intention", "react_and_move"),
        "action": direction.get("action_choice", "react_and_move"),
        "tone": direction.get("emotional_color", "natural_presence"),
        "voice": direction.get("voice_register", VOICE_REGISTER_NATURAL),
        "lead": normalizar_bool(direction.get("should_lead"), default=True),
        "preserve_scene": normalizar_bool(direction.get("must_preserve_current_scene")),
        "sexual": normalizar_bool(direction.get("sexual_expression_allowed")),
        "explicit": normalizar_bool(direction.get("explicit_sexual_language_allowed")),
        "avoid_question": normalizar_bool(direction.get("avoid_question"), default=True),
        "reason": direction.get("reason", ""),
    }

    return (
        "[DIREÇÃO DO TURNO]\n"
        + str(compact)
        + "\nMary deve reagir ao estilo deste usuário e executar um movimento concreto agora. "
        "Não repita a função das respostas anteriores, não use micropassos e não transforme cautela em passividade. "
        "Recusa pede criatividade sem pressão; pressa pede resposta proporcional; análise pede clareza com personalidade; humor pede humor real."
    )


__all__ = [
    "EXPERIENCE_MODE_NATURAL",
    "EXPERIENCE_MODE_PERSONAL_SHARE",
    "EXPERIENCE_MODE_UNEXPECTED_CONFESSION",
    "EXPERIENCE_MODE_PLAYFUL_CHALLENGE",
    "EXPERIENCE_MODE_PRIVATE_JOKE",
    "EXPERIENCE_MODE_MEMORY_CALLBACK",
    "EXPERIENCE_MODE_UNFINISHED_REVEAL",
    "EXPERIENCE_MODE_EMOTIONAL_REVERSAL",
    "EXPERIENCE_MODE_GENTLE_PROVOCATION",
    "EXPERIENCE_MODE_BOLD_PROVOCATION",
    "EXPERIENCE_MODE_ROMANTIC_ESCALATION",
    "EXPERIENCE_MODE_SEXUAL_TENSION",
    "EXPERIENCE_MODE_SEXUAL_INITIATIVE",
    "EXPERIENCE_MODE_SEEK_AFFECTION",
    "EXPERIENCE_MODE_SHOW_JEALOUSY",
    "EXPERIENCE_MODE_SHOW_VULNERABILITY",
    "EXPERIENCE_MODE_SET_BOUNDARY",
    "EXPERIENCE_MODE_CREATE_SHARED_PLAN",
    "EXPERIENCE_MODE_CONTINUE_SHARED_FANTASY",
    "EXPERIENCE_MODE_SURPRISE_TOPIC",
    "EXPERIENCE_MODE_HUMOR_BREAK",
    "EXPERIENCE_MODE_AFTERCARE",
    "EXPERIENCE_MODE_FRUSTRATION",
    "VOICE_REGISTER_NATURAL",
    "VOICE_REGISTER_PLAYFUL",
    "VOICE_REGISTER_WARM",
    "VOICE_REGISTER_ROMANTIC",
    "VOICE_REGISTER_VULNERABLE",
    "VOICE_REGISTER_TEASING",
    "VOICE_REGISTER_BOLD",
    "VOICE_REGISTER_EXPLICIT_PLAYFUL",
    "VOICE_REGISTER_EXPLICIT_INTENSE",
    "VOICE_REGISTER_AFFECTIONATE_SEXUAL",
    "VOICE_REGISTER_IRRITATED",
    "VOICE_REGISTER_BOUNDARY",
    "VOICE_REGISTER_AFTERCARE",
    "DEFAULT_EXPERIENCE_STATE",
    "DEFAULT_VOICE_STATE",
    "DEFAULT_TURN_DIRECTION",
    "criar_estado_experiencia",
    "criar_estado_voz",
    "criar_direcao_turno_padrao",
    "normalizar_estado_experiencia",
    "normalizar_estado_voz",
    "adicionar_thread_aberto",
    "marcar_thread_pronto",
    "resolver_thread",
    "planejar_direcao_turno",
    "sincronizar_direcao_apos_resposta",
    "montar_contexto_direcao",
]
