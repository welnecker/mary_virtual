from __future__ import annotations

from dataclasses import asdict
from time import perf_counter
from typing import Any

import streamlit as st

from auth.service import AuthenticationError
from catalog import StoryPackage, get_story, register_story
from config import APP_CAPTION, APP_TITLE, APP_VERSION, MODEL_DEFAULT, PROMPT_VERSION
from core import StoryEngine, StoryRuntime
from core.gate_classifier import classify_gate
from google_sheets_repository import GoogleSheetsRepositoryError, atualizar_registro, utc_now_iso
from openrouter_client import OpenRouterError, chamar_openrouter
from persistence import (
    create_runtime_session,
    create_story_session,
    finish_runtime_session,
    load_catalog_overrides,
    persist_interaction,
    persist_story_session,
)
from stories.casada_frustrada import package as casada_frustrada_package
from ui.login import AUTH_ACTION_REGISTER, renderizar_tela_login
from ui_v2 import render_catalog, render_story

st.set_page_config(page_title=f"{APP_TITLE} · Novo motor", page_icon="💬", layout="centered")


def _register_stories() -> None:
    try:
        get_story(casada_frustrada_package.manifest.id)
    except KeyError:
        register_story(casada_frustrada_package)


def _init_state() -> None:
    defaults: dict[str, Any] = {
        "v2_view": "catalog",
        "v2_user": None,
        "v2_runtime_session": None,
        "v2_catalog_rows": {},
        "v2_story_id": "",
        "v2_session": None,
        "v2_scenario_instance": None,
        "v2_messages": [],
        "v2_error": "",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def _model_caller(system_prompt: str, messages: list[dict[str, Any]]) -> str:
    api_key = str(st.secrets.get("OPENROUTER_API_KEY", "") or "").strip()
    model = str(st.session_state.get("v2_model") or MODEL_DEFAULT).strip()
    payload = [{"role": "system", "content": system_prompt}, *messages]
    return chamar_openrouter(
        messages=payload,
        model=model,
        api_key=api_key,
        temperature=0.75,
        max_tokens=450,
    )


def _active_user() -> dict[str, Any]:
    user = st.session_state.get("v2_user")
    if not isinstance(user, dict) or not str(user.get("user_id") or "").strip():
        raise RuntimeError("Usuário não autenticado.")
    return user


def _active_runtime_session() -> dict[str, Any]:
    session = st.session_state.get("v2_runtime_session")
    if not isinstance(session, dict) or not str(session.get("session_id") or "").strip():
        raise RuntimeError("Sessão técnica não iniciada.")
    return session


def _active_package() -> StoryPackage:
    story_id = str(st.session_state.get("v2_story_id") or "").strip()
    if not story_id:
        raise RuntimeError("Nenhuma história ativa.")
    return get_story(story_id)


def _authenticate() -> bool:
    if isinstance(st.session_state.get("v2_user"), dict):
        return True

    result = renderizar_tela_login(
        titulo="Entre para acessar as histórias",
        descricao="Sua conta, sessões e interações serão registradas nas planilhas do projeto.",
    )
    if result is None:
        return False

    user = result.get("user") if isinstance(result, dict) else None
    if not isinstance(user, dict):
        st.error("O login não retornou um usuário válido.")
        return False

    user_id = str(user.get("user_id") or "").strip()
    if not user_id:
        st.error("A conta não possui user_id.")
        return False

    if result.get("action") == AUTH_ACTION_REGISTER:
        now = utc_now_iso()
        atualizar_registro(
            "USERS",
            coluna_chave="user_id",
            valor_chave=user_id,
            alteracoes={
                "adult_confirmed_at": now,
                "adult_confirmation_version": 1,
                "auth_version": 1,
                "password_changed_at": now,
                "failed_login_count": 0,
                "active": True,
                "updated_at": now,
            },
        )

    runtime_session = create_runtime_session(
        user_id=user_id,
        model=str(st.session_state.get("v2_model") or MODEL_DEFAULT),
        prompt_version=PROMPT_VERSION,
        app_version=APP_VERSION,
    )
    catalog_rows = load_catalog_overrides()

    st.session_state["v2_user"] = user
    st.session_state["v2_runtime_session"] = runtime_session
    st.session_state["v2_catalog_rows"] = catalog_rows
    st.session_state["v2_error"] = ""
    st.rerun()
    return False


def _logout() -> None:
    runtime = st.session_state.get("v2_runtime_session")
    if isinstance(runtime, dict) and str(runtime.get("session_id") or "").strip():
        finish_runtime_session(runtime["session_id"], reason="logout")
    for key in (
        "v2_user",
        "v2_runtime_session",
        "v2_story_id",
        "v2_session",
        "v2_scenario_instance",
    ):
        st.session_state[key] = None if key != "v2_story_id" else ""
    st.session_state["v2_messages"] = []
    st.session_state["v2_catalog_rows"] = {}
    st.session_state["v2_view"] = "catalog"
    st.session_state["v2_error"] = ""
    st.rerun()


def _start_story(package: StoryPackage, chapter_id: str) -> None:
    user = _active_user()
    runtime = _active_runtime_session()
    chapter = package.get_chapter(chapter_id)
    engine = StoryEngine()
    story_session = engine.start_session(
        access_id="",
        story_id=package.manifest.id,
        chapter=chapter,
    )

    row = dict(st.session_state.get("v2_catalog_rows", {}).get(package.manifest.id, {}))
    scenario_version = int(float(row.get("scenario_version") or 1))
    scenario_instance = create_story_session(
        engine_session=story_session,
        user_id=str(user["user_id"]),
        scenario_version=scenario_version,
        opening_sent=True,
    )

    atualizar_registro(
        "SESSIONS",
        coluna_chave="session_id",
        valor_chave=str(runtime["session_id"]),
        alteracoes={
            "last_activity_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
            "last_scenario_id": package.manifest.id,
            "last_scenario_session_id": scenario_instance["scenario_session_id"],
        },
    )

    st.session_state["v2_story_id"] = package.manifest.id
    st.session_state["v2_session"] = story_session
    st.session_state["v2_scenario_instance"] = scenario_instance
    st.session_state["v2_messages"] = [
        {"role": "assistant", "content": engine.opening_message(chapter)}
    ]
    st.session_state["v2_error"] = ""
    st.session_state["v2_view"] = "story"
    st.rerun()


def _close_story(reason: str) -> None:
    session = st.session_state.get("v2_session")
    instance = st.session_state.get("v2_scenario_instance")
    if session is not None and getattr(session, "is_active", False):
        StoryEngine().close_session(session, reason=reason)
    if session is not None and isinstance(instance, dict):
        persist_story_session(
            instance=instance,
            engine_session=session,
            interaction_happened=False,
        )

    st.session_state["v2_view"] = "catalog"
    st.session_state["v2_story_id"] = ""
    st.session_state["v2_session"] = None
    st.session_state["v2_scenario_instance"] = None
    st.session_state["v2_messages"] = []
    st.session_state["v2_error"] = ""
    st.rerun()


def _send_message(user_text: str) -> None:
    user = _active_user()
    runtime_session = _active_runtime_session()
    package = _active_package()
    story_session = st.session_state["v2_session"]
    scenario_instance = st.session_state["v2_scenario_instance"]
    messages = list(st.session_state.get("v2_messages") or [])
    chapter = package.get_chapter(story_session.chapter_id)
    current_beat = chapter.beats[story_session.current_beat]

    gate_decision = None
    if story_session.current_beat_emitted and current_beat.gate:
        gate_decision = classify_gate(current_beat.gate, user_text)

    previous_messages = list(messages)
    messages.append({"role": "user", "content": user_text})
    started = perf_counter()
    runtime = StoryRuntime(_model_caller)

    try:
        result = runtime.respond(
            package=package,
            session=story_session,
            user_text=user_text,
            recent_messages=previous_messages,
            gate_decision=gate_decision,
        )
    except (OpenRouterError, ValueError, RuntimeError) as exc:
        st.session_state["v2_error"] = str(exc)
        st.session_state["v2_messages"] = messages
        st.rerun()
        return

    response_time_ms = int((perf_counter() - started) * 1000)
    messages.append({"role": "assistant", "content": result.response})

    scenario_instance["interaction_count"] = int(
        float(scenario_instance.get("interaction_count") or 0)
    ) + 1
    persist_story_session(
        instance=scenario_instance,
        engine_session=result.session,
        route=result.plan.route,
        interaction_happened=True,
    )
    persist_interaction(
        runtime_session_id=str(runtime_session["session_id"]),
        user_id=str(user["user_id"]),
        scenario_instance=scenario_instance,
        user_text=user_text,
        mary_response=result.response,
        model=str(st.session_state.get("v2_model") or MODEL_DEFAULT),
        prompt_version=PROMPT_VERSION,
        app_version=APP_VERSION,
        response_time_ms=response_time_ms,
        scenario_beat=result.plan.beat_id,
        scenario_route=result.plan.route,
        scenario_status=result.session.status,
        scenario_completed=not result.session.is_active,
    )

    st.session_state["v2_messages"] = messages
    st.session_state["v2_session"] = result.session
    st.session_state["v2_scenario_instance"] = scenario_instance
    st.session_state["v2_error"] = ""
    st.rerun()


def _render_sidebar() -> None:
    with st.sidebar:
        st.header("Novo motor")
        st.text_input("Modelo", value=MODEL_DEFAULT, key="v2_model")
        user = st.session_state.get("v2_user")
        if isinstance(user, dict):
            st.caption(str(user.get("preferred_name") or user.get("email") or user.get("user_id")))
            if st.button("Sair", use_container_width=True):
                _logout()
        session = st.session_state.get("v2_session")
        instance = st.session_state.get("v2_scenario_instance")
        if session is not None:
            with st.expander("Estado do motor"):
                st.json(asdict(session))
        if isinstance(instance, dict):
            with st.expander("SCENARIO_SESSIONS"):
                st.json(instance)


_register_stories()
_init_state()
_render_sidebar()
st.caption(APP_CAPTION)

try:
    authenticated = _authenticate()
except (AuthenticationError, GoogleSheetsRepositoryError, ValueError, RuntimeError) as exc:
    st.error(str(exc))
    authenticated = False

if authenticated:
    error = str(st.session_state.get("v2_error") or "").strip()
    if error:
        st.error(error)

    if st.session_state["v2_view"] == "story" and st.session_state.get("v2_session") is not None:
        render_story(
            package=_active_package(),
            session=st.session_state["v2_session"],
            messages=list(st.session_state.get("v2_messages") or []),
            on_send=_send_message,
            on_close=_close_story,
        )
    else:
        render_catalog(
            on_start=_start_story,
            catalog_rows=st.session_state.get("v2_catalog_rows") or {},
        )
