from __future__ import annotations

import sys
from functools import wraps
from typing import Any, Callable

import streamlit as st


DIAGNOSTIC_LOG_CONTROLS_VERSION = (
    "diagnostic-log-controls-v1-optional-heavy-log"
)

LOG_ENABLED_KEY = "diagnostic_interaction_log_enabled"

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
            # diagnóstico pesado — prompt completo e mensagens enviadas ao
            # modelo — deixa de ser duplicado no log.
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
            return list(registros or [])
        return original(registros, registro)

    wrapper._mary_diagnostic_log_wrapped = True  # type: ignore[attr-defined]
    setattr(module, "adicionar_registro_sessao", wrapper)


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
                "Quando ativado, mantém em memória o prompt completo, "
                "as mensagens enviadas ao modelo e os dados de diagnóstico "
                "para exportação em JSON/JSONL. Não cria chamadas extras ao "
                "modelo, mas aumenta memória, serialização e tamanho do log."
            ),
        )

        if not enabled:
            st.caption(
                "Log detalhado desativado. O histórico mínimo da história "
                "continua sendo salvo normalmente."
            )
            return None

        return original(*args, **kwargs)

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
    "aplicar_controles_log_diagnostico",
    "install_diagnostic_log_controls",
    "log_diagnostico_ativado",
]
