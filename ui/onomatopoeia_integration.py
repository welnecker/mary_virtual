from __future__ import annotations

import sys
from functools import wraps
from typing import Any, Callable

import streamlit as st

from relationship.onomatopoeia import (
    enriquecer_sinais_com_onomatopeias,
    montar_contexto_onomatopeias,
)


ONOMATOPOEIA_INTEGRATION_VERSION = (
    "onomatopoeia-integration-v2-controlled-expression"
)


_INSTALLED = False
_ORIGINAL_TITLE: Callable[..., Any] | None = None


def _texto_turno(args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
    value = kwargs.get("user_text")
    if value is None and args:
        value = args[0]
    return str(value or "")


def _patch_signal_detector(module: Any) -> None:
    original = getattr(module, "detectar_sinais_relacao", None)
    if not callable(original) or getattr(original, "_mary_onomatopoeia_wrapped", False):
        return

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
        result = original(*args, **kwargs)
        return enriquecer_sinais_com_onomatopeias(
            result,
            _texto_turno(args, kwargs),
        )

    wrapper._mary_onomatopoeia_wrapped = True  # type: ignore[attr-defined]
    setattr(module, "detectar_sinais_relacao", wrapper)


def _resolver_texto_usuario(kwargs: dict[str, Any]) -> str:
    direct = str(kwargs.get("user_message") or "").strip()
    if direct:
        return direct

    relationship_state = kwargs.get("relationship_state")
    if isinstance(relationship_state, dict):
        active_turn = relationship_state.get("active_turn")
        if isinstance(active_turn, dict):
            return str(active_turn.get("user_text") or "").strip()

    messages = st.session_state.get("messages")
    if isinstance(messages, list):
        for item in reversed(messages):
            if isinstance(item, dict) and item.get("role") == "user":
                return str(item.get("content") or "").strip()
    return ""


def _patch_prompt_builder(module: Any) -> None:
    original = getattr(module, "montar_prompt_sistema", None)
    if not callable(original) or getattr(original, "_mary_onomatopoeia_wrapped", False):
        return

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> str:
        prompt = str(original(*args, **kwargs) or "")
        context = montar_contexto_onomatopeias(
            _resolver_texto_usuario(kwargs)
        )
        return f"{prompt.rstrip()}\n\n{context}\n"

    wrapper._mary_onomatopoeia_wrapped = True  # type: ignore[attr-defined]
    setattr(module, "montar_prompt_sistema", wrapper)


def aplicar_integracao_onomatopeias() -> None:
    module = sys.modules.get("__main__")
    if module is None:
        return
    _patch_signal_detector(module)
    _patch_prompt_builder(module)


def install_onomatopoeia_integration() -> None:
    global _INSTALLED, _ORIGINAL_TITLE
    if _INSTALLED:
        return

    _ORIGINAL_TITLE = st.title

    def patched_title(*args: Any, **kwargs: Any) -> Any:
        aplicar_integracao_onomatopeias()
        assert _ORIGINAL_TITLE is not None
        return _ORIGINAL_TITLE(*args, **kwargs)

    st.title = patched_title
    _INSTALLED = True


__all__ = [
    "ONOMATOPOEIA_INTEGRATION_VERSION",
    "aplicar_integracao_onomatopeias",
    "install_onomatopoeia_integration",
]
