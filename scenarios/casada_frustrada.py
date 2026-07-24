from __future__ import annotations

"""Módulo público padronizado do cenário Casada Frustrada.

A implementação detalhada permanece em ``scenarios/stories/casada_frustrada``.
O registro e as integrações externas devem importar este módulo, exatamente como
fazem com ``scenarios.vizinha_porta_trancada``.
"""

from scenarios.stories.casada_frustrada.config import (
    SCENARIO_CONFIG,
    SCENARIO_ID,
    SCENARIO_VERSION,
    obter_configuracao,
)
from scenarios.stories.casada_frustrada.endings import (
    ENDINGS,
    ENDINGS_VERSION,
    obter_encerramentos,
)
from scenarios.stories.casada_frustrada.recoveries import (
    RECOVERIES_VERSION,
    RECOVERY_ROUTES,
    obter_recuperacoes,
)
from scenarios.stories.casada_frustrada.routes import (
    ROUTES,
    ROUTES_VERSION,
    obter_rotas,
)


PUBLIC_SCENARIO_MODULE_VERSION = (
    "casada-frustrada-public-module-v1-standardized"
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
