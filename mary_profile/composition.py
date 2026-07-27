from __future__ import annotations

from copy import deepcopy
from typing import Any


def mesclar_dict_profundo(
    base: dict[str, Any],
    incoming: Any,
) -> dict[str, Any]:
    result = deepcopy(base)
    if not isinstance(incoming, dict):
        return result

    for key, value in incoming.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = mesclar_dict_profundo(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


__all__ = ["mesclar_dict_profundo"]
