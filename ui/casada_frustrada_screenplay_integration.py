from __future__ import annotations

import sys
from functools import wraps
from typing import Any, Callable

import streamlit as st

from scenarios.stories.casada_frustrada.screenplay import (
    SCENARIO_ID,
    montar_orientacao_roteiro,
)


CASADA_FRUSTRADA_SCREENPLAY_INTEGRATION_VERSION = (
    "casada-frustrada-screenplay-integration-v1-route-aware"
)

_INSTALLED = False
_ORIGINAL_TITLE: Callable[..., Any] | None = None


def _scenario_context() -> tuple[str, str]:
    instance = st.session_state.get("scenario_instance")
    if not isinstance(instance, dict):
        return "", ""

    scene_state = instance.get("scene_state")
    if not isinstance(scene_state, dict):
        scene_state = {}

    scenario_id = str(instance.get("scenario_id") or "").strip()
    route = str(
        instance.get("current_route")
        or scene_state.get("current_route")
        or ""
    ).strip()
    return scenario_id, route


def _patch_prompt_builder(module: Any) -> None:
    original = getattr(module, "montar_prompt_sistema", None)
    if not callable(original) or getattr(
        original,
        "_mary_casada_screenplay_wrapped",
        False,
    ):
        return

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> str:
        prompt = str(original(*args, **kwargs) or "")
        scenario_id, route = _scenario_context()
        if scenario_id != SCENARIO_ID:
            return prompt

        guidance = montar_orientacao_roteiro(route)
        if not guidance:
            return prompt
        return f"{prompt.rstrip()}\n\n{guidance}\n"

    wrapper._mary_casada_screenplay_wrapped = True  # type: ignore[attr-defined]
    setattr(module, "montar_prompt_sistema", wrapper)


def aplicar_roteiro_casada_frustrada() -> None:
    module = sys.modules.get("__main__")
    if module is None:
        return
    _patch_prompt_builder(module)


def install_casada_frustrada_screenplay_integration() -> None:
    global _INSTALLED, _ORIGINAL_TITLE
    if _INSTALLED:
        return

    _ORIGINAL_TITLE = st.title

    @wraps(_ORIGINAL_TITLE)
    def patched_title(*args: Any, **kwargs: Any) -> Any:
        aplicar_roteiro_casada_frustrada()
        assert _ORIGINAL_TITLE is not None
        return _ORIGINAL_TITLE(*args, **kwargs)

    st.title = patched_title
    _INSTALLED = True


__all__ = [
    "CASADA_FRUSTRADA_SCREENPLAY_INTEGRATION_VERSION",
    "aplicar_roteiro_casada_frustrada",
    "install_casada_frustrada_screenplay_integration",
]
