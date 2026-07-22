from __future__ import annotations

import importlib.util
import re
import unicodedata
from pathlib import Path
from types import ModuleType
from typing import Any


SCENARIO_DIRECTOR_BRIDGE_VERSION = "scenario-director-bridge-v3-orgasm-evidence-guard"

_CANONICAL_PATH = Path(__file__).resolve().parent.parent / "scenario_director.py"
_SPEC = importlib.util.spec_from_file_location(
    "_relationship_scenario_director_canonical",
    _CANONICAL_PATH,
)

if _SPEC is None or _SPEC.loader is None:
    raise ImportError(
        "Não foi possível carregar relationship/scenario_director.py."
    )

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
        "A API do diretor de cenário está incompleta: "
        + ", ".join(_missing)
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
            _safe_float(
                sexual.get("arousal_level", state.get("arousal_level", 0.0))
            ),
        ),
    )


def _estimulo_apenas_seios(scene_state: dict[str, Any] | None) -> bool:
    state = scene_state if isinstance(scene_state, dict) else {}
    text = _normalizar_busca(
        " ".join(
            str(value or "")
            for value in (
                state.get("last_user_action"),
                state.get("recommended_focus"),
                (state.get("last_director_analysis") or {}).get("user_action")
                if isinstance(state.get("last_director_analysis"), dict)
                else "",
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


_ORIGINAL_NORMALIZAR_ANALISE = _canonical.normalizar_analise_diretor


def normalizar_analise_diretor(
    analise: dict[str, Any] | None,
    *,
    scene_state: dict[str, Any] | None,
) -> dict[str, Any]:
    """Impede que o diretor invente pré-orgasmo sem evidência corporal.

    Estímulo nos seios pode ser intenso, aumentar excitação e levar Mary a pedir
    outra ação. Sozinho, porém, não autoriza automaticamente pré-orgasmo. Uma
    exceção só existe quando o estado anterior já estava próximo do clímax.
    """

    result = _ORIGINAL_NORMALIZAR_ANALISE(
        analise,
        scene_state=scene_state,
    )

    previous_phase = _fase_anterior(scene_state)
    previous_arousal = _excitacao_anterior(scene_state)
    breast_only = _estimulo_apenas_seios(scene_state)

    explicit_near = bool(result.get("mary_near_orgasm"))
    explicit_done = bool(result.get("mary_orgasm_confirmed"))
    climax_signal = bool(result.get("climax_signal"))
    requested_phase = str(result.get("sexual_scene_phase") or "idle").lower()
    requested_intent = str(result.get("sexual_turn_intent") or "none").lower()
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
        breast_only
        or not (explicit_near or explicit_done or climax_signal)
    )

    if unsupported:
        result["sexual_scene_phase"] = (
            "active" if bool(result.get("intimate_action_started")) else "arousal"
        )
        result["sexual_turn_intent"] = "intensify"
        result["mary_near_orgasm"] = False
        result["mary_orgasm_confirmed"] = False
        result["climax_signal"] = False
        if str(result.get("recommended_phase") or "").lower() == "climax":
            result["recommended_phase"] = "intimacy"
        result["recommended_focus"] = (
            "Mary reage com prazer intenso ao estímulo atual, mantém a excitação "
            "e conduz um próximo movimento corporal coerente, sem anunciar "
            "pré-orgasmo ou orgasmo ainda."
        )

    return result


# O analisador canônico resolve este nome global em tempo de execução.
_canonical.normalizar_analise_diretor = normalizar_analise_diretor

_DIRECTOR_ORGASM_GUARD = """

REGRA DE PLAUSIBILIDADE DO PRAZER
- Não use a pressa narrativa como justificativa para pré-orgasmo ou orgasmo.
- Prazer intenso não significa automaticamente proximidade do clímax.
- Estímulo localizado nos seios ou mamilos normalmente aumenta excitação e pode
  provocar gemidos, perda parcial de controle ou pedido de continuidade, mas não
  deve sozinho marcar mary_near_orgasm, approach_orgasm ou orgasm.
- Só recomende pré-orgasmo quando o estado sexual anterior já estiver elevado ou
  houver sinais corporais convergentes explícitos no turno.
- recommended_focus nunca pode mandar Mary dizer “vou gozar” quando
  mary_near_orgasm=false e climax_signal=false.
""".strip()

DIRECTOR_SYSTEM_PROMPT = (
    str(_canonical.DIRECTOR_SYSTEM_PROMPT).strip()
    + "\n\n"
    + _DIRECTOR_ORGASM_GUARD
)
_canonical.DIRECTOR_SYSTEM_PROMPT = DIRECTOR_SYSTEM_PROMPT

criar_analise_diretor_padrao = _canonical.criar_analise_diretor_padrao
extrair_json_objeto = _canonical.extrair_json_objeto
analisar_turno_cenario = _canonical.analisar_turno_cenario
aplicar_analise_ao_estado = _canonical.aplicar_analise_ao_estado
integrar_direcao_cenario = _canonical.integrar_direcao_cenario
montar_direcao_narrativa = _canonical.montar_direcao_narrativa


__all__ = [
    "SCENARIO_DIRECTOR_BRIDGE_VERSION",
    *_REQUIRED_API,
]
