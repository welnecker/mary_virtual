from __future__ import annotations

import json
import logging
from copy import deepcopy
from functools import lru_cache, wraps
from threading import RLock
from time import monotonic
from datetime import datetime, timezone
from uuid import uuid4

import gspread
from google.oauth2.service_account import Credentials


RUNS_SHEET = "STORY_RUNS"
INTERACTIONS_SHEET = "INTERACTIONS"
DIRECTOR_AUDIT_SHEET = "DIRECTOR_AUDIT"
MODEL_AUDIT_SHEET = "MODEL_AUDIT"
FUNNEL_AUDIT_SHEET = "FUNNEL_AUDIT"
BLOCK_AUDIT_SHEET = "BLOCK_AUDIT"
DIRECT_SCRIPT_AUDIT_SHEET = "DIRECT_SCRIPT_AUDIT"
FUNNEL_REJECTIONS_SHEET = "FUNNEL_REJECTIONS"
CHECKPOINTS_SHEET = "STORY_CHECKPOINTS"
BRANCHES_SHEET = "STORY_BRANCHES"

RUN_HEADERS = [
    "run_id",
    "player_id",
    "status",
    "created_at",
    "updated_at",
    "last_seq",
    "active_user_role",
    "story_ledger",
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
    "story_ledger_before",
    "scene_json_before",
    "story_state_json_before",
    "mary_action",
    "hook_resolution",
    "mary_intent",
    "branch_id",
    "chapter_instance_id",
    "chapter_id",
    "chapter_turn",
]


DIRECTOR_AUDIT_HEADERS = [
    "run_id",
    "seq",
    "created_at",
    "chapter_id",
    "user_role",
    "user_text",
    "scene_direction",
    "director_model",
    "duration_ms",
    "conditional_transition",
    "advance_when",
    "scene_before_json",
    "director_input_payload",
    "director_raw_response",
    "director_parsed_json",
    "parse_error",
    "mary_action",
    "event",
    "proximity_before",
    "proximity_after",
    "sexual_intensity_before",
    "sexual_intensity_after",
    "microstep_complete",
    "scene_after_json",
    "main_model",
    "mary_text",
    "branch_id",
    "chapter_instance_id",
    "chapter_turn",
]

MODEL_AUDIT_HEADERS = [
    "run_id",
    "seq",
    "created_at",
    "chapter_id",
    "user_role",
    "user_text",
    "main_model",
    "fallback_model",
    "temperature",
    "system_prompt",
    "messages_json",
    "initial_raw_response",
    "retry_used",
    "retry_messages_json",
    "retry_raw_response",
    "final_raw_response",
    "mary_speech_raw",
    "mary_thought",
    "final_mary_text",
    "branch_id",
    "chapter_instance_id",
    "chapter_turn",
]

FUNNEL_AUDIT_HEADERS = [
    "run_id",
    "seq",
    "created_at",
    "chapter_id",
    "scene_id",
    "scene_order",
    "scene_turn_before",
    "scene_turn_after",
    "stage",
    "min_turns",
    "ideal_turns",
    "max_turns",
    "user_text",
    "mary_text",
    "boundary_ok",
    "violations_json",
    "exit_condition_met",
    "evaluation_json",
    "state_before_json",
    "state_after_json",
    "advanced",
    "advanced_to",
    "branch_id",
    "chapter_instance_id",
    "chapter_turn",
    "required_markers_json",
    "achieved_markers_json",
    "pending_markers_json",
    "exit_ready",
    "physical_state_json",
]

BLOCK_AUDIT_HEADERS = [
    "run_id",
    "seq",
    "created_at",
    "chapter_id",
    "block_id",
    "block_order",
    "block_turn_before",
    "block_turn_after",
    "stage",
    "target_min",
    "target_max",
    "max_interactions",
    "depends_on_user",
    "dynamic_requirement",
    "user_text",
    "mary_text",
    "mary_thought",
    "dependency_satisfied",
    "dependency_refused",
    "dependency_summary",
    "dependency_source_quote",
    "advanced",
    "advanced_to",
    "waiting_for_dependency",
    "holding_for_next_block",
    "state_before_json",
    "state_after_json",
    "physical_state_json",
    "branch_id",
    "chapter_instance_id",
    "chapter_turn",
]

DIRECT_SCRIPT_AUDIT_HEADERS = [
    "run_id",
    "seq",
    "created_at",
    "chapter_id",
    "line_id",
    "line_order",
    "line_type",
    "completion_type",
    "precondition",
    "instant_memory",
    "recent_memory",
    "permanent_memory",
    "wardrobe",
    "physical_action",
    "speech_guide",
    "style",
    "user_text",
    "mary_text",
    "mary_thought",
    "awaiting_reply_order",
    "completed_orders_json",
    "script_completed",
    "branch_id",
    "chapter_instance_id",
    "chapter_turn",
    "initial_description",
]

FUNNEL_REJECTION_HEADERS = [
    "created_at",
    "run_id",
    "chapter_id",
    "scene_id",
    "scene_order",
    "scene_turn",
    "branch_id",
    "chapter_instance_id",
    "chapter_turn",
    "user_text",
    "initial_mary_text",
    "initial_evaluation_json",
    "initial_violations_json",
    "correction_prompt",
    "retry_mary_text",
    "retry_evaluation_json",
    "retry_violations_json",
    "mission_progress_ok",
    "mission_progress_target",
    "pending_markers_json",
    "required_markers_json",
    "state_json",
]

CHECKPOINT_HEADERS = [
    "checkpoint_id",
    "run_id",
    "checkpoint_type",
    "source_seq",
    "source_chapter_id",
    "source_chapter_instance_id",
    "source_branch_id",
    "choice_point_id",
    "active_user_role",
    "story_ledger",
    "scene_json",
    "story_state_json",
    "created_at",
]

BRANCH_HEADERS = [
    "branch_id",
    "run_id",
    "parent_branch_id",
    "parent_checkpoint_id",
    "choice_id",
    "choice_label",
    "chapter_id",
    "chapter_instance_id",
    "created_at",
]



class PersistenceError(RuntimeError):
    pass


# Resource caches are scoped to credentials and spreadsheet. Validated schemas
# and run positions remain valid because these sheets are append-only.
_CACHE_LOCK = RLock()
_LOG = logging.getLogger(__name__)
_CHECKPOINT_TTL = 30.0


def _serialized_cache(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        with _CACHE_LOCK:
            return func(*args, **kwargs)
    return wrapped


@lru_cache(maxsize=16)
def _open_book(credentials_json: str, spreadsheet_id: str):
    return _client(json.loads(credentials_json)).open_by_key(spreadsheet_id)


def _checkpoint_records(ws, *, force: bool = False) -> list[dict]:
    """Refresh the immutable ledger; a 429 may use the last successful copy."""
    cached = getattr(ws, "_mary_checkpoint_records", None)
    if not force and cached is not None and monotonic() - ws._mary_checkpoint_loaded_at < _CHECKPOINT_TTL:
        return deepcopy(cached)
    try:
        rows = ws.get_all_records()
    except gspread.exceptions.APIError as exc:
        if getattr(exc, "code", None) != 429 or cached is None:
            raise
        _LOG.warning("MARY_SHEETS_AUDIT sheet=%s cache=STALE quota_429=1", CHECKPOINTS_SHEET)
        # Avoid hammering Sheets again during the same quota window.
        ws._mary_checkpoint_loaded_at = monotonic()
        return deepcopy(cached)
    ws._mary_checkpoint_records = deepcopy(rows)
    ws._mary_checkpoint_loaded_at = monotonic()
    return rows


@_serialized_cache
def _remember_run_rows(ws, records: list[dict]) -> None:
    ws._mary_run_rows = {
        str(item.get("run_id", "")): index
        for index, item in enumerate(records, start=2)
    }


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

    with _CACHE_LOCK:
        return _open_book(json.dumps(service_account_info, sort_keys=True), spreadsheet_id.strip())


def _ensure_worksheet(book, title: str, headers: list[str]):
    with _CACHE_LOCK:
        cache = getattr(book, "_mary_worksheets", {})
        key = (title, tuple(headers))
        if key not in cache:
            cache[key] = _validate_worksheet(book, title, headers)
            book._mary_worksheets = cache
        return cache[key]


def _validate_worksheet(book, title: str, headers: list[str]):
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

    if int(getattr(ws, "col_count", 0) or 0) < len(headers):
        ws.resize(cols=len(headers))

    existing = ws.row_values(1)
    if not existing:
        ws.append_row(headers, value_input_option="RAW")
    elif existing != headers:
        # Migração de nomenclatura da arquitetura antiga para o ledger estrutural.
        normalized_existing = [
            (
                "story_ledger"
                if item == "canonical_memory"
                else "story_ledger_before"
                if item == "canonical_memory_before"
                else item
            )
            for item in existing
        ]

        if (
            normalized_existing == headers
            or (
                len(normalized_existing) < len(headers)
                and normalized_existing == headers[: len(normalized_existing)]
            )
        ):
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
    _ensure_worksheet(book, DIRECTOR_AUDIT_SHEET, DIRECTOR_AUDIT_HEADERS)
    _ensure_worksheet(book, MODEL_AUDIT_SHEET, MODEL_AUDIT_HEADERS)
    _ensure_worksheet(book, FUNNEL_AUDIT_SHEET, FUNNEL_AUDIT_HEADERS)
    _ensure_worksheet(book, BLOCK_AUDIT_SHEET, BLOCK_AUDIT_HEADERS)
    _ensure_worksheet(book, DIRECT_SCRIPT_AUDIT_SHEET, DIRECT_SCRIPT_AUDIT_HEADERS)
    _ensure_worksheet(book, FUNNEL_REJECTIONS_SHEET, FUNNEL_REJECTION_HEADERS)
    _ensure_worksheet(book, CHECKPOINTS_SHEET, CHECKPOINT_HEADERS)
    _ensure_worksheet(book, BRANCHES_SHEET, BRANCH_HEADERS)
    return {
        "spreadsheet_id": book.id,
        "spreadsheet_title": book.title,
        "spreadsheet_url": book.url,
    }



def new_branch_id(choice_id: str = "branch") -> str:
    stem = str(choice_id or "branch").strip().lower().replace(" ", "_")
    return f"{stem}_{uuid4().hex[:10]}"


def new_chapter_instance_id(chapter_id: str) -> str:
    stem = str(chapter_id or "chapter").strip().lower().replace(" ", "_")
    return f"{stem}_{uuid4().hex[:10]}"


def new_checkpoint_id(checkpoint_type: str = "checkpoint") -> str:
    stem = str(checkpoint_type or "checkpoint").strip().lower().replace(" ", "_")
    return f"{stem}_{uuid4().hex[:10]}"


@_serialized_cache
def save_checkpoint(
    *,
    service_account_info: dict,
    run_id: str,
    checkpoint_type: str,
    source_seq: int,
    source_chapter_id: str,
    source_chapter_instance_id: str,
    source_branch_id: str,
    choice_point_id: str,
    active_user_role: str,
    story_ledger: str,
    scene_state: dict,
    story_state: dict,
    spreadsheet_id: str = "",
    spreadsheet_title: str = "MARY_CORE_PERSISTENCE",
    owner_email: str = "",
    checkpoint_id: str = "",
) -> str:
    book = open_or_create_book(
        service_account_info=service_account_info,
        spreadsheet_id=spreadsheet_id,
        spreadsheet_title=spreadsheet_title,
        owner_email=owner_email,
    )
    ws = _ensure_worksheet(book, CHECKPOINTS_SHEET, CHECKPOINT_HEADERS)

    existing = _checkpoint_records(ws)
    for item in existing:
        if (
            str(item.get("run_id", "")) == run_id
            and str(item.get("checkpoint_type", "")) == str(checkpoint_type)
            and str(item.get("source_chapter_instance_id", "")) == str(source_chapter_instance_id)
            and str(item.get("choice_point_id", "")) == str(choice_point_id)
        ):
            return str(item.get("checkpoint_id", "") or "")

    checkpoint_id = str(checkpoint_id or new_checkpoint_id(checkpoint_type))
    values = [
        checkpoint_id,
        run_id,
        checkpoint_type,
        int(source_seq or 0),
        source_chapter_id,
        source_chapter_instance_id,
        source_branch_id,
        choice_point_id,
        active_user_role,
        story_ledger,
        json.dumps(scene_state, ensure_ascii=False),
        json.dumps(story_state, ensure_ascii=False),
        _now(),
    ]
    ws.append_row(values, value_input_option="RAW")
    # Publish to the cache only after the write is confirmed.
    existing.append(dict(zip(CHECKPOINT_HEADERS, values)))
    ws._mary_checkpoint_records = deepcopy(existing)
    ws._mary_checkpoint_loaded_at = monotonic()
    return checkpoint_id


def save_branch(
    *,
    service_account_info: dict,
    run_id: str,
    branch_id: str,
    parent_branch_id: str,
    parent_checkpoint_id: str,
    choice_id: str,
    choice_label: str,
    chapter_id: str,
    chapter_instance_id: str,
    spreadsheet_id: str = "",
    spreadsheet_title: str = "MARY_CORE_PERSISTENCE",
    owner_email: str = "",
) -> None:
    book = open_or_create_book(
        service_account_info=service_account_info,
        spreadsheet_id=spreadsheet_id,
        spreadsheet_title=spreadsheet_title,
        owner_email=owner_email,
    )
    ws = _ensure_worksheet(book, BRANCHES_SHEET, BRANCH_HEADERS)
    ws.append_row(
        [
            branch_id,
            run_id,
            parent_branch_id,
            parent_checkpoint_id,
            choice_id,
            choice_label,
            chapter_id,
            chapter_instance_id,
            _now(),
        ],
        value_input_option="RAW",
    )


@_serialized_cache
def load_checkpoints(
    *,
    service_account_info: dict,
    run_id: str,
    checkpoint_type: str = "",
    spreadsheet_id: str = "",
    spreadsheet_title: str = "MARY_CORE_PERSISTENCE",
    owner_email: str = "",
) -> list[dict]:
    book = open_or_create_book(
        service_account_info=service_account_info,
        spreadsheet_id=spreadsheet_id,
        spreadsheet_title=spreadsheet_title,
        owner_email=owner_email,
    )
    ws = _ensure_worksheet(book, CHECKPOINTS_SHEET, CHECKPOINT_HEADERS)
    rows = [
        dict(item)
        for item in _checkpoint_records(ws)
        if str(item.get("run_id", "")) == run_id
    ]
    if checkpoint_type:
        rows = [
            item for item in rows
            if str(item.get("checkpoint_type", "")) == checkpoint_type
        ]
    rows.sort(key=lambda item: int(item.get("source_seq", 0) or 0))
    return rows


@_serialized_cache
def load_checkpoint(
    *,
    service_account_info: dict,
    checkpoint_id: str,
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
    ws = _ensure_worksheet(book, CHECKPOINTS_SHEET, CHECKPOINT_HEADERS)
    # A known checkpoint is immutable and need not be refreshed to restore it.
    cached = getattr(ws, "_mary_checkpoint_records", None) or []
    rows = (
        cached
        if any(str(item.get("checkpoint_id", "")) == checkpoint_id for item in cached)
        else _checkpoint_records(ws, force=True)
    )
    for item in rows:
        if str(item.get("checkpoint_id", "")) != checkpoint_id:
            continue
        try:
            scene_state = json.loads(str(item.get("scene_json", "") or "{}"))
            story_state = json.loads(str(item.get("story_state_json", "") or "{}"))
        except Exception as exc:
            raise PersistenceError("Checkpoint possui JSON inválido.") from exc
        return {
            **dict(item),
            "scene_state": scene_state,
            "story_state": story_state,
        }
    raise PersistenceError(f"Checkpoint não encontrado: {checkpoint_id}")


def create_run(
    *,
    service_account_info: dict,
    player_id: str,
    active_user_role: str,
    story_ledger: str,
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

    # Uma run ativa por player. Mesmo a criação automática de inicialização
    # arquiva qualquer ativa anterior para evitar duplicação em reruns/reloads.
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
            story_ledger,
            json.dumps(scene_state, ensure_ascii=False),
            json.dumps(story_state, ensure_ascii=False),
        ],
        value_input_option="RAW",
    )

    # Guarda adicional para reruns sequenciais: mantém somente a run recém-criada ativa.
    refreshed = ws.get_all_records()
    _remember_run_rows(ws, refreshed)
    for index, item in enumerate(refreshed, start=2):
        if (
            str(item.get("player_id", "")) == player_id
            and str(item.get("status", "active")) == "active"
            and str(item.get("run_id", "")) != run_id
        ):
            ws.update_cell(index, 3, "archived")

    return run_id


@_serialized_cache
def _find_run_row(ws, run_id: str) -> int | None:
    rows = getattr(ws, "_mary_run_rows", {})
    if run_id in rows:
        return rows[run_id]
    try:
        cell = ws.find(run_id, in_column=1)
    except gspread.exceptions.CellNotFound:
        return None
    rows[run_id] = int(cell.row)
    ws._mary_run_rows = rows
    return int(cell.row)


def save_turn(
    *,
    service_account_info: dict,
    run_id: str,
    player_id: str,
    active_user_role: str,
    story_ledger: str,
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
            before.get("story_ledger", ""),
            json.dumps(before.get("scene_state", {}), ensure_ascii=False),
            json.dumps(before.get("story_state", {}), ensure_ascii=False),
            turn_record.get("mary_action", ""),
            turn_record.get("hook_resolution", ""),
            turn_record.get("mary_intent", ""),
            turn_record.get("branch_id", ""),
            turn_record.get("chapter_instance_id", ""),
            turn_record.get("chapter_id", ""),
            int(turn_record.get("chapter_turn", 0) or 0),
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
            story_ledger,
            json.dumps(scene_state, ensure_ascii=False),
            json.dumps(story_state, ensure_ascii=False),
        ]],
        value_input_option="RAW",
    )
    return seq


def _audit_cell(value, limit: int = 45000) -> str:
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False)
    else:
        text = str(value or "")
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...[TRUNCADO PARA LIMITE DA CÉLULA]"


def save_director_audit(
    *,
    service_account_info: dict,
    run_id: str,
    seq: int,
    chapter_id: str,
    user_role: str,
    user_text: str,
    scene_direction: str,
    audit: dict,
    main_model: str = "",
    mary_text: str = "",
    branch_id: str = "",
    chapter_instance_id: str = "",
    chapter_turn: int = 0,
    spreadsheet_id: str = "",
    spreadsheet_title: str = "MARY_CORE_PERSISTENCE",
    owner_email: str = "",
) -> None:
    """Registra a atuação bruta do Diretor sem alterar a narrativa."""
    if not isinstance(audit, dict) or not audit:
        return

    book = open_or_create_book(
        service_account_info=service_account_info,
        spreadsheet_id=spreadsheet_id,
        spreadsheet_title=spreadsheet_title,
        owner_email=owner_email,
    )
    ws = _ensure_worksheet(book, DIRECTOR_AUDIT_SHEET, DIRECTOR_AUDIT_HEADERS)

    before = audit.get("scene_before", {})
    after = audit.get("scene_after", {})
    parsed = audit.get("parsed_response", {})

    ws.append_row(
        [
            run_id,
            int(seq or 0),
            _now(),
            chapter_id,
            user_role,
            user_text,
            scene_direction,
            str(audit.get("model", "") or ""),
            audit.get("duration_ms", ""),
            bool(audit.get("conditional_transition", False)),
            str(audit.get("advance_when", "") or ""),
            _audit_cell(before),
            _audit_cell(audit.get("input_payload", "")),
            _audit_cell(audit.get("raw_response", "")),
            _audit_cell(parsed),
            str(audit.get("parse_error", "") or ""),
            str(after.get("mary_action", "") or ""),
            str(after.get("event", "") or ""),
            str(before.get("proximity", "") or "") if isinstance(before, dict) else "",
            str(after.get("proximity", "") or "") if isinstance(after, dict) else "",
            str(before.get("sexual_intensity", "") or "") if isinstance(before, dict) else "",
            str(after.get("sexual_intensity", "") or "") if isinstance(after, dict) else "",
            bool(after.get("microstep_complete", False)) if isinstance(after, dict) else False,
            _audit_cell(after),
            main_model,
            _audit_cell(mary_text),
            branch_id,
            chapter_instance_id,
            int(chapter_turn or 0),
        ],
        value_input_option="RAW",
    )



def save_model_audit(
    *,
    service_account_info: dict,
    run_id: str,
    seq: int,
    chapter_id: str,
    user_role: str,
    user_text: str,
    audit: dict,
    branch_id: str = "",
    chapter_instance_id: str = "",
    chapter_turn: int = 0,
    spreadsheet_id: str = "",
    spreadsheet_title: str = "MARY_CORE_PERSISTENCE",
    owner_email: str = "",
) -> None:
    """Registra exatamente o pacote lógico enviado ao modelo principal e suas respostas."""
    if not isinstance(audit, dict) or not audit:
        return

    book = open_or_create_book(
        service_account_info=service_account_info,
        spreadsheet_id=spreadsheet_id,
        spreadsheet_title=spreadsheet_title,
        owner_email=owner_email,
    )
    ws = _ensure_worksheet(book, MODEL_AUDIT_SHEET, MODEL_AUDIT_HEADERS)

    ws.append_row(
        [
            run_id,
            int(seq or 0),
            _now(),
            chapter_id,
            user_role,
            user_text,
            str(audit.get("model", "") or ""),
            str(audit.get("fallback_model", "") or ""),
            audit.get("temperature", ""),
            _audit_cell(audit.get("system_prompt", "")),
            _audit_cell(audit.get("messages", [])),
            _audit_cell(audit.get("initial_raw_response", "")),
            bool(audit.get("retry_used", False)),
            _audit_cell(audit.get("retry_messages", [])),
            _audit_cell(audit.get("retry_raw_response", "")),
            _audit_cell(audit.get("final_raw_response", "")),
            _audit_cell(audit.get("mary_speech_raw", "")),
            _audit_cell(audit.get("mary_thought", "")),
            _audit_cell(audit.get("final_mary_text", "")),
            branch_id,
            chapter_instance_id,
            int(chapter_turn or 0),
        ],
        value_input_option="RAW",
    )


def save_funnel_rejection(
    *,
    service_account_info: dict,
    run_id: str,
    chapter_id: str,
    row: dict,
    state: dict,
    user_text: str,
    initial_mary_text: str,
    initial_evaluation: dict,
    correction_prompt: str,
    retry_mary_text: str,
    retry_evaluation: dict,
    pending_markers: list | None = None,
    required_markers: list | None = None,
    branch_id: str = "",
    chapter_instance_id: str = "",
    chapter_turn: int = 0,
    spreadsheet_id: str = "",
    spreadsheet_title: str = "MARY_CORE_PERSISTENCE",
    owner_email: str = "",
) -> None:
    """Persiste uma tentativa rejeitada antes do rollback atômico do turno."""
    book = open_or_create_book(
        service_account_info=service_account_info,
        spreadsheet_id=spreadsheet_id,
        spreadsheet_title=spreadsheet_title,
        owner_email=owner_email,
    )
    ws = _ensure_worksheet(
        book,
        FUNNEL_REJECTIONS_SHEET,
        FUNNEL_REJECTION_HEADERS,
    )
    initial_evaluation = (
        initial_evaluation if isinstance(initial_evaluation, dict) else {}
    )
    retry_evaluation = (
        retry_evaluation if isinstance(retry_evaluation, dict) else {}
    )
    ws.append_row(
        [
            _now(),
            run_id,
            chapter_id,
            str(row.get("scene_id", "") or ""),
            int(row.get("order", 0) or 0),
            int(state.get("scene_turn", 0) or 0) if isinstance(state, dict) else 0,
            branch_id,
            chapter_instance_id,
            int(chapter_turn or 0),
            _audit_cell(user_text),
            _audit_cell(initial_mary_text),
            _audit_cell(initial_evaluation),
            _audit_cell(initial_evaluation.get("violations", [])),
            _audit_cell(correction_prompt),
            _audit_cell(retry_mary_text),
            _audit_cell(retry_evaluation),
            _audit_cell(retry_evaluation.get("violations", [])),
            retry_evaluation.get("mission_progress_ok", ""),
            str(retry_evaluation.get("mission_progress_target", "") or ""),
            _audit_cell(pending_markers or []),
            _audit_cell(required_markers or []),
            _audit_cell(state if isinstance(state, dict) else {}),
        ],
        value_input_option="RAW",
    )


def save_funnel_audit(
    *,
    service_account_info: dict,
    run_id: str,
    seq: int,
    chapter_id: str,
    user_text: str,
    mary_text: str,
    row: dict,
    evaluation: dict,
    progress: dict,
    branch_id: str = "",
    chapter_instance_id: str = "",
    chapter_turn: int = 0,
    spreadsheet_id: str = "",
    spreadsheet_title: str = "MARY_CORE_PERSISTENCE",
    owner_email: str = "",
) -> None:
    """Registra o estado do funil em formato compacto e legível por turno."""
    if not isinstance(row, dict) or not row:
        return
    if not isinstance(progress, dict) or not progress:
        return

    book = open_or_create_book(
        service_account_info=service_account_info,
        spreadsheet_id=spreadsheet_id,
        spreadsheet_title=spreadsheet_title,
        owner_email=owner_email,
    )
    ws = _ensure_worksheet(
        book,
        FUNNEL_AUDIT_SHEET,
        FUNNEL_AUDIT_HEADERS,
    )

    before = progress.get("state_before", {})
    after = progress.get("state_after", {})

    ws.append_row(
        [
            run_id,
            int(seq or 0),
            _now(),
            chapter_id,
            str(row.get("scene_id", "") or ""),
            int(row.get("order", 0) or 0),
            int(before.get("scene_turn", 0) or 0) if isinstance(before, dict) else 0,
            int(after.get("scene_turn", 0) or 0) if isinstance(after, dict) else 0,
            str(progress.get("stage", "") or ""),
            int(row.get("min_turns", 0) or 0),
            int(row.get("ideal_turns", 0) or 0),
            int(row.get("max_turns", 0) or 0),
            _audit_cell(user_text),
            _audit_cell(mary_text),
            bool(evaluation.get("boundary_ok", True)) if isinstance(evaluation, dict) else True,
            _audit_cell(evaluation.get("violations", []) if isinstance(evaluation, dict) else []),
            bool(progress.get("exit_ready", False)),
            _audit_cell(evaluation if isinstance(evaluation, dict) else {}),
            _audit_cell(before),
            _audit_cell(after),
            bool(progress.get("advanced", False)),
            str(progress.get("advanced_to", "") or ""),
            branch_id,
            chapter_instance_id,
            int(chapter_turn or 0),
            _audit_cell(progress.get("required_markers", [])),
            _audit_cell(progress.get("achieved_markers", [])),
            _audit_cell(progress.get("pending_markers", [])),
            bool(progress.get("exit_ready", False)),
            _audit_cell(progress.get("physical_state", {})),
        ],
        value_input_option="RAW",
    )


def save_direct_script_audit(
    *,
    service_account_info: dict,
    run_id: str,
    seq: int,
    chapter_id: str,
    user_text: str,
    mary_text: str,
    mary_thought: str,
    row: dict,
    state: dict,
    branch_id: str = "",
    chapter_instance_id: str = "",
    chapter_turn: int = 0,
    spreadsheet_id: str = "",
    spreadsheet_title: str = "MARY_CORE_PERSISTENCE",
    owner_email: str = "",
) -> None:
    """Registra exatamente qual linha da MINHA_SUGESTAO foi usada no turno."""
    if not isinstance(state, dict):
        return

    book = open_or_create_book(
        service_account_info=service_account_info,
        spreadsheet_id=spreadsheet_id,
        spreadsheet_title=spreadsheet_title,
        owner_email=owner_email,
    )
    ws = _ensure_worksheet(
        book,
        DIRECT_SCRIPT_AUDIT_SHEET,
        DIRECT_SCRIPT_AUDIT_HEADERS,
    )
    row = row if isinstance(row, dict) else {}

    ws.append_row(
        [
            run_id,
            int(seq or 0),
            _now(),
            chapter_id,
            str(row.get("line_id", "") or ""),
            int(row.get("order", 0) or 0),
            str(row.get("type", "") or ""),
            str(row.get("completion_type", "") or ""),
            _audit_cell(row.get("precondition", "")),
            _audit_cell(row.get("instant_memory", "")),
            _audit_cell(row.get("recent_memory", "")),
            _audit_cell(row.get("permanent_memory", "")),
            _audit_cell(row.get("wardrobe", "")),
            _audit_cell(row.get("physical_action", "")),
            _audit_cell(row.get("speech_guide", "")),
            _audit_cell(row.get("style", "")),
            _audit_cell(user_text),
            _audit_cell(mary_text),
            _audit_cell(mary_thought),
            int(state.get("awaiting_reply_order", 0) or 0),
            _audit_cell(state.get("completed_orders", [])),
            bool(state.get("completed", False)),
            branch_id,
            chapter_instance_id,
            int(chapter_turn or 0),
            _audit_cell(row.get("initial_description", "")),
        ],
        value_input_option="RAW",
    )


def save_block_audit(
    *,
    service_account_info: dict,
    run_id: str,
    seq: int,
    chapter_id: str,
    user_text: str,
    mary_text: str,
    mary_thought: str,
    row: dict,
    dependency: dict,
    progress: dict,
    branch_id: str = "",
    chapter_instance_id: str = "",
    chapter_turn: int = 0,
    spreadsheet_id: str = "",
    spreadsheet_title: str = "MARY_CORE_PERSISTENCE",
    owner_email: str = "",
) -> None:
    """Registra a progressão do roteiro em blocos sem reutilizar semântica do funil."""
    if not isinstance(row, dict) or not row:
        return
    if not isinstance(progress, dict) or not progress:
        return

    book = open_or_create_book(
        service_account_info=service_account_info,
        spreadsheet_id=spreadsheet_id,
        spreadsheet_title=spreadsheet_title,
        owner_email=owner_email,
    )
    ws = _ensure_worksheet(
        book,
        BLOCK_AUDIT_SHEET,
        BLOCK_AUDIT_HEADERS,
    )

    before = progress.get("state_before", {})
    after = progress.get("state_after", {})
    dep = dependency if isinstance(dependency, dict) else {}

    ws.append_row(
        [
            run_id,
            int(seq or 0),
            _now(),
            chapter_id,
            str(row.get("block_id", "") or ""),
            int(row.get("order", 0) or 0),
            int(before.get("block_turn", 0) or 0) if isinstance(before, dict) else 0,
            int(after.get("block_turn", 0) or 0) if isinstance(after, dict) else 0,
            str(progress.get("stage", "") or ""),
            int(progress.get("target_min", row.get("target_min", 0)) or 0),
            int(progress.get("target_max", row.get("target_max", 0)) or 0),
            int(progress.get("max_interactions", row.get("max_turns", 0)) or 0),
            bool(row.get("depends_on_user", False)),
            _audit_cell(row.get("dynamic_requirement", "")),
            _audit_cell(user_text),
            _audit_cell(mary_text),
            _audit_cell(mary_thought),
            bool(progress.get("dependency_satisfied", False)),
            bool(dep.get("refused", False)),
            _audit_cell(dep.get("summary", "")),
            _audit_cell(dep.get("source_quote", "")),
            bool(progress.get("advanced", False)),
            str(progress.get("advanced_to", "") or ""),
            bool(progress.get("waiting_for_dependency", False)),
            bool(progress.get("holding_for_next_block", False)),
            _audit_cell(before),
            _audit_cell(after),
            _audit_cell(progress.get("physical_state", {})),
            branch_id,
            chapter_instance_id,
            int(chapter_turn or 0),
        ],
        value_input_option="RAW",
    )


def update_run_snapshot(
    *,
    service_account_info: dict,
    run_id: str,
    active_user_role: str,
    story_ledger: str,
    scene_state: dict,
    story_state: dict,
    spreadsheet_id: str = "",
    spreadsheet_title: str = "MARY_CORE_PERSISTENCE",
    owner_email: str = "",
) -> None:
    """Atualiza o snapshot da run sem criar uma interação.

    Usado em transições de capítulo/decisões de interface.
    """
    book = open_or_create_book(
        service_account_info=service_account_info,
        spreadsheet_id=spreadsheet_id,
        spreadsheet_title=spreadsheet_title,
        owner_email=owner_email,
    )
    runs_ws = _ensure_worksheet(book, RUNS_SHEET, RUN_HEADERS)
    row = _find_run_row(runs_ws, run_id)
    if row is None:
        raise PersistenceError(f"run_id não encontrado: {run_id}")

    # Preserve created_at and last_seq on the server instead of reading and
    # writing them back. One batch write commits the new snapshot atomically.
    runs_ws.batch_update(
        [
            {"range": f"C{row}", "values": [["active"]]},
            {"range": f"E{row}", "values": [[_now()]]},
            {"range": f"G{row}:J{row}", "values": [[
                active_user_role,
                story_ledger,
                json.dumps(scene_state, ensure_ascii=False),
                json.dumps(story_state, ensure_ascii=False),
            ]]},
        ],
        value_input_option="RAW",
    )


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
    _remember_run_rows(runs_ws, runs)
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
            "mary_action": str(item.get("mary_action", "") or ""),
            "hook_resolution": str(item.get("hook_resolution", "") or ""),
            "branch_id": str(item.get("branch_id", "") or ""),
            "chapter_instance_id": str(item.get("chapter_instance_id", "") or ""),
            "chapter_id": str(item.get("chapter_id", "") or ""),
            "chapter_turn": int(item.get("chapter_turn", 0) or 0),
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
        "story_ledger": str(run.get("story_ledger", "") or ""),
        "scene_state": scene_state,
        "story_state": story_state,
        "turn_records": turn_records,
        "messages": messages,
        "last_seq": int(run.get("last_seq", 0) or 0),
        "spreadsheet_id": book.id,
        "spreadsheet_url": book.url,
    }




def load_run_interactions(
    *,
    service_account_info: dict,
    run_id: str,
    spreadsheet_id: str = "",
    spreadsheet_title: str = "MARY_CORE_PERSISTENCE",
    owner_email: str = "",
) -> list[dict]:
    book = open_or_create_book(
        service_account_info=service_account_info,
        spreadsheet_id=spreadsheet_id,
        spreadsheet_title=spreadsheet_title,
        owner_email=owner_email,
    )
    interactions_ws = _ensure_worksheet(
        book,
        INTERACTIONS_SHEET,
        INTERACTION_HEADERS,
    )
    rows = [
        dict(item)
        for item in interactions_ws.get_all_records()
        if str(item.get("run_id", "")) == run_id
    ]
    rows.sort(key=lambda item: int(item.get("seq", 0) or 0))
    return rows

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
    fallback_snapshot: dict | None = None,
) -> dict:
    """Apaga a interação escolhida e tudo depois, restaurando o estado anterior.

    Para interações antigas sem snapshot persistido, o chamador pode fornecer
    fallback_snapshot reconstruído a partir do histórico anterior.
    """

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

    ledger_before = str(
        selected.get("story_ledger_before", "") or ""
    ).strip()

    if ledger_before:
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
    else:
        reconstructed = (
            fallback_snapshot
            if isinstance(fallback_snapshot, dict)
            else {}
        )
        ledger_before = str(
            reconstructed.get("story_ledger", "") or ""
        ).strip()
        scene_before = reconstructed.get("scene_state")
        story_before = reconstructed.get("story_state")
        active_role_before = str(
            reconstructed.get("active_user_role", "JANIO") or "JANIO"
        ).strip().upper()

        if (
            not ledger_before
            or not isinstance(scene_before, dict)
            or not isinstance(story_before, dict)
        ):
            raise PersistenceError(
                "A interação antiga não possui snapshot e a reconstrução "
                "do estado anterior não foi fornecida."
            )

    if active_role_before not in {"JANIO", "PERSONAGEM_DA_CENA"}:
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
            ledger_before,
            json.dumps(scene_before, ensure_ascii=False),
            json.dumps(story_before, ensure_ascii=False),
        ]],
        value_input_option="RAW",
    )

    return {
        "deleted_count": len(rows_to_delete),
        "last_seq": last_seq,
        "active_user_role": active_role_before,
        "story_ledger": ledger_before,
        "scene_state": scene_before,
        "story_state": story_before,
    }
