from __future__ import annotations

import json
import sys
from functools import wraps
from typing import Any, Callable

import streamlit as st


DIAGNOSTIC_LOG_CONTROLS_VERSION = (
    "diagnostic-log-controls-v3-bounded-chat-session"
)

LOG_ENABLED_KEY = "diagnostic_interaction_log_enabled"
MAX_LOCAL_DETAILED_LOGS = 2
MAX_SESSION_MESSAGES = 16
PRUNED_USER_COUNT_KEY = "pruned_user_message_count"
SYNTHETIC_COUNT_KEY = "_mary_synthetic_count_message"

_INSTALLED = False
_ORIGINAL_TITLE: Callable[..., Any] | None = None


def log_diagnostico_ativado() -> bool:
    """Retorna a preferência da sessão; o padrão é não gerar log pesado."""
    return bool(st.session_state.get(LOG_ENABLED_KEY, False))


def _mensagem_sintetica() -> dict[str, Any]:
    return {
        "role": "user",
        "content": ".",
        SYNTHETIC_COUNT_KEY: True,
    }


def _eh_mensagem_sintetica(item: Any) -> bool:
    return bool(
        isinstance(item, dict)
        and item.get(SYNTHETIC_COUNT_KEY) is True
    )


def _limitar_historico_sessao() -> None:
    """Mantém somente a janela recente no WebSocket do Streamlit.

    O histórico completo continua persistido remotamente. A quantidade de
    mensagens de usuário removidas é guardada separadamente para preservar a
    numeração e as regras de duração dos cenários.
    """
    mensagens = st.session_state.get("messages", [])
    if not isinstance(mensagens, list):
        st.session_state["messages"] = []
        st.session_state.setdefault(PRUNED_USER_COUNT_KEY, 0)
        return

    mensagens = [
        item for item in mensagens
        if not _eh_mensagem_sintetica(item)
    ]

    if len(mensagens) <= MAX_SESSION_MESSAGES:
        st.session_state["messages"] = mensagens
        st.session_state.setdefault(PRUNED_USER_COUNT_KEY, 0)
        return

    removidas = mensagens[:-MAX_SESSION_MESSAGES]
    mantidas = mensagens[-MAX_SESSION_MESSAGES:]
    usuarios_removidos = sum(
        1
        for item in removidas
        if (
            isinstance(item, dict)
            and item.get("role") == "user"
            and str(item.get("content") or "").strip()
        )
    )

    total_anterior = int(
        st.session_state.get(PRUNED_USER_COUNT_KEY, 0) or 0
    )
    st.session_state[PRUNED_USER_COUNT_KEY] = (
        total_anterior + usuarios_removidos
    )
    st.session_state["messages"] = mantidas


def _mensagens_com_contagem_preservada(
    mensagens: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    quantidade = max(
        0,
        int(st.session_state.get(PRUNED_USER_COUNT_KEY, 0) or 0),
    )
    if quantidade <= 0:
        return list(mensagens)
    return [
        *(_mensagem_sintetica() for _ in range(quantidade)),
        *list(mensagens),
    ]


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
        return atualizados[-MAX_LOCAL_DETAILED_LOGS:]

    wrapper._mary_diagnostic_log_wrapped = True  # type: ignore[attr-defined]
    setattr(module, "adicionar_registro_sessao", wrapper)


def _patch_history_restore(module: Any) -> None:
    original = getattr(module, "restaurar_historico_interacoes", None)
    if not callable(original) or getattr(
        original,
        "_mary_chat_history_wrapped",
        False,
    ):
        return

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        resultado = original(*args, **kwargs)
        _limitar_historico_sessao()
        return resultado

    wrapper._mary_chat_history_wrapped = True  # type: ignore[attr-defined]
    setattr(module, "restaurar_historico_interacoes", wrapper)


def _patch_scenario_history_counter(module: Any) -> None:
    original = getattr(
        module,
        "sincronizar_contagem_cenario_com_historico",
        None,
    )
    if not callable(original) or getattr(
        original,
        "_mary_chat_history_wrapped",
        False,
    ):
        return

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        novos_kwargs = dict(kwargs)
        mensagens = novos_kwargs.get("mensagens")
        if isinstance(mensagens, list):
            novos_kwargs["mensagens"] = (
                _mensagens_com_contagem_preservada(mensagens)
            )
        return original(*args, **novos_kwargs)

    wrapper._mary_chat_history_wrapped = True  # type: ignore[attr-defined]
    setattr(
        module,
        "sincronizar_contagem_cenario_com_historico",
        wrapper,
    )


def _patch_api_history(module: Any) -> None:
    original = getattr(module, "construir_historico_api", None)
    if not callable(original) or getattr(
        original,
        "_mary_chat_history_wrapped",
        False,
    ):
        return

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        resultado = original(*args, **kwargs)
        if not isinstance(resultado, list):
            return []
        return [
            item for item in resultado
            if not _eh_mensagem_sintetica(item)
        ]

    wrapper._mary_chat_history_wrapped = True  # type: ignore[attr-defined]
    setattr(module, "construir_historico_api", wrapper)


def _patch_interaction_processor(module: Any) -> None:
    original = getattr(module, "processar_interacao", None)
    if not callable(original) or getattr(
        original,
        "_mary_chat_history_wrapped",
        False,
    ):
        return

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        mensagens_reais = st.session_state.get("messages", [])
        if not isinstance(mensagens_reais, list):
            mensagens_reais = []

        st.session_state["messages"] = (
            _mensagens_com_contagem_preservada(mensagens_reais)
        )
        try:
            return original(*args, **kwargs)
        finally:
            mensagens_atuais = st.session_state.get("messages", [])
            if not isinstance(mensagens_atuais, list):
                mensagens_atuais = []
            st.session_state["messages"] = [
                item for item in mensagens_atuais
                if not _eh_mensagem_sintetica(item)
            ]
            _limitar_historico_sessao()

    wrapper._mary_chat_history_wrapped = True  # type: ignore[attr-defined]
    setattr(module, "processar_interacao", wrapper)


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
    st.session_state.setdefault(PRUNED_USER_COUNT_KEY, 0)

    _patch_log_record_builder(module)
    _patch_local_log_accumulator(module)
    _patch_history_restore(module)
    _patch_scenario_history_counter(module)
    _patch_api_history(module)
    _patch_interaction_processor(module)
    _patch_log_renderer(module)

    # Em cada rerun, descarta imediatamente mensagens antigas que ainda possam
    # ter vindo de uma versão anterior do aplicativo.
    _limitar_historico_sessao()


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
    "MAX_SESSION_MESSAGES",
    "aplicar_controles_log_diagnostico",
    "install_diagnostic_log_controls",
    "log_diagnostico_ativado",
]
