from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable

from google_sheets_repository import (
    GoogleSheetsRepositoryError,
    MEMORIES_SHEET,
    adicionar_registro,
    atualizar_registro,
    obter_registros_aba,
    utc_now_iso,
)
from memory_store import normalizar_bool, normalizar_memoria, normalizar_texto


MEMORY_REPOSITORY_VERSION = "memory-repository-v1-sheets-upsert"


def _importance_from_sheet(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.6
    if number > 1.0:
        number = number / 100.0
    return max(0.0, min(1.0, number))


def _importance_to_sheet(value: Any) -> int:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.6
    if number > 1.0:
        number = number / 100.0
    return int(round(max(0.0, min(1.0, number)) * 100))


def normalizar_memoria_persistida(
    record: dict[str, Any],
    *,
    user_id: str = "",
) -> dict[str, Any]:
    raw = deepcopy(record) if isinstance(record, dict) else {}
    if not raw:
        return {}

    memory_id = normalizar_texto(raw.get("memory_id") or raw.get("memory_key"))
    normalized = normalizar_memoria(
        {
            **raw,
            "memory_key": memory_id,
            "memory_text": raw.get("memory_text") or raw.get("content"),
            "importance": _importance_from_sheet(raw.get("importance")),
            "confidence": raw.get("confidence", 1.0),
            "active": normalizar_bool(raw.get("active"), default=True),
            "confirmed": normalizar_bool(raw.get("confirmed"), default=True),
            "user_id": raw.get("user_id") or user_id,
        },
        user_id=user_id,
    )
    if not normalized:
        return {}

    normalized["memory_id"] = memory_id or normalized["memory_key"]
    return normalized


def listar_memorias_usuario(
    user_id: str,
    *,
    active_only: bool = False,
    limit: int = 250,
) -> list[dict[str, Any]]:
    uid = normalizar_texto(user_id)
    if not uid:
        return []

    try:
        records = obter_registros_aba(MEMORIES_SHEET)
    except Exception as exc:
        if isinstance(exc, GoogleSheetsRepositoryError):
            raise
        raise GoogleSheetsRepositoryError(
            f"Não foi possível carregar as memórias do usuário: {exc}"
        ) from exc

    memories: list[dict[str, Any]] = []
    for record in records:
        if normalizar_texto(record.get("user_id")) != uid:
            continue
        memory = normalizar_memoria_persistida(record, user_id=uid)
        if not memory:
            continue
        if active_only and not (
            memory.get("active", True) and memory.get("confirmed", True)
        ):
            continue
        memories.append(memory)

    memories.sort(
        key=lambda item: normalizar_texto(item.get("updated_at") or item.get("created_at")),
        reverse=True,
    )
    return memories[: max(1, int(limit or 250))]


def _registro_planilha(memory: dict[str, Any]) -> dict[str, Any]:
    normalized = normalizar_memoria(memory, user_id=str(memory.get("user_id") or ""))
    if not normalized:
        return {}

    memory_id = normalizar_texto(
        memory.get("memory_id") or normalized.get("memory_key")
    )
    now = utc_now_iso()
    return {
        "memory_id": memory_id,
        "memory_key": normalized.get("memory_key", memory_id),
        "user_id": normalized.get("user_id", ""),
        "created_at": normalized.get("created_at") or now,
        "updated_at": now,
        "memory_type": normalized.get("memory_type", "general"),
        "content": normalized.get("memory_text", ""),
        "memory_text": normalized.get("memory_text", ""),
        "subject": normalized.get("subject", ""),
        "importance": _importance_to_sheet(normalized.get("importance", 0.6)),
        "confidence": normalized.get("confidence", 1.0),
        "source_interaction_id": normalizar_texto(
            memory.get("source_interaction_id")
        ),
        "scenario_id": normalizar_texto(memory.get("scenario_id")),
        "tags": ",".join(str(tag) for tag in normalized.get("tags", [])),
        "pinned": bool(normalized.get("pinned", False)),
        "confirmed": bool(normalized.get("confirmed", True)),
        "active": bool(normalized.get("active", True)),
    }


def salvar_ou_atualizar_memoria(memory: dict[str, Any]) -> dict[str, Any]:
    record = _registro_planilha(memory)
    if not record or not record.get("memory_id") or not record.get("user_id"):
        raise GoogleSheetsRepositoryError(
            "A memória não possui identificadores suficientes para persistência."
        )

    updated = atualizar_registro(
        MEMORIES_SHEET,
        coluna_chave="memory_id",
        valor_chave=str(record["memory_id"]),
        alteracoes=record,
    )
    if not updated:
        adicionar_registro(MEMORIES_SHEET, record)

    return normalizar_memoria_persistida(record, user_id=str(record["user_id"]))


def salvar_memorias_em_lote(
    memories: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    saved: list[dict[str, Any]] = []
    for memory in memories:
        if not isinstance(memory, dict):
            continue
        normalized = salvar_ou_atualizar_memoria(memory)
        if normalized:
            saved.append(normalized)
    return saved


def desativar_memoria(
    *,
    user_id: str,
    memory_id: str,
) -> bool:
    uid = normalizar_texto(user_id)
    mid = normalizar_texto(memory_id)
    if not uid or not mid:
        return False

    memories = listar_memorias_usuario(uid, active_only=False)
    target = next(
        (
            memory
            for memory in memories
            if normalizar_texto(memory.get("memory_id") or memory.get("memory_key")) == mid
        ),
        None,
    )
    if not target:
        return False

    return atualizar_registro(
        MEMORIES_SHEET,
        coluna_chave="memory_id",
        valor_chave=mid,
        alteracoes={
            "active": False,
            "updated_at": utc_now_iso(),
        },
    )


__all__ = [
    "MEMORY_REPOSITORY_VERSION",
    "normalizar_memoria_persistida",
    "listar_memorias_usuario",
    "salvar_ou_atualizar_memoria",
    "salvar_memorias_em_lote",
    "desativar_memoria",
]
