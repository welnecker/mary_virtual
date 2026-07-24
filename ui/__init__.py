from ui.sheets_grid_autogrow import (
    SHEETS_GRID_AUTOGROW_VERSION,
    install_sheets_grid_autogrow,
)
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
from ui.mary_relationship_persistence import (
    MARY_RELATIONSHIP_COLUMNS,
    MARY_RELATIONSHIP_PERSISTENCE_VERSION,
    aplicar_persistencia_relacionamento_mary,
    garantir_schema_mary_relationship,
    install_mary_relationship_persistence,
    sincronizar_estado_relacionamento,
)
from ui.memory_persistence import (
    MEMORY_COLUMNS,
    MEMORY_PERSISTENCE_VERSION,
    MEMORY_REPOSITORY_VERSION,
    aplicar_persistencia_memorias,
    install_memory_persistence,
)
from ui.scenario_catalog_persistence import (
    SCENARIO_CATALOG_PERSISTENCE_VERSION,
    SCENARIO_COLUMNS,
    aplicar_persistencia_catalogo_scenarios,
    garantir_schema_scenarios,
    install_scenario_catalog_persistence,
    sincronizar_catalogo_scenarios,
)
from ui.scenario_session_legacy_migration import (
    CANONICAL_SCENARIO_SESSION_COLUMNS,
    SCENARIO_SESSION_MIGRATION_VERSION,
    aplicar_migracao_sessoes_legadas,
    garantir_schema_scenario_sessions,
    install_scenario_session_legacy_migration,
    migrar_user_scenario_sessions,
)
from ui.user_visual_profile_persistence import (
    USER_VISUAL_PROFILE_COLUMNS,
    USER_VISUAL_PROFILE_PERSISTENCE_VERSION,
    aplicar_persistencia_perfil_visual,
    garantir_schema_user_visual_profile,
    install_user_visual_profile_persistence,
    obter_perfil_visual_ativo,
    persistir_nova_referencia_visual,
)
from ui.user_visual_profile_commit_fix import (
    USER_VISUAL_PROFILE_COMMIT_FIX_VERSION,
    aplicar_commit_perfil_visual,
    install_user_visual_profile_commit_fix,
)


# A proteção da grade precisa ser instalada antes de qualquer sincronização
# de cabeçalhos ou escrita nas abas do Google Sheets.
install_sheets_grid_autogrow()

# O pacote ui é carregado antes de main(). Os instaladores envolvem st.title;
# a integração real acontece depois que app.py já definiu todas as funções.
install_scenario_catalog_extension()
install_scenario_duration_extension()
install_elevenlabs_voice_integration()
install_app_runtime_integration()
install_interaction_rerun_optimizer()
install_diagnostic_log_controls()

# Removidas:
# install_onomatopoeia_integration()
# install_casada_frustrada_intimacy_integration()
# install_casada_frustrada_supermarket_calibration()
# install_casada_frustrada_spoken_sex_calibration()

install_pix_test_commerce_integration()
install_pix_continue_access_fix()
install_pix_active_session_access()
install_paid_chapter_continuation()
install_completed_history_visibility()
install_contrast_accessibility()
install_scenario_flip_cards()
install_mary_relationship_persistence()
install_memory_persistence()
install_scenario_catalog_persistence()
install_scenario_session_legacy_migration()

# Instalado antes do adaptador principal: na execução dos wrappers de st.title,
# o adaptador entra primeiro e o commit é aplicado sobre ele em seguida.
install_user_visual_profile_commit_fix()
install_user_visual_profile_persistence()


from ui.login import (
    AUTH_ACTION_LOGIN,
    AUTH_ACTION_REGISTER,
    AuthenticationResult,
    renderizar_tela_login,
)


__all__ = [
    "SHEETS_GRID_AUTOGROW_VERSION",
    "APP_RUNTIME_INTEGRATION_VERSION",
    "INTERACTION_RERUN_OPTIMIZER_VERSION",
    "DIAGNOSTIC_LOG_CONTROLS_VERSION",      
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
    "MARY_RELATIONSHIP_PERSISTENCE_VERSION",
    "MARY_RELATIONSHIP_COLUMNS",
    "MEMORY_PERSISTENCE_VERSION",
    "MEMORY_REPOSITORY_VERSION",
    "MEMORY_COLUMNS",
    "SCENARIO_CATALOG_PERSISTENCE_VERSION",
    "SCENARIO_COLUMNS",
    "SCENARIO_SESSION_MIGRATION_VERSION",
    "CANONICAL_SCENARIO_SESSION_COLUMNS",
    "USER_VISUAL_PROFILE_PERSISTENCE_VERSION",
    "USER_VISUAL_PROFILE_COMMIT_FIX_VERSION",
    "USER_VISUAL_PROFILE_COLUMNS",
    "aplicar_integracao_runtime",
    "aplicar_otimizacao_rerun",
    "aplicar_controles_log_diagnostico",       
    "aplicar_integracao_pix_teste",
    "aplicar_acesso_pix_por_sessao_ativa",
    "aplicar_continuacao_capitulos_pagos",
    "aplicar_contraste_acessivel",
    "aplicar_politica_adaptativa_encerramento",
    "ocultar_historias_concluidas_do_catalogo",
    "dobrar_duracao_configuracao",
    "aplicar_cards_reversiveis",
    "aplicar_persistencia_relacionamento_mary",
    "garantir_schema_mary_relationship",
    "sincronizar_estado_relacionamento",
    "aplicar_persistencia_memorias",
    "aplicar_persistencia_catalogo_scenarios",
    "garantir_schema_scenarios",
    "sincronizar_catalogo_scenarios",
    "aplicar_migracao_sessoes_legadas",
    "garantir_schema_scenario_sessions",
    "migrar_user_scenario_sessions",
    "aplicar_persistencia_perfil_visual",
    "aplicar_commit_perfil_visual",
    "garantir_schema_user_visual_profile",
    "obter_perfil_visual_ativo",
    "persistir_nova_referencia_visual",
    "install_sheets_grid_autogrow",
    "install_scenario_catalog_extension",
    "install_scenario_duration_extension",
    "install_elevenlabs_voice_integration",
    "install_app_runtime_integration",
    "install_interaction_rerun_optimizer",
    "install_diagnostic_log_controls",   
    "install_pix_test_commerce_integration",
    "install_pix_continue_access_fix",
    "install_pix_active_session_access",
    "install_paid_chapter_continuation",
    "install_completed_history_visibility",
    "install_contrast_accessibility",
    "install_scenario_flip_cards",
    "install_mary_relationship_persistence",
    "install_memory_persistence",
    "install_scenario_catalog_persistence",
    "install_scenario_session_legacy_migration",
    "install_user_visual_profile_commit_fix",
    "install_user_visual_profile_persistence",
    "log_diagnostico_ativado",
    "AUTH_ACTION_LOGIN",
    "AUTH_ACTION_REGISTER",
    "AuthenticationResult",
    "renderizar_tela_login",
]
