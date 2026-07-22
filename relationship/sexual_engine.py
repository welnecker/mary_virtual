from __future__ import annotations

import re
import unicodedata
from copy import deepcopy
from typing import Any


SEXUAL_PHASE_IDLE = "idle"
SEXUAL_PHASE_TENSION = "tension"
SEXUAL_PHASE_AROUSAL = "arousal"
SEXUAL_PHASE_BODY_EXPLORATION = "body_exploration"
SEXUAL_PHASE_GIVING_PLEASURE = "giving_pleasure"
SEXUAL_PHASE_RECEIVING_PLEASURE = "receiving_pleasure"
SEXUAL_PHASE_ORAL = "oral"
SEXUAL_PHASE_PENETRATION_START = "penetration_start"
SEXUAL_PHASE_PENETRATION_ACTIVE = "penetration_active"
SEXUAL_PHASE_PACE_CONTROL = "pace_control"
SEXUAL_PHASE_USER_EDGE = "user_edge"
SEXUAL_PHASE_MARY_EDGE = "mary_edge"
SEXUAL_PHASE_ACTIVE = "active"
SEXUAL_PHASE_PRE_ORGASM = "pre_orgasm"
SEXUAL_PHASE_USER_ORGASM = "user_orgasm"
SEXUAL_PHASE_MARY_ORGASM = "mary_orgasm"
SEXUAL_PHASE_ORGASM = "orgasm"
SEXUAL_PHASE_POST_ORGASM_ACTIVE = "post_orgasm_active"
SEXUAL_PHASE_POST_ORGASM = "post_orgasm"
SEXUAL_PHASE_FRUSTRATION = "frustration"
SEXUAL_PHASE_AFTERCARE = "aftercare"

SEXUAL_PHASES: tuple[str, ...] = (
    SEXUAL_PHASE_IDLE,
    SEXUAL_PHASE_TENSION,
    SEXUAL_PHASE_AROUSAL,
    SEXUAL_PHASE_BODY_EXPLORATION,
    SEXUAL_PHASE_GIVING_PLEASURE,
    SEXUAL_PHASE_RECEIVING_PLEASURE,
    SEXUAL_PHASE_ORAL,
    SEXUAL_PHASE_PENETRATION_START,
    SEXUAL_PHASE_PENETRATION_ACTIVE,
    SEXUAL_PHASE_PACE_CONTROL,
    SEXUAL_PHASE_USER_EDGE,
    SEXUAL_PHASE_MARY_EDGE,
    SEXUAL_PHASE_ACTIVE,
    SEXUAL_PHASE_PRE_ORGASM,
    SEXUAL_PHASE_USER_ORGASM,
    SEXUAL_PHASE_MARY_ORGASM,
    SEXUAL_PHASE_ORGASM,
    SEXUAL_PHASE_POST_ORGASM_ACTIVE,
    SEXUAL_PHASE_POST_ORGASM,
    SEXUAL_PHASE_FRUSTRATION,
    SEXUAL_PHASE_AFTERCARE,
)

ACTIVE_PHASES = {
    SEXUAL_PHASE_AROUSAL,
    SEXUAL_PHASE_BODY_EXPLORATION,
    SEXUAL_PHASE_GIVING_PLEASURE,
    SEXUAL_PHASE_RECEIVING_PLEASURE,
    SEXUAL_PHASE_ORAL,
    SEXUAL_PHASE_PENETRATION_START,
    SEXUAL_PHASE_PENETRATION_ACTIVE,
    SEXUAL_PHASE_PACE_CONTROL,
    SEXUAL_PHASE_USER_EDGE,
    SEXUAL_PHASE_MARY_EDGE,
    SEXUAL_PHASE_ACTIVE,
    SEXUAL_PHASE_PRE_ORGASM,
    SEXUAL_PHASE_USER_ORGASM,
    SEXUAL_PHASE_MARY_ORGASM,
    SEXUAL_PHASE_ORGASM,
    SEXUAL_PHASE_POST_ORGASM_ACTIVE,
    SEXUAL_PHASE_POST_ORGASM,
    SEXUAL_PHASE_FRUSTRATION,
}

DEFAULT_SEXUAL_STATE: dict[str, Any] = {
    "scene_phase": SEXUAL_PHASE_IDLE,
    "previous_scene_phase": "",
    "arousal_level": 0.0,
    "tension_level": 0.0,
    "user_arousal_estimate": 0.0,
    "stimulation_turns": 0,
    "consecutive_low_intensity_turns": 0,
    "same_activity_turns": 0,
    "current_activity": "",
    "current_position": "",
    "current_pace": "",
    "mary_is_leading": False,
    "mary_is_giving_pleasure": False,
    "mary_is_receiving_pleasure": False,
    "user_near_orgasm": False,
    "mary_near_orgasm": False,
    "post_orgasm_continue": False,
    "mary_pre_orgasm": False,
    "mary_orgasm_allowed": False,
    "mary_orgasm_done": False,
    "user_orgasm_warning": False,
    "user_orgasm_pending": False,
    "user_orgasm_done": False,
    "frustration_state": "",
    "aftercare_required": False,
    "last_stimulus_type": "",
    "last_transition_reason": "",
    "resolution_done": False,
}


SEXUAL_TERMS = (
    "tesao", "excitado", "excitada", "molhada", "duro", "buceta",
    "xoxota", "cu", "bunda", "peito", "peitos", "pau", "foder",
    "transar", "chupar", "lamber", "meter", "penetrar", "gozar",
    "orgasmo", "gemer", "rebolar", "tirar a roupa", "sem roupa",
)

ACTIVE_ACTION_TERMS = (
    "beijo", "beijar", "toco", "tocar", "aperto", "apertar", "puxo",
    "puxar", "tiro", "tirar", "abro", "abrir", "ajoelho", "ajoelhar",
    "monto", "montar", "entro", "meter", "penetro", "penetrar", "chupo",
    "chupar", "lambo", "lamber", "rebolo", "rebolar", "mais forte",
    "mais rapido", "mais rápido", "continua", "nao para", "não para",
)

USER_ORGASM_WARNING_TERMS = (
    "vou gozar", "to quase", "tô quase", "quase gozando",
)

USER_ORGASM_DONE_TERMS = (
    "to gozando", "tô gozando", "gozei", "eu gozei", "cheguei la",
    "cheguei lá", "meu orgasmo veio",
)

MARY_PRE_ORGASM_TERMS = (
    "vou gozar", "eu vou gozar", "to quase", "tô quase", "nao para",
    "não para", "continua", "mais forte",
)

MARY_ORGASM_DONE_TERMS = (
    "to gozando", "tô gozando", "gozei", "eu gozei", "me fez gozar",
    "estou gozando", "eu gozo", "gozando agora",
)

STOP_TERMS = (
    "para", "pare", "nao quero", "não quero", "chega", "desisto",
    "melhor nao", "melhor não", "nao gostei", "não gostei",
)


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


def limitar_float(
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
    if text in {"true", "1", "yes", "sim", "s", "verdadeiro"}:
        return True
    if text in {"false", "0", "no", "nao", "não", "n", "falso", ""}:
        return False
    return default


def remover_acentos(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(text or ""))
    return "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )


def normalizar_texto(value: Any) -> str:
    text = remover_acentos(str(value or "").strip().lower())
    return re.sub(r"\s+", " ", text).strip()


def contem_algum(text: str, terms: tuple[str, ...] | list[str]) -> bool:
    normalized = normalizar_texto(text)
    return any(normalizar_texto(term) in normalized for term in terms)


def normalizar_fase(phase: Any) -> str:
    normalized = normalizar_texto(phase)
    aliases = {
        "": SEXUAL_PHASE_IDLE,
        "none": SEXUAL_PHASE_IDLE,
        "inicio": SEXUAL_PHASE_IDLE,
        "nenhum": SEXUAL_PHASE_IDLE,
        "aproximacao": SEXUAL_PHASE_TENSION,
        "intimidade": SEXUAL_PHASE_TENSION,
        "excitacao": SEXUAL_PHASE_AROUSAL,
        "estimulo_corporal": SEXUAL_PHASE_BODY_EXPLORATION,
        "sexo_ou_estimulo": SEXUAL_PHASE_ACTIVE,
        "exploracao_corporal": SEXUAL_PHASE_BODY_EXPLORATION,
        "dando_prazer": SEXUAL_PHASE_GIVING_PLEASURE,
        "recebendo_prazer": SEXUAL_PHASE_RECEIVING_PLEASURE,
        "inicio_penetracao": SEXUAL_PHASE_PENETRATION_START,
        "penetracao_ativa": SEXUAL_PHASE_PENETRATION_ACTIVE,
        "controle": SEXUAL_PHASE_PACE_CONTROL,
        "limite_usuario": SEXUAL_PHASE_USER_EDGE,
        "limite_mary": SEXUAL_PHASE_MARY_EDGE,
        "pre_pico_mary": SEXUAL_PHASE_PRE_ORGASM,
        "pico_mary": SEXUAL_PHASE_ORGASM,
        "pos_pico_mary": SEXUAL_PHASE_POST_ORGASM,
        "pos_orgasmo_ativo": SEXUAL_PHASE_POST_ORGASM_ACTIVE,
        "desaceleracao": SEXUAL_PHASE_AFTERCARE,
    }
    normalized = aliases.get(normalized, normalized)
    return normalized if normalized in SEXUAL_PHASES else SEXUAL_PHASE_IDLE


def criar_estado_sexual_padrao() -> dict[str, Any]:
    return deepcopy(DEFAULT_SEXUAL_STATE)


def normalizar_estado_sexual(
    state: dict[str, Any] | None,
) -> dict[str, Any]:
    normalized = criar_estado_sexual_padrao()
    if isinstance(state, dict):
        normalized.update(state)

    normalized["scene_phase"] = normalizar_fase(
        normalized.get("scene_phase") or normalized.get("scene_stage")
    )
    normalized["previous_scene_phase"] = (
        normalizar_fase(normalized.get("previous_scene_phase"))
        if normalized.get("previous_scene_phase")
        else ""
    )

    for field in ("arousal_level", "tension_level", "user_arousal_estimate"):
        normalized[field] = limitar_float(normalized.get(field))

    for field in (
        "stimulation_turns",
        "consecutive_low_intensity_turns",
        "same_activity_turns",
    ):
        normalized[field] = max(0, safe_int(normalized.get(field)))

    for field in ("current_activity", "current_position", "current_pace"):
        normalized[field] = str(normalized.get(field) or "").strip().lower()

    for field in (
        "mary_is_leading",
        "mary_is_giving_pleasure",
        "mary_is_receiving_pleasure",
        "user_near_orgasm",
        "mary_near_orgasm",
        "post_orgasm_continue",
        "mary_pre_orgasm",
        "mary_orgasm_allowed",
        "mary_orgasm_done",
        "user_orgasm_warning",
        "user_orgasm_pending",
        "user_orgasm_done",
        "aftercare_required",
        "resolution_done",
    ):
        normalized[field] = normalizar_bool(normalized.get(field))

    if isinstance(state, dict):
        if "mary_pre_orgasm_signals" in state:
            normalized["mary_pre_orgasm"] = normalizar_bool(
                state.get("mary_pre_orgasm_signals")
            )
        if "force_resolution_now" in state:
            normalized["mary_orgasm_allowed"] = normalizar_bool(
                state.get("force_resolution_now")
            )
        if "mary_climax_done" in state:
            normalized["mary_orgasm_done"] = normalizar_bool(
                state.get("mary_climax_done")
            )
        if "partner_climax_pending" in state:
            normalized["user_orgasm_pending"] = normalizar_bool(
                state.get("partner_climax_pending")
            )
        if "user_climax_done" in state:
            normalized["user_orgasm_done"] = normalizar_bool(
                state.get("user_climax_done")
            )

    return aplicar_aliases_legados(normalized)


def aplicar_aliases_legados(state: dict[str, Any]) -> dict[str, Any]:
    state["scene_stage"] = state["scene_phase"]
    state["mary_stimulation_turns"] = state["stimulation_turns"]
    state["mary_pre_orgasm_signals"] = state["mary_pre_orgasm"]
    state["force_resolution_now"] = state["mary_orgasm_allowed"]
    state["mary_climax_done"] = state["mary_orgasm_done"]
    state["partner_climax_pending"] = state["user_orgasm_pending"]
    state["user_climax_done"] = state["user_orgasm_done"]
    return state


def alterar_fase(
    state: dict[str, Any],
    phase: str,
    *,
    reason: str,
) -> None:
    phase = normalizar_fase(phase)
    if state.get("scene_phase") != phase:
        state["previous_scene_phase"] = state.get("scene_phase", "")
        state["scene_phase"] = phase
    state["last_transition_reason"] = reason


def _nivel_sexual_relacao(
    relationship_state: dict[str, Any] | None,
) -> int:
    relationship = relationship_state if isinstance(relationship_state, dict) else {}
    return max(
        0,
        min(
            5,
            safe_int(
                relationship.get(
                    "sexual_level",
                    relationship.get("sexual_intimacy", 0),
                )
            ),
        ),
    )


def _cenario_privado(
    relationship_state: dict[str, Any] | None,
) -> bool:
    relationship = relationship_state if isinstance(relationship_state, dict) else {}
    for key in (
        "active_scenario",
        "scenario_state",
        "scene_state",
        "current_scenario",
        "scenario_context",
    ):
        candidate = relationship.get(key)
        if not isinstance(candidate, dict):
            continue
        nested = candidate.get("scene_state")
        if isinstance(nested, dict):
            candidate = nested
        if any(
            normalizar_bool(candidate.get(field))
            for field in (
                "private_space",
                "privacy_established",
                "alone_together",
                "room_private",
            )
        ):
            return True
        location = normalizar_texto(
            candidate.get("location") or candidate.get("current_location")
        )
        if any(term in location for term in ("quarto", "cama", "hotel", "casa")):
            return True
    return False


def atualizar_estado_sexual_antes_resposta(
    sexual_state: dict[str, Any] | None,
    *,
    user_text: str,
    relationship_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state = normalizar_estado_sexual(sexual_state)
    text = normalizar_texto(user_text)
    level = _nivel_sexual_relacao(relationship_state)
    private = _cenario_privado(relationship_state)

    if contem_algum(text, STOP_TERMS):
        state["frustration_state"] = "user_stopped_or_redirected"
        state["mary_orgasm_allowed"] = False
        state["mary_pre_orgasm"] = False
        alterar_fase(state, SEXUAL_PHASE_FRUSTRATION, reason="user_boundary")
        return aplicar_aliases_legados(state)

    sexual_signal = contem_algum(text, SEXUAL_TERMS)
    active_action = contem_algum(text, ACTIVE_ACTION_TERMS)
    user_warning = contem_algum(text, USER_ORGASM_WARNING_TERMS)
    user_done = contem_algum(text, USER_ORGASM_DONE_TERMS)

    if user_warning:
        state["user_orgasm_warning"] = True
        state["user_near_orgasm"] = True
        state["user_orgasm_pending"] = True
        state["user_arousal_estimate"] = max(
            state["user_arousal_estimate"],
            0.88,
        )

    if user_done:
        state["user_orgasm_done"] = True
        state["user_orgasm_warning"] = False
        state["user_near_orgasm"] = False
        state["user_orgasm_pending"] = False
        state["user_arousal_estimate"] = 1.0

    if sexual_signal:
        state["tension_level"] = limitar_float(
            state["tension_level"] + (0.22 if level >= 3 else 0.14)
        )
        state["arousal_level"] = limitar_float(
            state["arousal_level"] + (0.20 if level >= 3 else 0.10)
        )

    if active_action:
        state["stimulation_turns"] += 1
        state["arousal_level"] = limitar_float(
            state["arousal_level"] + (0.22 if level >= 4 else 0.15)
        )
        state["mary_is_receiving_pleasure"] = True
        state["mary_is_leading"] = level >= 3

    phase = state["scene_phase"]

    if phase == SEXUAL_PHASE_IDLE and sexual_signal:
        alterar_fase(state, SEXUAL_PHASE_TENSION, reason="sexual_signal")
    elif phase == SEXUAL_PHASE_TENSION and (active_action or state["tension_level"] >= 0.35):
        alterar_fase(state, SEXUAL_PHASE_AROUSAL, reason="tension_became_arousal")
    elif phase == SEXUAL_PHASE_AROUSAL and (
        active_action
        or (level >= 3 and private)
        or state["arousal_level"] >= 0.48
    ):
        alterar_fase(state, SEXUAL_PHASE_ACTIVE, reason="intimacy_converged")
    elif phase in ACTIVE_PHASES and phase not in {
        SEXUAL_PHASE_PRE_ORGASM,
        SEXUAL_PHASE_ORGASM,
        SEXUAL_PHASE_MARY_ORGASM,
        SEXUAL_PHASE_POST_ORGASM,
        SEXUAL_PHASE_POST_ORGASM_ACTIVE,
        SEXUAL_PHASE_AFTERCARE,
    }:
        alterar_fase(state, SEXUAL_PHASE_ACTIVE, reason="keep_active_sequence")

    if state["scene_phase"] == SEXUAL_PHASE_ACTIVE:
        if sexual_signal or active_action or (level >= 4 and private):
            state["mary_is_leading"] = True
            state["arousal_level"] = limitar_float(
                state["arousal_level"] + (0.12 if active_action else 0.07)
            )

        if (
            state["arousal_level"] >= 0.78
            and state["stimulation_turns"] >= 2
            and not state["mary_orgasm_done"]
        ):
            state["mary_pre_orgasm"] = True
            state["mary_near_orgasm"] = True
            alterar_fase(
                state,
                SEXUAL_PHASE_PRE_ORGASM,
                reason="mary_entered_pre_orgasm",
            )

    if state["scene_phase"] == SEXUAL_PHASE_PRE_ORGASM:
        state["mary_pre_orgasm"] = True
        state["mary_near_orgasm"] = True
        if sexual_signal or active_action:
            state["arousal_level"] = limitar_float(
                state["arousal_level"] + 0.12
            )
        if state["arousal_level"] >= 0.90 and state["stimulation_turns"] >= 3:
            state["mary_orgasm_allowed"] = True
            alterar_fase(
                state,
                SEXUAL_PHASE_ORGASM,
                reason="mary_orgasm_ready_without_extra_delay",
            )

    if state["mary_orgasm_done"] and not state["user_orgasm_done"]:
        state["user_orgasm_pending"] = True
        state["post_orgasm_continue"] = True
        alterar_fase(
            state,
            SEXUAL_PHASE_POST_ORGASM_ACTIVE,
            reason="mary_done_user_pending",
        )

    if state["mary_orgasm_done"] and state["user_orgasm_done"]:
        state["aftercare_required"] = True
        alterar_fase(state, SEXUAL_PHASE_AFTERCARE, reason="both_resolved")

    return aplicar_aliases_legados(state)


def detectar_orgasmo_mary_na_resposta(mary_response: str) -> bool:
    text = normalizar_texto(mary_response)
    return contem_algum(text, MARY_ORGASM_DONE_TERMS)


def detectar_pre_orgasmo_mary_na_resposta(mary_response: str) -> bool:
    return contem_algum(mary_response, MARY_PRE_ORGASM_TERMS)


def confirmar_orgasmo_mary_apos_resposta(
    state: dict[str, Any],
    *,
    mary_response: str,
) -> None:
    if not detectar_orgasmo_mary_na_resposta(mary_response):
        return

    if not state["mary_orgasm_allowed"] and state["scene_phase"] not in {
        SEXUAL_PHASE_ORGASM,
        SEXUAL_PHASE_MARY_ORGASM,
    }:
        return

    state["mary_orgasm_done"] = True
    state["resolution_done"] = True
    state["mary_orgasm_allowed"] = False
    state["mary_pre_orgasm"] = False
    state["mary_near_orgasm"] = False
    state["arousal_level"] = 1.0
    alterar_fase(state, SEXUAL_PHASE_POST_ORGASM, reason="mary_orgasm_confirmed")


def sincronizar_climax_usuario_apos_resposta(
    state: dict[str, Any],
    *,
    user_text: str,
) -> None:
    if contem_algum(user_text, USER_ORGASM_WARNING_TERMS):
        state["user_orgasm_warning"] = True
        state["user_near_orgasm"] = True
        state["user_orgasm_pending"] = True

    if contem_algum(user_text, USER_ORGASM_DONE_TERMS):
        state["user_orgasm_done"] = True
        state["user_orgasm_warning"] = False
        state["user_near_orgasm"] = False
        state["user_orgasm_pending"] = False


def atualizar_estado_sexual_apos_resposta(
    sexual_state: dict[str, Any] | None,
    *,
    user_text: str,
    mary_response: str,
) -> dict[str, Any]:
    state = normalizar_estado_sexual(sexual_state)

    if state["scene_phase"] == SEXUAL_PHASE_PRE_ORGASM and (
        detectar_pre_orgasmo_mary_na_resposta(mary_response)
    ):
        state["arousal_level"] = limitar_float(state["arousal_level"] + 0.08)

    confirmar_orgasmo_mary_apos_resposta(
        state,
        mary_response=mary_response,
    )
    sincronizar_climax_usuario_apos_resposta(
        state,
        user_text=user_text,
    )

    if state["mary_orgasm_done"] and not state["user_orgasm_done"]:
        state["user_orgasm_pending"] = True
        state["post_orgasm_continue"] = True
        alterar_fase(
            state,
            SEXUAL_PHASE_POST_ORGASM_ACTIVE,
            reason="mary_post_orgasm_keeps_participating",
        )
    elif state["user_orgasm_done"] and not state["mary_orgasm_done"]:
        state["post_orgasm_continue"] = True
        alterar_fase(
            state,
            SEXUAL_PHASE_POST_ORGASM_ACTIVE,
            reason="mary_still_needs_resolution",
        )
    elif state["mary_orgasm_done"] and state["user_orgasm_done"]:
        state["aftercare_required"] = True
        alterar_fase(state, SEXUAL_PHASE_AFTERCARE, reason="both_resolved")

    return aplicar_aliases_legados(state)


def validar_resposta_sexual(
    sexual_state: dict[str, Any] | None,
    mary_response: str,
) -> dict[str, Any]:
    state = normalizar_estado_sexual(sexual_state)
    orgasm_detected = detectar_orgasmo_mary_na_resposta(mary_response)
    pre_orgasm_detected = detectar_pre_orgasmo_mary_na_resposta(mary_response)
    errors: list[str] = []

    if (
        orgasm_detected
        and not state["mary_orgasm_allowed"]
        and state["scene_phase"] not in {
            SEXUAL_PHASE_ORGASM,
            SEXUAL_PHASE_MARY_ORGASM,
        }
        and not state["mary_orgasm_done"]
    ):
        errors.append("mary_orgasm_before_engine_authorization")

    if (
        state["scene_phase"] == SEXUAL_PHASE_PRE_ORGASM
        and not pre_orgasm_detected
    ):
        errors.append("mary_pre_orgasm_without_human_warning")

    if state["mary_orgasm_done"] and orgasm_detected:
        errors.append("repeated_mary_orgasm")

    return {
        "valid": not errors,
        "errors": errors,
        "mary_orgasm_detected": orgasm_detected,
        "mary_pre_orgasm_detected": pre_orgasm_detected,
    }


def iniciar_novo_ciclo_sexual(
    sexual_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    previous = normalizar_estado_sexual(sexual_state)
    new_state = criar_estado_sexual_padrao()
    new_state["previous_scene_phase"] = previous["scene_phase"]
    new_state["last_transition_reason"] = "new_sexual_cycle_started"
    return aplicar_aliases_legados(new_state)


def encerrar_cena_sexual(
    sexual_state: dict[str, Any] | None,
) -> dict[str, Any]:
    state = criar_estado_sexual_padrao()
    previous = normalizar_estado_sexual(sexual_state)
    state["previous_scene_phase"] = previous["scene_phase"]
    state["last_transition_reason"] = "sexual_scene_closed"
    return aplicar_aliases_legados(state)


def montar_contexto_sexual(
    sexual_state: dict[str, Any] | None,
) -> str:
    state = normalizar_estado_sexual(sexual_state)
    phase = state["scene_phase"]

    phase_instruction = {
        SEXUAL_PHASE_IDLE: "Não inicie sexo sem contexto do turno.",
        SEXUAL_PHASE_TENSION: "Crie tensão concreta e avance sem repetir insinuação.",
        SEXUAL_PHASE_AROUSAL: "Mary demonstra excitação e toma iniciativa corporal.",
        SEXUAL_PHASE_ACTIVE: "Sexo ativo: Mary conduz um movimento forte e natural.",
        SEXUAL_PHASE_PRE_ORGASM: (
            "Mary está realmente perto. A fala deve incluir aviso humano e sensorial, "
            "preferencialmente ‘vou gozar...’, junto de urgência, pedido ou perda de controle."
        ),
        SEXUAL_PHASE_ORGASM: (
            "Mary deve gozar claramente agora, em primeira pessoa, com palavras humanas, "
            "sensações corporais e quebra natural de fala; não permaneça no quase."
        ),
        SEXUAL_PHASE_POST_ORGASM_ACTIVE: (
            "Mary já chegou ao pico ou o usuário chegou primeiro; continue presente e ativa "
            "até a resolução pendente."
        ),
        SEXUAL_PHASE_POST_ORGASM: (
            "Preserve sensibilidade, humor, vulnerabilidade e reação corporal pós-pico."
        ),
        SEXUAL_PHASE_FRUSTRATION: (
            "Mary pode reclamar, redirecionar, pedir continuidade ou parar com personalidade."
        ),
        SEXUAL_PHASE_AFTERCARE: (
            "Desacelere sem esfriar Mary: proximidade, humor, carinho ou provocação leve."
        ),
    }.get(phase, "Preserve continuidade e avanço natural da intimidade.")

    return (
        "[MOTOR SEXUAL]\n"
        f"fase={phase}; excitação={state['arousal_level']:.2f}; "
        f"estímulos={state['stimulation_turns']}; conduz={state['mary_is_leading']}; "
        f"pré_orgasmo={state['mary_pre_orgasm']}; "
        f"orgasmo_liberado={state['mary_orgasm_allowed']}; "
        f"orgasmo_concluído={state['mary_orgasm_done']}; "
        f"usuário_concluiu={state['user_orgasm_done']}\n"
        f"{phase_instruction}\n"
        "Mary não é espectadora: deseja, conduz, pede, provoca, reage e pode usar "
        "linguagem explícita. Não pule a experiência, mas também não crie micropassos."
    )


__all__ = [
    "SEXUAL_PHASE_IDLE",
    "SEXUAL_PHASE_TENSION",
    "SEXUAL_PHASE_AROUSAL",
    "SEXUAL_PHASE_BODY_EXPLORATION",
    "SEXUAL_PHASE_GIVING_PLEASURE",
    "SEXUAL_PHASE_RECEIVING_PLEASURE",
    "SEXUAL_PHASE_ORAL",
    "SEXUAL_PHASE_PENETRATION_START",
    "SEXUAL_PHASE_PENETRATION_ACTIVE",
    "SEXUAL_PHASE_PACE_CONTROL",
    "SEXUAL_PHASE_USER_EDGE",
    "SEXUAL_PHASE_MARY_EDGE",
    "SEXUAL_PHASE_ACTIVE",
    "SEXUAL_PHASE_PRE_ORGASM",
    "SEXUAL_PHASE_USER_ORGASM",
    "SEXUAL_PHASE_MARY_ORGASM",
    "SEXUAL_PHASE_ORGASM",
    "SEXUAL_PHASE_POST_ORGASM_ACTIVE",
    "SEXUAL_PHASE_POST_ORGASM",
    "SEXUAL_PHASE_FRUSTRATION",
    "SEXUAL_PHASE_AFTERCARE",
    "DEFAULT_SEXUAL_STATE",
    "criar_estado_sexual_padrao",
    "normalizar_estado_sexual",
    "atualizar_estado_sexual_antes_resposta",
    "atualizar_estado_sexual_apos_resposta",
    "validar_resposta_sexual",
    "iniciar_novo_ciclo_sexual",
    "encerrar_cena_sexual",
    "montar_contexto_sexual",
]
