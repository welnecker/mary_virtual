from __future__ import annotations

"""Ponte de compatibilidade para a história modular da vizinha.

A fonte de verdade vive em ``scenarios/stories/vizinha_porta_trancada``.
Este módulo permanece apenas para imports históricos do registro e de versões
anteriores do app. Nenhuma regra narrativa deve ser adicionada aqui.
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


LEGACY_BRIDGE_VERSION = "vizinha-legacy-bridge-v2-modular-source"


__all__ = [
    "LEGACY_BRIDGE_VERSION",
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
