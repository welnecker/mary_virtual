from __future__ import annotations

from copy import deepcopy
from functools import wraps
import sys
from typing import Any, Callable

import streamlit as st

import ui.pix_test_commerce_integration as pix_commerce
import ui.scenario_menu as scenario_menu
from repositories.interaction_repository import listar_interacoes_sessao_cenario
from repositories.scenario_session_repository import (
    listar_sessoes_cenario_usuario,
    obter_sessao_cenario,
    salvar_instancia_cenario,
)
from scenarios.registry import iniciar_instancia_cenario
from scenarios.service import avaliar_acesso_cenario


PAID_CHAPTER_CONTINUATION_VERSION = (
    "paid-chapter-continuation-v1-history-preserved-per-paid-cycle"
)
PAID_SCENARIO_ID = "casada_frustrada"

_CONTEXT_KEY = "pix_chapter_purchase_context"
_HISTORY_KEY = "_mary_paid_chapter_history_messages"
_CURRENT_SESSION_KEY = "_mary_paid_chapter_session_id"
_PENDING_RESTORE_KEY = "_mary_paid_chapter_pending_restore"

_INSTALLED = False
_ORIGINAL_TITLE: Callable[..., Any] | None = None


def _texto(value: Any) -> str:
    return str(value or "").strip()


def _usuario_atual_id() -> str:
    usuario = (
        st.session_state.get("persistent_user")
        or st.session_state.get("auth_user")
        or {}
    )
    if not isinstance(usuario, dict):
        return ""
    return _texto(usuario.get("user_id"))


def _mensagens_da_sessao(
    *,
    user_id: str,
    scenario_session_id: str,
) -> list[dict[str, str]]:
    interacoes = listar_interacoes_sessao_cenario(
        user_id=user_id,
        scenario_session_id=scenario_session_id,
        limite=100,
    )
    mensagens: list[dict[str, str]] = []
    for interacao in interacoes:
        if _texto(interacao.get("error")):
            continue
        user_text = _texto(interacao.get("user_text"))
        mary_response = _texto(interacao.get("mary_response"))
        if user_text:
            mensagens.append({"role": "user", "content": user_text})
        if mary_response:
            mensagens.append({"role": "assistant", "content": mary_response})
    return mensagens


def _history_session_ids(sessao: dict[str, Any]) -> list[str]:
    story_progress = sessao.get("story_progress")
    if not isinstance(story_progress, dict):
        story_progress = {}

    raw_ids = story_progress.get("history_session_ids")
    if not isinstance(raw_ids, list):
        raw_ids = []

    ids: list[str] = []
    for value in raw_ids:
        session_id = _texto(value)
        if session_id and session_id not in ids:
            ids.append(session_id)

    parent_id = _texto(story_progress.get("parent_session_id"))
    if parent_id and parent_id not in ids:
        ids.append(parent_id)

    return ids


def _mensagens_historicas(
    *,
    user_id: str,
    sessao: dict[str, Any],
    incluir_sessao_atual: bool,
) -> list[dict[str, str]]:
    ids = _history_session_ids(sessao)
    current_id = _texto(sessao.get("scenario_session_id"))
    if incluir_sessao_atual and current_id and current_id not in ids:
        ids.append(current_id)

    mensagens: list[dict[str, str]] = []
    for session_id in ids:
        mensagens.extend(
            _mensagens_da_sessao(
                user_id=user_id,
                scenario_session_id=session_id,
            )
        )
    return mensagens


def _latest_completed_session(user_id: str) -> dict[str, Any] | None:
    sessoes = listar_sessoes_cenario_usuario(
        user_id,
        status="completed",
        scenario_id=PAID_SCENARIO_ID,
    )
    return sessoes[0] if sessoes else None


def _clear_ending_state(data: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(data if isinstance(data, dict) else {})
    for field in (
        "ending_ready",
        "ending_sent",
        "ending_forced",
        "ending_requested_by_user",
        "input_locked",
        "show_return_to_menu",
        "ending_countdown_visible",
    ):
        result[field] = False
    for field in (
        "ending_trigger",
        "ending_reason",
        "ending_type",
        "completed_at",
    ):
        result[field] = ""
    result["ending_trigger_interaction"] = 0
    result["ending_requested_at_interaction"] = 0
    result["ending_countdown_remaining"] = 0
    result["interaction_count"] = 0
    return result


def _create_continuation_instance(
    *,
    user_id: str,
    parent_session_id: str,
    unlocked_scenario_ids: set[str],
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    parent = obter_sessao_cenario(parent_session_id)
    if not isinstance(parent, dict):
        raise ValueError("O capítulo anterior não foi encontrado.")
    if _texto(parent.get("user_id")) != user_id:
        raise ValueError("O capítulo anterior não pertence ao usuário atual.")
    if _texto(parent.get("scenario_id")) != PAID_SCENARIO_ID:
        raise ValueError("O capítulo anterior não pertence a esta história.")
    if _texto(parent.get("status")).lower() != "completed":
        raise ValueError("O capítulo anterior ainda não foi concluído.")

    instancia = iniciar_instancia_cenario(
        scenario_id=PAID_SCENARIO_ID,
        user_id=user_id,
    )
    access = avaliar_acesso_cenario(
        cenario=instancia.get("scenario_config", {}),
        unlocked_scenario_ids=unlocked_scenario_ids,
    )
    if not bool(access.get("allowed")):
        raise PermissionError("Um novo pagamento é necessário para continuar.")

    previous_progress = parent.get("story_progress")
    if not isinstance(previous_progress, dict):
        previous_progress = {}

    history_ids = _history_session_ids(parent)
    if parent_session_id not in history_ids:
        history_ids.append(parent_session_id)

    previous_chapter = int(previous_progress.get("chapter_number", 1) or 1)
    chapter_number = previous_chapter + 1

    previous_scene = parent.get("scene_state")
    if not isinstance(previous_scene, dict):
        previous_scene = {}
    scene_state = _clear_ending_state(previous_scene)
    if _texto(scene_state.get("current_phase")).lower() == "ending":
        scene_state["current_phase"] = "aftercare"
    scene_state["continuation_mode"] = True
    scene_state["chapter_number"] = chapter_number
    scene_state["parent_session_id"] = parent_session_id

    previous_messages = _mensagens_historicas(
        user_id=user_id,
        sessao=parent,
        incluir_sessao_atual=True,
    )
    compact_context = previous_messages[-12:]
    scene_state["continuation_context"] = compact_context

    instancia.update(
        {
            "status": "active",
            "completed_at": "",
            "interaction_count": 0,
            "opening_sent": True,
            "current_phase": _texto(scene_state.get("current_phase")) or "aftercare",
            "current_route": _texto(scene_state.get("current_route")),
            "current_beat": _texto(scene_state.get("current_beat")),
            "active_hook": _texto(scene_state.get("active_hook")),
            "ending_ready": False,
            "ending_sent": False,
            "ending_type": "",
            "ending_reason": "",
            "input_locked": False,
            "show_return_to_menu": False,
            "summary": "",
            "scene_state": scene_state,
            "story_progress": {
                **deepcopy(previous_progress),
                "chapter_number": chapter_number,
                "parent_session_id": parent_session_id,
                "history_session_ids": history_ids,
                "continuation_mode": True,
            },
            "access_status": access.get("access_status"),
            "access_reason": access.get("access_reason"),
        }
    )
    salvar_instancia_cenario(instancia)
    return instancia, previous_messages


def _enrich_catalog(items: Any) -> Any:
    if not isinstance(items, list):
        return items
    user_id = _usuario_atual_id()
    if not user_id:
        return items

    completed = _latest_completed_session(user_id)
    for item in items:
        if not isinstance(item, dict):
            continue
        if _texto(item.get("scenario_id")) != PAID_SCENARIO_ID:
            continue
        if item.get("active_session"):
            continue
        item["completed_session"] = deepcopy(completed)
        item["continuation_available"] = bool(completed)
        if completed:
            item["completed_interaction_count"] = int(
                completed.get("interaction_count", 0) or 0
            )
    return items


def _patch_catalog(module: Any) -> None:
    original = getattr(module, "listar_cenarios_para_usuario", None)
    if not callable(original) or getattr(original, "_mary_chapter_catalog_wrapped", False):
        return

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return _enrich_catalog(original(*args, **kwargs))

    wrapper._mary_chapter_catalog_wrapped = True  # type: ignore[attr-defined]
    setattr(module, "listar_cenarios_para_usuario", wrapper)


def _patch_completed_history_listing(module: Any) -> None:
    original = getattr(module, "listar_historias_iniciadas_usuario", None)
    if not callable(original) or getattr(original, "_mary_chapter_history_wrapped", False):
        return

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        result = original(*args, **kwargs)
        status = _texto(kwargs.get("status")).lower()
        if status == "completed" and isinstance(result, list):
            return [
                item
                for item in result
                if not (
                    isinstance(item, dict)
                    and _texto(item.get("scenario_id")) == PAID_SCENARIO_ID
                )
            ]
        return result

    wrapper._mary_chapter_history_wrapped = True  # type: ignore[attr-defined]
    setattr(module, "listar_historias_iniciadas_usuario", wrapper)


def _render_completed_paid_card(cenario: dict[str, Any]) -> dict[str, str] | None:
    completed = cenario.get("completed_session")
    if not isinstance(completed, dict):
        return None

    card = scenario_menu._resolver_card(cenario)
    access_label = scenario_menu._rotulo_acesso(cenario)
    scenario_id = _texto(cenario.get("scenario_id"))
    total = int(completed.get("interaction_count", 0) or 0)

    with st.container(border=True):
        scenario_menu._render_card_copy(
            card=card,
            access_label=access_label,
        )
        st.caption(
            f"Capítulo concluído · {total} interações · histórico preservado"
        )
        st.write("Escolha como deseja usar o próximo ciclo pago.")
        col_continue, col_restart = st.columns(2)
        with col_continue:
            continue_clicked = st.button(
                "Continuar história",
                key="scenario_paid_continue_" + scenario_id,
                type="primary",
                use_container_width=True,
            )
        with col_restart:
            restart_clicked = st.button(
                "Recomeçar do início",
                key="scenario_paid_restart_" + scenario_id,
                use_container_width=True,
            )

    if continue_clicked:
        st.session_state[_CONTEXT_KEY] = {
            "scenario_id": scenario_id,
            "purchase_mode": "continue",
            "parent_session_id": _texto(completed.get("scenario_session_id")),
        }
        return {
            "action": scenario_menu.ACTION_UNLOCK,
            "scenario_id": scenario_id,
        }
    if restart_clicked:
        st.session_state[_CONTEXT_KEY] = {
            "scenario_id": scenario_id,
            "purchase_mode": "restart",
            "parent_session_id": "",
        }
        return {
            "action": scenario_menu.ACTION_UNLOCK,
            "scenario_id": scenario_id,
        }
    return None


def _patch_card_renderer() -> None:
    original = getattr(scenario_menu, "_renderizar_card", None)
    if not callable(original) or getattr(original, "_mary_chapter_card_wrapped", False):
        return

    @wraps(original)
    def wrapper(cenario: dict[str, Any]) -> Any:
        if (
            isinstance(cenario, dict)
            and _texto(cenario.get("scenario_id")) == PAID_SCENARIO_ID
            and bool(cenario.get("continuation_available"))
            and not bool(cenario.get("allowed"))
            and not bool(cenario.get("can_continue"))
        ):
            return _render_completed_paid_card(cenario)
        return original(cenario)

    wrapper._mary_chapter_card_wrapped = True  # type: ignore[attr-defined]
    scenario_menu._renderizar_card = wrapper


def _patch_purchase_builder() -> None:
    original = getattr(pix_commerce, "_obter_ou_criar_compra", None)
    if not callable(original) or getattr(original, "_mary_chapter_purchase_wrapped", False):
        return

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
        compra = original(*args, **kwargs)
        context = st.session_state.get(_CONTEXT_KEY)
        if not isinstance(context, dict):
            context = {}
        scenario_id = _texto(compra.get("scenario_id"))
        if scenario_id == _texto(context.get("scenario_id")):
            compra["purchase_mode"] = _texto(context.get("purchase_mode")) or "restart"
            compra["parent_session_id"] = _texto(context.get("parent_session_id"))
            pix_commerce._salvar_compra(compra)
        return compra

    wrapper._mary_chapter_purchase_wrapped = True  # type: ignore[attr-defined]
    pix_commerce._obter_ou_criar_compra = wrapper


def _patch_credit_grant() -> None:
    original = getattr(pix_commerce, "_conceder_credito", None)
    if not callable(original) or getattr(original, "_mary_chapter_credit_wrapped", False):
        return

    @wraps(original)
    def wrapper(compra: dict[str, Any]) -> None:
        original(compra)
        user_id = _texto(compra.get("user_id"))
        scenario_id = _texto(compra.get("scenario_id"))
        key = pix_commerce._store_key(user_id, scenario_id)
        credits = pix_commerce._credit_store()
        credit = credits.get(key)
        if isinstance(credit, dict):
            credit["purchase_mode"] = _texto(compra.get("purchase_mode")) or "restart"
            credit["parent_session_id"] = _texto(compra.get("parent_session_id"))
            credits[key] = credit
            st.session_state["pix_mp_test_credits"] = credits

    wrapper._mary_chapter_credit_wrapped = True  # type: ignore[attr-defined]
    pix_commerce._conceder_credito = wrapper


def _available_credit(user_id: str) -> dict[str, Any] | None:
    key = pix_commerce._store_key(user_id, PAID_SCENARIO_ID)
    credit = pix_commerce._credit_store().get(key)
    if not isinstance(credit, dict):
        return None
    if _texto(credit.get("status")) != "available":
        return None
    return credit


def _patch_scenario_start(module: Any) -> None:
    original = getattr(module, "iniciar_cenario_para_usuario", None)
    if not callable(original) or getattr(original, "_mary_chapter_start_wrapped", False):
        return

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        scenario_id = _texto(kwargs.get("scenario_id"))
        user_id = _texto(kwargs.get("user_id"))
        credit = _available_credit(user_id)
        if (
            scenario_id == PAID_SCENARIO_ID
            and isinstance(credit, dict)
            and _texto(credit.get("purchase_mode")) == "continue"
            and _texto(credit.get("parent_session_id"))
        ):
            unlocked = kwargs.get("unlocked_scenario_ids")
            unlocked_ids = set(unlocked) if isinstance(unlocked, (set, list, tuple)) else set()
            unlocked_ids.add(PAID_SCENARIO_ID)
            instancia, history = _create_continuation_instance(
                user_id=user_id,
                parent_session_id=_texto(credit.get("parent_session_id")),
                unlocked_scenario_ids=unlocked_ids,
            )
            pix_commerce._marcar_credito_em_uso(instancia)
            st.session_state[_PENDING_RESTORE_KEY] = {
                "scenario_session_id": _texto(instancia.get("scenario_session_id")),
                "history": history,
            }
            st.session_state.pop(_CONTEXT_KEY, None)
            return instancia

        result = original(*args, **kwargs)
        if scenario_id == PAID_SCENARIO_ID:
            st.session_state.pop(_CONTEXT_KEY, None)
        return result

    wrapper._mary_chapter_start_wrapped = True  # type: ignore[attr-defined]
    setattr(module, "iniciar_cenario_para_usuario", wrapper)


def _patch_scenario_continue(module: Any) -> None:
    original = getattr(module, "continuar_cenario_para_usuario", None)
    if not callable(original) or getattr(original, "_mary_chapter_continue_wrapped", False):
        return

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        result = original(*args, **kwargs)
        if not isinstance(result, tuple) or not result:
            return result
        instancia = result[0]
        if not isinstance(instancia, dict):
            return result
        progress = instancia.get("story_progress")
        if not isinstance(progress, dict) or not bool(progress.get("continuation_mode")):
            return result

        user_id = _texto(instancia.get("user_id"))
        history = _mensagens_historicas(
            user_id=user_id,
            sessao=instancia,
            incluir_sessao_atual=False,
        )
        current = _mensagens_da_sessao(
            user_id=user_id,
            scenario_session_id=_texto(instancia.get("scenario_session_id")),
        )
        st.session_state[_HISTORY_KEY] = history
        st.session_state[_CURRENT_SESSION_KEY] = _texto(
            instancia.get("scenario_session_id")
        )
        return instancia, [*history, *current]

    wrapper._mary_chapter_continue_wrapped = True  # type: ignore[attr-defined]
    setattr(module, "continuar_cenario_para_usuario", wrapper)
    scenario_menu.continuar_cenario_para_usuario = wrapper


def _patch_process_interaction(module: Any) -> None:
    original = getattr(module, "processar_interacao", None)
    if not callable(original) or getattr(original, "_mary_chapter_process_wrapped", False):
        return

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        instance = st.session_state.get("scenario_instance")
        session_id = _texto(
            instance.get("scenario_session_id") if isinstance(instance, dict) else ""
        )
        history_session_id = _texto(st.session_state.get(_CURRENT_SESSION_KEY))
        history = st.session_state.get(_HISTORY_KEY)
        if (
            not session_id
            or session_id != history_session_id
            or not isinstance(history, list)
            or not history
        ):
            return original(*args, **kwargs)

        full_messages = st.session_state.get("messages")
        if not isinstance(full_messages, list):
            full_messages = []
        prefix_count = len(history)
        current_messages = full_messages[prefix_count:]
        st.session_state["messages"] = current_messages
        try:
            return original(*args, **kwargs)
        finally:
            updated_current = st.session_state.get("messages")
            if not isinstance(updated_current, list):
                updated_current = current_messages
            st.session_state["messages"] = [*history, *updated_current]

    wrapper._mary_chapter_process_wrapped = True  # type: ignore[attr-defined]
    setattr(module, "processar_interacao", wrapper)


def _restore_pending_history() -> None:
    pending = st.session_state.pop(_PENDING_RESTORE_KEY, None)
    if not isinstance(pending, dict):
        return
    history = pending.get("history")
    if not isinstance(history, list):
        history = []
    session_id = _texto(pending.get("scenario_session_id"))
    st.session_state[_HISTORY_KEY] = history
    st.session_state[_CURRENT_SESSION_KEY] = session_id
    st.session_state["messages"] = list(history)
    st.session_state["initial_message_created"] = True
    st.session_state["history_restored"] = True


def aplicar_continuacao_capitulos_pagos() -> None:
    _restore_pending_history()
    module = sys.modules.get("__main__")
    if module is None:
        return
    _patch_catalog(module)
    _patch_completed_history_listing(module)
    _patch_card_renderer()
    _patch_purchase_builder()
    _patch_credit_grant()
    _patch_scenario_start(module)
    _patch_scenario_continue(module)
    _patch_process_interaction(module)


def install_paid_chapter_continuation() -> None:
    global _INSTALLED, _ORIGINAL_TITLE
    if _INSTALLED:
        return
    _ORIGINAL_TITLE = st.title

    def patched_title(*args: Any, **kwargs: Any) -> Any:
        aplicar_continuacao_capitulos_pagos()
        assert _ORIGINAL_TITLE is not None
        return _ORIGINAL_TITLE(*args, **kwargs)

    st.title = patched_title
    _INSTALLED = True


__all__ = [
    "PAID_CHAPTER_CONTINUATION_VERSION",
    "aplicar_continuacao_capitulos_pagos",
    "install_paid_chapter_continuation",
]
