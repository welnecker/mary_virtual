from __future__ import annotations

from functools import wraps
from typing import Any, Callable

import streamlit as st


SCENARIO_FINISH_BUTTON_SIDEBAR_VERSION = (
    "scenario-finish-button-sidebar-v1-no-chat-layout-jump"
)

_INSTALLED = False
_ORIGINAL_BUTTON: Callable[..., Any] | None = None
_FINISH_LABEL = "Finalizar história"


def install_scenario_finish_button_sidebar() -> None:
    """Renderiza o botão de encerramento na sidebar.

    O fluxo principal continua chamando ``st.button`` normalmente. Somente o botão
    com o rótulo exato de finalização é redirecionado para a sidebar, evitando que
    um elemento novo seja inserido abaixo do histórico e desloque a conversa após
    cada resposta.
    """

    global _INSTALLED, _ORIGINAL_BUTTON

    if _INSTALLED:
        return

    _ORIGINAL_BUTTON = st.button

    @wraps(_ORIGINAL_BUTTON)
    def patched_button(label: str, *args: Any, **kwargs: Any) -> Any:
        assert _ORIGINAL_BUTTON is not None

        if str(label or "").strip() != _FINISH_LABEL:
            return _ORIGINAL_BUTTON(label, *args, **kwargs)

        with st.sidebar:
            st.divider()
            st.caption("História")
            return _ORIGINAL_BUTTON(label, *args, **kwargs)

    st.button = patched_button
    _INSTALLED = True


__all__ = [
    "SCENARIO_FINISH_BUTTON_SIDEBAR_VERSION",
    "install_scenario_finish_button_sidebar",
]
