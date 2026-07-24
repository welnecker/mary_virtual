from __future__ import annotations

from functools import wraps
from typing import Any, Callable

import streamlit as st

from repositories.memory_repository import (
    MEMORY_COLUMNS,
    MEMORY_REPOSITORY_VERSION,
    garantir_schema_memories,
    migrar_memorias_existentes,
)


MEMORY_PERSISTENCE_VERSION = "memory-persistence-v1-schema-sync-and-migration"

_INSTALLED = False
_ORIGINAL_TITLE: Callable[..., Any] | None = None
_SESSION_FLAG = "_mary_memories_schema_ready"


def aplicar_persistencia_memorias() -> None:
    if st.session_state.get(_SESSION_FLAG):
        return
    garantir_schema_memories()
    migrar_memorias_existentes()
    st.session_state[_SESSION_FLAG] = True


def install_memory_persistence() -> None:
    global _INSTALLED, _ORIGINAL_TITLE
    if _INSTALLED:
        return

    original_title = st.title
    _ORIGINAL_TITLE = original_title

    @wraps(original_title)
    def title_wrapper(*args: Any, **kwargs: Any) -> Any:
        aplicar_persistencia_memorias()
        return original_title(*args, **kwargs)

    st.title = title_wrapper
    _INSTALLED = True


__all__ = [
    "MEMORY_COLUMNS",
    "MEMORY_PERSISTENCE_VERSION",
    "MEMORY_REPOSITORY_VERSION",
    "aplicar_persistencia_memorias",
    "install_memory_persistence",
]
