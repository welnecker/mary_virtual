from __future__ import annotations

from scenarios import registry as scenario_registry
from scenarios.casada_frustrada import (
    SCENARIO_ID,
    obter_configuracao,
    obter_encerramentos,
    obter_recuperacoes,
    obter_rotas,
)
from ui.casada_frustrada_canonical_prompt import (
    install_casada_frustrada_canonical_prompt,
)
from ui.interaction_persistence import install_interaction_persistence
from ui.scenario_catalog_visibility_fix import (
    install_scenario_catalog_visibility_fix,
)
from ui.scenario_event_persistence import install_scenario_event_persistence
from ui.session_persistence import install_session_persistence
from ui.sheets_read_quota_guard import install_sheets_read_quota_guard
from ui.user_account_persistence import install_user_account_persistence


SCENARIO_CATALOG_EXTENSION_VERSION = (
    "scenario-catalog-extension-v11-casada-canonical-screenplay"
)

_INSTALLED = False


def install_scenario_catalog_extension() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    # Precisa entrar antes dos demais wrappers: gravações deixam de limpar o
    # cache de todas as abas e leituras repetidas passam a ser consolidadas.
    install_sheets_read_quota_guard()

    # Todos os cenários expõem a mesma interface pública em scenarios/<id>.py.
    # O registro explícito permanece por compatibilidade com a arquitetura atual.
    scenario_registry.SCENARIO_LOADERS[SCENARIO_ID] = {
        "config_loader": obter_configuracao,
        "routes_loader": obter_rotas,
        "recoveries_loader": obter_recuperacoes,
        "endings_loader": obter_encerramentos,
    }

    # Única autoridade narrativa da Casada Frustrada. Ela é instalada cedo na
    # cadeia de st.title para ser aplicada por último ao construtor do prompt,
    # depois das integrações legadas ainda carregadas por compatibilidade.
    install_casada_frustrada_canonical_prompt()

    # Células administrativas vazias significam "usar o padrão do código".
    # Isso restaura cenários antigos após a expansão do schema da aba SCENARIOS.
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
