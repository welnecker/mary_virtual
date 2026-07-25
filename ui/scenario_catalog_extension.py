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
from ui.interaction_persistence import install_interaction_persistence
from ui.mary_relationship_compaction import install_mary_relationship_compaction
from ui.scenario_catalog_visibility_fix import install_scenario_catalog_visibility_fix
from ui.scenario_event_persistence import install_scenario_event_persistence
from ui.session_persistence import install_session_persistence
from ui.sheets_read_quota_guard import install_sheets_read_quota_guard
from ui.user_account_persistence import install_user_account_persistence


SCENARIO_CATALOG_EXTENSION_VERSION = (
    "scenario-catalog-extension-v14-independent-card-characters"
)

_INSTALLED = False


def install_scenario_catalog_extension() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    install_sheets_read_quota_guard()

    # Compatibilidade com o catálogo atual. A personalidade, psicologia, voz,
    # roteiro e transições já não são instaladas por wrappers específicos da UI.
    scenario_registry.SCENARIO_LOADERS[SCENARIO_ID] = {
        "config_loader": obter_configuracao,
        "routes_loader": obter_rotas,
        "recoveries_loader": obter_recuperacoes,
        "endings_loader": obter_encerramentos,
    }

    # Enriquece os dois cenários com seus pacotes independentes e acrescenta ao
    # prompt somente a Mary pertencente ao card ativo.
    instalar_cards_no_registry(scenario_registry)

    # Os antigos wrappers casada_frustrada_prompt_inputs e
    # casada_frustrada_canonical_prompt não são mais instalados. O conteúdo
    # específico agora vive em scenarios/stories/<card>/.

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
