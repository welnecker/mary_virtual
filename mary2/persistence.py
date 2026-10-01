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
    "active_user_role_before",
    "canonical_memory_before",
    "scene_json_before",
    "story_state_json_before",
]


class PersistenceError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_run_id() -> str:
    return f"mary_{uuid4().hex[:16]}"


def _client(service_account_info: dict):
    # Persistência usa apenas a Google Sheets API.
    # Não depende da Google Drive API.
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
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

    if not spreadsheet_id.strip():
        service_email = str(service_account_info.get("client_email", "") or "").strip()
        hint = (
            f" Compartilhe a planilha com {service_email} como Editor."
            if service_email else ""
        )
        raise PersistenceError(
            "MARY_SHEETS_ID não configurado. Crie uma planilha Google vazia, "
            "copie o ID da URL para MARY_SHEETS_ID e compartilhe-a com a service account."
            + hint
        )

    return client.open_by_key(spreadsheet_id.strip())


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
        # Migração segura: novas versões podem apenas acrescentar colunas ao final.
        # Isso preserva planilhas já existentes sem exigir recriação manual.
        if len(existing) < len(headers) and existing == headers[: len(existing)]:
            ws.update(
                range_name=f"A1:{gspread.utils.rowcol_to_a1(1, len(headers))}",
                values=[headers],
                value_input_option="RAW",
            )
        else:
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
    pre_turn_snapshot: dict | None = None,
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
    before = pre_turn_snapshot if isinstance(pre_turn_snapshot, dict) else {}
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
            before.get("active_user_role", active_user_role),
            before.get("canonical_memory", ""),
            json.dumps(before.get("scene_state", {}), ensure_ascii=False),
            json.dumps(before.get("story_state", {}), ensure_ascii=False),
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
            "seq": int(item.get("seq", 0) or 0),
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



def _parse_json_object(value: object, *, field_name: str) -> dict:
    raw = str(value or "").strip()
    if not raw:
        raise PersistenceError(
            f"A interação selecionada não possui snapshot de {field_name}. "
            "Ela foi salva antes da versão com rollback seguro."
        )
    try:
        parsed = json.loads(raw)
    except Exception as exc:
        raise PersistenceError(
            f"Snapshot inválido de {field_name} na interação selecionada."
        ) from exc
    if not isinstance(parsed, dict):
        raise PersistenceError(
            f"Snapshot inválido de {field_name} na interação selecionada."
        )
    return parsed


def delete_interactions_from_seq(
    *,
    service_account_info: dict,
    run_id: str,
    from_seq: int,
    spreadsheet_id: str = "",
    spreadsheet_title: str = "MARY_CORE_PERSISTENCE",
    owner_email: str = "",
) -> dict:
    """Apaga a interação escolhida e tudo depois, restaurando o estado anterior."""

    from_seq = int(from_seq)
    if from_seq < 1:
        raise PersistenceError("Sequência inválida para rollback.")

    book = open_or_create_book(
        service_account_info=service_account_info,
        spreadsheet_id=spreadsheet_id,
        spreadsheet_title=spreadsheet_title,
        owner_email=owner_email,
    )
    runs_ws = _ensure_worksheet(book, RUNS_SHEET, RUN_HEADERS)
    interactions_ws = _ensure_worksheet(
        book,
        INTERACTIONS_SHEET,
        INTERACTION_HEADERS,
    )

    run_row = _find_run_row(runs_ws, run_id)
    if run_row is None:
        raise PersistenceError(f"run_id não encontrado: {run_id}")

    records = interactions_ws.get_all_records()
    selected: dict | None = None
    rows_to_delete: list[int] = []
    remaining_seqs: list[int] = []

    for sheet_row, item in enumerate(records, start=2):
        if str(item.get("run_id", "")) != run_id:
            continue
        try:
            seq = int(item.get("seq", 0) or 0)
        except Exception:
            continue

        if seq == from_seq:
            selected = item
        if seq >= from_seq:
            rows_to_delete.append(sheet_row)
        else:
            remaining_seqs.append(seq)

    if selected is None:
        raise PersistenceError(
            f"Interação #{from_seq} não encontrada na run atual."
        )

    canonical_before = str(
        selected.get("canonical_memory_before", "") or ""
    ).strip()
    if not canonical_before:
        raise PersistenceError(
            "Esta interação foi salva antes da versão com rollback seguro. "
            "Para não corromper a continuidade, ela não foi apagada."
        )

    scene_before = _parse_json_object(
        selected.get("scene_json_before"),
        field_name="cena",
    )
    story_before = _parse_json_object(
        selected.get("story_state_json_before"),
        field_name="estado",
    )
    active_role_before = str(
        selected.get("active_user_role_before", "JANIO") or "JANIO"
    ).strip().upper()
    if active_role_before not in {"JANIO", "RICARDO"}:
        active_role_before = "JANIO"

    # Só apaga depois de validar todos os snapshots necessários.
    for sheet_row in sorted(rows_to_delete, reverse=True):
        interactions_ws.delete_rows(sheet_row)

    run_values = runs_ws.row_values(run_row)
    created_at = run_values[3] if len(run_values) > 3 else _now()
    now = _now()
    last_seq = max(remaining_seqs, default=0)

    runs_ws.update(
        range_name=f"C{run_row}:J{run_row}",
        values=[[
            "active",
            created_at,
            now,
            last_seq,
            active_role_before,
            canonical_before,
            json.dumps(scene_before, ensure_ascii=False),
            json.dumps(story_before, ensure_ascii=False),
        ]],
        value_input_option="RAW",
    )

    return {
        "deleted_count": len(rows_to_delete),
        "last_seq": last_seq,
        "active_user_role": active_role_before,
        "canonical_memory": canonical_before,
        "scene_state": scene_before,
        "story_state": story_before,
    }
