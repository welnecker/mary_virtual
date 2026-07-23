from __future__ import annotations

from typing import Any, Callable

import streamlit as st


INTERACTION_RERUN_OPTIMIZER_VERSION = (
    "interaction-rerun-optimizer-v2-native-rerun-restored"
)

_INSTALLED = False
_ORIGINAL_TITLE: Callable[..., Any] | None = None


def aplicar_otimizacao_rerun() -> None:
    """
    Mantém o ciclo nativo do app.

    processar_interacao termina deliberadamente com st.rerun() depois de salvar
    mensagens, relação, cenário e interação. Suprimir esse rerun deixa a árvore
    de widgets e o session_state em ciclos diferentes e pode causar desconexão
    posterior. Esta integração permanece apenas por compatibilidade de importação.
    """
    return None


def install_interaction_rerun_optimizer() -> None:
    global _INSTALLED, _ORIGINAL_TITLE
    if _INSTALLED:
        return

    _ORIGINAL_TITLE = st.title

    def patched_title(*args: Any, **kwargs: Any) -> Any:
        aplicar_otimizacao_rerun()
        assert _ORIGINAL_TITLE is not None
        return _ORIGINAL_TITLE(*args, **kwargs)

    st.title = patched_title
    _INSTALLED = True


__all__ = [
    "INTERACTION_RERUN_OPTIMIZER_VERSION",
    "aplicar_otimizacao_rerun",
    "install_interaction_rerun_optimizer",
]
