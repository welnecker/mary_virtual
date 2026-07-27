from __future__ import annotations

from typing import Any

import streamlit as st

from scenarios.stories.casada_frustrada.prompt_context import (
    montar_contexto_interpretativo,
)
from scenarios.stories.casada_frustrada.story_observer import (
    observar_estado_narrativo,
)
from scenarios.stories.casada_frustrada.story_structure import (
    STORY_STRUCTURE_VERSION,
)
from scenarios.stories.casada_frustrada.story_sync import (
    reconciliar_posicao_narrativa,
)


CASADA_FRUSTRADA_CANONICAL_PROMPT_VERSION = STORY_STRUCTURE_VERSION
_STORY_STATE_SESSION_KEY = "casada_frustrada_story_state"
_STORY_SYNC_SESSION_KEY = "casada_frustrada_story_sync"


def _messages() -> list[dict[str, Any]]:
    value = st.session_state.get("messages")
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)][-24:]


def build_route_compass(route: str, current_beat: str) -> dict[str, Any]:
    messages = _messages()
    synchronized = reconciliar_posicao_narrativa(
        messages=messages,
        legacy_route=route,
        legacy_beat=current_beat,
    )
    resolved_route = str(synchronized.get("route") or route)
    resolved_beat = str(synchronized.get("beat") or current_beat)

    story_state = observar_estado_narrativo(
        st.session_state.get(_STORY_STATE_SESSION_KEY),
        messages=messages,
        route=resolved_route,
        beat_id=resolved_beat,
    )
    st.session_state[_STORY_STATE_SESSION_KEY] = story_state
    st.session_state[_STORY_SYNC_SESSION_KEY] = synchronized

    context = montar_contexto_interpretativo(
        route=resolved_route,
        current_beat=resolved_beat,
        story_state_value=story_state,
    )
    context["synchronized_position"] = synchronized
    context["current_function"] = {
        "route": resolved_route,
        "beat": resolved_beat,
        "authority": (
            "Esta é a posição narrativa factual e autoritativa. O roteiro oficial e o "
            "beat graph foram sincronizados a partir da conversa. Se current_milestone "
            "legado divergir, ignore-o e siga esta função atual."
        ),
    }
    context["source_authority"] = (
        "official_screenplay e current_function descrevem a mesma posição narrativa. "
        "beat_graph apenas indexa o movimento atual; immersive_screenplay define sua "
        "direção dramática. Nenhum dos dois pode avançar ou permanecer sozinho."
    )
    return context


def question_policy(route: str, question_streak: int, gate: str) -> dict[str, Any]:
    synchronized = st.session_state.get(_STORY_SYNC_SESSION_KEY)
    synchronized = synchronized if isinstance(synchronized, dict) else {}
    resolved_route = str(synchronized.get("route") or route)
    resolved_beat = str(synchronized.get("beat") or "")
    decision_gate = bool(gate) or resolved_beat == "offer_video"
    blocked = question_streak >= 2 or (
        resolved_route == "hidden_call" and not decision_gate
    )
    return {
        "recent_question_streak": question_streak,
        "question_allowed": not blocked,
        "reason": (
            "A função atual exige uma decisão concreta do usuário."
            if decision_gate
            else "Duas respostas interrogativas consecutivas: agora Mary deve afirmar, reagir ou agir sem perguntar."
            if question_streak >= 2
            else "Pergunta opcional, nunca automática."
        ),
        "synchronized_route": resolved_route,
        "synchronized_beat": resolved_beat,
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
