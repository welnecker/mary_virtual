from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

_LEGACY_PATH = Path(__file__).resolve().parent.parent / "sexual_engine.py"
_SPEC = importlib.util.spec_from_file_location(
    "_relationship_sexual_engine_current",
    _LEGACY_PATH,
)

if _SPEC is None or _SPEC.loader is None:
    raise ImportError("Não foi possível carregar relationship/sexual_engine.py.")

_current = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_current)

for _name in dir(_current):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_current, _name)

_atualizar_antes_atual = _current.atualizar_estado_sexual_antes_resposta


def atualizar_estado_sexual_antes_resposta(
    sexual_state: dict[str, Any] | None,
    *,
    user_text: str,
    relationship_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Aceita a chamada antiga sem relationship_state.

    Quando o app restaurado não fornece o estado completo da relação,
    utiliza um dicionário vazio. Isso mantém a progressão conservadora
    e evita liberar avanços dependentes de vínculo por engano.
    """

    estado_relacao = (
        relationship_state
        if isinstance(relationship_state, dict)
        else {}
    )

    return _atualizar_antes_atual(
        sexual_state,
        user_text=user_text,
        relationship_state=estado_relacao,
    )


__all__ = [
    name
    for name in globals()
    if not name.startswith("_")
]
