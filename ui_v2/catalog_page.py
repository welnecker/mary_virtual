from __future__ import annotations

from collections.abc import Callable

import streamlit as st

from catalog import StoryPackage, list_stories


StartStory = Callable[[StoryPackage, str], None]


def _format_price(price_cents: int, currency: str) -> str:
    if currency.upper() == "BRL":
        value = price_cents / 100
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{currency.upper()} {price_cents / 100:.2f}"


def render_catalog(*, on_start: StartStory) -> None:
    st.title("Catálogo de histórias")
    st.caption("Cada card é uma história independente. Uma nova execução exige um novo acesso.")

    packages = list_stories()
    if not packages:
        st.info("Nenhuma história ativa foi registrada.")
        return

    columns = st.columns(2)
    for index, package in enumerate(packages):
        manifest = package.manifest
        with columns[index % len(columns)]:
            with st.container(border=True):
                if manifest.card_image:
                    try:
                        st.image(manifest.card_image, use_container_width=True)
                    except Exception:
                        st.caption("Imagem do card ainda não disponível.")
                st.subheader(manifest.title)
                st.write(manifest.description)
                st.caption(f"{len(manifest.chapter_ids)} capítulo(s)")
                st.markdown(f"**{_format_price(manifest.price_cents, manifest.currency)}**")

                chapter_id = st.selectbox(
                    "Capítulo",
                    options=list(manifest.chapter_ids),
                    key=f"chapter_{manifest.id}",
                )
                if st.button(
                    "Iniciar teste",
                    key=f"start_{manifest.id}",
                    type="primary",
                    use_container_width=True,
                ):
                    on_start(package, chapter_id)


__all__ = ["render_catalog"]
