from __future__ import annotations

import html
import json
import re
from typing import Any

import streamlit as st

import ui.app_runtime_integration as app_runtime
import ui.professional_experience as professional
from repositories.scenario_rollback_repository import apagar_ultimos_turnos_cenario


SIDEBAR_ROLLBACK_THOUGHT_STYLE_VERSION = (
    "sidebar-rollback-thought-style-v3-first-person-only"
)
_INSTALLED = False


def _text(value: Any) -> str:
    return str(value or "").strip()


def _render_rollback_controls_sidebar() -> None:
    if st.session_state.get("_mary_rollback_rendered"):
        return
    st.session_state["_mary_rollback_rendered"] = True

    instance = st.session_state.get("scenario_instance")
    if not isinstance(instance, dict):
        return
    if _text(instance.get("status")).lower() == "completed":
        return

    total = max(0, app_runtime._safe_int(instance.get("interaction_count"), 0))
    session_id = _text(instance.get("scenario_session_id"))
    user_id = app_runtime._resolver_usuario_atual()
    if total < 1 or not session_id or not user_id:
        return

    original_button = app_runtime._ORIGINAL_BUTTON
    if not callable(original_button):
        return

    with st.sidebar.expander("Corrigir últimos turnos", expanded=False):
        st.caption(
            "Remove os últimos turnos da história e sincroniza as abas "
            "INTERACTIONS e SCENARIO_SESSIONS."
        )
        quantity = int(
            st.number_input(
                "Quantidade de turnos",
                min_value=1,
                max_value=min(20, total),
                value=1,
                step=1,
                key="scenario_rollback_quantity",
            )
        )

        pending = bool(st.session_state.get("scenario_rollback_pending"))
        if not pending:
            if original_button(
                f"Apagar últimos {quantity} turno(s)",
                key="scenario_rollback_request",
                use_container_width=True,
            ):
                st.session_state["scenario_rollback_pending"] = True
                st.rerun()
            return

        st.warning(
            f"Isso apagará definitivamente os últimos {quantity} turno(s) "
            "desta história e fará a contagem recuar."
        )
        confirm_col, cancel_col = st.columns(2)
        with confirm_col:
            confirmed = original_button(
                "Confirmar exclusão",
                key="scenario_rollback_confirm",
                type="primary",
                use_container_width=True,
            )
        with cancel_col:
            cancelled = original_button(
                "Cancelar",
                key="scenario_rollback_cancel",
                use_container_width=True,
            )

        if cancelled:
            st.session_state.pop("scenario_rollback_pending", None)
            st.rerun()

        if confirmed:
            with st.spinner("Recuando a história e sincronizando os dados..."):
                result = apagar_ultimos_turnos_cenario(
                    user_id=user_id,
                    scenario_session_id=session_id,
                    quantidade=quantity,
                )

            session = result.get("session")
            if isinstance(session, dict):
                session["scenario_config"] = instance.get("scenario_config", {})
                st.session_state["scenario_instance"] = session

            messages = result.get("messages")
            if isinstance(messages, list):
                st.session_state["messages"] = messages

            st.session_state["history_restored"] = True
            st.session_state["initial_message_created"] = bool(messages)
            st.session_state.pop("scenario_rollback_pending", None)
            st.session_state.pop("scenario_finish_confirmation_pending", None)
            st.session_state["mensagem_operacao_persistente"] = (
                f"{result.get('deleted_turns', 0)} turno(s) removido(s). "
                f"A história voltou para {result.get('remaining_turns', 0)} interação(ões)."
            )
            st.rerun()


def _normalize_label(line: str) -> str:
    return line.strip().strip('"“”')


def _is_thought_line(line: str) -> bool:
    text = _normalize_label(line)
    if not text:
        return False
    return bool(
        re.match(
            r"^pensamento\s+de\s+mary\s*:\s*.+$",
            text,
            flags=re.IGNORECASE,
        )
    )


def _clean_thought(line: str) -> str:
    return re.sub(
        r"^pensamento\s+de\s+mary\s*:\s*",
        "",
        _normalize_label(line),
        flags=re.IGNORECASE,
    ).strip()


def _is_forbidden_narration(line: str) -> bool:
    text = _normalize_label(line)
    if not text:
        return False
    return bool(
        re.match(
            r"^(ponte\s+de\s+cena|ponte|transi[cç][aã]o|narra[cç][aã]o)\s*:",
            text,
            flags=re.IGNORECASE,
        )
        or re.match(
            r"^(mary|ela|a\s+morena|a\s+mulher)\s+"
            r"(olha|encosta|mexe|passa|fecha|abre|caminha|sorri|respira|fica|se\s+aproxima|se\s+afasta)\b",
            text,
            flags=re.IGNORECASE,
        )
    )


def _separar_resposta_mary(texto: str) -> tuple[list[tuple[str, str]], str]:
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
        elif _is_forbidden_narration(line):
            flush_speech()
            continue
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


def _render_response(texto: str) -> None:
    blocks, speech_text = _separar_resposta_mary(texto)
    if not blocks:
        return

    parts = ['<div class="mary-response">']
    for kind, content in blocks:
        escaped = html.escape(content).replace("\n", "<br>")
        if kind == "thought":
            parts.append(
                '<div class="mary-thought">'
                '<div style="font:700 .66rem system-ui;letter-spacing:.12em;'
                'text-transform:uppercase;color:#ad93c4;margin-bottom:.28rem;">'
                'Pensamento de Mary</div>'
                f'{escaped}</div>'
            )
        else:
            parts.append(f'<div class="mary-speech">{escaped}</div>')
    parts.append("</div>")
    professional._ORIGINAL_MARKDOWN("".join(parts), unsafe_allow_html=True)

    if speech_text:
        professional._render_voice_player(
            speech_text,
            autoplay=bool(st.session_state.get("mary_voice_autoplay", False)),
            key_seed=str(abs(hash(texto))),
        )


def _render_voice_player_dark(text: str, *, autoplay: bool, key_seed: str) -> None:
    if not text or not st.session_state.get("mary_voice_enabled", True):
        return

    profile_name, profile = professional._obter_configuracao_voz()
    safe_text = json.dumps(text, ensure_ascii=False)
    safe_profile_name = html.escape(profile_name)
    component_key = re.sub(r"[^a-zA-Z0-9_-]", "", key_seed)[-48:] or "mary"
    autoplay_js = "speakMary();" if autoplay else ""
    rate = float(profile["rate"])
    pitch = float(profile["pitch"])
    volume = float(profile["volume"])

    professional.components.html(
        f"""
        <style>
          html, body {{ margin:0; padding:0; background:transparent; }}
          .voice-row {{ display:flex; align-items:center; gap:8px; margin:2px 0 0 0; }}
          .voice-main {{
            border:1px solid rgba(255,255,255,.14);
            background:#1b1c24;
            color:#eee7f1;
            border-radius:999px;
            padding:7px 12px;
            cursor:pointer;
            font:600 12px system-ui,-apple-system,sans-serif;
            box-shadow:none;
            transition:background .16s ease,border-color .16s ease,transform .16s ease;
          }}
          .voice-main:hover {{ background:#292b36; border-color:rgba(255,255,255,.24); }}
          .voice-main:active {{ transform:translateY(1px); }}
          .voice-main:disabled {{ background:#171820; color:#8f8995; opacity:.72; }}
          .voice-stop {{
            border:0;
            background:transparent;
            color:#9e97a4;
            padding:5px;
            cursor:pointer;
            font:500 11px system-ui,-apple-system,sans-serif;
          }}
          .voice-stop:hover {{ color:#d8d1db; }}
        </style>
        <div class="voice-row">
          <button class="voice-main" id="mary-voice-{component_key}" onclick="speakMary()"
            title="Interpretação: {safe_profile_name}">
            ▶ Ouvir Mary · {safe_profile_name}
          </button>
          <button class="voice-stop" onclick="window.speechSynthesis.cancel()">parar</button>
        </div>
        <script>
          function chooseVoice() {{
            const voices = window.speechSynthesis.getVoices();
            const pt = voices.filter(v => (v.lang || '').toLowerCase().startsWith('pt'));
            const preferred = [
              /Microsoft Francisca/i, /Francisca/i, /Microsoft Maria/i,
              /Luciana/i, /Leticia/i, /Google Português do Brasil/i,
              /Google português/i, /female|feminina|feminino/i
            ];
            for (const pattern of preferred) {{
              const found = pt.find(v => pattern.test(v.name || ''));
              if (found) return found;
            }}
            return pt.find(v => (v.lang || '').toLowerCase() === 'pt-br') || pt[0] || voices[0];
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
        height=44,
    )


def _patch_thought_prompt() -> None:
    try:
        import scenarios.stories.casada_frustrada.compact_prompt as compact
        import ui.casada_frustrada_beat_runtime as beat_runtime
    except Exception:
        return

    current = compact.compilar_prompt_beat
    if getattr(current, "_mary_thought_format", False):
        return

    def wrapper(*args: Any, **kwargs: Any) -> str:
        base = str(current(*args, **kwargs) or "").strip()
        if not base:
            return base
        return (
            base
            + "\n\nFORMATO ESTRUTURAL DA RESPOSTA\n"
            + "- Fala audível de Mary: texto normal, sem rótulo.\n"
            + "- Pensamento privado opcional: linha isolada iniciada por "
              "'Pensamento de Mary:' e sempre escrita em primeira pessoa.\n"
            + "- Nunca escrever ponte de cena, rubrica ou narração em terceira pessoa.\n"
            + "- Nunca escrever 'Mary faz...', 'Ela olha...' ou equivalentes.\n"
            + "- Nunca misturar fala e pensamento no mesmo parágrafo.\n"
            + "- Somente a fala audível deve ser lida pela voz."
        )

    wrapper._mary_thought_format = True  # type: ignore[attr-defined]
    compact.compilar_prompt_beat = wrapper
    beat_runtime.compilar_prompt_beat = wrapper


def install_sidebar_rollback_and_thought_style() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    app_runtime._render_rollback_controls = _render_rollback_controls_sidebar
    professional._is_thought_line = _is_thought_line
    professional._clean_thought = _clean_thought
    professional.separar_resposta_mary = _separar_resposta_mary
    professional.renderizar_resposta_mary = _render_response
    professional._render_voice_player = _render_voice_player_dark
    _patch_thought_prompt()
    _INSTALLED = True


__all__ = [
    "SIDEBAR_ROLLBACK_THOUGHT_STYLE_VERSION",
    "install_sidebar_rollback_and_thought_style",
]
