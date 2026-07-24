from __future__ import annotations

import json
import sys
from copy import deepcopy
from functools import wraps
from typing import Any, Callable

import streamlit as st

import google_sheets_repository as sheets_repository
from user_profile import normalizar_perfil


USER_VISUAL_PROFILE_PERSISTENCE_VERSION = (
    "user-visual-profile-persistence-v1-versioned-restore"
)
USER_VISUAL_PROFILE_SHEET = "USER_VISUAL_PROFILE"

USER_VISUAL_PROFILE_COLUMNS = (
    "visual_profile_id",
    "user_id",
    "version",
    "created_at",
    "updated_at",
    "status",
    "reference_image_id",
    "image_hash",
    "reference_confirmed",
    "confirmed_at",
    "confirmation_source",
    "file_name",
    "mime_type",
    "size_bytes",
    "stable_traits_json",
    "variable_traits_json",
    "current_appearance_json",
    "first_impression",
    "first_impression_created_at",
    "source_interaction_id",
    "analysis_model",
    "analysis_prompt_version",
    "last_used_at",
    "active",
)

_INSTALLED = False
_ORIGINAL_TITLE: Callable[..., Any] | None = None


def _texto(value: Any) -> str:
    return str(value or "").strip()


def _inteiro(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _booleano(value: Any, default: bool = False) -> bool:
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


def _json_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return deepcopy(value)
    text = _texto(value)
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return deepcopy(parsed) if isinstance(parsed, dict) else {}


def _json_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return deepcopy(value)
    if isinstance(value, tuple):
        return list(value)
    text = _texto(value)
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    return deepcopy(parsed) if isinstance(parsed, list) else []


def _clear_caches() -> None:
    for name in ("obter_cabecalhos", "obter_registros_aba"):
        function = getattr(sheets_repository, name, None)
        clear = getattr(function, "clear", None)
        if callable(clear):
            clear()


def garantir_schema_user_visual_profile() -> list[str]:
    worksheet = sheets_repository.obter_aba(USER_VISUAL_PROFILE_SHEET)
    headers = list(sheets_repository.obter_cabecalhos(USER_VISUAL_PROFILE_SHEET))
    added: list[str] = []
    for column in USER_VISUAL_PROFILE_COLUMNS:
        if column in headers:
            continue
        headers.append(column)
        worksheet.update_cell(1, len(headers), column)
        added.append(column)
    if added:
        _clear_caches()
    return added


def listar_perfis_visuais_usuario(user_id: str) -> list[dict[str, Any]]:
    uid = _texto(user_id)
    if not uid:
        return []
    garantir_schema_user_visual_profile()
    rows = sheets_repository.obter_registros_aba(USER_VISUAL_PROFILE_SHEET)
    selected = [
        dict(row)
        for row in rows
        if _texto(row.get("user_id")) == uid
    ]
    selected.sort(
        key=lambda row: (
            _inteiro(row.get("version"), 0),
            _texto(row.get("updated_at") or row.get("created_at")),
        ),
        reverse=True,
    )
    return selected


def obter_perfil_visual_ativo(user_id: str) -> dict[str, Any] | None:
    rows = listar_perfis_visuais_usuario(user_id)
    for row in rows:
        if _booleano(row.get("active"), False) and _texto(row.get("status") or "active").lower() in {
            "active", "ativo"
        }:
            return row
    return rows[0] if rows else None


def hidratar_user_profile_visual(
    profile: dict[str, Any],
    persisted: dict[str, Any] | None,
) -> dict[str, Any]:
    normalized = normalizar_perfil(profile)
    if not isinstance(persisted, dict):
        return normalized

    visual = normalized.setdefault("visual_profile", {})
    visual["visual_profile_id"] = _texto(persisted.get("visual_profile_id"))
    visual["reference_confirmed"] = _booleano(
        persisted.get("reference_confirmed"), False
    )
    visual["reference_version"] = max(0, _inteiro(persisted.get("version"), 0))
    visual["reference_image_id"] = _texto(persisted.get("reference_image_id"))
    visual["image_hash"] = _texto(
        persisted.get("image_hash") or persisted.get("reference_image_id")
    )
    visual["file_name"] = _texto(persisted.get("file_name"))
    visual["mime_type"] = _texto(persisted.get("mime_type"))
    visual["size_bytes"] = max(0, _inteiro(persisted.get("size_bytes"), 0))
    visual["confirmation_source"] = _texto(persisted.get("confirmation_source"))
    visual["last_confirmed_at"] = _texto(
        persisted.get("confirmed_at") or persisted.get("updated_at")
    )
    visual["stable_traits"] = _json_list(persisted.get("stable_traits_json"))
    visual["variable_traits"] = _json_list(persisted.get("variable_traits_json"))
    visual["current_appearance"] = _json_dict(
        persisted.get("current_appearance_json")
    )
    visual["first_impression"] = _texto(persisted.get("first_impression"))
    visual["first_impression_created_at"] = _texto(
        persisted.get("first_impression_created_at")
    )
    normalized.setdefault("milestones", {})[
        "visual_reference_confirmed"
    ] = bool(visual["reference_confirmed"])
    return normalizar_perfil(normalized)


def _desativar_perfis_anteriores(user_id: str) -> None:
    now = sheets_repository.utc_now_iso()
    for row in listar_perfis_visuais_usuario(user_id):
        if not _booleano(row.get("active"), False):
            continue
        profile_id = _texto(row.get("visual_profile_id"))
        if not profile_id:
            continue
        sheets_repository.atualizar_registro(
            USER_VISUAL_PROFILE_SHEET,
            coluna_chave="visual_profile_id",
            valor_chave=profile_id,
            alteracoes={
                "active": False,
                "status": "superseded",
                "updated_at": now,
            },
        )


def persistir_nova_referencia_visual(
    *,
    user_id: str,
    profile: dict[str, Any],
    source_interaction_id: str = "",
    analysis_model: str = "",
    analysis_prompt_version: str = "",
) -> dict[str, Any]:
    uid = _texto(user_id)
    if not uid:
        raise sheets_repository.GoogleSheetsRepositoryError(
            "O usuário do perfil visual não foi identificado."
        )

    garantir_schema_user_visual_profile()
    normalized = normalizar_perfil(profile)
    visual = normalized.get("visual_profile")
    visual = visual if isinstance(visual, dict) else {}

    existing = listar_perfis_visuais_usuario(uid)
    next_version = max(
        [max(0, _inteiro(row.get("version"), 0)) for row in existing] or [0]
    ) + 1
    now = sheets_repository.utc_now_iso()
    reference_id = _texto(
        visual.get("reference_image_id") or visual.get("image_hash")
    )
    image_hash = _texto(visual.get("image_hash") or reference_id)
    visual_profile_id = sheets_repository.gerar_id("vis")

    _desativar_perfis_anteriores(uid)

    record = {
        "visual_profile_id": visual_profile_id,
        "user_id": uid,
        "version": next_version,
        "created_at": now,
        "updated_at": now,
        "status": "active",
        "reference_image_id": reference_id,
        "image_hash": image_hash,
        "reference_confirmed": bool(visual.get("reference_confirmed", True)),
        "confirmed_at": _texto(visual.get("last_confirmed_at")) or now,
        "confirmation_source": _texto(visual.get("confirmation_source")),
        "file_name": _texto(visual.get("file_name")),
        "mime_type": _texto(visual.get("mime_type")),
        "size_bytes": max(0, _inteiro(visual.get("size_bytes"), 0)),
        "stable_traits_json": sheets_repository.serializar_json(
            visual.get("stable_traits") if isinstance(visual.get("stable_traits"), list) else []
        ),
        "variable_traits_json": sheets_repository.serializar_json(
            visual.get("variable_traits") if isinstance(visual.get("variable_traits"), list) else []
        ),
        "current_appearance_json": sheets_repository.serializar_json(
            visual.get("current_appearance")
            if isinstance(visual.get("current_appearance"), dict)
            else {}
        ),
        "first_impression": _texto(visual.get("first_impression")),
        "first_impression_created_at": _texto(
            visual.get("first_impression_created_at")
        ),
        "source_interaction_id": _texto(source_interaction_id),
        "analysis_model": _texto(analysis_model),
        "analysis_prompt_version": _texto(analysis_prompt_version),
        "last_used_at": now,
        "active": True,
    }
    sheets_repository.adicionar_registro(USER_VISUAL_PROFILE_SHEET, record)
    _clear_caches()
    return record


def _confirmar_referencia_adapter(
    profile: dict[str, Any],
    *,
    image_id: str = "",
    stable_traits: list[str] | None = None,
    variable_traits: list[str] | None = None,
    current_appearance: dict[str, Any] | None = None,
    first_impression: str = "",
    image_hash: str = "",
    file_name: str = "",
    mime_type: str = "",
    size_bytes: int | None = None,
    confirmation_source: str = "",
    **_: Any,
) -> dict[str, Any]:
    reference_id = _texto(image_id or image_hash)
    if not reference_id:
        raise ValueError("A referência visual não possui identificador válido.")

    normalized = normalizar_perfil(profile)
    visual = normalized.setdefault("visual_profile", {})
    current_version = max(0, _inteiro(visual.get("reference_version"), 0))
    now = sheets_repository.utc_now_iso()

    visual.update(
        {
            "reference_confirmed": True,
            "reference_version": current_version + 1,
            "reference_image_id": reference_id,
            "image_hash": _texto(image_hash or reference_id),
            "file_name": _texto(file_name),
            "mime_type": _texto(mime_type),
            "size_bytes": max(0, _inteiro(size_bytes, 0)),
            "confirmation_source": _texto(confirmation_source),
            "stable_traits": [
                _texto(item) for item in (stable_traits or []) if _texto(item)
            ],
            "variable_traits": [
                _texto(item) for item in (variable_traits or []) if _texto(item)
            ],
            "current_appearance": deepcopy(current_appearance or {}),
            "last_confirmed_at": now,
        }
    )
    impression = _texto(first_impression)
    if impression and not _texto(visual.get("first_impression")):
        visual["first_impression"] = impression
        visual["first_impression_created_at"] = now

    normalized.setdefault("milestones", {})[
        "visual_reference_confirmed"
    ] = True
    normalized["updated_at"] = now
    return normalizar_perfil(normalized)


def _patch_app(module: Any) -> None:
    module.confirmar_referencia_visual = _confirmar_referencia_adapter

    original_hydrate = getattr(module, "hidratar_perfil_usuario", None)
    if callable(original_hydrate) and not getattr(
        original_hydrate, "_visual_profile_wrapped", False
    ):
        @wraps(original_hydrate)
        def hydrate_wrapper(user: dict[str, Any]) -> Any:
            result = original_hydrate(user)
            user_id = _texto(user.get("user_id")) if isinstance(user, dict) else ""
            if user_id:
                try:
                    persisted = obter_perfil_visual_ativo(user_id)
                    st.session_state["user_profile"] = hidratar_user_profile_visual(
                        st.session_state.get("user_profile", {}), persisted
                    )
                    st.session_state["user_visual_profile"] = persisted
                except sheets_repository.GoogleSheetsRepositoryError as exc:
                    st.warning(
                        "O perfil foi carregado, mas a referência visual não pôde "
                        f"ser restaurada: {exc}"
                    )
            return result

        hydrate_wrapper._visual_profile_wrapped = True  # type: ignore[attr-defined]
        module.hidratar_perfil_usuario = hydrate_wrapper

    original_prepare = getattr(module, "preparar_upload", None)
    if callable(original_prepare) and not getattr(
        original_prepare, "_visual_profile_persistence_wrapped", False
    ):
        @wraps(original_prepare)
        def prepare_wrapper(uploaded_file: Any) -> Any:
            before = normalizar_perfil(st.session_state.get("user_profile"))
            previous_id = _texto(
                before.get("visual_profile", {}).get("reference_image_id")
                if isinstance(before.get("visual_profile"), dict)
                else ""
            )
            result = original_prepare(uploaded_file)
            after = normalizar_perfil(st.session_state.get("user_profile"))
            visual = after.get("visual_profile")
            visual = visual if isinstance(visual, dict) else {}
            current_id = _texto(visual.get("reference_image_id"))
            if current_id and current_id != previous_id:
                user = (
                    st.session_state.get("persistent_user")
                    or st.session_state.get("auth_user")
                    or {}
                )
                user_id = _texto(user.get("user_id")) if isinstance(user, dict) else ""
                if user_id:
                    persisted = persistir_nova_referencia_visual(
                        user_id=user_id,
                        profile=after,
                    )
                    st.session_state["user_visual_profile"] = persisted
            return result

        prepare_wrapper._visual_profile_persistence_wrapped = True  # type: ignore[attr-defined]
        module.preparar_upload = prepare_wrapper


def aplicar_persistencia_perfil_visual() -> None:
    garantir_schema_user_visual_profile()
    app_module = sys.modules.get("__main__")
    if app_module is not None:
        _patch_app(app_module)


def install_user_visual_profile_persistence() -> None:
    global _INSTALLED, _ORIGINAL_TITLE
    if _INSTALLED:
        return
    original_title = st.title
    _ORIGINAL_TITLE = original_title

    @wraps(original_title)
    def title_wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            aplicar_persistencia_perfil_visual()
        except sheets_repository.GoogleSheetsRepositoryError as exc:
            st.warning(
                "Não foi possível preparar a persistência do perfil visual: "
                f"{exc}"
            )
        return original_title(*args, **kwargs)

    st.title = title_wrapper
    _INSTALLED = True


__all__ = [
    "USER_VISUAL_PROFILE_COLUMNS",
    "USER_VISUAL_PROFILE_PERSISTENCE_VERSION",
    "aplicar_persistencia_perfil_visual",
    "garantir_schema_user_visual_profile",
    "hidratar_user_profile_visual",
    "install_user_visual_profile_persistence",
    "listar_perfis_visuais_usuario",
    "obter_perfil_visual_ativo",
    "persistir_nova_referencia_visual",
]
