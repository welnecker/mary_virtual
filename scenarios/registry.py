from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

from scenarios.schema import (
    SCENARIO_STATUS_ACTIVE,
    normalizar_config_cenario,
)
from scenarios.stories.vizinha_porta_trancada.config import (
    SCENARIO_ID as VIZINHA_SCENARIO_ID,
    obter_configuracao as obter_configuracao_vizinha,
)

# Compatibilidade temporária durante a migração da história da vizinha.
# Rotas, recuperações e encerramentos continuam no arquivo antigo até
# que os respectivos módulos da nova pasta sejam preenchidos.
from scenarios.vizinha_porta_trancada import (
    obter_encerramentos as obter_encerramentos_vizinha,
    obter_recuperacoes as obter_recuperacoes_vizinha,
    obter_rotas as obter_rotas_vizinha,
)


ScenarioLoader = Callable[[], dict[str, Any]]


SCENARIO_LOADERS: dict[
    str,
    dict[str, ScenarioLoader],
] = {
    VIZINHA_SCENARIO_ID: {
        "config_loader": obter_configuracao_vizinha,
        "routes_loader": obter_rotas_vizinha,
        "recoveries_loader": obter_recuperacoes_vizinha,
        "endings_loader": obter_encerramentos_vizinha,
    },
}


def utc_now_iso() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


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


def _carregar_configuracao(
    *,
    scenario_id: str,
    loaders: dict[str, ScenarioLoader],
) -> dict[str, Any]:
    config_loader = _obter_loader(
        loaders,
        "config_loader",
    )

    if config_loader is None:
        raise ValueError(
            "O cenário não possui um carregador de configuração válido."
        )

    config = config_loader()

    if not isinstance(
        config,
        dict,
    ):
        raise ValueError(
            "A configuração do cenário é inválida."
        )

    config = normalizar_config_cenario(
        deepcopy(
            config
        )
    )

    scenario_id_config = str(
        config.get(
            "scenario_id",
            "",
        )
        or ""
    ).strip()

    if scenario_id_config != scenario_id:
        raise ValueError(
            "O scenario_id da configuração não corresponde "
            "ao scenario_id registrado."
        )

    return config


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

    contexto: list[str] = []

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
    cenarios: list[dict[str, Any]] = []

    for scenario_id, loaders in SCENARIO_LOADERS.items():
        try:
            config = _carregar_configuracao(
                scenario_id=scenario_id,
                loaders=loaders,
            )
        except ValueError:
            # Um cenário inválido não pode derrubar o catálogo inteiro.
            # A validação explícita continuará disponível em obter_cenario().
            continue

        if config.get(
            "status"
        ) != SCENARIO_STATUS_ACTIVE:
            continue

        card = deepcopy(
            config.get(
                "card",
                {},
            )
        )

        duration = deepcopy(
            config.get(
                "duration",
                {},
            )
        )

        commerce = deepcopy(
            config.get(
                "commerce",
                {},
            )
        )

        cenarios.append(
            {
                "scenario_id": scenario_id,
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
                "display_order": int(
                    config.get(
                        "display_order",
                        999,
                    )
                    or 999
                ),

                # Metadados completos usados pelo menu de cards.
                "card": card,
                "duration": duration,
                "commerce": commerce,

                # Campos achatados para facilitar a integração atual do app.
                "card_title": str(
                    card.get(
                        "title",
                        "",
                    )
                    or ""
                ),
                "card_subtitle": str(
                    card.get(
                        "subtitle",
                        "",
                    )
                    or ""
                ),
                "card_image": str(
                    card.get(
                        "image",
                        "",
                    )
                    or ""
                ),
                "card_badge": str(
                    card.get(
                        "badge",
                        "",
                    )
                    or ""
                ),
                "button_label_free": str(
                    card.get(
                        "button_label_free",
                        "Jogar gratuitamente",
                    )
                    or "Jogar gratuitamente"
                ),
                "button_label_locked": str(
                    card.get(
                        "button_label_locked",
                        "Desbloquear",
                    )
                    or "Desbloquear"
                ),
                "button_label_unlocked": str(
                    card.get(
                        "button_label_unlocked",
                        "Jogar",
                    )
                    or "Jogar"
                ),
                "access_type": str(
                    commerce.get(
                        "access_type",
                        "paid",
                    )
                    or "paid"
                ),
                "price_cents": int(
                    commerce.get(
                        "price_cents",
                        0,
                    )
                    or 0
                ),
                "currency": str(
                    commerce.get(
                        "currency",
                        "BRL",
                    )
                    or "BRL"
                ),
                "product_id": str(
                    commerce.get(
                        "product_id",
                        "",
                    )
                    or ""
                ),
                "target_interactions": int(
                    duration.get(
                        "target_interactions",
                        48,
                    )
                    or 48
                ),
                "soft_ending_start": int(
                    duration.get(
                        "soft_ending_start",
                        40,
                    )
                    or 40
                ),
                "hard_ending_limit": int(
                    duration.get(
                        "hard_ending_limit",
                        58,
                    )
                    or 58
                ),

                # Compatibilidade com componentes antigos.
                "max_interactions": int(
                    config.get(
                        "max_interactions",
                        duration.get(
                            "hard_ending_limit",
                            58,
                        ),
                    )
                    or 58
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

    config = _carregar_configuracao(
        scenario_id=scenario_id,
        loaders=loaders,
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

    scene_state = deepcopy(
        initial_state
    )

    scene_state.update(
        deepcopy(
            initial_scene_state
        )
    )

    defaults: dict[str, Any] = {
        "status": "active",
        "scene_active": True,
        "fantasy_established": True,
        "current_phase": "opening",
        "current_route": "",
        "current_beat": "",
        "active_hook": "",
        "interaction_count": 0,
        "opening_sent": False,
        "completed_beats": [],
        "failed_beats": [],
        "pending_events": [],
        "last_user_action": "",
        "last_director_decision": "",
        "climax_reached": False,
        "satisfaction_detected": False,
        "ending_ready": False,
        "ending_sent": False,
        "ending_type": "",
        "ending_reason": "",
        "input_locked": False,
        "show_return_to_menu": False,
    }

    for key, value in defaults.items():
        scene_state.setdefault(
            key,
            deepcopy(
                value
            ),
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
        pacote[
            "config"
        ]
    )

    scene_state = montar_estado_inicial_cenario(
        config
    )

    duration = deepcopy(
        config.get(
            "duration",
            {},
        )
    )

    commerce = deepcopy(
        config.get(
            "commerce",
            {},
        )
    )

    agora = utc_now_iso()

    scenario_version = int(
        config.get(
            "scenario_version",
            1,
        )
        or 1
    )

    hard_ending_limit = int(
        duration.get(
            "hard_ending_limit",
            config.get(
                "max_interactions",
                58,
            ),
        )
        or 58
    )

    opening_message = str(
        config.get(
            "opening_message",
            "",
        )
        or ""
    ).strip()

    return {
        "scenario_session_id": (
            f"scn_{uuid4().hex}"
        ),
        "user_id": user_id,
        "scenario_id": scenario_id,
        "scenario_version": scenario_version,

        "created_at": agora,
        "updated_at": agora,
        "last_interaction_at": "",
        "completed_at": "",

        "status": "active",
        "opening_sent": False,
        "interaction_count": 0,

        # Nova duração estruturada.
        "duration": duration,
        "target_interactions": int(
            duration.get(
                "target_interactions",
                48,
            )
            or 48
        ),
        "soft_ending_start": int(
            duration.get(
                "soft_ending_start",
                40,
            )
            or 40
        ),
        "hard_ending_limit": hard_ending_limit,

        # Compatibilidade com código antigo.
        "max_interactions": hard_ending_limit,

        # Informação comercial é carregada, mas ainda não autoriza acesso.
        # A autorização ficará no service.py da próxima etapa.
        "commerce": commerce,
        "access_type": str(
            commerce.get(
                "access_type",
                "paid",
            )
            or "paid"
        ),

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

        "climax_reached": False,
        "satisfaction_detected": False,
        "ending_ready": False,
        "ending_sent": False,
        "ending_type": "",
        "ending_reason": "",
        "input_locked": False,
        "show_return_to_menu": False,

        "opening_message": opening_message,
        "scenario_config": config,
        "scenario_prompt": pacote[
            "prompt"
        ],
        "scenario_routes": deepcopy(
            pacote[
                "routes"
            ]
        ),
        "scenario_recoveries": deepcopy(
            pacote[
                "recoveries"
            ]
        ),
        "scenario_endings": deepcopy(
            pacote[
                "endings"
            ]
        ),

        "scene_state": scene_state,

        "story_progress": {
            "completed_routes": [],
            "completed_beats": [],
            "failed_beats": [],
            "hooks_created": [],
            "hooks_resolved": [],
        },
        "summary": "",
    }


__all__ = [
    "SCENARIO_LOADERS",
    "iniciar_instancia_cenario",
    "listar_cenarios_disponiveis",
    "montar_estado_inicial_cenario",
    "montar_prompt_cenario",
    "obter_cenario",
]
