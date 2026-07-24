from __future__ import annotations

"""Módulo público padronizado do cenário Vizinha Porta Trancada.

A implementação detalhada permanece em
``scenarios/stories/vizinha_porta_trancada``. Registro, catálogo e integrações
externas devem importar este módulo público.
"""

from scenarios.stories.vizinha_porta_trancada.config import (
    SCENARIO_CONFIG,
    SCENARIO_ID,
    SCENARIO_VERSION,
    obter_configuracao,
)
from scenarios.stories.vizinha_porta_trancada.endings import (
    ENDINGS,
    ENDINGS_VERSION,
    obter_encerramentos,
)
from scenarios.stories.vizinha_porta_trancada.recoveries import (
    RECOVERIES_VERSION,
    RECOVERY_ROUTES,
    obter_recuperacoes,
)
from scenarios.stories.vizinha_porta_trancada.routes import (
    ROUTES,
    ROUTES_VERSION,
    obter_rotas,
)


PUBLIC_SCENARIO_MODULE_VERSION = (
    "vizinha-porta-trancada-public-module-v1-standardized"
)


__all__ = [
    "PUBLIC_SCENARIO_MODULE_VERSION",
    "SCENARIO_ID",
    "SCENARIO_VERSION",
    "SCENARIO_CONFIG",
    "ROUTES_VERSION",
    "ROUTES",
    "RECOVERIES_VERSION",
    "RECOVERY_ROUTES",
    "ENDINGS_VERSION",
    "ENDINGS",
    "obter_configuracao",
    "obter_rotas",
    "obter_recuperacoes",
    "obter_encerramentos",
]
