from __future__ import annotations

import sys
from typing import Any, Callable

import streamlit as st


COMPLETED_HISTORY_VISIBILITY_VERSION = (
    "completed-history-visibility-v1-hidden-from-catalog"
)

_INSTALLED = False
_ORIGINAL_TITLE: Callable[..., Any] | None = None


def ocultar_historias_concluidas_do_catalogo() -> None:
    """Mantém os registros concluídos, mas não os renderiza no catálogo."""

    module = sys.modules.get("__main__")
    if module is None:
        return

    renderer = getattr(module, "renderizar_historias_concluidas", None)
    if not callable(renderer):
        return
    if getattr(renderer, "_mary_completed_history_hidden", False):
        return

    def renderer_oculto(*args: Any, **kwargs: Any) -> str:
        return ""

    renderer_oculto._mary_completed_history_hidden = True  # type: ignore[attr-defined]
    setattr(module, "renderizar_historias_concluidas", renderer_oculto)


def install_completed_history_visibility() -> None:
    global _INSTALLED, _ORIGINAL_TITLE

    if _INSTALLED:
        return

    _ORIGINAL_TITLE = st.title

    def patched_title(*args: Any, **kwargs: Any) -> Any:
        ocultar_historias_concluidas_do_catalogo()
        assert _ORIGINAL_TITLE is not None
        return _ORIGINAL_TITLE(*args, **kwargs)

    st.title = patched_title
    _INSTALLED = True


__all__ = [
    "COMPLETED_HISTORY_VISIBILITY_VERSION",
    "install_completed_history_visibility",
    "ocultar_historias_concluidas_do_catalogo",
]
