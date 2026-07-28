from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

import streamlit as st

from catalog import StoryPackage, list_stories
from persistence import catalog_story_state

StartStory = Callable[[StoryPackage, str], None]
ContinueStory = Callable[[StoryPackage, Mapping[str, Any]], None]


def _text(value: Any) -> str:
    return str(value or "").strip()


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value if value not in (None, "") else default))
    except (TypeError, ValueError):
        return default


def _format_price(price_cents: int, currency: str) -> str:
    if currency.upper() == "BRL":
        value = price_cents / 100
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{currency.upper()} {price_cents / 100:.2f}"


def render_catalog(
    *,
    on_start: StartStory,
    on_continue: ContinueStory,
    catalog_rows: Mapping[str, Mapping[str, Any]] | None = None,
    story_sessions: Mapping[str, Mapping[str, Any]] | None = None,
) -> None:
    st.title("Catálogo de histórias")
    st.caption("Cada card é uma história independente, com roteiro e Mary próprios.")

    rows = dict(catalog_rows or {})
    sessions = dict(story_sessions or {})
    packages = list_stories()
    if not packages:
        st.info("Nenhuma história ativa foi registrada no código.")
        return

    visible: list[tuple[StoryPackage, Mapping[str, Any]]] = []
    for package in packages:
        row = rows.get(package.manifest.id)
        if rows and row is None:
            continue
        visible.append((package, row or {}))

    if not visible:
        st.info("Nenhuma história publicada em SCENARIOS possui pacote de roteiro registrado.")
        return

    visible.sort(
        key=lambda item: (
            _int(item[1].get("display_order"), 999),
            _text(item[1].get("card_title") or item[1].get("title") or item[0].manifest.title).casefold(),
        )
    )

    columns = st.columns(2)
    for index, (package, row) in enumerate(visible):
        manifest = package.manifest
        title = _text(row.get("card_title") or row.get("title")) or manifest.title
        description = _text(row.get("card_subtitle") or row.get("short_description")) or manifest.description
        image = _text(row.get("card_image")) or manifest.card_image
        price_cents = _int(row.get("price_cents"), manifest.price_cents)
        currency = _text(row.get("currency")) or manifest.currency
        access_type = (_text(row.get("access_type")) or "paid").lower()
        session_row = sessions.get(manifest.id)
        card_state = catalog_story_state(dict(session_row) if isinstance(session_row, Mapping) else None)

        with columns[index % len(columns)]:
            with st.container(border=True):
                if image:
                    try:
                        st.image(image, use_container_width=True)
                    except Exception:
                        st.caption("Imagem do card indisponível.")
                st.subheader(title)
                st.write(description)
                badge = _text(row.get("card_badge"))
                if badge:
                    st.caption(badge)
                st.caption(f"{len(manifest.chapter_ids)} história completa")
                if access_type == "free":
                    st.markdown("**Gratuito**")
                else:
                    st.markdown(f"**{_format_price(price_cents, currency)}**")

                chapter_id = manifest.chapter_ids[0]
                if card_state == "active" and isinstance(session_row, Mapping):
                    current_beat = _text(session_row.get("current_beat"))
                    st.caption(
                        f"Em andamento{f' · {current_beat}' if current_beat else ''}"
                    )
                    if st.button(
                        _text(row.get("button_label_unlocked")) or "Continuar",
                        key=f"continue_{manifest.id}",
                        type="primary",
                        use_container_width=True,
                    ):
                        on_continue(package, session_row)
                elif card_state == "finished":
                    st.caption("Execução anterior encerrada")
                    if st.button(
                        "Recomeçar",
                        key=f"restart_{manifest.id}",
                        type="primary",
                        use_container_width=True,
                    ):
                        on_start(package, chapter_id)
                else:
                    button_label = _text(
                        row.get("button_label_free")
                        if access_type == "free"
                        else row.get("button_label_unlocked")
                    ) or "Começar"
                    if st.button(
                        button_label,
                        key=f"start_{manifest.id}",
                        type="primary",
                        use_container_width=True,
                    ):
                        on_start(package, chapter_id)


__all__ = ["render_catalog"]
