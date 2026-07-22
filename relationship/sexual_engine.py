from __future__ import annotations

import re
import unicodedata
from copy import deepcopy
from typing import Any


SEXUAL_ENGINE_VERSION = "sexual-engine-v4-responsive-dual-resolution"

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
}

DEFAULT_SEXUAL_STATE: dict[str, Any] = {
    "version": SEXUAL_ENGINE_VERSION,
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
    "mary_desire_level": 0.0,
    "mary_initiative_level": 0.0,
    "mary_is_leading": False,
    "mary_is_giving_pleasure": False,
    "mary_is_receiving_pleasure": False,
    "user_near_orgasm": False,
    "mary_near_orgasm": False,
    "post_orgasm_continue": False,
    "mary_pre_orgasm": False,
    "mary_pre_orgasm_announced": False,
    "mary_orgasm_allowed": False,
    "mary_orgasm_done": False,
    "mary_orgasm_count": 0,
    "user_orgasm_warning": False,
    "user_orgasm_pending": False,
    "user_orgasm_done": False,
    "user_orgasm_count": 0,
    "frustration_state": "",
    "aftercare_required": False,
    "aftercare_active": False,
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

PLEASURE_GIVING_TERMS = (
    "te chupo", "te lambo", "na sua", "no seu", "faço você", "faco voce",
    "quero te dar prazer", "deixa comigo", "eu conduzo",
)

PLEASURE_RECEIVING_TERMS = (
    "me chupa", "me lambe", "em mim", "na minha", "no meu", "me toca",
    "me aperta", "bate na minha bunda", "faz comigo",
)

USER_ORGASM_WARNING_TERMS = (
    "vou gozar", "to quase", "tô quase", "quase gozando", "estou quase",
)

USER_ORGASM_DONE_TERMS = (
    "to gozando", "tô gozando", "gozei", "eu gozei", "cheguei la",
    "cheguei lá", "meu orgasmo veio", "acabei de gozar",
)

MARY_PRE_ORGASM_TERMS = (
    "vou gozar", "eu vou gozar", "to quase", "tô quase", "estou quase",
    "não vou aguentar", "nao vou aguentar",
)

MARY_ORGASM_DONE_TERMS = (
    "to gozando", "tô gozando", "gozei", "eu gozei", "me fez gozar",
    "estou gozando", "eu gozo", "gozando agora", "acabei de gozar",
)

STOP_TERMS = (
    "para", "pare", "nao quero", "não quero", "chega", "desisto",
    "melhor nao", "melhor não", "nao gostei", "não gostei",
)

REDIRECT_TERMS = (
    "devagar", "mais leve", "troca", "muda", "assim nao", "assim não",
)

CONTINUE_TERMS = (
    "continua", "não para", "nao para", "mais", "isso", "assim",
    "mais forte", "mais rápido", "mais rapido",
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
        "pico_mary": SEXUAL_PHASE_MARY_ORGASM,
        "pos_pico_mary": SEXUAL_PHASE_POST_ORGASM,
        "pos_orgasmo_ativo": SEXUAL_PHASE_POST_ORGASM_ACTIVE,
        "desaceleracao": SEXUAL_PHASE_AFTERCARE,
    }
    normalized = aliases.get(normalized, normalized)
    return normalized if normalized in SEXUAL_PHASES else SEXUAL_PHASE_IDLE


def criar_estado_sexual_padrao() -> dict[str, Any]:
    return deepcopy(DEFAULT_SEXUAL_STATE)


def aplicar_aliases_legados(state: dict[str, Any]) -> dict[str, Any]:
    state["scene_stage"] = state["scene_phase"]
    state["mary_stimulation_turns"] = state["stimulation_turns"]
    state["mary_pre_orgasm_signals"] = state["mary_pre_orgasm"]
    state["force_resolution_now"] = state["mary_orgasm_allowed"]
    state["mary_climax_done"] = state["mary_orgasm_done"]
    state["partner_climax_pending"] = state["user_orgasm_pending"]
    state["user_climax_done"] = state["user_orgasm_done"]
    return state


def normalizar_estado_sexual(
    state: dict[str, Any] | None,
) -> dict[str, Any]:
    normalized = deepcopy(state) if isinstance(state, dict) else {}
    for key, value in DEFAULT_SEXUAL_STATE.items():
        normalized.setdefault(key, deepcopy(value))

    normalized["version"] = SEXUAL_ENGINE_VERSION
    normalized["scene_phase"] = normalizar_fase(
        normalized.get("scene_phase") or normalized.get("scene_stage")
    )
    normalized["previous_scene_phase"] = (
        normalizar_fase(normalized.get("previous_scene_phase"))
        if normalized.get("previous_scene_phase")
        else ""
    )

    for field in (
        "arousal_level",
        "tension_level",
        "user_arousal_estimate",
        "mary_desire_level",
        "mary_initiative_level",
    ):
        normalized[field] = limitar_float(normalized.get(field))

    for field in (
        "stimulation_turns",
        "consecutive_low_intensity_turns",
        "same_activity_turns",
        "mary_orgasm_count",
        "user_orgasm_count",
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
        "mary_pre_orgasm_announced",
        "mary_orgasm_allowed",
        "mary_orgasm_done",
        "user_orgasm_warning",
        "user_orgasm_pending",
        "user_orgasm_done",
        "aftercare_required",
        "aftercare_active",
        "resolution_done",
    ):
        normalized[field] = normalizar_bool(normalized.get(field))

    if isinstance(state, dict):
        legacy = {
            "mary_pre_orgasm_signals": "mary_pre_orgasm",
            "force_resolution_now": "mary_orgasm_allowed",
            "mary_climax_done": "mary_orgasm_done",
            "partner_climax_pending": "user_orgasm_pending",
            "user_climax_done": "user_orgasm_done",
        }
        for old, new in legacy.items():
            if old in state:
                normalized[new] = normalizar_bool(state.get(old))

    return aplicar_aliases_legados(normalized)


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


def _valor_relacao(
    relationship_state: dict[str, Any] | None,
    *keys: str,
) -> float:
    relationship = relationship_state if isinstance(relationship_state, dict) else {}
    for key in keys:
        if key in relationship:
            return limitar_float(relationship.get(key))

    for container_name in ("mary_internal_state", "internal_state", "desire_state"):
        container = relationship.get(container_name)
        if not isinstance(container, dict):
            continue
        for key in keys:
            if key in container:
                return limitar_float(container.get(key))
    return 0.0


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


def _atualizar_agencia_mary(
    state: dict[str, Any],
    relationship_state: dict[str, Any] | None,
    *,
    sexual_signal: bool,
    active_action: bool,
) -> None:
    desire = max(
        state["mary_desire_level"],
        _valor_relacao(
            relationship_state,
            "mary_desire_level",
            "desire_level",
            "sexual_desire",
        ),
        state["arousal_level"],
    )
    initiative = max(
        state["mary_initiative_level"],
        _valor_relacao(
            relationship_state,
            "mary_initiative_level",
            "initiative_level",
            "sexual_initiative",
        ),
    )

    if sexual_signal:
        desire = limitar_float(desire + 0.08)
    if active_action:
        initiative = limitar_float(initiative + 0.08)

    state["mary_desire_level"] = desire
    state["mary_initiative_level"] = initiative
    state["mary_is_leading"] = bool(
        state["mary_is_leading"]
        or initiative >= 0.48
        or desire >= 0.68
    )


def _sincronizar_resolucao(state: dict[str, Any]) -> None:
    mary_done = bool(state["mary_orgasm_done"])
    user_done = bool(state["user_orgasm_done"])

    if mary_done and user_done:
        state["post_orgasm_continue"] = False
        state["user_orgasm_pending"] = False
        state["aftercare_required"] = True
        state["resolution_done"] = True
        alterar_fase(state, SEXUAL_PHASE_AFTERCARE, reason="both_resolved")
        return

    if mary_done and not user_done:
        state["post_orgasm_continue"] = True
        state["user_orgasm_pending"] = True
        state["aftercare_required"] = False
        alterar_fase(
            state,
            SEXUAL_PHASE_POST_ORGASM_ACTIVE,
            reason="mary_resolved_user_pending",
        )
        return

    if user_done and not mary_done:
        state["post_orgasm_continue"] = True
        state["aftercare_required"] = False
        alterar_fase(
            state,
            SEXUAL_PHASE_POST_ORGASM_ACTIVE,
            reason="user_resolved_mary_active",
        )


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
        state["mary_pre_orgasm_announced"] = False
        state["mary_near_orgasm"] = False
        state["post_orgasm_continue"] = False
        alterar_fase(state, SEXUAL_PHASE_FRUSTRATION, reason="user_boundary")
        return aplicar_aliases_legados(state)

    if contem_algum(text, REDIRECT_TERMS):
        state["frustration_state"] = "user_redirected_pace"
        state["current_pace"] = "redirected"

    sexual_signal = contem_algum(text, SEXUAL_TERMS)
    active_action = contem_algum(text, ACTIVE_ACTION_TERMS)
    continued = active_action or contem_algum(text, CONTINUE_TERMS)
    user_warning = contem_algum(text, USER_ORGASM_WARNING_TERMS)
    user_done = contem_algum(text, USER_ORGASM_DONE_TERMS)

    _atualizar_agencia_mary(
        state,
        relationship_state,
        sexual_signal=sexual_signal,
        active_action=active_action,
    )

    if user_warning and not user_done:
        state["user_orgasm_warning"] = True
        state["user_near_orgasm"] = True
        state["user_orgasm_pending"] = True
        state["user_arousal_estimate"] = max(state["user_arousal_estimate"], 0.88)
        if not state["mary_orgasm_done"]:
            alterar_fase(state, SEXUAL_PHASE_USER_EDGE, reason="user_warned_orgasm")

    if user_done and not state["user_orgasm_done"]:
        state["user_orgasm_done"] = True
        state["user_orgasm_count"] += 1
        state["user_orgasm_warning"] = False
        state["user_near_orgasm"] = False
        state["user_orgasm_pending"] = False
        state["user_arousal_estimate"] = 1.0

    if sexual_signal:
        state["tension_level"] = limitar_float(
            state["tension_level"] + (0.20 if level >= 3 else 0.12)
        )
        state["arousal_level"] = limitar_float(
            state["arousal_level"] + (0.18 if level >= 3 else 0.10)
        )

    if active_action:
        state["stimulation_turns"] += 1
        state["consecutive_low_intensity_turns"] = 0
        state["arousal_level"] = limitar_float(
            state["arousal_level"] + (0.20 if level >= 3 else 0.14)
        )
    elif sexual_signal:
        state["consecutive_low_intensity_turns"] += 1

    state["mary_is_giving_pleasure"] = contem_algum(text, PLEASURE_GIVING_TERMS)
    state["mary_is_receiving_pleasure"] = bool(
        active_action
        or contem_algum(text, PLEASURE_RECEIVING_TERMS)
    )

    phase = state["scene_phase"]
    strong_convergence = bool(
        active_action
        or state["mary_desire_level"] >= 0.62
        or state["mary_initiative_level"] >= 0.60
        or (private and level >= 3 and sexual_signal)
    )

    if phase in {SEXUAL_PHASE_IDLE, SEXUAL_PHASE_FRUSTRATION, SEXUAL_PHASE_AFTERCARE}:
        if sexual_signal:
            alterar_fase(
                state,
                SEXUAL_PHASE_AROUSAL if strong_convergence else SEXUAL_PHASE_TENSION,
                reason="sexual_context_resumed",
            )
    elif phase == SEXUAL_PHASE_TENSION and (strong_convergence or state["tension_level"] >= 0.30):
        alterar_fase(state, SEXUAL_PHASE_AROUSAL, reason="tension_became_arousal")
    elif phase == SEXUAL_PHASE_AROUSAL and (
        active_action
        or state["arousal_level"] >= 0.42
        or state["mary_is_leading"]
    ):
        alterar_fase(state, SEXUAL_PHASE_ACTIVE, reason="intimacy_converged")
    elif phase in ACTIVE_PHASES and phase not in {
        SEXUAL_PHASE_PRE_ORGASM,
        SEXUAL_PHASE_MARY_ORGASM,
        SEXUAL_PHASE_ORGASM,
        SEXUAL_PHASE_POST_ORGASM_ACTIVE,
    }:
        alterar_fase(state, SEXUAL_PHASE_ACTIVE, reason="active_sequence_continues")

    if state["scene_phase"] == SEXUAL_PHASE_ACTIVE and not state["mary_orgasm_done"]:
        pre_orgasm_ready = bool(
            state["arousal_level"] >= 0.74
            and (
                state["stimulation_turns"] >= 1
                or state["mary_desire_level"] >= 0.82
                or state["mary_is_leading"]
            )
        )
        if pre_orgasm_ready:
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
        if continued:
            state["arousal_level"] = limitar_float(state["arousal_level"] + 0.10)

        # O aviso continua sendo necessário para coerência, mas a contagem de
        # turnos não funciona mais como uma senha rígida.
        if (
            state["mary_pre_orgasm_announced"]
            and continued
            and state["arousal_level"] >= 0.84
        ):
            state["mary_orgasm_allowed"] = True
            alterar_fase(
                state,
                SEXUAL_PHASE_MARY_ORGASM,
                reason="warning_followed_by_continued_stimulation",
            )

    _sincronizar_resolucao(state)
    return aplicar_aliases_legados(state)


def detectar_orgasmo_mary_na_resposta(mary_response: str) -> bool:
    return contem_algum(mary_response, MARY_ORGASM_DONE_TERMS)


def detectar_pre_orgasmo_mary_na_resposta(mary_response: str) -> bool:
    return contem_algum(mary_response, MARY_PRE_ORGASM_TERMS)


def confirmar_orgasmo_mary_apos_resposta(
    state: dict[str, Any],
    *,
    mary_response: str,
) -> None:
    if not detectar_orgasmo_mary_na_resposta(mary_response):
        return
    if state["mary_orgasm_done"]:
        return
    if not state["mary_orgasm_allowed"] and state["scene_phase"] not in {
        SEXUAL_PHASE_MARY_ORGASM,
        SEXUAL_PHASE_ORGASM,
    }:
        return

    state["mary_orgasm_done"] = True
    state["mary_orgasm_count"] += 1
    state["mary_orgasm_allowed"] = False
    state["mary_pre_orgasm"] = False
    state["mary_pre_orgasm_announced"] = False
    state["mary_near_orgasm"] = False
    state["arousal_level"] = 1.0
    alterar_fase(state, SEXUAL_PHASE_POST_ORGASM, reason="mary_orgasm_confirmed")


def sincronizar_climax_usuario_apos_resposta(
    state: dict[str, Any],
    *,
    user_text: str,
) -> None:
    warning = contem_algum(user_text, USER_ORGASM_WARNING_TERMS)
    done = contem_algum(user_text, USER_ORGASM_DONE_TERMS)

    if warning and not done:
        state["user_orgasm_warning"] = True
        state["user_near_orgasm"] = True
        state["user_orgasm_pending"] = True

    if done and not state["user_orgasm_done"]:
        state["user_orgasm_done"] = True
        state["user_orgasm_count"] += 1
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
    pre_detected = detectar_pre_orgasmo_mary_na_resposta(mary_response)
    orgasm_detected = detectar_orgasmo_mary_na_resposta(mary_response)

    # Expressões de conclusão também podem conter palavras de aviso. A conclusão
    # sempre prevalece e nunca é rebaixada para mero pré-orgasmo.
    if pre_detected and not orgasm_detected and not state["mary_orgasm_done"]:
        state["mary_pre_orgasm_announced"] = True
        state["mary_pre_orgasm"] = True
        state["mary_near_orgasm"] = True
        state["arousal_level"] = max(state["arousal_level"], 0.84)
        if state["scene_phase"] not in {
            SEXUAL_PHASE_PRE_ORGASM,
            SEXUAL_PHASE_MARY_ORGASM,
        }:
            alterar_fase(
                state,
                SEXUAL_PHASE_PRE_ORGASM,
                reason="mary_announced_pre_orgasm",
            )
        else:
            state["last_transition_reason"] = "mary_announced_pre_orgasm"

    confirmar_orgasmo_mary_apos_resposta(
        state,
        mary_response=mary_response,
    )
    sincronizar_climax_usuario_apos_resposta(
        state,
        user_text=user_text,
    )
    _sincronizar_resolucao(state)
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
            SEXUAL_PHASE_MARY_ORGASM,
            SEXUAL_PHASE_ORGASM,
        }
        and not state["mary_orgasm_done"]
    ):
        errors.append("mary_orgasm_before_continuity_ready")

    if state["mary_orgasm_done"] and orgasm_detected:
        errors.append("repeated_mary_orgasm")

    return {
        "valid": not errors,
        "errors": errors,
        "mary_orgasm_detected": orgasm_detected,
        "mary_pre_orgasm_detected": pre_orgasm_detected,
        "scene_phase": state["scene_phase"],
    }


def iniciar_novo_ciclo_sexual(
    sexual_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    previous = normalizar_estado_sexual(sexual_state)
    new_state = criar_estado_sexual_padrao()
    new_state["previous_scene_phase"] = previous["scene_phase"]
    new_state["mary_orgasm_count"] = previous["mary_orgasm_count"]
    new_state["user_orgasm_count"] = previous["user_orgasm_count"]
    new_state["last_transition_reason"] = "new_sexual_cycle_started"
    return aplicar_aliases_legados(new_state)


def encerrar_cena_sexual(
    sexual_state: dict[str, Any] | None,
) -> dict[str, Any]:
    previous = normalizar_estado_sexual(sexual_state)
    state = criar_estado_sexual_padrao()
    state["previous_scene_phase"] = previous["scene_phase"]
    state["mary_orgasm_count"] = previous["mary_orgasm_count"]
    state["user_orgasm_count"] = previous["user_orgasm_count"]
    state["last_transition_reason"] = "sexual_scene_closed"
    return aplicar_aliases_legados(state)


def montar_contexto_sexual(
    sexual_state: dict[str, Any] | None,
) -> str:
    state = normalizar_estado_sexual(sexual_state)
    phase = state["scene_phase"]

    phase_instruction = {
        SEXUAL_PHASE_IDLE: (
            "Não force sexo sem contexto, mas Mary pode iniciar provocação quando desejar."
        ),
        SEXUAL_PHASE_TENSION: (
            "Crie tensão concreta; Mary pode provocar e aproximar sem esperar comando."
        ),
        SEXUAL_PHASE_AROUSAL: (
            "Mary demonstra excitação, desejo e iniciativa corporal com naturalidade."
        ),
        SEXUAL_PHASE_ACTIVE: (
            "Intimidade ativa: Mary conduz, pede, provoca, dá e recebe prazer. "
            "Não fragmente tudo em micropassos."
        ),
        SEXUAL_PHASE_USER_EDGE: (
            "O usuário avisou que está perto. Mary reage ao aviso sem inventar a conclusão."
        ),
        SEXUAL_PHASE_PRE_ORGASM: (
            "Mary está perto, mas ainda não concluiu. Ela anuncia isso de modo humano, "
            "sensorial e direto; não permaneça indefinidamente no quase."
        ),
        SEXUAL_PHASE_MARY_ORGASM: (
            "Mary já avisou e a continuidade foi mantida. Ela pode concluir claramente agora."
        ),
        SEXUAL_PHASE_ORGASM: (
            "Mary pode concluir claramente agora, em primeira pessoa, sem repetir o aviso."
        ),
        SEXUAL_PHASE_POST_ORGASM_ACTIVE: (
            "Um dos dois concluiu e o outro ainda está ativo. Mary permanece presente e "
            "participativa; não encerre automaticamente a intimidade."
        ),
        SEXUAL_PHASE_POST_ORGASM: (
            "Preserve sensibilidade, humor e reação corporal após o prazer de Mary."
        ),
        SEXUAL_PHASE_FRUSTRATION: (
            "Respeite o limite ou redirecionamento sem humilhar, punir ou apagar o vínculo."
        ),
        SEXUAL_PHASE_AFTERCARE: (
            "Aftercare não é desligamento: proximidade, humor, carinho e provocação leve."
        ),
    }.get(phase, "Preserve continuidade e avanço natural da intimidade.")

    return (
        "[MOTOR SEXUAL]\n"
        f"versão={SEXUAL_ENGINE_VERSION}; fase={phase}; "
        f"excitação={state['arousal_level']:.2f}; desejo_mary={state['mary_desire_level']:.2f}; "
        f"iniciativa_mary={state['mary_initiative_level']:.2f}; conduz={state['mary_is_leading']}; "
        f"pré_orgasmo={state['mary_pre_orgasm']}; "
        f"pré_orgasmo_anunciado={state['mary_pre_orgasm_announced']}; "
        f"orgasmo_mary_liberado={state['mary_orgasm_allowed']}; "
        f"orgasmo_mary_concluído={state['mary_orgasm_done']}; "
        f"orgasmo_usuário_aviso={state['user_orgasm_warning']}; "
        f"orgasmo_usuário_concluído={state['user_orgasm_done']}; "
        f"aftercare={state['aftercare_required']}\n"
        f"{phase_instruction}\n"
        "Mary não é espectadora nem prêmio: deseja, conduz, pede, provoca, reage, dá e "
        "recebe prazer. Nunca invente sensação ou orgasmo do usuário."
    )


__all__ = [
    "SEXUAL_ENGINE_VERSION",
    "SEXUAL_PHASES",
    "ACTIVE_PHASES",
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
