from ui.app_runtime_integration import (
    APP_RUNTIME_INTEGRATION_VERSION,
    aplicar_integracao_runtime,
    aplicar_politica_adaptativa_encerramento,
    install_app_runtime_integration,
)


# O pacote ui é carregado antes de main(). O instalador apenas envolve st.title;
# a integração real acontece depois que app.py já definiu todas as funções.
install_app_runtime_integration()


from ui.login import (
    AUTH_ACTION_LOGIN,
    AUTH_ACTION_REGISTER,
    AuthenticationResult,
    renderizar_tela_login,
)


__all__ = [
    "APP_RUNTIME_INTEGRATION_VERSION",
    "aplicar_integracao_runtime",
    "aplicar_politica_adaptativa_encerramento",
    "install_app_runtime_integration",
    "AUTH_ACTION_LOGIN",
    "AUTH_ACTION_REGISTER",
    "AuthenticationResult",
    "renderizar_tela_login",
]
