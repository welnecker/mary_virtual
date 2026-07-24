from __future__ import annotations

from copy import deepcopy
import sys
import time
from typing import Any, Callable

import google_sheets_repository as sheets_repository


SHEETS_READ_QUOTA_GUARD_VERSION = (
    "sheets-read-quota-guard-v1-per-sheet-cache-stale-fallback"
)

_RECORD_TTL_SECONDS = 120.0
_HEADER_TTL_SECONDS = 600.0

_INSTALLED = False
_ORIGINAL_GET_RECORDS: Callable[..., Any] | None = None
_ORIGINAL_GET_HEADERS: Callable[..., Any] | None = None
_ORIGINAL_ADD: Callable[..., Any] | None = None
_ORIGINAL_UPDATE: Callable[..., Any] | None = None

_RECORD_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_HEADER_CACHE: dict[str, tuple[float, list[str]]] = {}


def _sheet_name(value: Any) -> str:
    return str(value or "").strip()


def _is_quota_error(exc: BaseException) -> bool:
    text = str(exc or "").lower()
    return (
        "429" in text
        or "quota exceeded" in text
        or "read requests per minute" in text
        or "resource_exhausted" in text
    )


def _copy_records(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [deepcopy(dict(row)) for row in rows if isinstance(row, dict)]


def _cached_records(name: str, *, allow_expired: bool = False) -> list[dict[str, Any]] | None:
    cached = _RECORD_CACHE.get(name)
    if cached is None:
        return None
    timestamp, rows = cached
    if not allow_expired and time.monotonic() - timestamp > _RECORD_TTL_SECONDS:
        return None
    return _copy_records(rows)


def _cached_headers(name: str, *, allow_expired: bool = False) -> list[str] | None:
    cached = _HEADER_CACHE.get(name)
    if cached is None:
        return None
    timestamp, headers = cached
    if not allow_expired and time.monotonic() - timestamp > _HEADER_TTL_SECONDS:
        return None
    return list(headers)


def obter_registros_aba_protegido(nome_aba: str) -> list[dict[str, Any]]:
    name = _sheet_name(nome_aba)
    fresh = _cached_records(name)
    if fresh is not None:
        return fresh
    if _ORIGINAL_GET_RECORDS is None:
        return []
    try:
        rows = _ORIGINAL_GET_RECORDS(name)
    except Exception as exc:
        stale = _cached_records(name, allow_expired=True)
        if stale is not None and _is_quota_error(exc):
            return stale
        raise
    normalized = _copy_records(rows if isinstance(rows, list) else [])
    _RECORD_CACHE[name] = (time.monotonic(), normalized)
    return _copy_records(normalized)


def obter_cabecalhos_protegido(nome_aba: str) -> list[str]:
    name = _sheet_name(nome_aba)
    fresh = _cached_headers(name)
    if fresh is not None:
        return fresh
    if _ORIGINAL_GET_HEADERS is None:
        return []
    try:
        headers = _ORIGINAL_GET_HEADERS(name)
    except Exception as exc:
        stale = _cached_headers(name, allow_expired=True)
        if stale is not None and _is_quota_error(exc):
            return stale
        raise
    normalized = [str(value).strip() for value in (headers or [])]
    _HEADER_CACHE[name] = (time.monotonic(), normalized)
    return list(normalized)


def _no_global_clear(*_: Any, **__: Any) -> None:
    """Compatibilidade com st.cache_data.clear sem invalidar todas as abas."""


def invalidar_aba(nome_aba: str) -> None:
    name = _sheet_name(nome_aba)
    _RECORD_CACHE.pop(name, None)


def adicionar_registro_protegido(nome_aba: str, dados: dict[str, Any]) -> None:
    if _ORIGINAL_ADD is None:
        raise RuntimeError("Persistência do Google Sheets não inicializada.")
    name = _sheet_name(nome_aba)
    _ORIGINAL_ADD(name, dados)
    cached = _cached_records(name, allow_expired=True)
    if cached is not None:
        cached.append(deepcopy(dict(dados or {})))
        _RECORD_CACHE[name] = (time.monotonic(), cached)


def atualizar_registro_protegido(
    nome_aba: str,
    *,
    coluna_chave: str,
    valor_chave: str,
    alteracoes: dict[str, Any],
) -> bool:
    if _ORIGINAL_UPDATE is None:
        raise RuntimeError("Persistência do Google Sheets não inicializada.")
    name = _sheet_name(nome_aba)
    updated = _ORIGINAL_UPDATE(
        name,
        coluna_chave=coluna_chave,
        valor_chave=valor_chave,
        alteracoes=alteracoes,
    )
    if updated:
        cached = _cached_records(name, allow_expired=True)
        if cached is not None:
            target = str(valor_chave or "").strip()
            for row in cached:
                if str(row.get(coluna_chave, "") or "").strip() == target:
                    row.update(deepcopy(dict(alteracoes or {})))
                    break
            _RECORD_CACHE[name] = (time.monotonic(), cached)
    return bool(updated)


def _patch_imported_references() -> None:
    """Atualiza módulos que importaram funções antes da instalação do guard."""
    for module in list(sys.modules.values()):
        if module is None:
            continue
        namespace = getattr(module, "__dict__", None)
        if not isinstance(namespace, dict):
            continue
        if namespace.get("obter_registros_aba") is _ORIGINAL_GET_RECORDS:
            namespace["obter_registros_aba"] = obter_registros_aba_protegido
        if namespace.get("obter_cabecalhos") is _ORIGINAL_GET_HEADERS:
            namespace["obter_cabecalhos"] = obter_cabecalhos_protegido
        if namespace.get("adicionar_registro") is _ORIGINAL_ADD:
            namespace["adicionar_registro"] = adicionar_registro_protegido
        if namespace.get("atualizar_registro") is _ORIGINAL_UPDATE:
            namespace["atualizar_registro"] = atualizar_registro_protegido


def install_sheets_read_quota_guard() -> None:
    global _INSTALLED
    global _ORIGINAL_GET_RECORDS, _ORIGINAL_GET_HEADERS
    global _ORIGINAL_ADD, _ORIGINAL_UPDATE

    if _INSTALLED:
        return

    _ORIGINAL_GET_RECORDS = sheets_repository.obter_registros_aba
    _ORIGINAL_GET_HEADERS = sheets_repository.obter_cabecalhos
    _ORIGINAL_ADD = sheets_repository.adicionar_registro
    _ORIGINAL_UPDATE = sheets_repository.atualizar_registro

    obter_registros_aba_protegido.clear = _no_global_clear  # type: ignore[attr-defined]
    obter_cabecalhos_protegido.clear = _no_global_clear  # type: ignore[attr-defined]

    sheets_repository.obter_registros_aba = obter_registros_aba_protegido
    sheets_repository.obter_cabecalhos = obter_cabecalhos_protegido
    sheets_repository.adicionar_registro = adicionar_registro_protegido
    sheets_repository.atualizar_registro = atualizar_registro_protegido

    _patch_imported_references()
    _INSTALLED = True


__all__ = [
    "SHEETS_READ_QUOTA_GUARD_VERSION",
    "adicionar_registro_protegido",
    "atualizar_registro_protegido",
    "install_sheets_read_quota_guard",
    "invalidar_aba",
    "obter_cabecalhos_protegido",
    "obter_registros_aba_protegido",
]
