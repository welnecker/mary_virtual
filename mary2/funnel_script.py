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


def ensure_funnel_state(narrative: dict, rows: list[dict]) -> dict:
    scene_ids = [
        _clean(row.get("scene_id"))
        for row in rows
        if _clean(row.get("scene_id"))
    ]
    state = narrative.get("funnel_script")
    if not isinstance(state, dict) or state.get("engine") != "carona_funnel_v1":
        state = {
            "engine": "carona_funnel_v1",
            "scene_index": 0,
            "scene_id": scene_ids[0] if scene_ids else "",
            "scene_turn": 0,
            "completed_scene_ids": [],
            "memory": {
                "user_facts": [],
                "mary_facts": [],
                "consumed_topics": [],
                "consolidated": [],
            },
            "last_evaluation": {},
            "last_advance_reason": "",
            "completed": False,
        }
        narrative["funnel_script"] = state

    # O motor novo substitui o estado híbrido somente na Carona.
    narrative.pop("hybrid_script", None)

    memory = state.get("memory")
    if not isinstance(memory, dict):
        memory = {}
        state["memory"] = memory
    for key in ("user_facts", "mary_facts", "consumed_topics", "consolidated"):
        if not isinstance(memory.get(key), list):
            memory[key] = []

    index = max(0, _int(state.get("scene_index"), 0))
    if rows:
        index = min(index, len(rows) - 1)
        expected_id = _clean(rows[index].get("scene_id"))
        if _clean(state.get("scene_id")) not in scene_ids:
            state["scene_id"] = expected_id
        elif _clean(state.get("scene_id")) != expected_id:
            found = next(
                (
                    i
                    for i, row in enumerate(rows)
                    if _clean(row.get("scene_id"))
                    == _clean(state.get("scene_id"))
                ),
                index,
            )
            index = found

    state["scene_index"] = index
    state["scene_turn"] = max(0, _int(state.get("scene_turn"), 0))
    state["completed_scene_ids"] = _unique_text(
        state.get("completed_scene_ids", []),
        limit=64,
    )
    state["completed"] = bool(state.get("completed", False))
    return state


def current_funnel_row(rows: list[dict], state: dict) -> dict:
    if not rows or bool(state.get("completed", False)):
        return {}
    index = max(
        0,
        min(_int(state.get("scene_index"), 0), len(rows) - 1),
    )
    return dict(rows[index])


def funnel_stage(row: dict, state: dict) -> str:
    next_turn = int(state.get("scene_turn", 0) or 0) + 1
    min_turns = int(row.get("min_turns", 1) or 1)
    ideal_turns = int(
        row.get("ideal_turns", min_turns) or min_turns
    )
    max_turns = int(
        row.get("max_turns", ideal_turns) or ideal_turns
    )

    if next_turn <= min_turns:
        return "abertura"
    if next_turn < ideal_turns:
        return "desenvolvimento"
    if next_turn < max_turns:
        return "convergencia"
    return "fechamento"


def _memory_text(state: dict) -> str:
    memory = (
        state.get("memory", {})
        if isinstance(state, dict)
        else {}
    )
    sections: list[str] = []

    for key, title in (
        ("user_facts", "FATOS DO USUÁRIO NESTA CENA"),
        ("mary_facts", "FATOS JÁ ESTABELECIDOS POR MARY"),
        ("consumed_topics", "ASSUNTOS JÁ CONSUMIDOS"),
        ("consolidated", "MEMÓRIA CONSOLIDADA DE CENAS ANTERIORES"),
    ):
        items = _unique_text(
            memory.get(key, [])
            if isinstance(memory, dict)
            else []
        )
        sections.append(title)
        sections.extend(f"- {item}" for item in items)
        if not items:
            sections.append("- (nenhum)")

    return "\n".join(sections)
