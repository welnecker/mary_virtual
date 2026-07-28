from __future__ import annotations

from dataclasses import asdict
from typing import Any
from uuid import uuid4

import streamlit as st

from catalog import StoryPackage, get_story, register_story
from commerce.story_access import StoryAccess, bind_access_to_session, consume_access
from config import APP_CAPTION, APP_TITLE, MODEL_DEFAULT
from core import StoryEngine, StoryRuntime
from core.gate_classifier import classify_gate
from openrouter_client import OpenRouterError, chamar_openrouter
from stories.casada_frustrada import package as casada_frustrada_package
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
        "v2_story_id": "",
        "v2_session": None,
        "v2_access": None,
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


def _active_package() -> StoryPackage:
    story_id = str(st.session_state.get("v2_story_id") or "").strip()
    if not story_id:
        raise RuntimeError("Nenhuma história ativa.")
    return get_story(story_id)


def _start_story(package: StoryPackage, chapter_id: str) -> None:
    access = StoryAccess(
        id=f"access_{uuid4().hex}",
        user_id="local_test_user",
        story_id=package.manifest.id,
        chapter_id=chapter_id,
        payment_id=f"test_payment_{uuid4().hex}",
    )
    session_id = f"story_session_{uuid4().hex}"
    bind_access_to_session(access, session_id=session_id)

    chapter = package.get_chapter(chapter_id)
    engine = StoryEngine()
    session = engine.start_session(
        access_id=access.id,
        story_id=package.manifest.id,
        chapter=chapter,
    )

    st.session_state["v2_story_id"] = package.manifest.id
    st.session_state["v2_access"] = access
    st.session_state["v2_session"] = session
    st.session_state["v2_messages"] = [
        {"role": "assistant", "content": engine.opening_message(chapter)}
    ]
    st.session_state["v2_error"] = ""
    st.session_state["v2_view"] = "story"
    st.rerun()


def _close_story(reason: str) -> None:
    session = st.session_state.get("v2_session")
    access = st.session_state.get("v2_access")

    if session is not None and getattr(session, "is_active", False):
        StoryEngine().close_session(session, reason=reason)
    if access is not None and getattr(access, "status", "") != "consumed":
        consume_access(access, reason=reason)

    st.session_state["v2_view"] = "catalog"
    st.session_state["v2_story_id"] = ""
    st.session_state["v2_session"] = None
    st.session_state["v2_access"] = None
    st.session_state["v2_messages"] = []
    st.session_state["v2_error"] = ""
    st.rerun()


def _send_message(user_text: str) -> None:
    package = _active_package()
    session = st.session_state["v2_session"]
    messages = list(st.session_state.get("v2_messages") or [])
    chapter = package.get_chapter(session.chapter_id)
    current_beat = chapter.beats[session.current_beat]

    gate_decision = None
    if session.current_beat_emitted and current_beat.gate:
        gate_decision = classify_gate(current_beat.gate, user_text)

    previous_messages = list(messages)
    messages.append({"role": "user", "content": user_text})

    runtime = StoryRuntime(_model_caller)
    try:
        result = runtime.respond(
            package=package,
            session=session,
            user_text=user_text,
            recent_messages=previous_messages,
            gate_decision=gate_decision,
        )
    except (OpenRouterError, ValueError, RuntimeError) as exc:
        st.session_state["v2_error"] = str(exc)
        st.session_state["v2_messages"] = messages
        st.rerun()
        return

    messages.append({"role": "assistant", "content": result.response})
    st.session_state["v2_messages"] = messages
    st.session_state["v2_session"] = result.session
    st.session_state["v2_error"] = ""

    if not result.session.is_active:
        access = st.session_state.get("v2_access")
        if access is not None and access.status != "consumed":
            consume_access(access, reason=result.session.ending_reason or "story_finished")

    st.rerun()


def _render_debug() -> None:
    with st.sidebar:
        st.header("Novo motor")
        st.text_input("Modelo", value=MODEL_DEFAULT, key="v2_model")
        st.caption("Branch: refactor/roteiro-linha-mestra")
        session = st.session_state.get("v2_session")
        access = st.session_state.get("v2_access")
        if session is not None:
            with st.expander("Estado da sessão"):
                st.json(asdict(session))
        if access is not None:
            with st.expander("Estado do acesso"):
                st.json(asdict(access))


_register_stories()
_init_state()
_render_debug()

st.caption(APP_CAPTION)
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
    render_catalog(on_start=_start_story)
