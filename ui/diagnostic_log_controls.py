from __future__ import annotations

import json
import sys
from functools import wraps
from typing import Any, Callable

import streamlit as st


DIAGNOSTIC_LOG_CONTROLS_VERSION = (
    "diagnostic-log-controls-v2-bounded-lightweight-render"
)

LOG_ENABLED_KEY = "diagnostic_interaction_log_enabled"
MAX_LOCAL_DETAILED_LOGS = 2

_INSTALLED = False
_ORIGINAL_TITLE: Callable[..., Any] | None = None


def log_diagnostico_ativado() -> bool:
    """Retorna a preferência da sessão; o padrão é não gerar log pesado."""
    return bool(st.session_state.get(LOG_ENABLED_KEY, False))


def _patch_log_record_builder(module: Any) -> None:
    original = getattr(module, "criar_registro_interacao", None)
    if not callable(original) or getattr(
        original,
        "_mary_diagnostic_log_wrapped",
        False,
    ):
        return

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
        if not log_diagnostico_ativado():
            # O registro mínimo ainda é criado e persistido para manter
            # histórico, contagem, retomada e rollback. Apenas o conteúdo
            # diagnóstico pesado deixa de ser duplicado na sessão local.
            kwargs = dict(kwargs)
            kwargs["raw_messages"] = []

        registro = original(*args, **kwargs)

        if isinstance(registro, dict):
            registro["diagnostic_log_enabled"] = (
                log_diagnostico_ativado()
            )
        return registro

    wrapper._mary_diagnostic_log_wrapped = True  # type: ignore[attr-defined]
    setattr(module, "criar_registro_interacao", wrapper)


def _patch_local_log_accumulator(module: Any) -> None:
    original = getattr(module, "adicionar_registro_sessao", None)
    if not callable(original) or getattr(
        original,
        "_mary_diagnostic_log_wrapped",
        False,
    ):
        return

    @wraps(original)
    def wrapper(
        registros: list[dict[str, Any]],
        registro: dict[str, Any],
    ) -> list[dict[str, Any]]:
        if not log_diagnostico_ativado():
            return []

        atualizados = original(list(registros or []), registro)
        if not isinstance(atualizados, list):
            return []

        # Prompts e mensagens brutas podem ter dezenas de milhares de
        # caracteres. Manter oito registros completos fazia o WebSocket do
        # Streamlit crescer até desconectar. Dois registros são suficientes
        # para comparar o turno atual com o anterior.
        return atualizados[-MAX_LOCAL_DETAILED_LOGS:]

    wrapper._mary_diagnostic_log_wrapped = True  # type: ignore[attr-defined]
    setattr(module, "adicionar_registro_sessao", wrapper)


def _resumo_registro(registro: dict[str, Any]) -> dict[str, Any]:
    raw_messages = registro.get("raw_messages")
    if not isinstance(raw_messages, list):
        raw_messages = []

    raw_prompt = str(registro.get("raw_system_prompt") or "")
    resposta = str(registro.get("mary_response") or "")
    usuario = str(registro.get("user_text") or "")

    return {
        "timestamp": registro.get("timestamp"),
        "interaction_number": registro.get("interaction_number"),
        "interaction_id": registro.get("interaction_id"),
        "model": registro.get("model"),
        "response_time_ms": registro.get("response_time_ms"),
        "error": registro.get("error"),
        "user_chars": len(usuario),
        "mary_chars": len(resposta),
        "raw_prompt_chars": len(raw_prompt),
        "raw_messages_count": len(raw_messages),
    }


def _patch_log_renderer(module: Any) -> None:
    original = getattr(module, "renderizar_log_interacoes", None)
    if not callable(original) or getattr(
        original,
        "_mary_diagnostic_log_wrapped",
        False,
    ):
        return

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        enabled = st.checkbox(
            "Gerar log diagnóstico detalhado",
            value=False,
            key=LOG_ENABLED_KEY,
            help=(
                "Quando ativado, mantém somente os dois turnos detalhados mais "
                "recentes para evitar excesso de memória e desconexão do app."
            ),
        )

        if not enabled:
            # Remove imediatamente qualquer carga pesada remanescente de uma
            # execução anterior ou de uma versão antiga do aplicativo.
            st.session_state["interaction_logs"] = []
            st.caption(
                "Log detalhado desativado. O histórico mínimo da história "
                "continua sendo salvo normalmente."
            )
            return None

        registros = st.session_state.get("interaction_logs", [])
        if not isinstance(registros, list):
            registros = []

        registros = registros[-MAX_LOCAL_DETAILED_LOGS:]
        st.session_state["interaction_logs"] = registros

        with st.expander("Log de interações", expanded=False):
            if not registros:
                st.info("Nenhuma interação detalhada registrada nesta sessão.")
                return None

            conteudo_json = json.dumps(
                registros,
                ensure_ascii=False,
                indent=2,
                default=str,
            )
            conteudo_jsonl = "\n".join(
                json.dumps(item, ensure_ascii=False, default=str)
                for item in registros
            )

            st.download_button(
                "Baixar JSON detalhado",
                data=conteudo_json,
                file_name="mary_interactions.json",
                mime="application/json",
                use_container_width=True,
            )
            st.download_button(
                "Baixar JSONL detalhado",
                data=conteudo_jsonl,
                file_name="mary_interactions.jsonl",
                mime="application/x-ndjson",
                use_container_width=True,
            )

            st.caption(
                "Prévia leve dos dois turnos mais recentes. O conteúdo completo "
                "fica disponível apenas nos arquivos de download."
            )
            for registro in reversed(registros):
                st.json(_resumo_registro(registro), expanded=False)
        return None

    wrapper._mary_diagnostic_log_wrapped = True  # type: ignore[attr-defined]
    setattr(module, "renderizar_log_interacoes", wrapper)


def aplicar_controles_log_diagnostico() -> None:
    module = sys.modules.get("__main__")
    if module is None:
        return

    st.session_state.setdefault(LOG_ENABLED_KEY, False)
    _patch_log_record_builder(module)
    _patch_local_log_accumulator(module)
    _patch_log_renderer(module)


def install_diagnostic_log_controls() -> None:
    global _INSTALLED, _ORIGINAL_TITLE

    if _INSTALLED:
        return

    _ORIGINAL_TITLE = st.title

    def patched_title(*args: Any, **kwargs: Any) -> Any:
        aplicar_controles_log_diagnostico()
        assert _ORIGINAL_TITLE is not None
        return _ORIGINAL_TITLE(*args, **kwargs)

    st.title = patched_title
    _INSTALLED = True


__all__ = [
    "DIAGNOSTIC_LOG_CONTROLS_VERSION",
    "LOG_ENABLED_KEY",
    "MAX_LOCAL_DETAILED_LOGS",
    "aplicar_controles_log_diagnostico",
    "install_diagnostic_log_controls",
    "log_diagnostico_ativado",
]
