from __future__ import annotations

from copy import deepcopy
from functools import wraps
import sys
from typing import Any, Callable

import streamlit as st

import google_sheets_repository as sheets_repository
import scenarios.registry as scenario_registry
import scenarios.service as scenario_service


SCENARIO_CATALOG_PERSISTENCE_VERSION = (
    "scenario-catalog-persistence-v1-schema-sync-safe-overrides"
)
SCENARIOS_SHEET = "SCENARIOS"

SCENARIO_COLUMNS = (
    "scenario_id",
    "category",
    "title",
    "short_description",
    "status",
    "adult_only",
    "display_order",
    "scenario_version",
    "opening_message",
    "max_interactions",
    "access_type",
    "price_cents",
    "currency",
    "product_id",
    "card_title",
    "card_subtitle",
    "card_image",
    "card_badge",
    "button_label_free",
    "button_label_locked",
    "button_label_unlocked",
    "target_interactions",
    "soft_ending_start",
    "hard_ending_limit",
    "published",
    "active",
    "config_source",
    "created_at",
    "updated_at",
)

_INSTALLED = False
_ORIGINAL_TITLE: Callable[..., Any] | None = None
_ORIGINAL_REGISTRY_LIST: Callable[..., Any] | None = None


def _texto(value: Any) -> str:
    return str(value or "").strip()


def _booleano(value: Any, *, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    text = _texto(value).lower()
    if text in {"true", "1", "sim", "yes", "verdadeiro", "active", "ativo"}:
        return True
    if text in {"false", "0", "nao", "não", "no", "falso", "inactive", "inativo", ""}:
        return False
    return default


def _inteiro(value: Any, *, default: int = 0, minimum: int = 0) -> int:
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        number = default
    return max(minimum, number)


def _clear_sheet_caches() -> None:
    for name in ("obter_cabecalhos", "obter_registros_aba"):
        function = getattr(sheets_repository, name, None)
        clear = getattr(function, "clear", None)
        if callable(clear):
            clear()


def garantir_schema_scenarios() -> list[str]:
    worksheet = sheets_repository.obter_aba(SCENARIOS_SHEET)
    headers = list(sheets_repository.obter_cabecalhos(SCENARIOS_SHEET))
    added: list[str] = []
    for column in SCENARIO_COLUMNS:
        if column in headers:
            continue
        headers.append(column)
        worksheet.update_cell(1, len(headers), column)
        added.append(column)
    if added:
        _clear_sheet_caches()
    return added


def _registro_do_catalogo(item: dict[str, Any], existing: dict[str, Any] | None = None) -> dict[str, Any]:
    existing = dict(existing or {})
    now = sheets_repository.utc_now_iso()
    card = item.get("card") if isinstance(item.get("card"), dict) else {}
    duration = item.get("duration") if isinstance(item.get("duration"), dict) else {}
    commerce = item.get("commerce") if isinstance(item.get("commerce"), dict) else {}

    scenario_id = _texto(item.get("scenario_id"))
    return {
        "scenario_id": scenario_id,
        "category": _texto(existing.get("category")) or _texto(item.get("category")),
        "title": _texto(existing.get("title")) or _texto(item.get("title")) or scenario_id,
        "short_description": (
            _texto(existing.get("short_description"))
            or _texto(item.get("short_description"))
        ),
        "status": _texto(existing.get("status")) or "active",
        "adult_only": (
            _booleano(existing.get("adult_only"), default=bool(item.get("adult_only")))
            if "adult_only" in existing
            else bool(item.get("adult_only"))
        ),
        "display_order": _inteiro(
            existing.get("display_order", item.get("display_order", 999)),
            default=999,
        ),
        "scenario_version": _inteiro(
            item.get("scenario_version", 1), default=1, minimum=1
        ),
        "opening_message": _texto(existing.get("opening_message")),
        "max_interactions": _inteiro(
            existing.get("max_interactions", item.get("max_interactions", 58)),
            default=58,
            minimum=1,
        ),
        "access_type": (
            _texto(existing.get("access_type"))
            or _texto(commerce.get("access_type"))
            or _texto(item.get("access_type"))
            or "paid"
        ).lower(),
        "price_cents": _inteiro(
            existing.get("price_cents", commerce.get("price_cents", item.get("price_cents", 0))),
            default=0,
        ),
        "currency": (
            _texto(existing.get("currency"))
            or _texto(commerce.get("currency"))
            or _texto(item.get("currency"))
            or "BRL"
        ).upper(),
        "product_id": (
            _texto(existing.get("product_id"))
            or _texto(commerce.get("product_id"))
            or _texto(item.get("product_id"))
        ),
        "card_title": _texto(existing.get("card_title")) or _texto(card.get("title")) or _texto(item.get("card_title")),
        "card_subtitle": _texto(existing.get("card_subtitle")) or _texto(card.get("subtitle")) or _texto(item.get("card_subtitle")),
        "card_image": _texto(existing.get("card_image")) or _texto(card.get("image")) or _texto(item.get("card_image")),
        "card_badge": _texto(existing.get("card_badge")) or _texto(card.get("badge")) or _texto(item.get("card_badge")),
        "button_label_free": _texto(existing.get("button_label_free")) or _texto(card.get("button_label_free")) or _texto(item.get("button_label_free")) or "Jogar gratuitamente",
        "button_label_locked": _texto(existing.get("button_label_locked")) or _texto(card.get("button_label_locked")) or _texto(item.get("button_label_locked")) or "Desbloquear",
        "button_label_unlocked": _texto(existing.get("button_label_unlocked")) or _texto(card.get("button_label_unlocked")) or _texto(item.get("button_label_unlocked")) or "Jogar",
        "target_interactions": _inteiro(
            existing.get("target_interactions", duration.get("target_interactions", item.get("target_interactions", 48))),
            default=48,
            minimum=1,
        ),
        "soft_ending_start": _inteiro(
            existing.get("soft_ending_start", duration.get("soft_ending_start", item.get("soft_ending_start", 40))),
            default=40,
            minimum=1,
        ),
        "hard_ending_limit": _inteiro(
            existing.get("hard_ending_limit", duration.get("hard_ending_limit", item.get("hard_ending_limit", 58))),
            default=58,
            minimum=1,
        ),
        "published": _booleano(existing.get("published"), default=True),
        "active": _booleano(existing.get("active"), default=True),
        "config_source": "python_registry",
        "created_at": _texto(existing.get("created_at")) or now,
        "updated_at": now,
    }


def sincronizar_catalogo_scenarios() -> list[dict[str, Any]]:
    garantir_schema_scenarios()
    if _ORIGINAL_REGISTRY_LIST is None:
        return []

    code_items = _ORIGINAL_REGISTRY_LIST()
    if not isinstance(code_items, list):
        return []
    existing_rows = sheets_repository.obter_registros_aba(SCENARIOS_SHEET)
    existing_by_id = {
        _texto(row.get("scenario_id")): dict(row)
        for row in existing_rows
        if _texto(row.get("scenario_id"))
    }
    synced: list[dict[str, Any]] = []
    for item in code_items:
        if not isinstance(item, dict):
            continue
        scenario_id = _texto(item.get("scenario_id"))
        if not scenario_id:
            continue
        existing = existing_by_id.get(scenario_id)
        record = _registro_do_catalogo(item, existing)
        if existing is None:
            sheets_repository.adicionar_registro(SCENARIOS_SHEET, record)
        else:
            # Campos editoriais já existentes são preservados; metadados técnicos
            # e datas são atualizados sem substituir decisões administrativas.
            technical_changes = {
                "scenario_version": record["scenario_version"],
                "config_source": "python_registry",
                "updated_at": record["updated_at"],
            }
            sheets_repository.atualizar_registro(
                SCENARIOS_SHEET,
                coluna_chave="scenario_id",
                valor_chave=scenario_id,
                alteracoes=technical_changes,
            )
            record.update(existing)
            record.update(technical_changes)
        synced.append(record)
    _clear_sheet_caches()
    return synced


def _aplicar_override(item: dict[str, Any], row: dict[str, Any]) -> dict[str, Any] | None:
    status = _texto(row.get("status") or "active").lower()
    if status not in {"active", "ativo", "published", "publicado"}:
        return None
    if not _booleano(row.get("active"), default=True):
        return None
    if not _booleano(row.get("published"), default=True):
        return None

    result = deepcopy(item)
    result["category"] = _texto(row.get("category")) or result.get("category", "")
    result["title"] = _texto(row.get("title")) or result.get("title", "")
    result["short_description"] = _texto(row.get("short_description")) or result.get("short_description", "")
    result["adult_only"] = _booleano(row.get("adult_only"), default=bool(result.get("adult_only")))
    result["display_order"] = _inteiro(row.get("display_order", result.get("display_order", 999)), default=999)

    access_type = _texto(row.get("access_type")) or _texto(result.get("access_type")) or "paid"
    price_cents = _inteiro(row.get("price_cents", result.get("price_cents", 0)), default=0)
    currency = (_texto(row.get("currency")) or _texto(result.get("currency")) or "BRL").upper()
    product_id = _texto(row.get("product_id")) or _texto(result.get("product_id"))
    result.update({
        "access_type": access_type,
        "price_cents": price_cents,
        "currency": currency,
        "product_id": product_id,
    })
    commerce = deepcopy(result.get("commerce")) if isinstance(result.get("commerce"), dict) else {}
    commerce.update({
        "access_type": access_type,
        "price_cents": price_cents,
        "currency": currency,
        "product_id": product_id,
    })
    result["commerce"] = commerce

    card = deepcopy(result.get("card")) if isinstance(result.get("card"), dict) else {}
    card_fields = {
        "title": "card_title",
        "subtitle": "card_subtitle",
        "image": "card_image",
        "badge": "card_badge",
        "button_label_free": "button_label_free",
        "button_label_locked": "button_label_locked",
        "button_label_unlocked": "button_label_unlocked",
    }
    for key, column in card_fields.items():
        value = _texto(row.get(column))
        if value:
            card[key] = value
            result[column] = value
    result["card"] = card

    duration = deepcopy(result.get("duration")) if isinstance(result.get("duration"), dict) else {}
    target = _inteiro(row.get("target_interactions", duration.get("target_interactions", 48)), default=48, minimum=1)
    soft = _inteiro(row.get("soft_ending_start", duration.get("soft_ending_start", 40)), default=40, minimum=1)
    hard = _inteiro(row.get("hard_ending_limit", duration.get("hard_ending_limit", result.get("max_interactions", 58))), default=58, minimum=1)
    soft = min(soft, hard)
    target = min(max(target, soft), hard)
    duration.update({
        "target_interactions": target,
        "soft_ending_start": soft,
        "hard_ending_limit": hard,
    })
    result["duration"] = duration
    result["target_interactions"] = target
    result["soft_ending_start"] = soft
    result["hard_ending_limit"] = hard
    result["max_interactions"] = _inteiro(row.get("max_interactions", hard), default=hard, minimum=1)
    return result


def listar_cenarios_disponiveis() -> list[dict[str, Any]]:
    if _ORIGINAL_REGISTRY_LIST is None:
        return []
    code_items = _ORIGINAL_REGISTRY_LIST()
    if not isinstance(code_items, list):
        return []
    try:
        garantir_schema_scenarios()
        rows = sheets_repository.obter_registros_aba(SCENARIOS_SHEET)
    except Exception:
        # Falha da planilha não derruba o catálogo embarcado no código.
        return code_items

    by_id = {
        _texto(row.get("scenario_id")): dict(row)
        for row in rows
        if _texto(row.get("scenario_id"))
    }
    result: list[dict[str, Any]] = []
    for item in code_items:
        if not isinstance(item, dict):
            continue
        scenario_id = _texto(item.get("scenario_id"))
        row = by_id.get(scenario_id)
        if row is None:
            result.append(deepcopy(item))
            continue
        overridden = _aplicar_override(item, row)
        if overridden is not None:
            result.append(overridden)
    result.sort(key=lambda value: (
        _inteiro(value.get("display_order", 999), default=999),
        _texto(value.get("title")).lower(),
    ))
    return result


def _patch_catalog_functions() -> None:
    scenario_registry.listar_cenarios_disponiveis = listar_cenarios_disponiveis
    scenario_service.listar_cenarios_disponiveis = listar_cenarios_disponiveis
    main_module = sys.modules.get("__main__")
    if main_module is not None and hasattr(main_module, "listar_cenarios_disponiveis"):
        main_module.listar_cenarios_disponiveis = listar_cenarios_disponiveis


def aplicar_persistencia_catalogo_scenarios() -> None:
    _patch_catalog_functions()
    try:
        sincronizar_catalogo_scenarios()
    except sheets_repository.GoogleSheetsRepositoryError:
        # O app continua com o catálogo Python quando Sheets estiver indisponível.
        pass


def install_scenario_catalog_persistence() -> None:
    global _INSTALLED, _ORIGINAL_TITLE, _ORIGINAL_REGISTRY_LIST
    if _INSTALLED:
        return
    _ORIGINAL_REGISTRY_LIST = scenario_registry.listar_cenarios_disponiveis
    original_title = st.title
    _ORIGINAL_TITLE = original_title

    @wraps(original_title)
    def title_wrapper(*args: Any, **kwargs: Any) -> Any:
        aplicar_persistencia_catalogo_scenarios()
        return original_title(*args, **kwargs)

    st.title = title_wrapper
    _INSTALLED = True


__all__ = [
    "SCENARIO_CATALOG_PERSISTENCE_VERSION",
    "SCENARIO_COLUMNS",
    "SCENARIOS_SHEET",
    "aplicar_persistencia_catalogo_scenarios",
    "garantir_schema_scenarios",
    "install_scenario_catalog_persistence",
    "listar_cenarios_disponiveis",
    "sincronizar_catalogo_scenarios",
]
