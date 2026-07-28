from __future__ import annotations

from collections.abc import Callable
from typing import Any

import streamlit as st

from catalog import StoryPackage
from core import StorySession


SendMessage = Callable[[str], None]
CloseStory = Callable[[str], None]


def render_story(
    *,
    package: StoryPackage,
    session: StorySession,
    messages: list[dict[str, Any]],
    on_send: SendMessage,
    on_close: CloseStory,
) -> None:
    manifest = package.manifest
    chapter = package.get_chapter(session.chapter_id)

    header_left, header_right = st.columns([4, 1])
    with header_left:
        st.title(manifest.title)
        st.caption(
            f"{chapter.title} · Beat atual: {session.current_beat} · "
            f"Interações: {max(0, int(session.turn_count or 0))}"
        )
    with header_right:
        if st.button("Desistir", use_container_width=True):
            on_close("user_abandoned")

    for message in messages:
        role = str(message.get("role") or "assistant")
        content = str(message.get("content") or "").strip()
        if not content:
            continue
        with st.chat_message("user" if role == "user" else "assistant"):
            st.markdown(content)

    if not session.is_active:
        st.warning("Esta execução foi encerrada. Para iniciar novamente, será necessário um novo acesso.")
        if st.button("Voltar ao catálogo", type="primary", use_container_width=True):
            on_close(session.ending_reason or "closed")
        return

    user_text = st.chat_input("Responda à Mary")
    if user_text:
        try:
            on_send(user_text)
        except Exception as exc:
            st.error(
                "Falha ao processar o turno: "
                f"{type(exc).__name__}: {exc}"
            )
            st.exception(exc)


__all__ = ["render_story"]
