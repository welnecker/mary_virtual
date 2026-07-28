from __future__ import annotations

import html
import re
from collections.abc import Callable
from typing import Any

import streamlit as st

from catalog import StoryPackage
from core import StorySession


SendMessage = Callable[[str], None]
CloseStory = Callable[[str], None]

_THOUGHT_BLOCK = re.compile(r"(?s)(\*\([^*]+?\)\*|\*[^*]+?\*)")


def _render_assistant_content(content: str) -> None:
    """Renderiza fala e pensamento de Mary como elementos visuais distintos."""
    parts = _THOUGHT_BLOCK.split(str(content or ""))
    for part in parts:
        text = part.strip()
        if not text:
            continue

        is_thought = text.startswith("*") and text.endswith("*")
        if not is_thought:
            st.markdown(text)
            continue

        thought = text[1:-1].strip()
        if thought.startswith("(") and thought.endswith(")"):
            thought = thought[1:-1].strip()

        safe = html.escape(thought).replace("\n", "<br>")
        st.markdown(
            (
                '<div style="margin:0.55rem 0;padding:0.75rem 0.9rem;'
                'border-left:4px solid #c44ed8;border-radius:0.45rem;'
                'background:rgba(196,78,216,0.10);color:#c7c8d1;'
                'font-style:italic;line-height:1.5">'
                '<span style="font-size:0.76rem;font-style:normal;'
                'font-weight:700;letter-spacing:0.04em;opacity:0.72">'
                f'PENSAMENTO DE MARY</span><br>{safe}</div>'
            ),
            unsafe_allow_html=True,
        )


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
            if role == "user":
                st.markdown(content)
            else:
                _render_assistant_content(content)

    if not session.is_active:
        st.warning("Esta execução foi encerrada. Para iniciar novamente, será necessário um novo acesso.")
        if st.button("Voltar ao catálogo", type="primary", use_container_width=True):
            on_close(session.ending_reason or "closed")
        return

    user_text = st.chat_input("Responda à Mary")
    if user_text:
        on_send(user_text)


__all__ = ["render_story"]
