from __future__ import annotations

from copy import deepcopy
from functools import wraps
from typing import Any, Callable

import streamlit as st

import ui.card_runtime_integration as runtime


SCENE_TRANSITION_PRESENTATION_VERSION = (
    "scene-transition-presentation-v1-next-turn-styled-card"
)
_INSTALLED = False
_STYLE_APPLIED = False

_TRANSITION_CSS = r"""
<style>
div[data-testid="stChatMessage"] blockquote {
    margin: 0.65rem 0 1rem 0;
    padding: 0.8rem 1rem;
    border-left: 4px solid rgba(181, 111, 255, 0.9);
    border-radius: 0.55rem;
    background: linear-gradient(
        135deg,
        rgba(109, 72, 145, 0.20),
        rgba(67, 45, 92, 0.12)
    );
    color: rgba(245, 236, 255, 0.94);
    font-family: Georgia, "Times New Roman", serif;
    font-size: 0.95rem;
    font-style: italic;
    letter-spacing: 0.01em;
}
div[data-testid="stChatMessage"] blockquote p {
    margin: 0;
}
</style>
""".strip()


def _text(value: Any) -> str:
    return str(value or "").strip()


def _instance() -> dict[str, Any] | None:
    value = st.session_state.get("scenario_instance")
    return value if isinstance(value, dict) else None


def _bridge_is_armed() -> bool:
    instance = _instance()
    if not isinstance(instance, dict):
        return False
    scene = instance.get("scene_state")
    if not isinstance(scene, dict):
        return False
    bridge = scene.get("dialogue_bridge")
    return isinstance(bridge, dict) and _text(bridge.get("status")) == "armed"


def _patch_next_turn_activation() -> None:
    current = getattr(runtime, "_arm_or_activate_bridge", None)
    if not callable(current) or getattr(current, "_mary_next_turn_bridge", False):
        return

    @wraps(current)
    def wrapper(prompt: Any) -> tuple[str, str]:
        # A primeira despedida arma a ponte e recebe somente uma resposta curta.
        # A interação imediatamente seguinte ativa a nova cena, mesmo quando o
        # usuário repete "tchau", "até" ou "valeu". Essa nova despedida não é
        # respondida novamente: a cena anterior já terminou.
        effective_prompt = "continuar a história na próxima cena" if _bridge_is_armed() else prompt
        return current(effective_prompt)

    wrapper._mary_next_turn_bridge = True  # type: ignore[attr-defined]
    runtime._arm_or_activate_bridge = wrapper


def _patch_bridge_prompt() -> None:
    current = getattr(runtime, "_bridge_prompt_block", None)
    if not callable(current) or getattr(current, "_mary_styled_transition", False):
        return

    @wraps(current)
    def wrapper() -> str:
        base = _text(current())
        if "PONTE LÓGICA DE DIÁLOGO" not in base:
            return base
        return (
            base
            + "\n\nFORMATO VISUAL OBRIGATÓRIO DA TRANSIÇÃO\n"
            + "- A primeira linha da resposta deve conter somente a mudança de tempo ou "
              "lugar, escrita como citação Markdown neste formato: > *texto da transição*\n"
            + "- Use uma única frase curta, por exemplo: > *Algum tempo depois, em outra "
              "seção do supermercado...*\n"
            + "- Depois da citação, deixe uma linha em branco e escreva apenas a nova fala "
              "de Mary.\n"
            + "- A citação é um quadro de passagem narrativa; não é fala em voz alta e não "
              "deve conter diálogo, explicação ou resumo.\n"
            + "- Não inclua a despedida anterior junto da transição."
        )

    wrapper._mary_styled_transition = True  # type: ignore[attr-defined]
    runtime._bridge_prompt_block = wrapper


def _patch_runtime_style() -> None:
    current = getattr(runtime, "aplicar_card_runtime", None)
    if not callable(current) or getattr(current, "_mary_transition_style", False):
        return

    @wraps(current)
    def wrapper() -> None:
        global _STYLE_APPLIED
        current()
        if not _STYLE_APPLIED:
            st.markdown(_TRANSITION_CSS, unsafe_allow_html=True)
            _STYLE_APPLIED = True

    wrapper._mary_transition_style = True  # type: ignore[attr-defined]
    runtime.aplicar_card_runtime = wrapper


def install_scene_transition_presentation() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    _patch_next_turn_activation()
    _patch_bridge_prompt()
    _patch_runtime_style()
    _INSTALLED = True


__all__ = [
    "SCENE_TRANSITION_PRESENTATION_VERSION",
    "install_scene_transition_presentation",
]
