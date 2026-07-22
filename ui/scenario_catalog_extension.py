from __future__ import annotations

from scenarios import registry as scenario_registry
from scenarios.stories.casada_frustrada.config import (
    SCENARIO_ID,
    obter_configuracao,
)
from scenarios.stories.casada_frustrada.endings import obter_encerramentos
from scenarios.stories.casada_frustrada.recoveries import obter_recuperacoes
from scenarios.stories.casada_frustrada.routes import obter_rotas


SCENARIO_CATALOG_EXTENSION_VERSION = (
    "scenario-catalog-extension-v1-casada-frustrada"
)

_INSTALLED = False


def install_scenario_catalog_extension() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    scenario_registry.SCENARIO_LOADERS[SCENARIO_ID] = {
        "config_loader": obter_configuracao,
        "routes_loader": obter_rotas,
        "recoveries_loader": obter_recuperacoes,
        "endings_loader": obter_encerramentos,
    }
    _INSTALLED = True


__all__ = [
    "SCENARIO_CATALOG_EXTENSION_VERSION",
    "install_scenario_catalog_extension",
]
