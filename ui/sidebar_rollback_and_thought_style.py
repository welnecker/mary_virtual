from __future__ import annotations

import html
import re
from typing import Any

import streamlit as st

import ui.app_runtime_integration as app_runtime
import ui.professional_experience as professional
from repositories.scenario_rollback_repository import apagar_ultimos_turnos_cenario


SIDEBAR_ROLLBACK_THOUGHT_STYLE_VERSION = (
    "sidebar-rollback-thought-style-v2-story-blocks"
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
    if len(text) >= 3 and text.startswith("*") and text.endswith("*"):
        return True
    return bool(
        re.match(
            r"^(pensamentos?\s+de\s+mary|pensamentos?|penso|por dentro)\s*:\s*.+$",
            text,
            flags=re.IGNORECASE,
        )
    )


def _clean_thought(line: str) -> str:
    text = _normalize_label(line)
    if text.startswith("*") and text.endswith("*"):
        text = text[1:-1].strip()
    return re.sub(
        r"^(pensamentos?\s+de\s+mary|pensamentos?|penso|por dentro)\s*:\s*",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()


def _is_bridge_line(line: str) -> bool:
    text = _normalize_label(line)
    if not text:
        return False
    if len(text) >= 3 and text.startswith("(") and text.endswith(")"):
        return True
    if re.match(
        r"^(ponte\s+de\s+cena|ponte|transi[cç][aã]o|narra[cç][aã]o)\s*:\s*.+$",
        text,
        flags=re.IGNORECASE,
    ):
        return True
    return bool(
        re.match(
            r"^(enquanto|pouco depois|algum tempo depois|mais tarde|j[aá] em casa|"
            r"no banheiro|naquele momento|quando voc[eê]|quando ele|quando ela)\b",
            text,
            flags=re.IGNORECASE,
        )
        and "?" not in text
    )


def _clean_bridge(line: str) -> str:
    text = _normalize_label(line)
    if text.startswith("(") and text.endswith(")"):
        text = text[1:-1].strip()
    return re.sub(
        r"^(ponte\s+de\s+cena|ponte|transi[cç][aã]o|narra[cç][aã]o)\s*:\s*",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()


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
        elif _is_bridge_line(line):
            flush_speech()
            bridge = _clean_bridge(line)
            if bridge:
                blocks.append(("bridge", bridge))
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
        elif kind == "bridge":
            parts.append(
                '<div style="padding:.62rem .78rem;border-radius:12px;'
                'border:1px solid rgba(255,255,255,.09);'
                'background:linear-gradient(90deg,rgba(255,255,255,.075),rgba(255,255,255,.025));'
                'color:#c8c1cc;font:italic .91rem/1.55 Georgia,serif;">'
                '<div style="font:700 .66rem system-ui;letter-spacing:.12em;'
                'text-transform:uppercase;color:#9f96a6;margin-bottom:.28rem;">'
                'Ponte de cena</div>'
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


def _patch_thought_prompt() -> None:
    # Compatibilidade com o runtime antigo, quando ainda estiver instalado.
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
            + "- Ação, passagem de tempo ou mudança de posição: linha isolada iniciada por "
              "'Ponte de cena:'.\n"
            + "- Pensamento privado: linha isolada iniciada por 'Pensamento de Mary:'.\n"
            + "- Nunca misture fala, ponte e pensamento no mesmo parágrafo.\n"
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
    _patch_thought_prompt()
    _INSTALLED = True


__all__ = [
    "SIDEBAR_ROLLBACK_THOUGHT_STYLE_VERSION",
    "install_sidebar_rollback_and_thought_style",
]
