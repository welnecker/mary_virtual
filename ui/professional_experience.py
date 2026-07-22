from __future__ import annotations

import html
import json
import re
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator

import streamlit as st
import streamlit.components.v1 as components


PROFESSIONAL_EXPERIENCE_VERSION = "professional-experience-v2-risuai-voice"

_CURRENT_CHAT_ROLE: ContextVar[str] = ContextVar(
    "mary_current_chat_role",
    default="",
)
_INSTALLED = False

_ORIGINAL_TITLE = st.title
_ORIGINAL_CAPTION = st.caption
_ORIGINAL_CHAT_MESSAGE = st.chat_message
_ORIGINAL_MARKDOWN = st.markdown
_ORIGINAL_CHAT_INPUT = st.chat_input


APP_CSS = r"""
<style>
:root {
    --mary-bg: #08090d;
    --mary-panel: rgba(20, 21, 28, 0.92);
    --mary-border: rgba(255, 255, 255, 0.09);
    --mary-text: #f4f1f5;
    --mary-muted: #aaa4b1;
    --mary-accent: #d44878;
    --mary-accent-2: #a449d1;
    --mary-thought: #b9afc7;
}
.stApp {
    background:
        radial-gradient(circle at 12% 0%, rgba(164,73,209,.14), transparent 32rem),
        radial-gradient(circle at 88% 6%, rgba(212,72,120,.13), transparent 30rem),
        linear-gradient(180deg, #0b0c11 0%, var(--mary-bg) 100%);
    color: var(--mary-text);
}
[data-testid="stHeader"] {
    background: rgba(8, 9, 13, .70);
    backdrop-filter: blur(14px);
}
.block-container {
    max-width: 980px;
    padding-top: 1.6rem;
    padding-bottom: 6rem;
}
h1, h2, h3 { letter-spacing: -0.035em; }
[data-testid="stSidebar"] {
    background: rgba(12, 13, 18, .96);
    border-right: 1px solid var(--mary-border);
}
[data-testid="stChatMessage"] {
    border: 1px solid var(--mary-border);
    border-radius: 22px;
    padding: .25rem .45rem;
    margin: .75rem 0;
    background: var(--mary-panel);
    box-shadow: 0 16px 46px rgba(0,0,0,.20);
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    background: rgba(34, 35, 44, .76);
}
.mary-response {
    display: flex;
    flex-direction: column;
    gap: .62rem;
    padding: .15rem .1rem .05rem;
}
.mary-speech {
    color: var(--mary-text);
    font-size: 1.02rem;
    line-height: 1.68;
    white-space: pre-wrap;
}
.mary-thought {
    color: var(--mary-thought);
    font-family: Georgia, "Times New Roman", serif;
    font-size: .94rem;
    font-style: italic;
    line-height: 1.55;
    padding: .58rem .76rem;
    border-left: 2px solid rgba(164,73,209,.62);
    background: linear-gradient(90deg, rgba(164,73,209,.10), transparent);
    border-radius: 0 12px 12px 0;
}
.mary-story-bar {
    display: flex;
    flex-direction: column;
    gap: .16rem;
    padding: .35rem 0 .55rem;
}
.mary-story-label {
    color: var(--mary-muted);
    text-transform: uppercase;
    letter-spacing: .12em;
    font-size: .68rem;
    font-weight: 700;
}
.mary-story-title {
    color: var(--mary-text);
    font-size: 1.05rem;
    font-weight: 680;
}
.mary-catalog-hero {
    padding: 1.25rem 1.35rem;
    margin: .2rem 0 1.25rem;
    border-radius: 24px;
    border: 1px solid var(--mary-border);
    background:
        linear-gradient(120deg, rgba(212,72,120,.16), rgba(164,73,209,.10)),
        rgba(19,20,27,.82);
}
.mary-catalog-eyebrow {
    color: #df78a0;
    font-size: .70rem;
    font-weight: 750;
    letter-spacing: .14em;
    text-transform: uppercase;
}
.mary-catalog-title {
    margin-top: .24rem;
    color: var(--mary-text);
    font-size: 1.65rem;
    font-weight: 760;
    letter-spacing: -.035em;
}
.mary-catalog-copy {
    margin-top: .3rem;
    color: var(--mary-muted);
    line-height: 1.55;
}
.mary-card-shell {
    min-height: 150px;
    padding: .2rem 0 .45rem;
}
.mary-card-badge {
    display: inline-flex;
    padding: .24rem .55rem;
    border-radius: 999px;
    color: #f4c8d8;
    background: rgba(212,72,120,.16);
    border: 1px solid rgba(212,72,120,.28);
    font-size: .67rem;
    font-weight: 720;
    letter-spacing: .08em;
    text-transform: uppercase;
}
.mary-card-title {
    margin-top: .75rem;
    font-size: 1.20rem;
    font-weight: 730;
    line-height: 1.24;
}
.mary-card-copy {
    min-height: 3.2rem;
    margin-top: .42rem;
    color: var(--mary-muted);
    font-size: .91rem;
    line-height: 1.48;
}
.mary-card-access {
    margin-top: .65rem;
    color: #d7cfdb;
    font-size: .78rem;
    font-weight: 620;
}
.stButton > button {
    border-radius: 14px;
    min-height: 2.65rem;
    font-weight: 670;
    border-color: rgba(255,255,255,.10);
}
.stButton > button[kind="primary"] {
    background: linear-gradient(115deg, var(--mary-accent), var(--mary-accent-2));
    border: 0;
    box-shadow: 0 10px 28px rgba(212,72,120,.20);
}
[data-testid="stChatInput"] {
    background: rgba(14,15,20,.92);
    border: 1px solid var(--mary-border);
    border-radius: 18px;
    backdrop-filter: blur(16px);
}
@media (max-width: 720px) {
    .block-container { padding-left: .75rem; padding-right: .75rem; }
    [data-testid="stChatMessage"] { border-radius: 18px; }
}
</style>
"""


def _render_professional_shell() -> None:
    """Renderiza elementos que precisam existir novamente em cada rerun."""

    _ORIGINAL_MARKDOWN(APP_CSS, unsafe_allow_html=True)
    with st.sidebar:
        st.markdown("#### Experiência")
        st.toggle(
            "Voz de Mary",
            value=True,
            key="mary_voice_enabled",
            help="Mostra o controle de voz nas mensagens de Mary.",
        )
        st.toggle(
            "Falar automaticamente",
            value=False,
            key="mary_voice_autoplay",
            help="Lê somente falas diretas. Pensamentos não são falados.",
        )
        st.caption("A voz não lê pensamentos nem ações marcadas.")


def _is_thought_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if len(stripped) >= 3 and stripped.startswith("*") and stripped.endswith("*"):
        return True
    if len(stripped) >= 3 and stripped.startswith("(") and stripped.endswith(")"):
        return True
    return stripped.casefold().startswith(("pensamento:", "penso:", "por dentro:"))


def _clean_thought(line: str) -> str:
    text = line.strip()
    if text.startswith("*") and text.endswith("*"):
        text = text[1:-1].strip()
    if text.startswith("(") and text.endswith(")"):
        text = text[1:-1].strip()
    return re.sub(
        r"^(pensamento|penso|por dentro)\s*:\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )


def separar_resposta_mary(texto: str) -> tuple[list[tuple[str, str]], str]:
    """Separa fala e pensamento no padrão inspirado no RisuAI."""

    text = str(texto or "").strip()
    if not text:
        return [], ""

    blocks: list[tuple[str, str]] = []
    speech_buffer: list[str] = []

    def flush_speech() -> None:
        if not speech_buffer:
            return
        speech = "\n".join(speech_buffer).strip()
        speech_buffer.clear()
        if speech:
            blocks.append(("speech", speech))

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            if speech_buffer and speech_buffer[-1] != "":
                speech_buffer.append("")
            continue
        if _is_thought_line(line):
            flush_speech()
            thought = _clean_thought(line)
            if thought:
                blocks.append(("thought", thought))
        else:
            speech_buffer.append(line)

    flush_speech()
    speech_text = " ".join(
        content.replace("\n", " ")
        for kind, content in blocks
        if kind == "speech"
    )
    speech_text = re.sub(r"[*_`#>]", "", speech_text)
    speech_text = re.sub(r"\s+", " ", speech_text).strip()
    return blocks, speech_text


def _render_voice_player(text: str, *, autoplay: bool, key_seed: str) -> None:
    if not text or not st.session_state.get("mary_voice_enabled", True):
        return

    safe_text = json.dumps(text, ensure_ascii=False)
    component_key = re.sub(r"[^a-zA-Z0-9_-]", "", key_seed)[-48:] or "mary"
    autoplay_js = "speakMary();" if autoplay else ""

    components.html(
        f"""
        <div style="display:flex;align-items:center;gap:8px;margin:2px 0 0 0;">
          <button id="mary-voice-{component_key}" onclick="speakMary()"
            style="border:1px solid rgba(255,255,255,.13);background:rgba(255,255,255,.055);
                   color:#ddd7e2;border-radius:999px;padding:6px 11px;cursor:pointer;
                   font:600 12px system-ui,-apple-system,sans-serif;">▶ Ouvir Mary</button>
          <button onclick="window.speechSynthesis.cancel()"
            style="border:0;background:transparent;color:#8f8996;padding:5px;cursor:pointer;
                   font:500 11px system-ui,-apple-system,sans-serif;">parar</button>
        </div>
        <script>
          function chooseVoice() {{
            const voices = window.speechSynthesis.getVoices();
            const pt = voices.filter(v => (v.lang || '').toLowerCase().startsWith('pt'));
            return pt.find(v => /female|femin|maria|luciana|francisca|leticia|google português/i.test(v.name))
                || pt.find(v => (v.lang || '').toLowerCase() === 'pt-br')
                || pt[0] || voices[0];
          }}
          function speakMary() {{
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance({safe_text});
            utterance.lang = 'pt-BR';
            utterance.rate = 0.96;
            utterance.pitch = 1.04;
            const voice = chooseVoice();
            if (voice) utterance.voice = voice;
            window.speechSynthesis.speak(utterance);
          }}
          window.speechSynthesis.onvoiceschanged = () => {{}};
          {autoplay_js}
        </script>
        """,
        height=42,
    )


def renderizar_resposta_mary(texto: str) -> None:
    blocks, speech_text = separar_resposta_mary(texto)
    if not blocks:
        return

    parts = ['<div class="mary-response">']
    for kind, content in blocks:
        escaped = html.escape(content).replace("\n", "<br>")
        css_class = "mary-thought" if kind == "thought" else "mary-speech"
        parts.append(f'<div class="{css_class}">{escaped}</div>')
    parts.append("</div>")
    _ORIGINAL_MARKDOWN("".join(parts), unsafe_allow_html=True)

    if speech_text:
        _render_voice_player(
            speech_text,
            autoplay=bool(st.session_state.get("mary_voice_autoplay", False)),
            key_seed=str(abs(hash(texto))),
        )


def voltar_ao_catalogo() -> None:
    """Sai da tela atual sem apagar a história persistida."""

    st.session_state["scenario_instance"] = None
    st.session_state["selected_scenario_id"] = ""
    st.session_state["scenario_selector_visible"] = True
    st.session_state["messages"] = []
    st.session_state["initial_message_created"] = False
    st.session_state["history_restored"] = True
    st.session_state["pending_image"] = None
    st.session_state["pending_mary_image"] = None


def _patched_title(*args: Any, **kwargs: Any) -> Any:
    _render_professional_shell()
    return _ORIGINAL_TITLE(*args, **kwargs)


def _patched_caption(body: Any, *args: Any, **kwargs: Any) -> Any:
    text = str(body or "").strip()
    if text.startswith(("História ativa:", "História concluída:")):
        status, _, title = text.partition(":")
        left, right = st.columns([0.76, 0.24])
        with left:
            _ORIGINAL_MARKDOWN(
                '<div class="mary-story-bar">'
                f'<div class="mary-story-label">{html.escape(status)}</div>'
                f'<div class="mary-story-title">{html.escape(title.strip())}</div>'
                "</div>",
                unsafe_allow_html=True,
            )
        with right:
            if st.button(
                "← Histórias",
                key="mary_back_to_stories_top",
                use_container_width=True,
            ):
                voltar_ao_catalogo()
                st.rerun()
        return None
    return _ORIGINAL_CAPTION(body, *args, **kwargs)


@contextmanager
def _patched_chat_message(name: str, *args: Any, **kwargs: Any) -> Iterator[Any]:
    token = _CURRENT_CHAT_ROLE.set(str(name or ""))
    try:
        with _ORIGINAL_CHAT_MESSAGE(name, *args, **kwargs) as container:
            yield container
    finally:
        _CURRENT_CHAT_ROLE.reset(token)


def _patched_markdown(body: Any, *args: Any, **kwargs: Any) -> Any:
    role = _CURRENT_CHAT_ROLE.get().casefold()
    text = str(body or "")
    if (
        role in {"assistant", "ai"}
        and text.strip()
        and not kwargs.get("unsafe_allow_html", False)
    ):
        renderizar_resposta_mary(text)
        return None
    return _ORIGINAL_MARKDOWN(body, *args, **kwargs)


def _patched_chat_input(*args: Any, **kwargs: Any) -> Any:
    if isinstance(st.session_state.get("scenario_instance"), dict):
        st.caption(
            "As falas diretas podem ser ouvidas. Pensamentos aparecem em outra tipografia."
        )
    return _ORIGINAL_CHAT_INPUT(*args, **kwargs)


def install_professional_experience() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    st.title = _patched_title
    st.caption = _patched_caption
    st.chat_message = _patched_chat_message
    st.markdown = _patched_markdown
    st.chat_input = _patched_chat_input
    _INSTALLED = True


__all__ = [
    "PROFESSIONAL_EXPERIENCE_VERSION",
    "install_professional_experience",
    "renderizar_resposta_mary",
    "separar_resposta_mary",
    "voltar_ao_catalogo",
]
