from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable

from google_sheets_repository import (
    GoogleSheetsRepositoryError,
    MEMORIES_SHEET,
    adicionar_registro,
    atualizar_registro,
    gerar_id,
    obter_aba,
    obter_cabecalhos,
    obter_registros_aba,
    utc_now_iso,
)
from memory_store import normalizar_bool, normalizar_memoria, normalizar_texto


MEMORY_REPOSITORY_VERSION = "memory-repository-v2-schema-sync-and-migration"

MEMORY_COLUMNS = (
    "memory_id",
    "memory_key",
    "user_id",
    "version",
    "created_at",
    "updated_at",
    "memory_type",
    "content",
    "memory_text",
    "subject",
    "importance",
    "confidence",
    "source_interaction_id",
    "scenario_id",
    "scenario_session_id",
    "tags",
    "pinned",
    "confirmed",
    "active",
)


def _clear_sheet_caches() -> None:
    for function in (obter_cabecalhos, obter_registros_aba):
        clear = getattr(function, "clear", None)
        if callable(clear):
            clear()


def garantir_schema_memories() -> list[str]:
    """Adiciona ao cabeçalho somente as colunas ainda ausentes."""
    worksheet = obter_aba(MEMORIES_SHEET)
    headers = list(obter_cabecalhos(MEMORIES_SHEET))
    added: list[str] = []

    for column in MEMORY_COLUMNS:
        if column in headers:
            continue
        headers.append(column)
        worksheet.update_cell(1, len(headers), column)
        added.append(column)

    if added:
        _clear_sheet_caches()
    return added


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


def _confidence_from_sheet(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.8
    if number > 1.0:
        number = number / 100.0
    return max(0.0, min(1.0, number))


def _confidence_to_sheet(value: Any) -> int:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.8
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

    memory_id = normalizar_texto(raw.get("memory_id"))
    memory_key = normalizar_texto(raw.get("memory_key") or memory_id)
    normalized = normalizar_memoria(
        {
            **raw,
            "memory_key": memory_key,
            "memory_text": raw.get("memory_text") or raw.get("content"),
            "importance": _importance_from_sheet(raw.get("importance")),
            "confidence": _confidence_from_sheet(raw.get("confidence")),
            "active": normalizar_bool(raw.get("active"), default=True),
            "confirmed": normalizar_bool(raw.get("confirmed"), default=True),
            "pinned": normalizar_bool(raw.get("pinned"), default=False),
            "user_id": raw.get("user_id") or user_id,
        },
        user_id=user_id,
    )
    if not normalized:
        return {}

    normalized["memory_id"] = memory_id or gerar_id("mem")
    normalized["version"] = max(1, _safe_int(raw.get("version"), 1))
    normalized["scenario_id"] = normalizar_texto(raw.get("scenario_id"))
    normalized["scenario_session_id"] = normalizar_texto(
        raw.get("scenario_session_id")
    )
    normalized["source_interaction_id"] = normalizar_texto(
        raw.get("source_interaction_id")
    )
    return normalized


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _registro_planilha(memory: dict[str, Any]) -> dict[str, Any]:
    normalized = normalizar_memoria(memory, user_id=str(memory.get("user_id") or ""))
    if not normalized:
        return {}

    memory_id = normalizar_texto(memory.get("memory_id")) or gerar_id("mem")
    now = utc_now_iso()
    tags = normalized.get("tags", [])
    if not isinstance(tags, list):
        tags = []

    return {
        "memory_id": memory_id,
        "memory_key": normalized.get("memory_key", ""),
        "user_id": normalized.get("user_id", ""),
        "version": max(1, _safe_int(memory.get("version"), 1)),
        "created_at": normalized.get("created_at") or now,
        "updated_at": now,
        "memory_type": normalized.get("memory_type", "general"),
        "content": normalized.get("memory_text", ""),
        "memory_text": normalized.get("memory_text", ""),
        "subject": normalized.get("subject", ""),
        "importance": _importance_to_sheet(normalized.get("importance", 0.6)),
        "confidence": _confidence_to_sheet(normalized.get("confidence", 0.8)),
        "source_interaction_id": normalizar_texto(
            memory.get("source_interaction_id")
        ),
        "scenario_id": normalizar_texto(memory.get("scenario_id")),
        "scenario_session_id": normalizar_texto(
            memory.get("scenario_session_id")
        ),
        "tags": ",".join(str(tag) for tag in tags),
        "pinned": bool(normalized.get("pinned", False)),
        "confirmed": bool(normalized.get("confirmed", True)),
        "active": bool(normalized.get("active", True)),
    }


def migrar_memorias_existentes() -> int:
    """Normaliza linhas antigas sem apagar conteúdo nem criar duplicatas."""
    garantir_schema_memories()
    records = obter_registros_aba(MEMORIES_SHEET)
    migrated = 0

    for record in records:
        user_id = normalizar_texto(record.get("user_id"))
        content = normalizar_texto(record.get("memory_text") or record.get("content"))
        if not user_id or not content:
            continue

        normalized = normalizar_memoria_persistida(record, user_id=user_id)
        if not normalized:
            continue
        payload = _registro_planilha({**record, **normalized})
        current_id = normalizar_texto(record.get("memory_id"))
        key_column = "memory_id"
        key_value = current_id

        if not key_value:
            key_column = "memory_key"
            key_value = normalizar_texto(payload.get("memory_key"))

        if key_value:
            updated = atualizar_registro(
                MEMORIES_SHEET,
                coluna_chave=key_column,
                valor_chave=key_value,
                alteracoes=payload,
            )
            if updated:
                migrated += 1
                continue

        adicionar_registro(MEMORIES_SHEET, payload)
        migrated += 1

    return migrated


def listar_memorias_usuario(
    user_id: str,
    *,
    active_only: bool = False,
    limit: int = 250,
) -> list[dict[str, Any]]:
    garantir_schema_memories()
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

    best_by_key: dict[str, dict[str, Any]] = {}
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
        key = normalizar_texto(memory.get("memory_key") or memory.get("memory_id"))
        current = best_by_key.get(key)
        if current is None or normalizar_texto(
            memory.get("updated_at")
        ) > normalizar_texto(current.get("updated_at")):
            best_by_key[key] = memory

    memories = list(best_by_key.values())
    memories.sort(
        key=lambda item: normalizar_texto(item.get("updated_at") or item.get("created_at")),
        reverse=True,
    )
    return memories[: max(1, int(limit or 250))]


def salvar_ou_atualizar_memoria(memory: dict[str, Any]) -> dict[str, Any]:
    garantir_schema_memories()
    record = _registro_planilha(memory)
    if not record or not record.get("memory_key") or not record.get("user_id"):
        raise GoogleSheetsRepositoryError(
            "A memória não possui identificadores suficientes para persistência."
        )

    existing = next(
        (
            item
            for item in obter_registros_aba(MEMORIES_SHEET)
            if normalizar_texto(item.get("user_id")) == record["user_id"]
            and normalizar_texto(item.get("memory_key")) == record["memory_key"]
        ),
        None,
    )

    if existing is not None:
        existing_id = normalizar_texto(existing.get("memory_id"))
        if existing_id:
            record["memory_id"] = existing_id
            record["created_at"] = normalizar_texto(existing.get("created_at")) or record[
                "created_at"
            ]
            record["version"] = max(
                _safe_int(existing.get("version"), 1),
                _safe_int(record.get("version"), 1),
            )
            atualizar_registro(
                MEMORIES_SHEET,
                coluna_chave="memory_id",
                valor_chave=existing_id,
                alteracoes=record,
            )
        else:
            atualizar_registro(
                MEMORIES_SHEET,
                coluna_chave="memory_key",
                valor_chave=record["memory_key"],
                alteracoes=record,
            )
    else:
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
    garantir_schema_memories()
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
        valor_chave=normalizar_texto(target.get("memory_id")),
        alteracoes={
            "active": False,
            "updated_at": utc_now_iso(),
        },
    )


__all__ = [
    "MEMORY_COLUMNS",
    "MEMORY_REPOSITORY_VERSION",
    "desativar_memoria",
    "garantir_schema_memories",
    "listar_memorias_usuario",
    "migrar_memorias_existentes",
    "normalizar_memoria_persistida",
    "salvar_memorias_em_lote",
    "salvar_ou_atualizar_memoria",
]
