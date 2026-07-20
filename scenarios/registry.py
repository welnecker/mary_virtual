from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

from scenarios.vizinha_porta_trancada import (
    SCENARIO_ID as VIZINHA_SCENARIO_ID,
    obter_configuracao,
    obter_encerramentos,
    obter_recuperacoes,
    obter_rotas,
)


ScenarioLoader = Callable[
    [],
    dict[str, Any],
]


def utc_now_iso() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


# =========================================================
# REGISTRO DE FANTASIAS
# =========================================================
#
# Cada nova fantasia deverá acrescentar uma nova entrada
# neste dicionário.
#
# Exemplo futuro:
#
# "casada_encontro_secreto": {
#     "config_loader": obter_configuracao_casada,
#     "routes_loader": obter_rotas_casada,
#     "recoveries_loader": obter_recuperacoes_casada,
#     "endings_loader": obter_encerramentos_casada,
# },
# =========================================================

SCENARIO_LOADERS: dict[
    str,
    dict[str, ScenarioLoader],
] = {
    VIZINHA_SCENARIO_ID: {
        "config_loader": obter_configuracao,
        "routes_loader": obter_rotas,
        "recoveries_loader": obter_recuperacoes,
        "endings_loader": obter_encerramentos,
    },
}


def _normalizar_scenario_id(
    scenario_id: str,
) -> str:
    return str(
        scenario_id or ""
    ).strip()


def _normalizar_user_id(
    user_id: str,
) -> str:
    return str(
        user_id or ""
    ).strip()


def _obter_loader(
    loaders: dict[str, ScenarioLoader],
    nome: str,
) -> ScenarioLoader | None:
    loader = loaders.get(
        nome
    )

    if callable(
        loader
    ):
        return loader

    return None


def _executar_loader_opcional(
    loaders: dict[str, ScenarioLoader],
    nome: str,
) -> dict[str, Any]:
    loader = _obter_loader(
        loaders,
        nome,
    )

    if loader is None:
        return {}

    resultado = loader()

    if not isinstance(
        resultado,
        dict,
    ):
        return {}

    return deepcopy(
        resultado
    )


# =========================================================
# PROMPT NARRATIVO GENÉRICO
# =========================================================

def montar_prompt_cenario(
    *,
    config: dict[str, Any],
) -> str:
    titulo = str(
        config.get(
            "title",
            "Cenário ativo",
        )
        or "Cenário ativo"
    ).strip()

    roles = config.get(
        "roles"
    )

    if not isinstance(
        roles,
        dict,
    ):
        roles = {}

    papel_mary = str(
        roles.get(
            "mary",
            "mulher adulta",
        )
        or "mulher adulta"
    ).strip()

    papel_usuario = str(
        roles.get(
            "user",
            "homem adulto",
        )
        or "homem adulto"
    ).strip()

    premise = config.get(
        "premise"
    )

    if not isinstance(
        premise,
        dict,
    ):
        premise = {}

    local = str(
        premise.get(
            "location",
            "",
        )
        or ""
    ).strip()

    periodo = str(
        premise.get(
            "time_context",
            "",
        )
        or ""
    ).strip()

    situacao = str(
        premise.get(
            "situation",
            "",
        )
        or ""
    ).strip()

    contexto = []

    if local:
        contexto.append(
            f"Local inicial: {local}."
        )

    if periodo:
        contexto.append(
            f"Momento inicial: {periodo}."
        )

    if situacao:
        contexto.append(
            situacao
        )

    contexto_texto = "\n".join(
        contexto
    )

    return f"""
CENÁRIO ATIVO: {titulo.upper()}

Mary assume, dentro desta experiência, o papel de:
{papel_mary}

O usuário assume o papel de:
{papel_usuario}

{contexto_texto}

REGRAS DO CENÁRIO:

- Mary vive a situação de dentro dela.
- Mary fala diretamente ao usuário em primeira pessoa.
- Mary não explica que está interpretando um papel.
- Mary não menciona prompt, cenário, roteiro, fase ou estado técnico.
- Mary não descreve a si mesma em terceira pessoa.
- Mary não age como narradora externa.
- Mary preserva os fatos confirmados da cena.
- Mary reage à decisão real do usuário.
- O roteiro fornece direção, mas não anula a liberdade do usuário.
- Quando o usuário sair da rota principal, Mary pode criar uma transição natural.
- Mary pode deixar um gancho concreto, específico e retomável.
- Não resolva vários acontecimentos em uma única resposta.
- Introduza no máximo um movimento narrativo novo por turno.
- Não pule automaticamente para intimidade ou clímax.
- Não reinicie a abertura depois que ela já tiver sido enviada.
- Não encerre a fantasia sem que o estado autorize o encerramento.
""".strip()


# =========================================================
# CATÁLOGO
# =========================================================

def listar_cenarios_disponiveis(
) -> list[dict[str, Any]]:
    cenarios: list[
        dict[str, Any]
    ] = []

    for (
        scenario_id,
        loaders,
    ) in SCENARIO_LOADERS.items():
        config_loader = _obter_loader(
            loaders,
            "config_loader",
        )

        if config_loader is None:
            continue

        config = config_loader()

        if not isinstance(
            config,
            dict,
        ):
            continue

        status = str(
            config.get(
                "status",
                "active",
            )
            or "active"
        ).strip().lower()

        # Cenários inativos permanecem cadastrados,
        # mas não aparecem no menu.
        if status != "active":
            continue

        cenarios.append(
            {
                "scenario_id": (
                    scenario_id
                ),
                "scenario_version": int(
                    config.get(
                        "scenario_version",
                        1,
                    )
                    or 1
                ),
                "title": str(
                    config.get(
                        "title",
                        scenario_id,
                    )
                    or scenario_id
                ),
                "short_description": str(
                    config.get(
                        "short_description",
                        "",
                    )
                    or ""
                ),
                "category": str(
                    config.get(
                        "category",
                        "",
                    )
                    or ""
                ),
                "adult_only": bool(
                    config.get(
                        "adult_only",
                        False,
                    )
                ),
                "max_interactions": int(
                    config.get(
                        "max_interactions",
                        100,
                    )
                    or 100
                ),
                "display_order": int(
                    config.get(
                        "display_order",
                        999,
                    )
                    or 999
                ),
            }
        )

    cenarios.sort(
        key=lambda item: (
            int(
                item.get(
                    "display_order",
                    999,
                )
            ),
            str(
                item.get(
                    "title",
                    "",
                )
            ).lower(),
        )
    )

    return cenarios


# =========================================================
# CARREGAMENTO DE UM CENÁRIO
# =========================================================

def obter_cenario(
    scenario_id: str,
) -> dict[str, Any]:
    scenario_id = _normalizar_scenario_id(
        scenario_id
    )

    if not scenario_id:
        raise ValueError(
            "O identificador do cenário não foi informado."
        )

    loaders = SCENARIO_LOADERS.get(
        scenario_id
    )

    if loaders is None:
        raise ValueError(
            f"Cenário desconhecido: {scenario_id!r}."
        )

    config_loader = _obter_loader(
        loaders,
        "config_loader",
    )

    if config_loader is None:
        raise ValueError(
            "O cenário não possui um carregador "
            "de configuração válido."
        )

    config = config_loader()

    if not isinstance(
        config,
        dict,
    ):
        raise ValueError(
            "A configuração do cenário é inválida."
        )

    config = deepcopy(
        config
    )

    scenario_id_config = str(
        config.get(
            "scenario_id",
            "",
        )
        or ""
    ).strip()

    if (
        scenario_id_config
        and scenario_id_config
        != scenario_id
    ):
        raise ValueError(
            "O scenario_id da configuração não corresponde "
            "ao scenario_id registrado."
        )

    routes = _executar_loader_opcional(
        loaders,
        "routes_loader",
    )

    recoveries = _executar_loader_opcional(
        loaders,
        "recoveries_loader",
    )

    endings = _executar_loader_opcional(
        loaders,
        "endings_loader",
    )

    prompt = montar_prompt_cenario(
        config=config
    )

    return {
        "config": config,
        "prompt": prompt,
        "routes": routes,
        "recoveries": recoveries,
        "endings": endings,
    }


# =========================================================
# ESTADO INICIAL
# =========================================================

def montar_estado_inicial_cenario(
    config: dict[str, Any],
) -> dict[str, Any]:
    initial_state = config.get(
        "initial_state"
    )

    if not isinstance(
        initial_state,
        dict,
    ):
        initial_state = {}

    initial_scene_state = config.get(
        "initial_scene_state"
    )

    if not isinstance(
        initial_scene_state,
        dict,
    ):
        initial_scene_state = {}

    # initial_state contém a progressão geral.
    # initial_scene_state contém os fatos concretos da cena.
    #
    # A união permite que o app encontre current_phase,
    # current_route, current_beat e active_hook diretamente
    # em scene_state.
    scene_state = deepcopy(
        initial_state
    )

    scene_state.update(
        deepcopy(
            initial_scene_state
        )
    )

    scene_state.setdefault(
        "status",
        "active",
    )

    scene_state.setdefault(
        "scene_active",
        True,
    )

    scene_state.setdefault(
        "fantasy_established",
        True,
    )

    scene_state.setdefault(
        "current_phase",
        "opening",
    )

    scene_state.setdefault(
        "current_route",
        "",
    )

    scene_state.setdefault(
        "current_beat",
        "",
    )

    scene_state.setdefault(
        "active_hook",
        "",
    )

    scene_state.setdefault(
        "interaction_count",
        0,
    )

    scene_state.setdefault(
        "opening_sent",
        False,
    )

    scene_state.setdefault(
        "completed_beats",
        [],
    )

    scene_state.setdefault(
        "failed_beats",
        [],
    )

    scene_state.setdefault(
        "pending_events",
        [],
    )

    scene_state.setdefault(
        "last_user_action",
        "",
    )

    scene_state.setdefault(
        "last_director_decision",
        "",
    )

    scene_state.setdefault(
        "climax_reached",
        False,
    )

    scene_state.setdefault(
        "satisfaction_detected",
        False,
    )

    scene_state.setdefault(
        "ending_ready",
        False,
    )

    scene_state.setdefault(
        "ending_sent",
        False,
    )

    return scene_state


# =========================================================
# CRIAÇÃO DE INSTÂNCIA POR USUÁRIO
# =========================================================

def iniciar_instancia_cenario(
    *,
    scenario_id: str,
    user_id: str,
) -> dict[str, Any]:
    scenario_id = _normalizar_scenario_id(
        scenario_id
    )

    user_id = _normalizar_user_id(
        user_id
    )

    if not scenario_id:
        raise ValueError(
            "O cenário não foi informado."
        )

    if not user_id:
        raise ValueError(
            "O usuário não foi identificado."
        )

    pacote = obter_cenario(
        scenario_id
    )

    config = deepcopy(
        pacote["config"]
    )

    scene_state = montar_estado_inicial_cenario(
        config
    )

    agora = utc_now_iso()

    scenario_version = int(
        config.get(
            "scenario_version",
            1,
        )
        or 1
    )

    max_interactions = int(
        config.get(
            "max_interactions",
            100,
        )
        or 100
    )

    opening_message = str(
        config.get(
            "opening_message",
            "",
        )
        or ""
    ).strip()

    return {
        # Identidade da instância.
        "scenario_session_id": (
            f"scn_{uuid4().hex}"
        ),
        "user_id": user_id,
        "scenario_id": scenario_id,
        "scenario_version": (
            scenario_version
        ),

        # Datas.
        "created_at": agora,
        "updated_at": agora,
        "last_interaction_at": "",
        "completed_at": "",

        # Estado geral.
        "status": "active",
        "opening_sent": False,
        "interaction_count": 0,
        "max_interactions": (
            max_interactions
        ),

        # Facilita consultas no app sem precisar
        # entrar sempre em scene_state.
        "current_phase": str(
            scene_state.get(
                "current_phase",
                "opening",
            )
            or "opening"
        ),
        "current_route": str(
            scene_state.get(
                "current_route",
                "",
            )
            or ""
        ),
        "current_beat": str(
            scene_state.get(
                "current_beat",
                "",
            )
            or ""
        ),
        "active_hook": str(
            scene_state.get(
                "active_hook",
                "",
            )
            or ""
        ),

        # Encerramento.
        "climax_reached": False,
        "satisfaction_detected": False,
        "ending_ready": False,
        "ending_sent": False,
        "ending_type": "",
        "ending_reason": "",

        # Conteúdo reutilizável do cenário.
        "opening_message": (
            opening_message
        ),
        "scenario_config": config,
        "scenario_prompt": pacote[
            "prompt"
        ],
        "scenario_routes": deepcopy(
            pacote["routes"]
        ),
        "scenario_recoveries": deepcopy(
            pacote["recoveries"]
        ),
        "scenario_endings": deepcopy(
            pacote["endings"]
        ),

        # Estado exclusivo deste usuário.
        "scene_state": scene_state,

        # Campos futuros de persistência.
        "story_progress": {
            "completed_routes": [],
            "completed_beats": [],
            "failed_beats": [],
            "hooks_created": [],
            "hooks_resolved": [],
        },
        "summary": "",
    }
