from __future__ import annotations

import re
from typing import Any

import streamlit as st

import ui.app_runtime_integration as app_runtime
import ui.professional_experience as professional
from repositories.scenario_rollback_repository import apagar_ultimos_turnos_cenario


SIDEBAR_ROLLBACK_THOUGHT_STYLE_VERSION = (
    "sidebar-rollback-thought-style-v1"
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

    # Todo o fluxo fica preso à sidebar. Nada é inserido abaixo das mensagens.
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


def _normalize_thought_label(line: str) -> str:
    text = line.strip()
    text = text.strip('"“”')
    return text


def _is_thought_line(line: str) -> bool:
    text = _normalize_thought_label(line)
    if not text:
        return False
    if len(text) >= 3 and text.startswith("*") and text.endswith("*"):
        return True
    if len(text) >= 3 and text.startswith("(") and text.endswith(")"):
        return True
    return bool(
        re.match(
            r"^(pensamentos?\s+de\s+mary|pensamentos?|penso|por dentro)\s*:\s*.+$",
            text,
            flags=re.IGNORECASE,
        )
    )


def _clean_thought(line: str) -> str:
    text = _normalize_thought_label(line)
    if text.startswith("*") and text.endswith("*"):
        text = text[1:-1].strip()
    if text.startswith("(") and text.endswith(")"):
        text = text[1:-1].strip()
    return re.sub(
        r"^(pensamentos?\s+de\s+mary|pensamentos?|penso|por dentro)\s*:\s*",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()


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
            + "\n\nFORMATO DE FALA E PENSAMENTO\n"
            + "- A fala audível de Mary fica em texto normal e pode ser lida pela voz.\n"
            + "- Quando o beat realmente pedir um pensamento privado, escreva-o em uma "
              "linha isolada no formato: Pensamento de Mary: texto curto.\n"
            + "- Não misture pensamento e fala na mesma linha.\n"
            + "- Pensamento não é ouvido pelo usuário e não deve conter explicação de roteiro.\n"
            + "- Não acrescente pensamento em todo turno; use apenas quando ele acrescentar "
              "contradição, desejo, receio ou decisão que Mary não diria em voz alta."
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
    _patch_thought_prompt()
    _INSTALLED = True


__all__ = [
    "SIDEBAR_ROLLBACK_THOUGHT_STYLE_VERSION",
    "install_sidebar_rollback_and_thought_style",
]
