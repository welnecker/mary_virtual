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
from ui.casada_frustrada_supermarket_calibration import (
    CASADA_FRUSTRADA_SUPERMARKET_VERSION,
    aplicar_calibracao_supermercado_casada_frustrada,
    install_casada_frustrada_supermarket_calibration,
)
from ui.casada_frustrada_spoken_sex_calibration import (
    CASADA_FRUSTRADA_SPOKEN_SEX_VERSION,
    aplicar_calibracao_sexo_falado_casada_frustrada,
    install_casada_frustrada_spoken_sex_calibration,
)
from ui.pix_test_commerce_integration import (
    PIX_TEST_COMMERCE_VERSION,
    aplicar_integracao_pix_teste,
    install_pix_test_commerce_integration,
)
from ui.pix_continue_access_fix import (
    PIX_CONTINUE_ACCESS_FIX_VERSION,
    install_pix_continue_access_fix,
)
from ui.pix_active_session_access import (
    PIX_ACTIVE_SESSION_ACCESS_VERSION,
    aplicar_acesso_pix_por_sessao_ativa,
    install_pix_active_session_access,
)
from ui.paid_chapter_continuation import (
    PAID_CHAPTER_CONTINUATION_VERSION,
    aplicar_continuacao_capitulos_pagos,
    install_paid_chapter_continuation,
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
from ui.scenario_flip_cards import (
    SCENARIO_FLIP_CARDS_VERSION,
    aplicar_cards_reversiveis,
    install_scenario_flip_cards,
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
install_casada_frustrada_supermarket_calibration()
install_casada_frustrada_spoken_sex_calibration()
install_pix_test_commerce_integration()
install_pix_continue_access_fix()
install_pix_active_session_access()
install_paid_chapter_continuation()
install_completed_history_visibility()
install_contrast_accessibility()
install_scenario_flip_cards()


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
    "CASADA_FRUSTRADA_SUPERMARKET_VERSION",
    "CASADA_FRUSTRADA_SPOKEN_SEX_VERSION",
    "PIX_TEST_COMMERCE_VERSION",
    "PIX_CONTINUE_ACCESS_FIX_VERSION",
    "PIX_ACTIVE_SESSION_ACCESS_VERSION",
    "PAID_CHAPTER_CONTINUATION_VERSION",
    "COMPLETED_HISTORY_VISIBILITY_VERSION",
    "CONTRAST_ACCESSIBILITY_VERSION",
    "SCENARIO_CATALOG_EXTENSION_VERSION",
    "SCENARIO_DURATION_EXTENSION_VERSION",
    "ELEVENLABS_VOICE_INTEGRATION_VERSION",
    "SCENARIO_FLIP_CARDS_VERSION",
    "aplicar_integracao_runtime",
    "aplicar_otimizacao_rerun",
    "aplicar_controles_log_diagnostico",
    "aplicar_integracao_onomatopeias",
    "aplicar_integracao_intimidade_casada_frustrada",
    "aplicar_calibracao_supermercado_casada_frustrada",
    "aplicar_calibracao_sexo_falado_casada_frustrada",
    "aplicar_integracao_pix_teste",
    "aplicar_acesso_pix_por_sessao_ativa",
    "aplicar_continuacao_capitulos_pagos",
    "aplicar_contraste_acessivel",
    "aplicar_politica_adaptativa_encerramento",
    "ocultar_historias_concluidas_do_catalogo",
    "dobrar_duracao_configuracao",
    "aplicar_cards_reversiveis",
    "install_scenario_catalog_extension",
    "install_scenario_duration_extension",
    "install_elevenlabs_voice_integration",
    "install_app_runtime_integration",
    "install_interaction_rerun_optimizer",
    "install_diagnostic_log_controls",
    "install_onomatopoeia_integration",
    "install_casada_frustrada_intimacy_integration",
    "install_casada_frustrada_supermarket_calibration",
    "install_casada_frustrada_spoken_sex_calibration",
    "install_pix_test_commerce_integration",
    "install_pix_continue_access_fix",
    "install_pix_active_session_access",
    "install_paid_chapter_continuation",
    "install_completed_history_visibility",
    "install_contrast_accessibility",
    "install_scenario_flip_cards",
    "log_diagnostico_ativado",
    "AUTH_ACTION_LOGIN",
    "AUTH_ACTION_REGISTER",
    "AuthenticationResult",
    "renderizar_tela_login",
]
