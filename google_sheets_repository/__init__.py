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


def atualizar_relacionamento_mary(
    user_id: str,
    alteracoes: dict[str, Any] | None = None,
    **campos: Any,
) -> dict[str, Any]:
    """Atualiza MARY_RELATIONSHIP aceitando a interface antiga do app."""

    user_id_normalizado = str(user_id or "").strip()
    if not user_id_normalizado:
        raise _base.GoogleSheetsRepositoryError(
            "O user_id não foi informado."
        )

    dados: dict[str, Any] = {}
    if isinstance(alteracoes, dict):
        dados.update(alteracoes)
    dados.update(campos)
    dados.pop("user_id", None)
    dados["updated_at"] = _base.utc_now_iso()

    existente = _base.obter_ou_criar_relacionamento_mary(
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
    return atualizado
