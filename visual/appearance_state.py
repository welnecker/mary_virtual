from __future__ import annotations

from copy import deepcopy
from typing import Any


DEFAULT_VARIABLE_APPEARANCE_STATE: dict[str, Any] = {
    "hairstyle": "",
    "clothing": "",
    "makeup": "",
    "accessories": "",
    "expression": "",
    "location": "",
}


def criar_estado_aparencia_variavel_padrao() -> dict[str, Any]:
    return deepcopy(DEFAULT_VARIABLE_APPEARANCE_STATE)


__all__ = [
    "DEFAULT_VARIABLE_APPEARANCE_STATE",
    "criar_estado_aparencia_variavel_padrao",
]
