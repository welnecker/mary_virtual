from __future__ import annotations

from typing import Any

import google_sheets_repository as _repo

_criar_sessao_original = _repo.criar_sessao


def _criar_sessao_compativel(
    *,
    user_id: str,
    model: str,
    prompt_version: str,
    app_version: str,
    session_id: str | None = None,
    started_at: str | None = None,
    **_: Any,
) -> dict[str, Any]:
    """Aceita tanto a assinatura atual quanto a usada pelo app restaurado."""

    if not session_id and not started_at:
        return _criar_sessao_original(
            user_id=user_id,
            model=model,
            prompt_version=prompt_version,
            app_version=app_version,
        )

    agora = _repo.utc_now_iso()
    sessao = {
        "session_id": str(session_id or _repo.gerar_id("ses")).strip(),
        "user_id": str(user_id or "").strip(),
        "started_at": str(started_at or agora).strip(),
        "last_activity_at": agora,
        "ended_at": "",
        "model": model,
        "prompt_version": prompt_version,
        "app_version": app_version,
        "status": "active",
    }

    _repo.adicionar_registro(
        _repo.SESSIONS_SHEET,
        sessao,
    )

    return sessao


_repo.criar_sessao = _criar_sessao_compativel
