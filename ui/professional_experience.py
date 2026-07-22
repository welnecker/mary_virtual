from __future__ import annotations

import html
import json
import re
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator

import streamlit as st
import streamlit.components.v1 as components


PROFESSIONAL_EXPERIENCE_VERSION = "professional-experience-v3-contrast-expressive-voice"

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

VOICE_PROFILES: dict[str, dict[str, float]] = {
    "Quente": {
        "rate": 0.87,
        "pitch": 0.92,
        "volume": 1.0,
    },
    "Viva": {
        "rate": 1.00,
        "pitch": 1.08,
        "volume": 1.0,
    },
    "Suave": {
        "rate": 0.91,
        "pitch": 1.00,
        "volume": 0.94,
    },
    "Natural": {
        "rate": 0.96,
        "pitch": 1.02,
        "volume": 1.0,
    },
}


APP_CSS = r"""
<style>
:root {
    --mary-bg: #08090d;
    --mary-panel: rgba(20, 21, 28, 0.94);
    --mary-panel-user: rgba(38, 39, 49, 0.96);
    --mary-border: rgba(255, 255, 255, 0.11);
    --mary-text: #f7f3f8;
    --mary-muted: #b9b2bf;
    --mary-accent: #d44878;
    --mary-accent-2: #a449d1;
    --mary-thought: #c9bed5;
}

html, body, .stApp {
    color: var(--mary-text) !important;
}

.stApp {
    background:
        radial-gradient(circle at 12% 0%, rgba(164,73,209,.14), transparent 32rem),
        radial-gradient(circle at 88% 6%, rgba(212,72,120,.13), transparent 30rem),
        linear-gradient(180deg, #0b0c11 0%, var(--mary-bg) 100%);
}

.stApp p,
.stApp li,
.stApp label,
.stApp h1,
.stApp h2,
.stApp h3,
.stApp h4,
.stApp h5,
.stApp h6,
.stApp [data-testid="stMarkdownContainer"] {
    color: var(--mary-text);
}

[data-testid="stHeader"] {
    background: rgba(8, 9, 13, .72);
    backdrop-filter: blur(14px);
}

.block-container {
    max-width: 980px;
    padding-top: 1.6rem;
    padding-bottom: 6rem;
}

h1, h2, h3 { letter-spacing: -0.035em; }

/* Sidebar: força contraste independentemente do tema do Streamlit. */
[data-testid="stSidebar"] {
    background: #0d0e13 !important;
    border-right: 1px solid var(--mary-border);
}

[data-testid="stSidebar"] *,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] div,
[data-testid="stSidebar"] small,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
    color: #f3eef5 !important;
}

[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p,
[data-testid="stSidebar"] .stCaption {
    color: #bdb5c3 !important;
}

/* Entradas, selects e uploads. */
.stTextInput input,
.stTextArea textarea,
[data-testid="stChatInput"] textarea,
[data-baseweb="select"] > div,
[data-baseweb="input"] input {
    color: #f7f3f8 !important;
    background-color: #171820 !important;
    -webkit-text-fill-color: #f7f3f8 !important;
    caret-color: #ffffff !important;
}

.stTextInput input::placeholder,
.stTextArea textarea::placeholder,
[data-testid="stChatInput"] textarea::placeholder {
    color: #948d9b !important;
    opacity: 1 !important;
}

[data-baseweb="popover"],
[data-baseweb="menu"],
[role="listbox"] {
    background: #171820 !important;
    color: #f7f3f8 !important;
}

[data-baseweb="menu"] *,
[role="option"] {
    color: #f7f3f8 !important;
}

/* Mensagens do chat. */
[data-testid="stChatMessage"] {
    color: var(--mary-text) !important;
    border: 1px solid var(--mary-border);
    border-radius: 22px;
    padding: .25rem .45rem;
    margin: .75rem 0;
    background: var(--mary-panel);
    box-shadow: 0 16px 46px rgba(0,0,0,.22);
}

[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] span,
[data-testid="stChatMessage"] li,
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] {
    color: #f7f3f8 !important;
}

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    background: var(--mary-panel-user) !important;
}

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) p,
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) span,
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) [data-testid="stMarkdownContainer"] {
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
}

.mary-response {
    display: flex;
    flex-direction: column;
    gap: .62rem;
    padding: .15rem .1rem .05rem;
}

.mary-speech {
    color: var(--mary-text) !important;
    -webkit-text-fill-color: var(--mary-text) !important;
    font-size: 1.02rem;
    line-height: 1.68;
    white-space: pre-wrap;
}

.mary-thought {
    color: var(--mary-thought) !important;
    -webkit-text-fill-color: var(--mary-thought) !important;
    font-family: Georgia, "Times New Roman", serif;
    font-size: .94rem;
    font-style: italic;
    line-height: 1.55;
    padding: .58rem .76rem;
    border-left: 2px solid rgba(164,73,209,.72);
    background: linear-gradient(90deg, rgba(164,73,209,.13), transparent);
    border-radius: 0 12px 12px 0;
}

.mary-story-bar {
    display: flex;
    flex-direction: column;
    gap: .16rem;
    padding: .35rem 0 .55rem;
}

.mary-story-label {
    color: var(--mary-muted) !important;
    text-transform: uppercase;
    letter-spacing: .12em;
    font-size: .68rem;
    font-weight: 700;
}

.mary-story-title {
    color: var(--mary-text) !important;
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
        rgba(19,20,27,.88);
}

.mary-catalog-eyebrow {
    color: #e681a8 !important;
    font-size: .70rem;
    font-weight: 750;
    letter-spacing: .14em;
    text-transform: uppercase;
}

.mary-catalog-title {
    margin-top: .24rem;
    color: var(--mary-text) !important;
    font-size: 1.65rem;
    font-weight: 760;
    letter-spacing: -.035em;
}

.mary-catalog-copy {
    margin-top: .3rem;
    color: var(--mary-muted) !important;
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
    color: #f4c8d8 !important;
    background: rgba(212,72,120,.16);
    border: 1px solid rgba(212,72,120,.28);
    font-size: .67rem;
    font-weight: 720;
    letter-spacing: .08em;
    text-transform: uppercase;
}

.mary-card-title {
    margin-top: .75rem;
    color: #ffffff !important;
    font-size: 1.20rem;
    font-weight: 730;
    line-height: 1.24;
}

.mary-card-copy {
    min-height: 3.2rem;
    margin-top: .42rem;
    color: var(--mary-muted) !important;
    font-size: .91rem;
    line-height: 1.48;
}

.mary-card-access {
    margin-top: .65rem;
    color: #ddd5e0 !important;
    font-size: .78rem;
    font-weight: 620;
}

.stButton > button {
    color: #f8f4f9 !important;
    background: #20212a !important;
    border-radius: 14px;
    min-height: 2.65rem;
    font-weight: 670;
    border: 1px solid rgba(255,255,255,.14) !important;
}

.stButton > button p,
.stButton > button span {
    color: #f8f4f9 !important;
}

.stButton > button[kind="primary"] {
    color: #ffffff !important;
    background: linear-gradient(115deg, var(--mary-accent), var(--mary-accent-2)) !important;
    border: 0 !important;
    box-shadow: 0 10px 28px rgba(212,72,120,.22);
}

[data-testid="stChatInput"] {
    color: #ffffff !important;
    background: rgba(14,15,20,.96);
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
        st.selectbox(
            "Interpretação da voz",
            options=list(VOICE_PROFILES),
            index=0,
            key="mary_voice_profile",
            help=(
                "Quente é mais lenta e grave; Viva é mais energética; "
                "Suave é delicada; Natural preserva um ritmo neutro."
            ),
        )
        st.toggle(
            "Falar automaticamente",
            value=False,
            key="mary_voice_autoplay",
            help="Lê somente falas diretas. Pensamentos não são falados.",
        )
        st.caption(
            "A qualidade e o timbre dependem das vozes femininas instaladas no navegador."
        )


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


def _obter_configuracao_voz() -> tuple[str, dict[str, float]]:
    profile_name = str(
        st.session_state.get("mary_voice_profile", "Quente")
        or "Quente"
    ).strip()
    profile = VOICE_PROFILES.get(profile_name, VOICE_PROFILES["Quente"])
    return profile_name, profile


def _render_voice_player(text: str, *, autoplay: bool, key_seed: str) -> None:
    if not text or not st.session_state.get("mary_voice_enabled", True):
        return

    profile_name, profile = _obter_configuracao_voz()
    safe_text = json.dumps(text, ensure_ascii=False)
    safe_profile_name = html.escape(profile_name)
    component_key = re.sub(r"[^a-zA-Z0-9_-]", "", key_seed)[-48:] or "mary"
    autoplay_js = "speakMary();" if autoplay else ""
    rate = float(profile["rate"])
    pitch = float(profile["pitch"])
    volume = float(profile["volume"])

    components.html(
        f"""
        <div style="display:flex;align-items:center;gap:8px;margin:2px 0 0 0;">
          <button id="mary-voice-{component_key}" onclick="speakMary()"
            title="Interpretação: {safe_profile_name}"
            style="border:1px solid rgba(255,255,255,.15);background:rgba(255,255,255,.07);
                   color:#f1eaf3;border-radius:999px;padding:6px 11px;cursor:pointer;
                   font:600 12px system-ui,-apple-system,sans-serif;">
            ▶ Ouvir Mary · {safe_profile_name}
          </button>
          <button onclick="window.speechSynthesis.cancel()"
            style="border:0;background:transparent;color:#a8a0ad;padding:5px;cursor:pointer;
                   font:500 11px system-ui,-apple-system,sans-serif;">parar</button>
        </div>
        <script>
          function chooseVoice() {{
            const voices = window.speechSynthesis.getVoices();
            const pt = voices.filter(v => (v.lang || '').toLowerCase().startsWith('pt'));
            const preferred = [
              /Microsoft Francisca/i,
              /Francisca/i,
              /Microsoft Maria/i,
              /Luciana/i,
              /Leticia/i,
              /Google Português do Brasil/i,
              /Google português/i,
              /female|feminina|feminino/i
            ];
            for (const pattern of preferred) {{
              const found = pt.find(v => pattern.test(v.name || ''));
              if (found) return found;
            }}
            return pt.find(v => (v.lang || '').toLowerCase() === 'pt-br')
                || pt[0]
                || voices[0];
          }}
          function speakMary() {{
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance({safe_text});
            utterance.lang = 'pt-BR';
            utterance.rate = {rate};
            utterance.pitch = {pitch};
            utterance.volume = {volume};
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
    "VOICE_PROFILES",
    "install_professional_experience",
    "renderizar_resposta_mary",
    "separar_resposta_mary",
    "voltar_ao_catalogo",
]
