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
from ui.casada_frustrada_intimacy_integration import (
    CASADA_FRUSTRADA_INTIMACY_VERSION,
    aplicar_integracao_intimidade_casada_frustrada,
    install_casada_frustrada_intimacy_integration,
)
from ui.pix_test_commerce_integration import (
    PIX_TEST_COMMERCE_VERSION,
    aplicar_integracao_pix_teste,
    install_pix_test_commerce_integration,
)
from ui.completed_history_visibility import (
    COMPLETED_HISTORY_VISIBILITY_VERSION,
    install_completed_history_visibility,
    ocultar_historias_concluidas_do_catalogo,
)
from ui.contrast_accessibility import (
    CONTRAST_ACCESSIBILITY_VERSION,
    aplicar_contraste_acessivel,
    install_contrast_accessibility,
)
from ui.scenario_catalog_extension import (
    SCENARIO_CATALOG_EXTENSION_VERSION,
    install_scenario_catalog_extension,
)
from ui.scenario_duration_extension import (
    SCENARIO_DURATION_EXTENSION_VERSION,
    dobrar_duracao_configuracao,
    install_scenario_duration_extension,
)
from ui.elevenlabs_voice_integration import (
    ELEVENLABS_VOICE_INTEGRATION_VERSION,
    install_elevenlabs_voice_integration,
)


# O pacote ui é carregado antes de main(). Os instaladores envolvem st.title;
# a integração real acontece depois que app.py já definiu todas as funções.
install_scenario_catalog_extension()
install_scenario_duration_extension()
install_elevenlabs_voice_integration()
install_app_runtime_integration()
install_interaction_rerun_optimizer()
install_diagnostic_log_controls()
install_onomatopoeia_integration()
install_casada_frustrada_intimacy_integration()
install_pix_test_commerce_integration()
install_completed_history_visibility()
install_contrast_accessibility()


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
    "CASADA_FRUSTRADA_INTIMACY_VERSION",
    "PIX_TEST_COMMERCE_VERSION",
    "COMPLETED_HISTORY_VISIBILITY_VERSION",
    "CONTRAST_ACCESSIBILITY_VERSION",
    "SCENARIO_CATALOG_EXTENSION_VERSION",
    "SCENARIO_DURATION_EXTENSION_VERSION",
    "ELEVENLABS_VOICE_INTEGRATION_VERSION",
    "aplicar_integracao_runtime",
    "aplicar_otimizacao_rerun",
    "aplicar_controles_log_diagnostico",
    "aplicar_integracao_onomatopeias",
    "aplicar_integracao_intimidade_casada_frustrada",
    "aplicar_integracao_pix_teste",
    "aplicar_contraste_acessivel",
    "aplicar_politica_adaptativa_encerramento",
    "ocultar_historias_concluidas_do_catalogo",
    "dobrar_duracao_configuracao",
    "install_scenario_catalog_extension",
    "install_scenario_duration_extension",
    "install_elevenlabs_voice_integration",
    "install_app_runtime_integration",
    "install_interaction_rerun_optimizer",
    "install_diagnostic_log_controls",
    "install_onomatopoeia_integration",
    "install_casada_frustrada_intimacy_integration",
    "install_pix_test_commerce_integration",
    "install_completed_history_visibility",
    "install_contrast_accessibility",
    "log_diagnostico_ativado",
    "AUTH_ACTION_LOGIN",
    "AUTH_ACTION_REGISTER",
    "AuthenticationResult",
    "renderizar_tela_login",
]
