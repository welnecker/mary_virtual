from __future__ import annotations

import re
import unicodedata
from copy import deepcopy
from typing import Any


SEXUAL_PHASE_IDLE = "idle"
SEXUAL_PHASE_TENSION = "tension"
SEXUAL_PHASE_AROUSAL = "arousal"
SEXUAL_PHASE_ACTIVE = "active"
SEXUAL_PHASE_PRE_ORGASM = "pre_orgasm"
SEXUAL_PHASE_ORGASM = "orgasm"
SEXUAL_PHASE_POST_ORGASM = "post_orgasm"
SEXUAL_PHASE_FRUSTRATION = "frustration"
SEXUAL_PHASE_AFTERCARE = "aftercare"


SEXUAL_PHASES: tuple[str, ...] = (
    SEXUAL_PHASE_IDLE,
    SEXUAL_PHASE_TENSION,
    SEXUAL_PHASE_AROUSAL,
    SEXUAL_PHASE_ACTIVE,
    SEXUAL_PHASE_PRE_ORGASM,
    SEXUAL_PHASE_ORGASM,
    SEXUAL_PHASE_POST_ORGASM,
    SEXUAL_PHASE_FRUSTRATION,
    SEXUAL_PHASE_AFTERCARE,
)


DEFAULT_SEXUAL_STATE: dict[str, Any] = {
    "scene_phase": SEXUAL_PHASE_IDLE,
    "previous_scene_phase": "",
    "arousal_level": 0.0,
    "tension_level": 0.0,
    "stimulation_turns": 0,
    "consecutive_low_intensity_turns": 0,
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


# ==========================================================
# CONVERSÃO E NORMALIZAÇÃO
# ==========================================================


def safe_int(
    value: Any,
    default: int = 0,
) -> int:
    try:
        return int(
            value
        )
    except (TypeError, ValueError):
        return default


def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    try:
        return float(
            value
        )
    except (TypeError, ValueError):
        return default


def normalizar_bool(
    value: Any,
    *,
    default: bool = False,
) -> bool:
    if isinstance(
        value,
        bool,
    ):
        return value

    if value is None:
        return default

    if isinstance(
        value,
        (int, float),
    ):
        return bool(
            value
        )

    text = str(
        value
    ).strip().lower()

    if text in {
        "true",
        "1",
        "yes",
        "sim",
        "s",
        "verdadeiro",
    }:
        return True

    if text in {
        "false",
        "0",
        "no",
        "nao",
        "não",
        "n",
        "falso",
        "",
    }:
        return False

    return default


def limitar_float(
    value: Any,
    *,
    minimum: float = 0.0,
    maximum: float = 1.0,
) -> float:
    normalized = safe_float(
        value,
        minimum,
    )

    return max(
        minimum,
        min(
            maximum,
            normalized,
        ),
    )


def remover_acentos(
    text: str,
) -> str:
    normalized = unicodedata.normalize(
        "NFKD",
        str(
            text or ""
        ),
    )

    return "".join(
        character
        for character in normalized
        if not unicodedata.combining(
            character
        )
    )


def normalizar_texto(
    value: Any,
) -> str:
    text = remover_acentos(
        str(
            value or ""
        ).strip().lower()
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def contem_algum(
    text: str,
    terms: tuple[str, ...] | list[str],
) -> bool:
    normalized_text = normalizar_texto(
        text
    )

    return any(
        normalizar_texto(
            term
        ) in normalized_text
        for term in terms
        if str(
            term or ""
        ).strip()
    )


def normalizar_fase(
    phase: Any,
) -> str:
    normalized = normalizar_texto(
        phase
    )

    aliases = {
        "": SEXUAL_PHASE_IDLE,
        "none": SEXUAL_PHASE_IDLE,
        "inicio": SEXUAL_PHASE_IDLE,
        "nenhum": SEXUAL_PHASE_IDLE,
        "aproximacao": SEXUAL_PHASE_TENSION,
        "intimidade": SEXUAL_PHASE_TENSION,
        "excitacao": SEXUAL_PHASE_AROUSAL,
        "estimulo_corporal": SEXUAL_PHASE_ACTIVE,
        "sexo_ou_estimulo": SEXUAL_PHASE_ACTIVE,
        "pre_pico_mary": SEXUAL_PHASE_PRE_ORGASM,
        "pico_mary": SEXUAL_PHASE_ORGASM,
        "pos_pico_mary": SEXUAL_PHASE_POST_ORGASM,
        "pos_pico_mary_com_parceiro_pendente": (
            SEXUAL_PHASE_POST_ORGASM
        ),
        "desaceleracao": SEXUAL_PHASE_AFTERCARE,
    }

    normalized = aliases.get(
        normalized,
        normalized,
    )

    if normalized in SEXUAL_PHASES:
        return normalized

    return SEXUAL_PHASE_IDLE


# ==========================================================
# ESTADO
# ==========================================================


def criar_estado_sexual_padrao() -> dict[str, Any]:
    return deepcopy(
        DEFAULT_SEXUAL_STATE
    )


def normalizar_estado_sexual(
    state: dict[str, Any] | None,
) -> dict[str, Any]:
    normalized = criar_estado_sexual_padrao()

    if not isinstance(
        state,
        dict,
    ):
        return normalized

    normalized.update(
        state
    )

    normalized["scene_phase"] = normalizar_fase(
        normalized.get(
            "scene_phase"
        )
        or normalized.get(
            "scene_stage"
        )
    )

    normalized["previous_scene_phase"] = normalizar_fase(
        normalized.get(
            "previous_scene_phase"
        )
    ) if normalized.get(
        "previous_scene_phase"
    ) else ""

    normalized["arousal_level"] = limitar_float(
        normalized.get(
            "arousal_level",
            0.0,
        )
    )

    normalized["tension_level"] = limitar_float(
        normalized.get(
            "tension_level",
            0.0,
        )
    )

    normalized["stimulation_turns"] = max(
        0,
        safe_int(
            normalized.get(
                "stimulation_turns",
                normalized.get(
                    "mary_stimulation_turns",
                    0,
                ),
            )
        ),
    )

    normalized["consecutive_low_intensity_turns"] = max(
        0,
        safe_int(
            normalized.get(
                "consecutive_low_intensity_turns",
                0,
            )
        ),
    )

    bool_fields = (
        "mary_pre_orgasm",
        "mary_orgasm_allowed",
        "mary_orgasm_done",
        "user_orgasm_warning",
        "user_orgasm_pending",
        "user_orgasm_done",
        "aftercare_required",
        "resolution_done",
    )

    for field in bool_fields:
        normalized[field] = normalizar_bool(
            normalized.get(
                field
            ),
            default=False,
        )

    # Compatibilidade temporária com o motor antigo.
    if "mary_pre_orgasm_signals" in state:
        normalized["mary_pre_orgasm"] = normalizar_bool(
            state.get(
                "mary_pre_orgasm_signals"
            )
        )

    if "force_resolution_now" in state:
        normalized["mary_orgasm_allowed"] = normalizar_bool(
            state.get(
                "force_resolution_now"
            )
        )

    if "mary_climax_done" in state:
        normalized["mary_orgasm_done"] = normalizar_bool(
            state.get(
                "mary_climax_done"
            )
        )

    if "partner_climax_pending" in state:
        normalized["user_orgasm_pending"] = normalizar_bool(
            state.get(
                "partner_climax_pending"
            )
        )

    if "user_climax_done" in state:
        normalized["user_orgasm_done"] = normalizar_bool(
            state.get(
                "user_climax_done"
            )
        )

    if state.get(
        "mary_frustracao_climax"
    ):
        normalized["frustration_state"] = str(
            state.get(
                "mary_frustracao_climax"
            )
        ).strip()

    return normalized


def aplicar_aliases_legados(
    state: dict[str, Any],
) -> dict[str, Any]:
    state["scene_stage"] = state[
        "scene_phase"
    ]

    state["mary_pre_orgasm_signals"] = state[
        "mary_pre_orgasm"
    ]

    state["force_resolution_now"] = state[
        "mary_orgasm_allowed"
    ]

    state["mary_climax_done"] = state[
        "mary_orgasm_done"
    ]

    state["partner_climax_pending"] = state[
        "user_orgasm_pending"
    ]

    state["user_climax_done"] = state[
        "user_orgasm_done"
    ]

    state["mary_frustracao_climax"] = state[
        "frustration_state"
    ]

    state["mary_stimulation_turns"] = state[
        "stimulation_turns"
    ]

    return state


def alterar_fase(
    state: dict[str, Any],
    new_phase: str,
    *,
    reason: str,
) -> None:
    current_phase = normalizar_fase(
        state.get(
            "scene_phase"
        )
    )

    normalized_new_phase = normalizar_fase(
        new_phase
    )

    if current_phase != normalized_new_phase:
        state[
            "previous_scene_phase"
        ] = current_phase

    state[
        "scene_phase"
    ] = normalized_new_phase

    state[
        "last_transition_reason"
    ] = str(
        reason or ""
    ).strip()


# ==========================================================
# DETECÇÃO DE SINAIS
# ==========================================================


def detectar_sinal_climax_usuario(
    user_text: str,
) -> str:
    text = normalizar_texto(
        user_text
    )

    negations = (
        "nao gozei",
        "ainda nao gozei",
        "nao estou gozando",
        "nao acabei",
        "estou segurando",
        "to segurando",
        "segurei",
        "nao quero terminar",
    )

    if contem_algum(
        text,
        negations,
    ):
        return "none"

    ongoing = (
        "estou gozando",
        "to gozando",
        "gozando agora",
        "eu gozei",
        "ja gozei",
        "acabei agora",
    )

    warning = (
        "vou gozar",
        "estou quase",
        "to quase",
        "nao vou aguentar",
        "vou perder o controle",
        "ta vindo",
    )

    if contem_algum(
        text,
        ongoing,
    ):
        return "ongoing"

    if contem_algum(
        text,
        warning,
    ):
        return "warning"

    return "none"


def detectar_orgasmo_mary_na_resposta(
    mary_response: str,
) -> bool:
    text = normalizar_texto(
        mary_response
    )

    if not text:
        return False

    negations = (
        "nao gozei",
        "ainda nao gozei",
        "quase gozei",
        "estou quase",
        "to quase",
        "vou gozar",
        "sem gozar",
        "segurei",
    )

    if contem_algum(
        text,
        negations,
    ):
        return False

    confirmations = (
        "eu gozei",
        "estou gozando",
        "to gozando",
        "meu orgasmo",
        "gozei agora",
        "gozei muito",
    )

    return contem_algum(
        text,
        confirmations,
    )


def detectar_climax_usuario_na_resposta(
    mary_response: str,
) -> bool:
    text = normalizar_texto(
        mary_response
    )

    confirmations = (
        "voce gozou",
        "voce acabou",
        "senti voce gozar",
        "agora que voce gozou",
    )

    return contem_algum(
        text,
        confirmations,
    )


def detectar_intensidade_turno(
    user_text: str,
) -> dict[str, Any]:
    text = normalizar_texto(
        user_text
    )

    tension_terms = (
        "atraido",
        "atraida",
        "desejo",
        "vontade",
        "provocando",
        "provocacao",
        "beijo",
        "beijar",
        "tesao",
        "excitada",
        "excitado",
    )

    active_terms = (
        "toque intimo",
        "tocando",
        "acariciando",
        "masturb",
        "sexo oral",
        "penetracao",
        "transando",
        "ritmo",
        "mais forte",
        "mais fundo",
        "continua assim",
    )

    sustained_terms = (
        "continua",
        "nao para",
        "mantem",
        "mesmo ritmo",
        "mais",
        "assim",
        "desse jeito",
    )

    deescalation_terms = (
        "para",
        "pare",
        "chega",
        "nao quero",
        "muda de assunto",
        "vamos parar",
        "encerra",
        "acabou",
        "nao estou confortavel",
    )

    aftercare_terms = (
        "fica comigo",
        "vem ca",
        "descansa",
        "respira",
        "carinho",
        "abraco",
        "deita comigo",
        "ta tudo bem",
    )

    return {
        "has_tension": contem_algum(
            text,
            tension_terms,
        ),
        "has_active_stimulation": contem_algum(
            text,
            active_terms,
        ),
        "has_sustained_stimulation": contem_algum(
            text,
            sustained_terms,
        ),
        "requests_deescalation": contem_algum(
            text,
            deescalation_terms,
        ),
        "has_aftercare_signal": contem_algum(
            text,
            aftercare_terms,
        ),
    }


def detectar_tipo_estimulo(
    user_text: str,
) -> str:
    text = normalizar_texto(
        user_text
    )

    stimulus_groups = {
        "kiss": (
            "beijo",
            "beijar",
            "boca",
            "labios",
        ),
        "touch": (
            "toque",
            "acaricia",
            "acariciando",
            "mao",
            "dedos",
        ),
        "oral": (
            "sexo oral",
            "oral",
            "lingua",
            "lambendo",
        ),
        "penetration": (
            "penetracao",
            "penetrando",
            "entra e sai",
            "ritmo",
            "mais fundo",
        ),
        "fantasy": (
            "imagina",
            "fantasia",
            "eu imaginaria",
            "na nossa fantasia",
        ),
    }

    for stimulus_type, terms in stimulus_groups.items():
        if contem_algum(
            text,
            terms,
        ):
            return stimulus_type

    return ""


# ==========================================================
# REGRAS DE ACESSO
# ==========================================================


def obter_nivel_sexual_relacao(
    relationship_state: dict[str, Any] | None,
) -> int:
    state = (
        relationship_state
        if isinstance(
            relationship_state,
            dict,
        )
        else {}
    )

    value = (
        state.get(
            "sexual_level"
        )
        or state.get(
            "sexual_intimacy"
        )
        or 0
    )

    return max(
        0,
        min(
            5,
            safe_int(
                value,
                0,
            ),
        ),
    )


def cena_sexual_pode_avancar(
    relationship_state: dict[str, Any] | None,
) -> bool:
    return (
        obter_nivel_sexual_relacao(
            relationship_state
        )
        >= 3
    )


def cena_sexual_intensa_permitida(
    relationship_state: dict[str, Any] | None,
) -> bool:
    return (
        obter_nivel_sexual_relacao(
            relationship_state
        )
        >= 4
    )


# ==========================================================
# GATE DO ORGASMO DE MARY
# ==========================================================


def calcular_minimo_turnos_estimulo(
    relationship_state: dict[str, Any] | None,
) -> int:
    sexual_level = obter_nivel_sexual_relacao(
        relationship_state
    )

    # Relação mais íntima permite fluxo mais natural,
    # mas nunca orgasmo imediato.
    if sexual_level >= 5:
        return 4

    if sexual_level >= 4:
        return 5

    return 6


def atualizar_gate_orgasmo_mary(
    state: dict[str, Any],
    *,
    relationship_state: dict[str, Any] | None,
) -> None:
    if state[
        "mary_orgasm_done"
    ]:
        state[
            "mary_pre_orgasm"
        ] = False

        state[
            "mary_orgasm_allowed"
        ] = False

        return

    phase = normalizar_fase(
        state.get(
            "scene_phase"
        )
    )

    stimulation_turns = safe_int(
        state.get(
            "stimulation_turns",
            0,
        )
    )

    arousal = limitar_float(
        state.get(
            "arousal_level",
            0.0,
        )
    )

    minimum_turns = calcular_minimo_turnos_estimulo(
        relationship_state
    )

    active_phase = phase in {
        SEXUAL_PHASE_ACTIVE,
        SEXUAL_PHASE_PRE_ORGASM,
    }

    pre_orgasm_ready = (
        active_phase
        and stimulation_turns >= max(
            3,
            minimum_turns - 2,
        )
        and arousal >= 0.72
    )

    resolution_ready = (
        active_phase
        and stimulation_turns >= minimum_turns
        and arousal >= 0.9
    )

    if resolution_ready:
        state[
            "mary_pre_orgasm"
        ] = True

        state[
            "mary_orgasm_allowed"
        ] = True

        alterar_fase(
            state,
            SEXUAL_PHASE_ORGASM,
            reason="orgasm_gate_reached",
        )

        return

    if pre_orgasm_ready:
        state[
            "mary_pre_orgasm"
        ] = True

        state[
            "mary_orgasm_allowed"
        ] = False

        alterar_fase(
            state,
            SEXUAL_PHASE_PRE_ORGASM,
            reason="pre_orgasm_threshold_reached",
        )

        return

    state[
        "mary_pre_orgasm"
    ] = False

    state[
        "mary_orgasm_allowed"
    ] = False


# ==========================================================
# PROGRESSÃO ANTES DA RESPOSTA
# ==========================================================


def atualizar_progressao_por_sinais(
    state: dict[str, Any],
    *,
    signals: dict[str, Any],
    relationship_state: dict[str, Any] | None,
) -> None:
    phase = normalizar_fase(
        state.get(
            "scene_phase"
        )
    )

    if signals[
        "requests_deescalation"
    ]:
        state[
            "arousal_level"
        ] = max(
            0.0,
            state[
                "arousal_level"
            ] - 0.25,
        )

        state[
            "tension_level"
        ] = max(
            0.0,
            state[
                "tension_level"
            ] - 0.3,
        )

        state[
            "mary_pre_orgasm"
        ] = False

        state[
            "mary_orgasm_allowed"
        ] = False

        state[
            "stimulation_turns"
        ] = 0

        state[
            "aftercare_required"
        ] = (
            phase
            in {
                SEXUAL_PHASE_ACTIVE,
                SEXUAL_PHASE_PRE_ORGASM,
                SEXUAL_PHASE_ORGASM,
                SEXUAL_PHASE_POST_ORGASM,
            }
        )

        alterar_fase(
            state,
            (
                SEXUAL_PHASE_AFTERCARE
                if state[
                    "aftercare_required"
                ]
                else SEXUAL_PHASE_IDLE
            ),
            reason="user_requested_deescalation",
        )

        return

    if signals[
        "has_active_stimulation"
    ]:
        if not cena_sexual_pode_avancar(
            relationship_state
        ):
            state[
                "tension_level"
            ] = min(
                1.0,
                state[
                    "tension_level"
                ] + 0.08,
            )

            alterar_fase(
                state,
                SEXUAL_PHASE_TENSION,
                reason="sexual_progression_blocked_by_relationship_level",
            )

            return

        state[
            "consecutive_low_intensity_turns"
        ] = 0

        state[
            "stimulation_turns"
        ] += 1

        arousal_increment = (
            0.16
            if signals[
                "has_sustained_stimulation"
            ]
            else 0.11
        )

        state[
            "arousal_level"
        ] = min(
            1.0,
            state[
                "arousal_level"
            ] + arousal_increment,
        )

        state[
            "tension_level"
        ] = min(
            1.0,
            state[
                "tension_level"
            ] + 0.08,
        )

        if phase not in {
            SEXUAL_PHASE_PRE_ORGASM,
            SEXUAL_PHASE_ORGASM,
        }:
            alterar_fase(
                state,
                SEXUAL_PHASE_ACTIVE,
                reason="active_stimulation_detected",
            )

        return

    if signals[
        "has_tension"
    ]:
        state[
            "consecutive_low_intensity_turns"
        ] = 0

        state[
            "tension_level"
        ] = min(
            1.0,
            state[
                "tension_level"
            ] + 0.12,
        )

        state[
            "arousal_level"
        ] = min(
            1.0,
            state[
                "arousal_level"
            ] + 0.04,
        )

        if phase == SEXUAL_PHASE_IDLE:
            alterar_fase(
                state,
                SEXUAL_PHASE_TENSION,
                reason="sexual_tension_detected",
            )

        elif (
            phase == SEXUAL_PHASE_TENSION
            and state[
                "tension_level"
            ] >= 0.55
        ):
            alterar_fase(
                state,
                SEXUAL_PHASE_AROUSAL,
                reason="tension_became_arousal",
            )

        return

    state[
        "consecutive_low_intensity_turns"
    ] += 1

    state[
        "tension_level"
    ] = max(
        0.0,
        state[
            "tension_level"
        ] - 0.05,
    )

    if phase not in {
        SEXUAL_PHASE_ACTIVE,
        SEXUAL_PHASE_PRE_ORGASM,
        SEXUAL_PHASE_ORGASM,
        SEXUAL_PHASE_POST_ORGASM,
    }:
        state[
            "arousal_level"
        ] = max(
            0.0,
            state[
                "arousal_level"
            ] - 0.04,
        )

    if (
        state[
            "consecutive_low_intensity_turns"
        ] >= 3
        and phase in {
            SEXUAL_PHASE_TENSION,
            SEXUAL_PHASE_AROUSAL,
        }
    ):
        alterar_fase(
            state,
            SEXUAL_PHASE_IDLE,
            reason="sexual_tension_naturally_dissipated",
        )


def processar_climax_usuario_antes_resposta(
    state: dict[str, Any],
    *,
    user_text: str,
) -> None:
    signal = detectar_sinal_climax_usuario(
        user_text
    )

    state[
        "user_orgasm_warning"
    ] = signal == "warning"

    if signal == "none":
        return

    if signal == "warning":
        state[
            "user_orgasm_pending"
        ] = True

        state[
            "user_orgasm_done"
        ] = False

        if (
            not state[
                "mary_orgasm_done"
            ]
            and not state[
                "mary_orgasm_allowed"
            ]
        ):
            state[
                "frustration_state"
            ] = "control_rhythm"

            if state[
                "mary_pre_orgasm"
            ]:
                alterar_fase(
                    state,
                    SEXUAL_PHASE_PRE_ORGASM,
                    reason="user_climax_warning_before_mary_resolution",
                )

        return

    if signal == "ongoing":
        state[
            "user_orgasm_pending"
        ] = False

        state[
            "user_orgasm_done"
        ] = True

        if not state[
            "mary_orgasm_done"
        ]:
            state[
                "frustration_state"
            ] = "user_finished_before_mary"

            state[
                "mary_pre_orgasm"
            ] = False

            state[
                "mary_orgasm_allowed"
            ] = False

            state[
                "aftercare_required"
            ] = True

            alterar_fase(
                state,
                SEXUAL_PHASE_FRUSTRATION,
                reason="user_climax_confirmed_before_mary",
            )

        else:
            state[
                "frustration_state"
            ] = ""

            state[
                "aftercare_required"
            ] = True

            alterar_fase(
                state,
                SEXUAL_PHASE_AFTERCARE,
                reason="user_climax_confirmed_after_mary",
            )


def atualizar_estado_sexual_antes_resposta(
    sexual_state: dict[str, Any] | None,
    *,
    user_text: str,
    relationship_state: dict[str, Any] | None,
) -> dict[str, Any]:
    state = normalizar_estado_sexual(
        sexual_state
    )

    signals = detectar_intensidade_turno(
        user_text
    )

    stimulus_type = detectar_tipo_estimulo(
        user_text
    )

    if stimulus_type:
        state[
            "last_stimulus_type"
        ] = stimulus_type

    atualizar_progressao_por_sinais(
        state,
        signals=signals,
        relationship_state=relationship_state,
    )

    atualizar_gate_orgasmo_mary(
        state,
        relationship_state=relationship_state,
    )

    processar_climax_usuario_antes_resposta(
        state,
        user_text=user_text,
    )

    if (
        signals[
            "has_aftercare_signal"
        ]
        and state[
            "aftercare_required"
        ]
    ):
        alterar_fase(
            state,
            SEXUAL_PHASE_AFTERCARE,
            reason="aftercare_signal_detected",
        )

    return aplicar_aliases_legados(
        state
    )


# ==========================================================
# SINCRONIZAÇÃO APÓS A RESPOSTA
# ==========================================================


def confirmar_orgasmo_mary_apos_resposta(
    state: dict[str, Any],
    *,
    mary_response: str,
) -> None:
    orgasm_detected = detectar_orgasmo_mary_na_resposta(
        mary_response
    )

    if not orgasm_detected:
        return

    if state[
        "mary_orgasm_done"
    ]:
        return

    if not state[
        "mary_orgasm_allowed"
    ]:
        # O modelo concluiu antes do gate. O fato não é confirmado.
        # A validação posterior poderá regenerar a resposta.
        state[
            "last_transition_reason"
        ] = "unauthorized_mary_orgasm_detected"

        return

    state[
        "mary_orgasm_done"
    ] = True

    state[
        "mary_pre_orgasm"
    ] = False

    state[
        "mary_orgasm_allowed"
    ] = False

    state[
        "resolution_done"
    ] = True

    state[
        "stimulation_turns"
    ] = 0

    if state[
        "user_orgasm_done"
    ]:
        state[
            "user_orgasm_pending"
        ] = False

        state[
            "aftercare_required"
        ] = True

        alterar_fase(
            state,
            SEXUAL_PHASE_AFTERCARE,
            reason="both_resolutions_completed",
        )

    else:
        state[
            "user_orgasm_pending"
        ] = True

        state[
            "aftercare_required"
        ] = False

        alterar_fase(
            state,
            SEXUAL_PHASE_POST_ORGASM,
            reason="mary_resolution_completed_user_pending",
        )


def sincronizar_climax_usuario_apos_resposta(
    state: dict[str, Any],
    *,
    mary_response: str,
) -> None:
    if state[
        "user_orgasm_done"
    ]:
        return

    if not detectar_climax_usuario_na_resposta(
        mary_response
    ):
        return

    state[
        "user_orgasm_done"
    ] = True

    state[
        "user_orgasm_pending"
    ] = False

    if state[
        "mary_orgasm_done"
    ]:
        state[
            "aftercare_required"
        ] = True

        alterar_fase(
            state,
            SEXUAL_PHASE_AFTERCARE,
            reason="user_resolution_confirmed_after_mary",
        )


def atualizar_pos_pico_e_aftercare(
    state: dict[str, Any],
) -> None:
    mary_done = state[
        "mary_orgasm_done"
    ]

    user_done = state[
        "user_orgasm_done"
    ]

    if mary_done and user_done:
        state[
            "user_orgasm_pending"
        ] = False

        state[
            "aftercare_required"
        ] = True

        state[
            "frustration_state"
        ] = ""

        alterar_fase(
            state,
            SEXUAL_PHASE_AFTERCARE,
            reason="complete_resolution_aftercare",
        )

        return

    if mary_done and not user_done:
        state[
            "user_orgasm_pending"
        ] = True

        state[
            "aftercare_required"
        ] = False

        alterar_fase(
            state,
            SEXUAL_PHASE_POST_ORGASM,
            reason="mary_done_user_still_pending",
        )

        return

    if user_done and not mary_done:
        state[
            "user_orgasm_pending"
        ] = False

        if not state[
            "frustration_state"
        ]:
            state[
                "frustration_state"
            ] = "user_finished_before_mary"

        state[
            "aftercare_required"
        ] = True

        alterar_fase(
            state,
            SEXUAL_PHASE_FRUSTRATION,
            reason="user_done_mary_unresolved",
        )


def atualizar_estado_sexual_apos_resposta(
    sexual_state: dict[str, Any] | None,
    *,
    user_text: str,
    mary_response: str,
) -> dict[str, Any]:
    state = normalizar_estado_sexual(
        sexual_state
    )

    confirmar_orgasmo_mary_apos_resposta(
        state,
        mary_response=mary_response,
    )

    sincronizar_climax_usuario_apos_resposta(
        state,
        mary_response=mary_response,
    )

    atualizar_pos_pico_e_aftercare(
        state
    )

    return aplicar_aliases_legados(
        state
    )


# ==========================================================
# VALIDAÇÃO DA RESPOSTA
# ==========================================================


def validar_resposta_sexual(
    sexual_state: dict[str, Any] | None,
    mary_response: str,
) -> dict[str, Any]:
    state = normalizar_estado_sexual(
        sexual_state
    )

    mary_orgasm_detected = detectar_orgasmo_mary_na_resposta(
        mary_response
    )

    errors: list[str] = []

    if (
        mary_orgasm_detected
        and not state[
            "mary_orgasm_allowed"
        ]
        and not state[
            "mary_orgasm_done"
        ]
    ):
        errors.append(
            "mary_orgasm_before_engine_authorization"
        )

    if (
        state[
            "mary_orgasm_done"
        ]
        and state[
            "scene_phase"
        ] == SEXUAL_PHASE_ORGASM
    ):
        errors.append(
            "repeated_mary_orgasm_phase"
        )

    if (
        state[
            "scene_phase"
        ] == SEXUAL_PHASE_AFTERCARE
        and state[
            "mary_orgasm_allowed"
        ]
    ):
        errors.append(
            "orgasm_authorization_active_during_aftercare"
        )

    return {
        "valid": not errors,
        "errors": errors,
        "mary_orgasm_detected": mary_orgasm_detected,
    }


# ==========================================================
# NOVO CICLO SEXUAL
# ==========================================================


def iniciar_novo_ciclo_sexual(
    sexual_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    previous = normalizar_estado_sexual(
        sexual_state
    )

    new_state = criar_estado_sexual_padrao()

    new_state[
        "previous_scene_phase"
    ] = previous[
        "scene_phase"
    ]

    new_state[
        "last_transition_reason"
    ] = "new_sexual_cycle_started"

    return aplicar_aliases_legados(
        new_state
    )


def encerrar_cena_sexual(
    sexual_state: dict[str, Any] | None,
) -> dict[str, Any]:
    state = normalizar_estado_sexual(
        sexual_state
    )

    state[
        "arousal_level"
    ] = 0.0

    state[
        "tension_level"
    ] = 0.0

    state[
        "stimulation_turns"
    ] = 0

    state[
        "consecutive_low_intensity_turns"
    ] = 0

    state[
        "mary_pre_orgasm"
    ] = False

    state[
        "mary_orgasm_allowed"
    ] = False

    state[
        "user_orgasm_warning"
    ] = False

    state[
        "user_orgasm_pending"
    ] = False

    state[
        "frustration_state"
    ] = ""

    state[
        "aftercare_required"
    ] = False

    alterar_fase(
        state,
        SEXUAL_PHASE_IDLE,
        reason="sexual_scene_closed",
    )

    return aplicar_aliases_legados(
        state
    )
