from __future__ import annotations

from functools import wraps
from typing import Any, Callable

import ui.casada_frustrada_script_runtime as script_runtime
from ui.casada_frustrada_canonical_prompt import sincronizar_memoria_na_instancia


CASADA_FRUSTRADA_MEMORY_PERSISTENCE_VERSION = (
    "casada-frustrada-memory-persistence-v1"
)
_INSTALLED = False


def install_casada_frustrada_memory_persistence() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    original: Callable[..., Any] = script_runtime.salvar_instancia_cenario
    if getattr(original, "_mary_canonical_memory_persistence", False):
        _INSTALLED = True
        return

    @wraps(original)
    def wrapper(instance: Any, *args: Any, **kwargs: Any) -> Any:
        sincronizar_memoria_na_instancia(instance)
        return original(instance, *args, **kwargs)

    wrapper._mary_canonical_memory_persistence = True  # type: ignore[attr-defined]
    script_runtime.salvar_instancia_cenario = wrapper
    _INSTALLED = True


__all__ = [
    "CASADA_FRUSTRADA_MEMORY_PERSISTENCE_VERSION",
    "install_casada_frustrada_memory_persistence",
]
