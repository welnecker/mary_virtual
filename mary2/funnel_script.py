from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

import gspread

from openrouter_client import chat


FUNNEL_HEADERS = {
    "ordem": "order",
    "cena id": "scene_id",
    "objetivo da cena": "objective",
    "abertura permitida": "opening_allowed",
    "convergência": "convergence",
    "convergencia": "convergence",
    "não pode": "forbidden",
    "nao pode": "forbidden",
    "min turns": "min_turns",
    "ideal turns": "ideal_turns",
    "max turns": "max_turns",
    "condição de saída": "exit_condition",
    "condicao de saida": "exit_condition",
    "saída prevista": "next_scene",
    "saida prevista": "next_scene",
    "atmosfera / atitude": "atmosphere",
    "vestimenta": "wardrobe",
    "fatos fixos da cena": "fixed_facts",
    "memória a consolidar": "memory_policy",
    "memoria a consolidar": "memory_policy",
}


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _int(value: Any, default: int) -> int:
    try:
        return int(float(_clean(value)))
    except Exception:
        return int(default)


def _unique_text(items: list[Any], *, limit: int = 24) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items or []:
        value = _clean(item)
        if not value:
            continue
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
        if len(result) >= limit:
            break
    return result


def load_funnel_rows(
    *,
    service_account_info: dict,
    spreadsheet_id: str,
    worksheet_name: str,
) -> list[dict]:
    if not service_account_info:
        raise ValueError("service_account_info ausente para roteiro em funil")
    if not _clean(spreadsheet_id):
        raise ValueError("spreadsheet_id ausente para roteiro em funil")

    client = gspread.service_account_from_dict(service_account_info)
    worksheet = client.open_by_key(_clean(spreadsheet_id)).worksheet(
        _clean(worksheet_name) or "ROTEIRO_FUNIL_CARONA"
    )
    values = worksheet.get_all_values()
    if not values:
        return []

    header_index = -1
    headers: list[str] = []
    for idx, row in enumerate(values):
        normalized = [_clean(cell).lower() for cell in row]
        if "ordem" in normalized and "cena id" in normalized and "objetivo da cena" in normalized:
            header_index = idx
            headers = normalized
            break
    if header_index < 0:
        raise ValueError("cabeçalho do roteiro em funil não encontrado")

    rows: list[dict] = []
    for source_row in values[header_index + 1 :]:
        if not any(_clean(cell) for cell in source_row):
            continue
        record: dict[str, Any] = {}
        for index, header in enumerate(headers):
            key = FUNNEL_HEADERS.get(header)
            if key:
                record[key] = _clean(source_row[index] if index < len(source_row) else "")
        if not _clean(record.get("scene_id")):
            continue
        record["order"] = _int(record.get("order"), len(rows) + 1)
        record["min_turns"] = max(1, _int(record.get("min_turns"), 1))
        record["ideal_turns"] = max(
            record["min_turns"],
            _int(record.get("ideal_turns"), record["min_turns"]),
        )
        record["max_turns"] = max(
            record["ideal_turns"],
            _int(record.get("max_turns"), record["ideal_turns"]),
        )
        rows.append(record)

    rows.sort(key=lambda item: int(item.get("order", 0) or 0))
    return rows
