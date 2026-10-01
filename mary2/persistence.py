from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

import gspread
from google.oauth2.service_account import Credentials


RUNS_SHEET = "STORY_RUNS"
INTERACTIONS_SHEET = "INTERACTIONS"

RUN_HEADERS = [
    "run_id",
    "player_id",
    "status",
    "created_at",
    "updated_at",
    "last_seq",
    "active_user_role",
    "canonical_memory",
    "scene_json",
    "story_state_json",
]

INTERACTION_HEADERS = [
    "run_id",
    "seq",
    "created_at",
    "user_role",
    "scene_direction",
    "scene_caption",
    "user_text",
    "mary_text",
]


class PersistenceError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_run_id() -> str:
    return f"mary_{uuid4().hex[:16]}"


def _client(service_account_info: dict):
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(service_account_info, scopes=scopes)
    return gspread.authorize(creds)


def open_or_create_book(
    *,
    service_account_info: dict,
    spreadsheet_id: str = "",
    spreadsheet_title: str = "MARY_CORE_PERSISTENCE",
    owner_email: str = "",
):
    client = _client(service_account_info)

    if spreadsheet_id.strip():
        return client.open_by_key(spreadsheet_id.strip())

    title = spreadsheet_title.strip() or "MARY_CORE_PERSISTENCE"

    try:
        return client.open(title)
    except gspread.SpreadsheetNotFound:
        book = client.create(title)
        if owner_email.strip():
            try:
                book.share(
                    owner_email.strip(),
                    perm_type="user",
                    role="writer",
                    notify=False,
                )
            except Exception:
                # A persistência não deve falhar apenas porque o compartilhamento
                # automático não foi permitido pela configuração do Drive.
                pass
        return book


def _ensure_worksheet(book, title: str, headers: list[str]):
    try:
        ws = book.worksheet(title)
    except gspread.WorksheetNotFound:
        # Reaproveita a aba vazia padrão na primeira criação.
        worksheets = book.worksheets()
        if (
            len(worksheets) == 1
            and worksheets[0].title in {"Sheet1", "Página1", "Planilha1"}
            and not worksheets[0].get_all_values()
        ):
            ws = worksheets[0]
            ws.update_title(title)
        else:
            ws = book.add_worksheet(title=title, rows=1000, cols=max(len(headers), 10))

    existing = ws.row_values(1)
    if not existing:
        ws.append_row(headers, value_input_option="RAW")
    elif existing != headers:
        raise PersistenceError(
            f"Cabeçalho inesperado em {title}. Esperado: {headers}; atual: {existing}"
        )
    return ws


def ensure_schema(
    *,
    service_account_info: dict,
    spreadsheet_id: str = "",
    spreadsheet_title: str = "MARY_CORE_PERSISTENCE",
    owner_email: str = "",
) -> dict:
    book = open_or_create_book(
        service_account_info=service_account_info,
        spreadsheet_id=spreadsheet_id,
        spreadsheet_title=spreadsheet_title,
        owner_email=owner_email,
    )
    _ensure_worksheet(book, RUNS_SHEET, RUN_HEADERS)
    _ensure_worksheet(book, INTERACTIONS_SHEET, INTERACTION_HEADERS)
    return {
        "spreadsheet_id": book.id,
        "spreadsheet_title": book.title,
        "spreadsheet_url": book.url,
    }


def create_run(
    *,
    service_account_info: dict,
    player_id: str,
    active_user_role: str,
    canonical_memory: str,
    scene_state: dict,
    story_state: dict,
    spreadsheet_id: str = "",
    spreadsheet_title: str = "MARY_CORE_PERSISTENCE",
    owner_email: str = "",
    archive_previous: bool = True,
) -> str:
    book = open_or_create_book(
        service_account_info=service_account_info,
        spreadsheet_id=spreadsheet_id,
        spreadsheet_title=spreadsheet_title,
        owner_email=owner_email,
    )
    ws = _ensure_worksheet(book, RUNS_SHEET, RUN_HEADERS)

    if archive_previous:
        rows = ws.get_all_records()
        now_archive = _now()
        for index, item in enumerate(rows, start=2):
            if (
                str(item.get("player_id", "")) == player_id
                and str(item.get("status", "active")) == "active"
            ):
                ws.update(
                    range_name=f"C{index}:E{index}",
                    values=[["archived", item.get("created_at", ""), now_archive]],
                    value_input_option="RAW",
                )

    run_id = new_run_id()
    now = _now()
    ws.append_row(
        [
            run_id,
            player_id,
            "active",
            now,
            now,
            0,
            active_user_role,
            canonical_memory,
            json.dumps(scene_state, ensure_ascii=False),
            json.dumps(story_state, ensure_ascii=False),
        ],
        value_input_option="RAW",
    )
    return run_id


def _find_run_row(ws, run_id: str) -> int | None:
    try:
        cell = ws.find(run_id, in_column=1)
        return int(cell.row)
    except Exception:
        return None


def save_turn(
    *,
    service_account_info: dict,
    run_id: str,
    player_id: str,
    active_user_role: str,
    canonical_memory: str,
    scene_state: dict,
    story_state: dict,
    turn_record: dict,
    spreadsheet_id: str = "",
    spreadsheet_title: str = "MARY_CORE_PERSISTENCE",
    owner_email: str = "",
) -> int:
    book = open_or_create_book(
        service_account_info=service_account_info,
        spreadsheet_id=spreadsheet_id,
        spreadsheet_title=spreadsheet_title,
        owner_email=owner_email,
    )
    runs_ws = _ensure_worksheet(book, RUNS_SHEET, RUN_HEADERS)
    interactions_ws = _ensure_worksheet(book, INTERACTIONS_SHEET, INTERACTION_HEADERS)

    row = _find_run_row(runs_ws, run_id)
    if row is None:
        raise PersistenceError(f"run_id não encontrado: {run_id}")

    row_values = runs_ws.row_values(row)
    created_at = row_values[3] if len(row_values) > 3 else _now()
    current_seq = row_values[5] if len(row_values) > 5 else "0"
    try:
        seq = int(current_seq) + 1
    except Exception:
        seq = 1

    now = _now()
    interactions_ws.append_row(
        [
            run_id,
            seq,
            now,
            turn_record.get("user_role", active_user_role),
            turn_record.get("direction", ""),
            turn_record.get("caption", ""),
            turn_record.get("user_text", ""),
            turn_record.get("mary_text", ""),
        ],
        value_input_option="RAW",
    )

    runs_ws.update(
        range_name=f"C{row}:J{row}",
        values=[[
            "active",
            created_at,
            now,
            seq,
            active_user_role,
            canonical_memory,
            json.dumps(scene_state, ensure_ascii=False),
            json.dumps(story_state, ensure_ascii=False),
        ]],
        value_input_option="RAW",
    )
    return seq


def load_latest_run(
    *,
    service_account_info: dict,
    player_id: str,
    interaction_limit: int = 30,
    spreadsheet_id: str = "",
    spreadsheet_title: str = "MARY_CORE_PERSISTENCE",
    owner_email: str = "",
) -> dict | None:
    book = open_or_create_book(
        service_account_info=service_account_info,
        spreadsheet_id=spreadsheet_id,
        spreadsheet_title=spreadsheet_title,
        owner_email=owner_email,
    )
    runs_ws = _ensure_worksheet(book, RUNS_SHEET, RUN_HEADERS)
    interactions_ws = _ensure_worksheet(book, INTERACTIONS_SHEET, INTERACTION_HEADERS)

    runs = runs_ws.get_all_records()
    candidates = [
        r for r in runs
        if str(r.get("player_id", "")) == player_id
        and str(r.get("status", "active")) == "active"
    ]
    if not candidates:
        return None

    candidates.sort(key=lambda r: str(r.get("updated_at", "")), reverse=True)
    run = candidates[0]
    run_id = str(run["run_id"])

    all_interactions = interactions_ws.get_all_records()
    rows = [r for r in all_interactions if str(r.get("run_id", "")) == run_id]
    rows.sort(key=lambda r: int(r.get("seq", 0) or 0))
    rows = rows[-interaction_limit:]

    turn_records = []
    messages = []
    for item in rows:
        record = {
            "caption": str(item.get("scene_caption", "") or ""),
            "direction": str(item.get("scene_direction", "") or ""),
            "user_role": str(item.get("user_role", "JANIO") or "JANIO"),
            "user_text": str(item.get("user_text", "") or ""),
            "mary_text": str(item.get("mary_text", "") or ""),
        }
        turn_records.append(record)

        if record["user_text"]:
            messages.append({
                "role": "user",
                "content": f"[PAPEL={record['user_role']}] {record['user_text']}",
            })
        if record["mary_text"]:
            messages.append({
                "role": "assistant",
                "content": record["mary_text"],
            })

    try:
        scene_state = json.loads(str(run.get("scene_json", "") or "{}"))
    except Exception:
        scene_state = {}

    try:
        story_state = json.loads(str(run.get("story_state_json", "") or "{}"))
    except Exception:
        story_state = {}

    return {
        "run_id": run_id,
        "active_user_role": str(run.get("active_user_role", "JANIO") or "JANIO"),
        "canonical_memory": str(run.get("canonical_memory", "") or ""),
        "scene_state": scene_state,
        "story_state": story_state,
        "turn_records": turn_records,
        "messages": messages,
        "last_seq": int(run.get("last_seq", 0) or 0),
        "spreadsheet_id": book.id,
        "spreadsheet_url": book.url,
    }
