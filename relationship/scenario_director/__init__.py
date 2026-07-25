from __future__ import annotations

import importlib.util
import re
import unicodedata
from copy import deepcopy
from pathlib import Path
from types import ModuleType
from typing import Any

from scenarios.card_registry import enriquecer_config_com_card, obter_card


SCENARIO_DIRECTOR_BRIDGE_VERSION = (
    "scenario-director-bridge-v4-card-aware-semantic-routing"
)

_CANONICAL_PATH = Path(__file__).resolve().parent.parent / "scenario_director.py"
_SPEC = importlib.util.spec_from_file_location(
    "_relationship_scenario_director_canonical",
    _CANONICAL_PATH,
)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError("Não foi possível carregar relationship/scenario_director.py.")

_canonical: ModuleType = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_canonical)

_REQUIRED_API = (
    "DIRECTOR_SYSTEM_PROMPT",
    "criar_analise_diretor_padrao",
    "extrair_json_objeto",
    "normalizar_analise_diretor",
    "analisar_turno_cenario",
    "aplicar_analise_ao_estado",
    "integrar_direcao_cenario",
    "montar_direcao_narrativa",
)
_missing = [name for name in _REQUIRED_API if not hasattr(_canonical, name)]
if _missing:
    raise ImportError(
        "A API do diretor de cenário está incompleta: " + ", ".join(_missing)
    )


def _normalizar_busca(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _estado_sexual(scene_state: dict[str, Any] | None) -> dict[str, Any]:
    state = scene_state if isinstance(scene_state, dict) else {}
    sexual = state.get("sexual_state")
    return sexual if isinstance(sexual, dict) else {}


def _fase_anterior(scene_state: dict[str, Any] | None) -> str:
    state = scene_state if isinstance(scene_state, dict) else {}
    sexual = _estado_sexual(state)
    return str(
        sexual.get("scene_phase")
        or sexual.get("scene_stage")
        or state.get("sexual_scene_phase")
        or "idle"
    ).strip().lower()


def _excitacao_anterior(scene_state: dict[str, Any] | None) -> float:
    state = scene_state if isinstance(scene_state, dict) else {}
    sexual = _estado_sexual(state)
    return max(
        0.0,
        min(
            1.0,
            _safe_float(sexual.get("arousal_level", state.get("arousal_level", 0.0))),
        ),
    )


def _estimulo_apenas_seios(scene_state: dict[str, Any] | None) -> bool:
    state = scene_state if isinstance(scene_state, dict) else {}
    last_analysis = state.get("last_director_analysis")
    text = _normalizar_busca(
        " ".join(
            str(value or "")
            for value in (
                state.get("last_user_action"),
                state.get("recommended_focus"),
                last_analysis.get("user_action") if isinstance(last_analysis, dict) else "",
            )
        )
    )
    breast = any(
        token in text
        for token in ("seio", "seios", "peito", "peitos", "mamilo", "mamilos")
    )
    genital_or_penetrative = any(
        token in text
        for token in (
            "clitoris", "buceta", "xoxota", "vagina", "cu ", "anal",
            "penetr", "meter", "metendo", "pau", "dedo dentro", "oral nela",
        )
    )
    return breast and not genital_or_penetrative


def _foco_forca_orgasmo(value: Any) -> bool:
    text = _normalizar_busca(value)
    return any(
        marker in text
        for marker in (
            "pre orgasmo", "preorgasmo", "vai gozar", "vou gozar",
            "orgasmo", "quase gozando", "explodir", "chegar ao climax",
        )
    )


def _texto(value: Any) -> str:
    return str(value or "").strip()


def _transicao_permitida(scenario_id: str, current_route: str, next_route: str) -> bool:
    card = obter_card(scenario_id)
    routes = card.get("routes") if isinstance(card, dict) else {}
    current = routes.get(current_route) if isinstance(routes, dict) else {}
    if not isinstance(current, dict):
        return False
    possible = set(current.get("possible_next_routes") or [])
    forbidden = set(current.get("forbidden_transitions") or [])
    return bool(next_route and next_route in possible and next_route not in forbidden)


_ORIGINAL_NORMALIZAR_ANALISE = _canonical.normalizar_analise_diretor
_ORIGINAL_ANALISAR = _canonical.analisar_turno_cenario
_ORIGINAL_APLICAR = _canonical.aplicar_analise_ao_estado


def normalizar_analise_diretor(
    analise: dict[str, Any] | None,
    *,
    scene_state: dict[str, Any] | None,
) -> dict[str, Any]:
    raw = analise if isinstance(analise, dict) else {}
    result = _ORIGINAL_NORMALIZAR_ANALISE(raw, scene_state=scene_state)

    # Campos narrativos pertencentes ao contrato de cards. O normalizador
    # canônico antigo não os conhecia e os descartava.
    result["recommended_route"] = _texto(raw.get("recommended_route"))
    result["recommended_beat"] = _texto(raw.get("recommended_beat"))
    result["scene_closing_signal"] = bool(raw.get("scene_closing_signal", False))
    result["story_ending_signal"] = bool(
        raw.get("story_ending_signal", raw.get("ending_signal", False))
    )
    result["transition_reason"] = _texto(raw.get("transition_reason"))

    # Fim de local/bloco não encerra a história inteira.
    if result["scene_closing_signal"] and not result["story_ending_signal"]:
        result["ending_signal"] = False
    else:
        result["ending_signal"] = result["story_ending_signal"]

    previous_phase = _fase_anterior(scene_state)
    previous_arousal = _excitacao_anterior(scene_state)
    breast_only = _estimulo_apenas_seios(scene_state)
    explicit_near = bool(result.get("mary_near_orgasm"))
    explicit_done = bool(result.get("mary_orgasm_confirmed"))
    climax_signal = bool(result.get("climax_signal"))
    requested_phase = _texto(result.get("sexual_scene_phase")).lower() or "idle"
    requested_intent = _texto(result.get("sexual_turn_intent")).lower() or "none"
    focus_forces_orgasm = _foco_forca_orgasmo(result.get("recommended_focus"))
    already_near = previous_phase in {"pre_orgasm", "orgasm"} or previous_arousal >= 0.84
    orgasm_request = (
        requested_phase in {"pre_orgasm", "orgasm"}
        or requested_intent in {"approach_orgasm", "orgasm"}
        or focus_forces_orgasm
        or explicit_near
        or explicit_done
        or climax_signal
    )
    unsupported = orgasm_request and not already_near and (
        breast_only or not (explicit_near or explicit_done or climax_signal)
    )
    if unsupported:
        result["sexual_scene_phase"] = (
            "active" if bool(result.get("intimate_action_started")) else "arousal"
        )
        result["sexual_turn_intent"] = "intensify"
        result["mary_near_orgasm"] = False
        result["mary_orgasm_confirmed"] = False
        result["climax_signal"] = False
        if _texto(result.get("recommended_phase")).lower() == "climax":
            result["recommended_phase"] = "intimacy"
        result["recommended_focus"] = (
            "Mary reage com prazer intenso ao estímulo atual e conduz um próximo "
            "movimento coerente, sem anunciar pré-orgasmo ou orgasmo ainda."
        )
    return result


# O analisador canônico resolve este nome global em tempo de execução.
_canonical.normalizar_analise_diretor = normalizar_analise_diretor

_CARD_DIRECTOR_RULES = """
CONTRATO DE PERSONAGEM POR CARD
- scenario_config pode conter card_package, character_profile, psychology_profile,
  voice_profile, transition_policy e screenplay_policy.
- Esses campos definem exclusivamente a Mary do card atual. Não importe traços de
  outros cards nem complete a personagem com uma Mary global incompatível.
- Interprete transições semanticamente pelo turno, histórico e estado. Não use
  frases fixas, palavras-chave obrigatórias ou quantidade de interações.
- Retorne também: recommended_route, recommended_beat, scene_closing_signal,
  story_ending_signal e transition_reason.
- recommended_route deve permanecer vazio quando a rota atual ainda estiver viva.
- Uma mudança de local ou fim de conversa presencial é scene_closing_signal; não é
  story_ending_signal quando existe uma próxima rota válida.
- Só recomende rotas presentes em possible_next_routes da rota atual.
- O motor sexual compartilhado controla mecânica corporal; character_profile,
  psychology_profile e voice_profile controlam como esta Mary vive e expressa isso.
""".strip()

_DIRECTOR_ORGASM_GUARD = """
REGRA DE PLAUSIBILIDADE DO PRAZER
- Não use pressa narrativa como justificativa para pré-orgasmo ou orgasmo.
- Prazer intenso não significa automaticamente proximidade do clímax.
- Estímulo localizado nos seios normalmente aumenta excitação, mas não deve sozinho
  marcar pré-orgasmo ou orgasmo.
- recommended_focus nunca pode mandar Mary dizer “vou gozar” quando
  mary_near_orgasm=false e climax_signal=false.
""".strip()

DIRECTOR_SYSTEM_PROMPT = (
    str(_canonical.DIRECTOR_SYSTEM_PROMPT).strip()
    + "\n\n"
    + _CARD_DIRECTOR_RULES
    + "\n\n"
    + _DIRECTOR_ORGASM_GUARD
)
_canonical.DIRECTOR_SYSTEM_PROMPT = DIRECTOR_SYSTEM_PROMPT


def analisar_turno_cenario(*args: Any, **kwargs: Any) -> dict[str, Any]:
    enriched = dict(kwargs)
    config = enriched.get("scenario_config")
    if isinstance(config, dict):
        config = enriquecer_config_com_card(config)
        enriched["scenario_config"] = config
    result = _ORIGINAL_ANALISAR(*args, **enriched)
    result = deepcopy(result) if isinstance(result, dict) else {}
    if isinstance(config, dict):
        result["_scenario_id"] = _texto(config.get("scenario_id"))
    return result


def aplicar_analise_ao_estado(*args: Any, **kwargs: Any) -> dict[str, Any]:
    scene_state = kwargs.get("scene_state")
    analysis = kwargs.get("analise")
    if scene_state is None and args:
        scene_state = args[0]
    if analysis is None and len(args) > 1:
        analysis = args[1]

    result = _ORIGINAL_APLICAR(*args, **kwargs)
    result = deepcopy(result) if isinstance(result, dict) else {}
    analysis = analysis if isinstance(analysis, dict) else {}

    scenario_id = _texto(analysis.get("_scenario_id") or result.get("scenario_id"))
    current_route = _texto(result.get("current_route"))
    next_route = _texto(analysis.get("recommended_route"))
    next_beat = _texto(analysis.get("recommended_beat"))

    if scenario_id and _transicao_permitida(scenario_id, current_route, next_route):
        result["previous_route"] = current_route
        result["current_route"] = next_route
        if next_beat:
            result["current_beat"] = next_beat
        result["last_route_transition_reason"] = _texto(
            analysis.get("transition_reason")
        )
        result["scene_closing_signal"] = bool(
            analysis.get("scene_closing_signal", False)
        )
        result["ending_ready"] = bool(
            analysis.get("story_ending_signal", False)
        )
        result["ending_sent"] = False

    # Impede que encerramento de uma cena fique gravado como fim irreversível.
    if bool(analysis.get("scene_closing_signal")) and not bool(
        analysis.get("story_ending_signal")
    ):
        result["ending_ready"] = False
        result["ending_sent"] = False
        result["ending_reason"] = ""
        result["ending_type"] = ""

    result["last_director_analysis"] = deepcopy(analysis)
    return result


criar_analise_diretor_padrao = _canonical.criar_analise_diretor_padrao
extrair_json_objeto = _canonical.extrair_json_objeto
integrar_direcao_cenario = _canonical.integrar_direcao_cenario
montar_direcao_narrativa = _canonical.montar_direcao_narrativa


__all__ = [
    "SCENARIO_DIRECTOR_BRIDGE_VERSION",
    *_REQUIRED_API,
]
