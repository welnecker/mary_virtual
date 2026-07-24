from __future__ import annotations

from functools import wraps
import sys
from typing import Any, Callable

import streamlit as st

import google_sheets_repository as sheets_repository
from relationship import montar_resumo_estado_relacao, normalizar_estado_relacao


MARY_RELATIONSHIP_PERSISTENCE_VERSION = (
    "mary-relationship-persistence-v1-schema-sync"
)

MARY_RELATIONSHIP_COLUMNS = (
    "relationship_id",
    "user_id",
    "version",
    "created_at",
    "updated_at",
    "status",
    "mary_revealed",
    "first_mary_image_id",
    "first_reveal_at",
    "user_has_seen_mary",
    "user_first_visual_reaction",
    "relationship_summary",
    "relationship_state_json",
    "last_interaction_at",
    "last_scenario_id",
    "last_scenario_session_id",
    "active",
)

_INSTALLED = False
_ORIGINAL_TITLE: Callable[..., Any] | None = None


def _texto(value: Any) -> str:
    return str(value or "").strip()


def _booleano(value: Any, *, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = _texto(value).lower()
    if not text:
        return default
    return text in {"true", "1", "sim", "yes", "verdadeiro"}


def _inteiro(value: Any, *, default: int = 1) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _relationship_id(user_id: str) -> str:
    return "rel_" + _texto(user_id)


def _clear_sheet_caches() -> None:
    for name in ("obter_cabecalhos", "obter_registros_aba"):
        function = getattr(sheets_repository, name, None)
        clear = getattr(function, "clear", None)
        if callable(clear):
            clear()


def garantir_schema_mary_relationship() -> list[str]:
    """Adiciona ao cabeçalho somente as colunas ainda ausentes."""
    sheet_name = sheets_repository.MARY_RELATIONSHIP_SHEET
    worksheet = sheets_repository.obter_aba(sheet_name)
    headers = list(sheets_repository.obter_cabecalhos(sheet_name))
    added: list[str] = []

    for column in MARY_RELATIONSHIP_COLUMNS:
        if column in headers:
            continue
        headers.append(column)
        worksheet.update_cell(1, len(headers), column)
        added.append(column)

    if added:
        _clear_sheet_caches()
    return added


def _normalizar_relacionamento(
    record: dict[str, Any] | None,
    *,
    user_id: str,
) -> dict[str, Any]:
    now = sheets_repository.utc_now_iso()
    normalized = dict(record or {})
    normalized["relationship_id"] = (
        _texto(normalized.get("relationship_id")) or _relationship_id(user_id)
    )
    normalized["user_id"] = user_id
    normalized["version"] = max(1, _inteiro(normalized.get("version"), default=1))
    normalized["created_at"] = _texto(normalized.get("created_at")) or now
    normalized["updated_at"] = _texto(normalized.get("updated_at")) or now
    normalized["status"] = _texto(normalized.get("status")) or "active"
    normalized["mary_revealed"] = _booleano(normalized.get("mary_revealed"))
    normalized["first_mary_image_id"] = _texto(
        normalized.get("first_mary_image_id")
    )
    normalized["first_reveal_at"] = _texto(normalized.get("first_reveal_at"))
    normalized["user_has_seen_mary"] = _booleano(
        normalized.get("user_has_seen_mary")
    )
    normalized["user_first_visual_reaction"] = _texto(
        normalized.get("user_first_visual_reaction")
    )
    normalized["relationship_summary"] = _texto(
        normalized.get("relationship_summary")
    )
    normalized["relationship_state_json"] = _texto(
        normalized.get("relationship_state_json")
    )
    normalized["last_interaction_at"] = _texto(
        normalized.get("last_interaction_at")
    )
    normalized["last_scenario_id"] = _texto(normalized.get("last_scenario_id"))
    normalized["last_scenario_session_id"] = _texto(
        normalized.get("last_scenario_session_id")
    )
    normalized["active"] = _booleano(normalized.get("active"), default=True)
    return normalized


def obter_ou_criar_relacionamento_mary(user_id: str) -> dict[str, Any]:
    user_id = _texto(user_id)
    if not user_id:
        raise sheets_repository.GoogleSheetsRepositoryError(
            "O user_id não foi informado."
        )

    garantir_schema_mary_relationship()
    existing = sheets_repository.buscar_registro(
        sheets_repository.MARY_RELATIONSHIP_SHEET,
        coluna="user_id",
        valor=user_id,
    )
    normalized = _normalizar_relacionamento(existing, user_id=user_id)

    if existing is None:
        sheets_repository.adicionar_registro(
            sheets_repository.MARY_RELATIONSHIP_SHEET,
            normalized,
        )
        return normalized

    changes = {
        key: value
        for key, value in normalized.items()
        if _texto(existing.get(key)) != _texto(value)
    }
    if changes:
        sheets_repository.atualizar_registro(
            sheets_repository.MARY_RELATIONSHIP_SHEET,
            coluna_chave="user_id",
            valor_chave=user_id,
            alteracoes=changes,
        )
    return normalized


def _resolver_user_id(identifier: str) -> str:
    identifier = _texto(identifier)
    if not identifier:
        return ""
    if identifier.startswith("rel_"):
        by_relationship = sheets_repository.buscar_registro(
            sheets_repository.MARY_RELATIONSHIP_SHEET,
            coluna="relationship_id",
            valor=identifier,
        )
        if isinstance(by_relationship, dict):
            found = _texto(by_relationship.get("user_id"))
            if found:
                return found
        return identifier[4:]
    return identifier


def atualizar_relacionamento_mary(
    identifier: str,
    changes: dict[str, Any] | None = None,
    **fields: Any,
) -> dict[str, Any]:
    garantir_schema_mary_relationship()
    user_id = _resolver_user_id(identifier)
    if not user_id:
        raise sheets_repository.GoogleSheetsRepositoryError(
            "O relacionamento não possui identificador válido."
        )

    current = obter_ou_criar_relacionamento_mary(user_id)
    payload: dict[str, Any] = {}
    if isinstance(changes, dict):
        payload.update(changes)
    payload.update(fields)
    payload.pop("user_id", None)
    payload.pop("relationship_id", None)
    payload["updated_at"] = sheets_repository.utc_now_iso()

    if "version" in payload:
        payload["version"] = max(1, _inteiro(payload["version"], default=1))
    for field in (
        "mary_revealed",
        "user_has_seen_mary",
        "active",
    ):
        if field in payload:
            payload[field] = _booleano(payload[field])

    sheets_repository.atualizar_registro(
        sheets_repository.MARY_RELATIONSHIP_SHEET,
        coluna_chave="user_id",
        valor_chave=user_id,
        alteracoes=payload,
    )
    updated = dict(current)
    updated.update(payload)
    return _normalizar_relacionamento(updated, user_id=user_id)


def sincronizar_estado_relacionamento(
    interaction_record: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    user = (
        st.session_state.get("persistent_user")
        or st.session_state.get("auth_user")
        or {}
    )
    if not isinstance(user, dict):
        return None
    user_id = _texto(user.get("user_id"))
    if not user_id:
        return None

    state = normalizar_estado_relacao(
        st.session_state.get("relationship_state")
    )
    scenario = st.session_state.get("scenario_instance")
    scenario = scenario if isinstance(scenario, dict) else {}
    interaction_record = (
        interaction_record if isinstance(interaction_record, dict) else {}
    )

    try:
        summary = _texto(montar_resumo_estado_relacao(state))
    except Exception:
        summary = ""

    payload = {
        "relationship_summary": summary,
        "relationship_state_json": sheets_repository.serializar_json(state),
        "last_interaction_at": (
            _texto(interaction_record.get("timestamp"))
            or sheets_repository.utc_now_iso()
        ),
        "last_scenario_id": _texto(scenario.get("scenario_id")),
        "last_scenario_session_id": _texto(
            scenario.get("scenario_session_id")
        ),
        "status": "active",
        "active": True,
    }
    updated = atualizar_relacionamento_mary(user_id, payload)
    st.session_state["mary_relationship"] = updated
    return updated


def _patch_repository_exports() -> None:
    sheets_repository.obter_ou_criar_relacionamento_mary = (
        obter_ou_criar_relacionamento_mary
    )
    sheets_repository.atualizar_relacionamento_mary = atualizar_relacionamento_mary


def _patch_app(module: Any) -> None:
    module.obter_ou_criar_relacionamento_mary = obter_ou_criar_relacionamento_mary

    original = getattr(module, "registrar_interacao_local_e_remota", None)
    if not callable(original) or getattr(original, "_mary_relationship_wrapped", False):
        return

    @wraps(original)
    def wrapper(record: dict[str, Any]) -> Any:
        result = original(record)
        if isinstance(record, dict) and not _texto(record.get("error")):
            try:
                sincronizar_estado_relacionamento(record)
            except sheets_repository.GoogleSheetsRepositoryError as exc:
                st.warning(
                    "A interação foi salva, mas o estado relacional não pôde "
                    f"ser atualizado: {exc}"
                )
        return result

    wrapper._mary_relationship_wrapped = True  # type: ignore[attr-defined]
    module.registrar_interacao_local_e_remota = wrapper


def aplicar_persistencia_relacionamento_mary() -> None:
    _patch_repository_exports()
    app_module = sys.modules.get("__main__")
    if app_module is not None:
        _patch_app(app_module)


def install_mary_relationship_persistence() -> None:
    global _INSTALLED, _ORIGINAL_TITLE
    if _INSTALLED:
        return

    original_title = st.title
    _ORIGINAL_TITLE = original_title

    @wraps(original_title)
    def title_wrapper(*args: Any, **kwargs: Any) -> Any:
        aplicar_persistencia_relacionamento_mary()
        return original_title(*args, **kwargs)

    st.title = title_wrapper
    _INSTALLED = True


__all__ = [
    "MARY_RELATIONSHIP_COLUMNS",
    "MARY_RELATIONSHIP_PERSISTENCE_VERSION",
    "aplicar_persistencia_relacionamento_mary",
    "atualizar_relacionamento_mary",
    "garantir_schema_mary_relationship",
    "install_mary_relationship_persistence",
    "obter_ou_criar_relacionamento_mary",
    "sincronizar_estado_relacionamento",
]
