from __future__ import annotations

import importlib.util
from copy import deepcopy
from pathlib import Path
from typing import Any

_LEGACY_PATH = Path(__file__).resolve().parent.parent / "scenario_director.py"
_SPEC = importlib.util.spec_from_file_location(
    "_relationship_scenario_director_current",
    _LEGACY_PATH,
)

if _SPEC is None or _SPEC.loader is None:
    raise ImportError("Não foi possível carregar relationship/scenario_director.py.")

_current = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_current)

for _name in dir(_current):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_current, _name)

_analisar_atual = _current.analisar_turno_cenario
_aplicar_atual = _current.aplicar_analise_ao_estado
_integrar_atual = _current.integrar_direcao_cenario


def analisar_turno_cenario(
    *,
    user_text: str,
    scene_state: dict[str, Any] | None = None,
    interaction_number: int | None = None,
    api_key: str | None = None,
    model: str | None = None,
    scenario_config: dict[str, Any] | None = None,
    last_mary_response: str = "",
    recent_messages: list[dict[str, Any]] | None = None,
    **_: Any,
) -> dict[str, Any]:
    """Aceita simultaneamente os contratos antigo e atual do diretor."""

    state = deepcopy(scene_state) if isinstance(scene_state, dict) else {}

    if api_key and model and isinstance(scenario_config, dict):
        return _analisar_atual(
            api_key=api_key,
            model=model,
            scenario_config=scenario_config,
            scene_state=state,
            user_text=str(user_text or ""),
            last_mary_response=str(last_mary_response or ""),
            recent_messages=(
                recent_messages
                if isinstance(recent_messages, list)
                else []
            ),
        )

    analysis = _current.criar_analise_diretor_padrao(state)
    text = str(user_text or "").strip()
    analysis["user_action"] = text[:500]
    analysis["scene_changed"] = bool(text)
    analysis["narrative_progress"] = bool(text)
    analysis["confidence"] = 0.35 if text else 0.0

    try:
        number = max(0, int(interaction_number or 0))
    except (TypeError, ValueError):
        number = 0

    analysis["interaction_number"] = number
    return analysis


def aplicar_analise_ao_estado(
    *,
    scene_state: dict[str, Any],
    analise: dict[str, Any] | None = None,
    analysis: dict[str, Any] | None = None,
    interaction_number: int = 0,
    **_: Any,
) -> dict[str, Any]:
    """Aceita tanto `analise` quanto o alias antigo `analysis`."""

    state = scene_state if isinstance(scene_state, dict) else {}
    selected = analise if isinstance(analise, dict) else analysis
    if not isinstance(selected, dict):
        selected = _current.criar_analise_diretor_padrao(state)

    return _aplicar_atual(
        scene_state=state,
        analise=selected,
        interaction_number=interaction_number,
    )


def integrar_direcao_cenario(
    *,
    turn_direction: dict[str, Any],
    analise_cenario: dict[str, Any] | None = None,
    analysis: dict[str, Any] | None = None,
    scene_state: dict[str, Any] | None = None,
    turn_intent: dict[str, Any] | None = None,
    **_: Any,
) -> dict[str, Any]:
    """Compatibiliza o retorno novo com o envelope esperado pelo app antigo."""

    selected = (
        analise_cenario
        if isinstance(analise_cenario, dict)
        else analysis
    )
    if not isinstance(selected, dict):
        selected = {}

    state = deepcopy(scene_state) if isinstance(scene_state, dict) else {}
    direction = _integrar_atual(
        turn_direction=(
            turn_direction if isinstance(turn_direction, dict) else {}
        ),
        analise_cenario=selected,
        scene_state=state,
    )

    if turn_intent is None:
        return direction

    intent = deepcopy(turn_intent) if isinstance(turn_intent, dict) else {}

    if direction.get("should_lead"):
        intent["may_lead_conversation"] = True
    if direction.get("avoid_question"):
        intent["avoid_question"] = True
    if direction.get("sexual_expression_allowed"):
        intent["may_initiate_sexual_tension"] = True
    if direction.get("explicit_sexual_language_allowed"):
        intent["may_initiate_sexual_scene"] = True

    return {
        "turn_intent": intent,
        "turn_direction": direction,
        "scene_state": state,
    }


__all__ = [
    name
    for name in globals()
    if not name.startswith("_")
]
