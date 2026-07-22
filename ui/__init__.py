from ui.app_runtime_integration import (
    APP_RUNTIME_INTEGRATION_VERSION,
    aplicar_integracao_runtime,
    aplicar_politica_adaptativa_encerramento,
    install_app_runtime_integration,
)
from ui.interaction_rerun_optimizer import (
    INTERACTION_RERUN_OPTIMIZER_VERSION,
    aplicar_otimizacao_rerun,
    install_interaction_rerun_optimizer,
)
from ui.diagnostic_log_controls import (
    DIAGNOSTIC_LOG_CONTROLS_VERSION,
    aplicar_controles_log_diagnostico,
    install_diagnostic_log_controls,
    log_diagnostico_ativado,
)
from ui.onomatopoeia_integration import (
    ONOMATOPOEIA_INTEGRATION_VERSION,
    aplicar_integracao_onomatopeias,
    install_onomatopoeia_integration,
)


# O pacote ui é carregado antes de main(). Os instaladores envolvem st.title;
# a integração real acontece depois que app.py já definiu todas as funções.
install_app_runtime_integration()
install_interaction_rerun_optimizer()
install_diagnostic_log_controls()
install_onomatopoeia_integration()


from ui.login import (
    AUTH_ACTION_LOGIN,
    AUTH_ACTION_REGISTER,
    AuthenticationResult,
    renderizar_tela_login,
)


__all__ = [
    "APP_RUNTIME_INTEGRATION_VERSION",
    "INTERACTION_RERUN_OPTIMIZER_VERSION",
    "DIAGNOSTIC_LOG_CONTROLS_VERSION",
    "ONOMATOPOEIA_INTEGRATION_VERSION",
    "aplicar_integracao_runtime",
    "aplicar_otimizacao_rerun",
    "aplicar_controles_log_diagnostico",
    "aplicar_integracao_onomatopeias",
    "aplicar_politica_adaptativa_encerramento",
    "install_app_runtime_integration",
    "install_interaction_rerun_optimizer",
    "install_diagnostic_log_controls",
    "install_onomatopoeia_integration",
    "log_diagnostico_ativado",
    "AUTH_ACTION_LOGIN",
    "AUTH_ACTION_REGISTER",
    "AuthenticationResult",
    "renderizar_tela_login",
]
