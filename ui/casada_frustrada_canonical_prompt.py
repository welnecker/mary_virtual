from __future__ import annotations

from typing import Any

import streamlit as st

from scenarios.stories.casada_frustrada.canonical_memory import (
    atualizar_memoria_canonica,
    memoria_canonica_para_prompt,
)
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
    return [item for item in value if isinstance(item, dict)][-80:]


def _scenario_instance() -> dict[str, Any] | None:
    value = st.session_state.get("scenario_instance")
    if not isinstance(value, dict):
        return None
    if str(value.get("scenario_id") or "").strip() != "casada_frustrada":
        return None
    return value


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

    instance = _scenario_instance()
    previous_memory = instance.get("story_memory") if isinstance(instance, dict) else None
    canonical_memory = atualizar_memoria_canonica(
        previous_memory,
        messages=messages,
        route=resolved_route,
        beat=resolved_beat,
    )
    if isinstance(instance, dict):
        instance["story_memory"] = canonical_memory
        st.session_state["scenario_instance"] = instance

    context = montar_contexto_interpretativo(
        route=resolved_route,
        current_beat=resolved_beat,
        story_state_value=story_state,
    )
    context["canonical_story_memory"] = memoria_canonica_para_prompt(canonical_memory)
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
        "canonical_story_memory registra o passado compartilhado irreversível; "
        "official_screenplay define a direção dramática atual; current_function indexa a "
        "função aberta. Nenhuma função pode contradizer ou repetir uma memória desbloqueada."
    )
    context["output_contract"] = {
        "speech": (
            "Fala audível de Mary em texto normal, sem rótulo. Somente este conteúdo "
            "pode ser ouvido pelo usuário."
        ),
        "thought": (
            "Pensamento privado é opcional, dinâmico e sempre em primeira pessoa. Use-o "
            "somente quando revelar algo que Mary não diria. Escrever em parágrafo isolado "
            "iniciado exatamente por 'Pensamento de Mary:'."
        ),
        "thought_position": (
            "Não existe posição fixa para o pensamento. Coloque-o imediatamente antes da "
            "fala que ele prepara, entre duas falas quando ocorre uma mudança interna, ou "
            "logo depois da fala que o provoca. Nunca empurrá-lo automaticamente para o fim. "
            "A ordem dos blocos deve acompanhar a cronologia mental e verbal daquele turno."
        ),
        "thought_seed_policy": (
            "Qualquer thought_seed legado é apenas indicação psicológica. Não copiar, não "
            "parafrasear mecanicamente e não tratá-lo como texto obrigatório. Produzir um "
            "pensamento novo, curto e coerente com a fala atual, ou omiti-lo."
        ),
        "forbidden_narration": (
            "Nunca escrever narração em terceira pessoa, ponte de cena, rubrica ou descrição "
            "externa de ações. Não usar 'Mary faz', 'Mary olha', 'Ela faz', 'Ela olha', "
            "'Ponte de cena:' ou equivalentes. Gestos e hesitações devem aparecer pela fala "
            "ou por pensamento privado em primeira pessoa."
        ),
        "separation": (
            "Nunca misturar fala e pensamento no mesmo parágrafo. A resposta contém apenas "
            "fala direta e, quando realmente necessário, pensamento privado intercalado na "
            "posição lógica."
        ),
    }
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
