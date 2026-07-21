from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

_BASE_PATH = Path(__file__).resolve().parent.parent / "google_sheets_repository.py"
_SPEC = importlib.util.spec_from_file_location(
    "_google_sheets_repository_base",
    _BASE_PATH,
)

if _SPEC is None or _SPEC.loader is None:
    raise ImportError("Não foi possível carregar o repositório do Google Sheets.")

_base = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_base)

for _nome in dir(_base):
    if not _nome.startswith("__"):
        globals()[_nome] = getattr(_base, _nome)

_criar_sessao_original = _base.criar_sessao
_criar_relacionamento_original = _base.criar_relacionamento_mary
_obter_relacionamento_original = _base.obter_ou_criar_relacionamento_mary


def criar_sessao(
    *,
    user_id: str,
    model: str,
    prompt_version: str,
    app_version: str,
    session_id: str | None = None,
    started_at: str | None = None,
    **_: Any,
) -> dict[str, Any]:
    """Aceita a assinatura atual e a usada pelo app restaurado."""

    if not session_id and not started_at:
        return _criar_sessao_original(
            user_id=user_id,
            model=model,
            prompt_version=prompt_version,
            app_version=app_version,
        )

    agora = _base.utc_now_iso()
    sessao = {
        "session_id": str(
            session_id or _base.gerar_id("ses")
        ).strip(),
        "user_id": str(user_id or "").strip(),
        "started_at": str(started_at or agora).strip(),
        "last_activity_at": agora,
        "ended_at": "",
        "model": model,
        "prompt_version": prompt_version,
        "app_version": app_version,
        "status": "active",
    }

    _base.adicionar_registro(
        _base.SESSIONS_SHEET,
        sessao,
    )
    return sessao


def _relationship_id_padrao(user_id: str) -> str:
    return "rel_" + str(user_id or "").strip()


def _normalizar_relacionamento(
    registro: dict[str, Any] | None,
    *,
    user_id: str,
) -> dict[str, Any]:
    agora = _base.utc_now_iso()
    normalizado = dict(registro or {})

    normalizado.setdefault(
        "relationship_id",
        _relationship_id_padrao(user_id),
    )
    normalizado.setdefault("user_id", user_id)
    normalizado.setdefault("created_at", agora)
    normalizado.setdefault("updated_at", agora)
    normalizado.setdefault("mary_revealed", False)
    normalizado.setdefault("first_mary_image_id", "")
    normalizado.setdefault("first_reveal_at", "")
    normalizado.setdefault("user_has_seen_mary", False)
    normalizado.setdefault("user_first_visual_reaction", "")
    normalizado.setdefault("relationship_summary", "")

    return normalizado


def criar_relacionamento_mary(
    *,
    user_id: str,
) -> dict[str, Any]:
    user_id_normalizado = str(user_id or "").strip()
    if not user_id_normalizado:
        raise _base.GoogleSheetsRepositoryError(
            "O user_id não foi informado."
        )

    criado = _criar_relacionamento_original(
        user_id=user_id_normalizado
    )
    normalizado = _normalizar_relacionamento(
        criado,
        user_id=user_id_normalizado,
    )

    _base.atualizar_registro(
        _base.MARY_RELATIONSHIP_SHEET,
        coluna_chave="user_id",
        valor_chave=user_id_normalizado,
        alteracoes={
            "relationship_id": normalizado["relationship_id"],
        },
    )
    return normalizado


def obter_ou_criar_relacionamento_mary(
    user_id: str,
) -> dict[str, Any]:
    user_id_normalizado = str(user_id or "").strip()
    if not user_id_normalizado:
        raise _base.GoogleSheetsRepositoryError(
            "O user_id não foi informado."
        )

    existente = _obter_relacionamento_original(
        user_id_normalizado
    )
    normalizado = _normalizar_relacionamento(
        existente,
        user_id=user_id_normalizado,
    )

    if not str(existente.get("relationship_id", "") if isinstance(existente, dict) else "").strip():
        _base.atualizar_registro(
            _base.MARY_RELATIONSHIP_SHEET,
            coluna_chave="user_id",
            valor_chave=user_id_normalizado,
            alteracoes={
                "relationship_id": normalizado["relationship_id"],
            },
        )

    return normalizado


def _resolver_user_id_por_identificador(
    identificador: str,
) -> str:
    valor = str(identificador or "").strip()
    if not valor:
        return ""

    por_relacionamento = _base.buscar_registro(
        _base.MARY_RELATIONSHIP_SHEET,
        coluna="relationship_id",
        valor=valor,
    )
    if isinstance(por_relacionamento, dict):
        encontrado = str(
            por_relacionamento.get("user_id", "")
        ).strip()
        if encontrado:
            return encontrado

    if valor.startswith("rel_"):
        return valor[4:]

    return valor


def atualizar_relacionamento_mary(
    identificador: str,
    alteracoes: dict[str, Any] | None = None,
    **campos: Any,
) -> dict[str, Any]:
    """Aceita relationship_id ou user_id e a interface antiga do app."""

    user_id_normalizado = _resolver_user_id_por_identificador(
        identificador
    )
    if not user_id_normalizado:
        raise _base.GoogleSheetsRepositoryError(
            "O relacionamento não possui identificador válido."
        )

    dados: dict[str, Any] = {}
    if isinstance(alteracoes, dict):
        dados.update(alteracoes)
    dados.update(campos)
    dados.pop("user_id", None)
    dados["updated_at"] = _base.utc_now_iso()

    existente = obter_ou_criar_relacionamento_mary(
        user_id_normalizado
    )

    _base.atualizar_registro(
        _base.MARY_RELATIONSHIP_SHEET,
        coluna_chave="user_id",
        valor_chave=user_id_normalizado,
        alteracoes=dados,
    )

    atualizado = dict(existente)
    atualizado.update(dados)
    atualizado["user_id"] = user_id_normalizado
    atualizado.setdefault(
        "relationship_id",
        _relationship_id_padrao(user_id_normalizado),
    )
    return atualizado
