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


__all__ = [
    "SCENARIO_CONFIG",
    "SCENARIO_ID",
    "SCENARIO_VERSION",
    "ROUTES",
    "ROUTES_VERSION",
    "RECOVERY_ROUTES",
    "RECOVERIES_VERSION",
    "ENDINGS",
    "ENDINGS_VERSION",
    "obter_configuracao",
    "obter_rotas",
    "obter_recuperacoes",
    "obter_encerramentos",
]
