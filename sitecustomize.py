from __future__ import annotations

from typing import Any

from gspread import Worksheet
from gspread.exceptions import GSpreadException


# ==========================================================
# COMPATIBILIDADE COM CABEÇALHOS DUPLICADOS NO GOOGLE SHEETS
# ==========================================================


_get_all_records_original = Worksheet.get_all_records


def _get_all_records_compativel(
    self: Worksheet,
    *args: Any,
    **kwargs: Any,
) -> list[dict[str, Any]]:
    """
    Mantém o comportamento normal do gspread e aplica um fallback
    somente quando a linha de cabeçalho possui nomes duplicados.

    No fallback, a primeira ocorrência de cada cabeçalho é preservada.
    Colunas duplicadas posteriores e cabeçalhos vazios são ignorados.
    """

    try:
        return _get_all_records_original(
            self,
            *args,
            **kwargs,
        )
    except GSpreadException as exc:
        mensagem = str(exc).lower()

        if (
            "header row" not in mensagem
            or "duplicates" not in mensagem
        ):
            raise

        head = int(kwargs.get("head", 1) or 1)
        default_blank = kwargs.get("default_blank", "")
        valores = self.get_all_values()

        if len(valores) < head:
            return []

        cabecalhos_brutos = [
            str(valor).strip()
            for valor in valores[head - 1]
        ]

        indices_unicos: list[tuple[str, int]] = []
        vistos: set[str] = set()

        for indice, cabecalho in enumerate(
            cabecalhos_brutos
        ):
            if not cabecalho or cabecalho in vistos:
                continue

            vistos.add(cabecalho)
            indices_unicos.append(
                (cabecalho, indice)
            )

        registros: list[dict[str, Any]] = []

        for linha in valores[head:]:
            if not any(
                str(valor).strip()
                for valor in linha
            ):
                continue

            registro: dict[str, Any] = {}

            for cabecalho, indice in indices_unicos:
                registro[cabecalho] = (
                    linha[indice]
                    if indice < len(linha)
                    else default_blank
                )

            registros.append(registro)

        return registros


Worksheet.get_all_records = _get_all_records_compativel


# ==========================================================
# COMPATIBILIDADE DA CRIAÇÃO DE SESSÃO
# ==========================================================


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
        "session_id": str(
            session_id or _repo.gerar_id("ses")
        ).strip(),
        "user_id": str(user_id or "").strip(),
        "started_at": str(
            started_at or agora
        ).strip(),
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
