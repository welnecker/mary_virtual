from __future__ import annotations

from typing import Any, Callable

import streamlit as st


CONTRAST_ACCESSIBILITY_VERSION = "contrast-accessibility-v1-dark-inputs"

_INSTALLED = False
_ORIGINAL_TITLE: Callable[..., Any] | None = None


CONTRAST_CSS = r"""
<style>
:root {
    --mary-input-bg: #15161d;
    --mary-input-bg-strong: #0f1016;
    --mary-input-border: rgba(255, 255, 255, 0.18);
    --mary-input-border-focus: #d44878;
    --mary-input-text: #ffffff;
    --mary-input-muted: #aaa3b0;
}

/* Inputs comuns, inclusive login e campos BaseWeb internos. */
.stTextInput input,
.stTextArea textarea,
[data-baseweb="input"] input,
[data-baseweb="textarea"] textarea,
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {
    color: var(--mary-input-text) !important;
    -webkit-text-fill-color: var(--mary-input-text) !important;
    caret-color: var(--mary-input-text) !important;
    background: var(--mary-input-bg) !important;
}

.stTextInput > div > div,
.stTextArea > div > div,
[data-testid="stTextInput"] > div > div,
[data-testid="stTextArea"] > div > div,
[data-baseweb="input"],
[data-baseweb="textarea"] {
    color: var(--mary-input-text) !important;
    background: var(--mary-input-bg) !important;
    border-color: var(--mary-input-border) !important;
}

.stTextInput input::placeholder,
.stTextArea textarea::placeholder,
[data-testid="stTextInput"] input::placeholder,
[data-testid="stTextArea"] textarea::placeholder {
    color: var(--mary-input-muted) !important;
    -webkit-text-fill-color: var(--mary-input-muted) !important;
    opacity: 1 !important;
}

/* Selectbox: corrige texto branco sobre superfície branca. */
[data-testid="stSelectbox"] [data-baseweb="select"] > div,
[data-testid="stSelectbox"] [data-baseweb="select"] div,
[data-baseweb="select"] > div {
    color: var(--mary-input-text) !important;
    -webkit-text-fill-color: var(--mary-input-text) !important;
    background-color: var(--mary-input-bg) !important;
    border-color: var(--mary-input-border) !important;
}

[data-testid="stSelectbox"] [data-baseweb="select"] span,
[data-testid="stSelectbox"] [data-baseweb="select"] input,
[data-testid="stSelectbox"] svg {
    color: var(--mary-input-text) !important;
    fill: var(--mary-input-text) !important;
    -webkit-text-fill-color: var(--mary-input-text) !important;
}

[data-baseweb="popover"],
[data-baseweb="menu"],
[role="listbox"],
[role="option"] {
    color: var(--mary-input-text) !important;
    background: #181922 !important;
}

[role="option"]:hover,
[role="option"][aria-selected="true"] {
    background: #2a2c38 !important;
}

/* Quadro de upload de fotografia. */
[data-testid="stFileUploader"],
[data-testid="stFileUploaderDropzone"],
[data-testid="stFileUploaderDropzone"] > div {
    color: var(--mary-input-text) !important;
    background: var(--mary-input-bg-strong) !important;
    border-color: var(--mary-input-border) !important;
}

[data-testid="stFileUploader"] *,
[data-testid="stFileUploaderDropzone"] *,
[data-testid="stFileUploaderDropzone"] span,
[data-testid="stFileUploaderDropzone"] small {
    color: var(--mary-input-text) !important;
    -webkit-text-fill-color: var(--mary-input-text) !important;
}

[data-testid="stFileUploaderDropzone"] small {
    color: var(--mary-input-muted) !important;
    -webkit-text-fill-color: var(--mary-input-muted) !important;
}

[data-testid="stFileUploaderDropzone"] button {
    color: #ffffff !important;
    background: #292b36 !important;
    border: 1px solid var(--mary-input-border) !important;
}

/* Barra inferior e caixa onde o usuário escreve o prompt. */
[data-testid="stBottomBlockContainer"],
[data-testid="stBottom"],
.stChatFloatingInputContainer {
    background: linear-gradient(
        180deg,
        rgba(8, 9, 13, 0) 0%,
        rgba(8, 9, 13, 0.94) 22%,
        #08090d 100%
    ) !important;
}

[data-testid="stChatInput"],
[data-testid="stChatInput"] > div,
[data-testid="stChatInput"] [data-baseweb="textarea"],
[data-testid="stChatInput"] [data-baseweb="base-input"] {
    color: var(--mary-input-text) !important;
    background: #111219 !important;
    border-color: var(--mary-input-border) !important;
}

[data-testid="stChatInput"] textarea {
    color: var(--mary-input-text) !important;
    -webkit-text-fill-color: var(--mary-input-text) !important;
    caret-color: #ffffff !important;
    background: #111219 !important;
}

[data-testid="stChatInput"] textarea::placeholder {
    color: var(--mary-input-muted) !important;
    -webkit-text-fill-color: var(--mary-input-muted) !important;
    opacity: 1 !important;
}

[data-testid="stChatInput"] button,
[data-testid="stChatInput"] svg {
    color: #ffffff !important;
    fill: #ffffff !important;
}

/* Foco visível para teclado e digitação. */
.stTextInput input:focus,
.stTextArea textarea:focus,
[data-testid="stChatInput"] textarea:focus,
[data-baseweb="input"]:focus-within,
[data-baseweb="select"] > div:focus-within,
[data-testid="stFileUploaderDropzone"]:focus-within {
    border-color: var(--mary-input-border-focus) !important;
    box-shadow: 0 0 0 1px var(--mary-input-border-focus) !important;
    outline: none !important;
}

/* Evita que o preenchimento automático do navegador volte ao branco. */
input:-webkit-autofill,
input:-webkit-autofill:hover,
input:-webkit-autofill:focus,
textarea:-webkit-autofill {
    -webkit-text-fill-color: var(--mary-input-text) !important;
    -webkit-box-shadow: 0 0 0 1000px var(--mary-input-bg) inset !important;
    box-shadow: 0 0 0 1000px var(--mary-input-bg) inset !important;
    caret-color: #ffffff !important;
}
</style>
"""


def aplicar_contraste_acessivel() -> None:
    st.markdown(CONTRAST_CSS, unsafe_allow_html=True)


def install_contrast_accessibility() -> None:
    global _INSTALLED, _ORIGINAL_TITLE
    if _INSTALLED:
        return

    _ORIGINAL_TITLE = st.title

    def patched_title(*args: Any, **kwargs: Any) -> Any:
        aplicar_contraste_acessivel()
        assert _ORIGINAL_TITLE is not None
        return _ORIGINAL_TITLE(*args, **kwargs)

    st.title = patched_title
    _INSTALLED = True


__all__ = [
    "CONTRAST_ACCESSIBILITY_VERSION",
    "aplicar_contraste_acessivel",
    "install_contrast_accessibility",
]
