from __future__ import annotations

from scenarios import registry as scenario_registry
from scenarios.card_registry import instalar_cards_no_registry
from scenarios.casada_frustrada import (
    SCENARIO_ID,
    obter_configuracao,
    obter_encerramentos,
    obter_recuperacoes,
    obter_rotas,
)
from ui.card_runtime_integration import install_card_runtime_integration
from ui.interaction_persistence import install_interaction_persistence
from ui.mary_relationship_compaction import install_mary_relationship_compaction
from ui.persistence_hot_path_optimizer import install_persistence_hot_path_optimizer
from ui.relationship_event_compaction import install_relationship_event_compaction
from ui.scenario_catalog_visibility_fix import install_scenario_catalog_visibility_fix
from ui.scenario_event_compaction import install_scenario_event_compaction
from ui.scenario_event_persistence import install_scenario_event_persistence
from ui.scenario_history_recovery import install_scenario_history_recovery
from ui.session_persistence import install_session_persistence
from ui.sheets_read_quota_guard import install_sheets_read_quota_guard
from ui.user_account_persistence import install_user_account_persistence


SCENARIO_CATALOG_EXTENSION_VERSION = (
    "scenario-catalog-extension-v21-safe-startup-without-title-bridge"
)

_INSTALLED = False


def install_scenario_catalog_extension() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    install_sheets_read_quota_guard()

    scenario_registry.SCENARIO_LOADERS[SCENARIO_ID] = {
        "config_loader": obter_configuracao,
        "routes_loader": obter_rotas,
        "recoveries_loader": obter_recuperacoes,
        "endings_loader": obter_encerramentos,
    }

    instalar_cards_no_registry(scenario_registry)

    install_relationship_event_compaction()
    install_persistence_hot_path_optimizer()
    install_scenario_event_compaction()

    install_scenario_history_recovery()

    # A integração experimental de ponte não é instalada durante o bootstrap.
    # Ela alterava st.title e a cadeia de funções do diretor antes do primeiro
    # render, podendo manter o Streamlit indefinidamente em estado de carga.
    # A política semântica continua disponível no card e será reintegrada em um
    # ponto explícito do processamento de interação, sem monkey patch de UI.
    install_card_runtime_integration()

    install_mary_relationship_compaction()
    install_scenario_catalog_visibility_fix()
    install_user_account_persistence()
    install_session_persistence()
    install_interaction_persistence()
    install_scenario_event_persistence()
    _INSTALLED = True


__all__ = [
    "SCENARIO_CATALOG_EXTENSION_VERSION",
    "install_scenario_catalog_extension",
]
