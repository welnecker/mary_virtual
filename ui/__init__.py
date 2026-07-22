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


# O pacote ui é carregado antes de main(). Os instaladores envolvem st.title;
# a integração real acontece depois que app.py já definiu todas as funções.
install_app_runtime_integration()
install_interaction_rerun_optimizer()


from ui.login import (
    AUTH_ACTION_LOGIN,
    AUTH_ACTION_REGISTER,
    AuthenticationResult,
    renderizar_tela_login,
)


__all__ = [
    "APP_RUNTIME_INTEGRATION_VERSION",
    "INTERACTION_RERUN_OPTIMIZER_VERSION",
    "aplicar_integracao_runtime",
    "aplicar_otimizacao_rerun",
    "aplicar_politica_adaptativa_encerramento",
    "install_app_runtime_integration",
    "install_interaction_rerun_optimizer",
    "AUTH_ACTION_LOGIN",
    "AUTH_ACTION_REGISTER",
    "AuthenticationResult",
    "renderizar_tela_login",
]
