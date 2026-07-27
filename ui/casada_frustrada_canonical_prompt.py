from __future__ import annotations

from typing import Any

import streamlit as st

from scenarios.stories.casada_frustrada.prompt_context import (
    aplicar_estado_narrativo_ao_compasso,
)
from scenarios.stories.casada_frustrada.story_observer import (
    observar_estado_narrativo,
)
from scenarios.stories.casada_frustrada.story_structure import (
    STORY_STRUCTURE_VERSION,
    build_story_compass,
)


CASADA_FRUSTRADA_CANONICAL_PROMPT_VERSION = STORY_STRUCTURE_VERSION
_STORY_STATE_SESSION_KEY = "casada_frustrada_story_state"


def _messages() -> list[dict[str, Any]]:
    value = st.session_state.get("messages")
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)][-16:]


def build_route_compass(route: str, current_beat: str) -> dict[str, Any]:
    story_state = observar_estado_narrativo(
        st.session_state.get(_STORY_STATE_SESSION_KEY),
        messages=_messages(),
        route=route,
        beat_id=current_beat,
    )
    st.session_state[_STORY_STATE_SESSION_KEY] = story_state
    return aplicar_estado_narrativo_ao_compasso(
        build_story_compass(route, current_beat),
        story_state,
    )


def question_policy(route: str, question_streak: int, gate: str) -> dict[str, Any]:
    decision_gate = bool(gate)
    blocked = question_streak >= 2 or (route == "hidden_call" and not decision_gate)
    return {
        "recent_question_streak": question_streak,
        "question_allowed": not blocked,
        "reason": (
            "Pergunta somente para obter a decisão concreta exigida pelo portão atual."
            if route == "hidden_call" and decision_gate
            else "Duas respostas interrogativas consecutivas: agora Mary deve afirmar, reagir ou agir sem perguntar."
            if question_streak >= 2
            else "Pergunta opcional, nunca automática."
        ),
    }


# Mantido por compatibilidade com versões antigas. O módulo agora funciona como
# adaptador temporário entre Streamlit e o domínio narrativo da história.
def aplicar_prompt_canonico_casada_frustrada() -> None:
    return None


def install_casada_frustrada_canonical_prompt() -> None:
    return None


__all__ = [
    "CASADA_FRUSTRADA_CANONICAL_PROMPT_VERSION",
    "build_route_compass",
    "question_policy",
    "aplicar_prompt_canonico_casada_frustrada",
    "install_casada_frustrada_canonical_prompt",
]
