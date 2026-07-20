from __future__ import annotations

import json

from copy import deepcopy
from typing import Any

from openrouter_client import (
    OpenRouterError,
    chamar_openrouter,
)


DIRECTOR_SYSTEM_PROMPT = """
Você é um diretor narrativo interno.

Sua função é interpretar semanticamente o último turno de uma
fantasia interativa entre adultos.

Você não escreve a resposta de Mary.

Você analisa:
- o que o usuário realmente fez, disse, recusou ou propôs;
- o que mudou concretamente na cena;
- quais elementos foram resolvidos;
- quais continuam abertos;
- se a relação avançou, recuou ou permaneceu igual;
- se a história progrediu;
- qual deve ser o foco imediato da próxima resposta;
- se Mary precisa criar um pequeno gancho para evitar estagnação.

A história é adaptativa.

Não exija que o usuário siga um roteiro predeterminado.
Não considere desvios como erro.
Não force o retorno à rota original quando a nova direção for coerente.
Não invente fatos ausentes.
Não determine sentimentos internos do usuário.
Não pule diretamente para romance, sexo, clímax ou encerramento.
Não avance várias etapas em um único turno.

As fases narrativas são orientações aproximadas:
- opening;
- familiarity;
- tension;
- intimacy;
- climax;
- aftercare;
- ending.

A fase deve depender dos acontecimentos confirmados e do grau de
envolvimento, não apenas do número de interações.

Retorne exclusivamente um objeto JSON válido.
Não use markdown.
Não acrescente explicações fora do JSON.
""".strip()


def normalizar_lista_texto(
    valor: Any,
) -> list[str]:
    if not isinstance(
        valor,
        list,
    ):
        return []

    return [
        str(item).strip()
        for item in valor
        if str(
            item or ""
        ).strip()
    ]


def criar_analise_diretor_padrao(
    scene_state: dict[str, Any],
) -> dict[str, Any]:
    return {
        "user_action": "",
        "scene_changed": False,
        "new_facts": [],
        "resolved_elements": [],
        "open_elements": [],
        "relationship_effect": "unchanged",
        "narrative_progress": False,
        "recommended_phase": str(
            scene_state.get(
                "current_phase",
                "opening",
            )
            or "opening"
        ),
        "recommended_focus": "",
        "should_create_hook": False,
        "hook_purpose": "",
        "user_disengaged": False,
        "climax_signal": False,
        "satisfaction_signal": False,
        "ending_signal": False,
        "confidence": 0.0,
    }


def extrair_json_objeto(
    texto: str,
) -> dict[str, Any]:
    texto = str(
        texto or ""
    ).strip()

    if texto.startswith(
        "```"
    ):
        linhas = texto.splitlines()

        if linhas:
            linhas = linhas[1:]

        if (
            linhas
            and linhas[-1].strip()
            == "```"
        ):
            linhas = linhas[:-1]

        texto = "\n".join(
            linhas
        ).strip()

        if texto.lower().startswith(
            "json"
        ):
            texto = texto[4:].strip()

    inicio = texto.find(
        "{"
    )

    fim = texto.rfind(
        "}"
    )

    if (
        inicio < 0
        or fim < inicio
    ):
        raise ValueError(
            "O diretor não retornou um objeto JSON."
        )

    resultado = json.loads(
        texto[inicio: fim + 1]
    )

    if not isinstance(
        resultado,
        dict,
    ):
        raise ValueError(
            "A análise do diretor não é um objeto."
        )

    return resultado


def normalizar_analise_diretor(
    analise: dict[str, Any],
    *,
    scene_state: dict[str, Any],
) -> dict[str, Any]:
    padrao = criar_analise_diretor_padrao(
        scene_state
    )

    resultado = deepcopy(
        padrao
    )

    resultado[
        "user_action"
    ] = str(
        analise.get(
            "user_action",
            "",
        )
        or ""
    ).strip()

    for campo in (
        "scene_changed",
        "narrative_progress",
        "should_create_hook",
        "user_disengaged",
        "climax_signal",
        "satisfaction_signal",
        "ending_signal",
    ):
        resultado[campo] = bool(
            analise.get(
                campo,
                padrao[campo],
            )
        )

    for campo in (
        "new_facts",
        "resolved_elements",
        "open_elements",
    ):
        resultado[campo] = (
            normalizar_lista_texto(
                analise.get(
                    campo
                )
            )
        )

    relationship_effect = str(
        analise.get(
            "relationship_effect",
            "unchanged",
        )
        or "unchanged"
    ).strip().lower()

    if relationship_effect not in {
        "increased",
        "decreased",
        "unchanged",
        "mixed",
    }:
        relationship_effect = (
            "unchanged"
        )

    resultado[
        "relationship_effect"
    ] = relationship_effect

    recommended_phase = str(
        analise.get(
            "recommended_phase",
            padrao[
                "recommended_phase"
            ],
        )
        or padrao[
            "recommended_phase"
        ]
    ).strip().lower()

    if recommended_phase not in {
        "opening",
        "familiarity",
        "tension",
        "intimacy",
        "climax",
        "aftercare",
        "ending",
    }:
        recommended_phase = padrao[
            "recommended_phase"
        ]

    resultado[
        "recommended_phase"
    ] = recommended_phase

    resultado[
        "recommended_focus"
    ] = str(
        analise.get(
            "recommended_focus",
            "",
        )
        or ""
    ).strip()

    resultado[
        "hook_purpose"
    ] = str(
        analise.get(
            "hook_purpose",
            "",
        )
        or ""
    ).strip()

    try:
        confidence = float(
            analise.get(
                "confidence",
                0.0,
            )
            or 0.0
        )

    except (
        TypeError,
        ValueError,
    ):
        confidence = 0.0

    resultado[
        "confidence"
    ] = max(
        0.0,
        min(
            1.0,
            confidence,
        ),
    )

    return resultado

def integrar_direcao_cenario(
    *,
    turn_direction: dict[str, Any],
    analise_cenario: dict[str, Any],
    scene_state: dict[str, Any],
) -> dict[str, Any]:
    direcao = deepcopy(
        turn_direction
    )

    if not analise_cenario:
        return direcao

    scene_active = bool(
        scene_state.get(
            "scene_active",
            False,
        )
    )

    if not scene_active:
        return direcao

    turns_without_advance = int(
        scene_state.get(
            "turns_since_story_advance",
            0,
        )
        or 0
    )

    narrative_progress = bool(
        analise_cenario.get(
            "narrative_progress",
            False,
        )
    )

    should_create_hook = bool(
        analise_cenario.get(
            "should_create_hook",
            False,
        )
    )

    user_disengaged = bool(
        analise_cenario.get(
            "user_disengaged",
            False,
        )
    )

    # Em uma fantasia ativa, a cena precisa ser preservada,
    # independentemente do modo geral escolhido.
    direcao[
        "preserve_current_scene"
    ] = True

    direcao[
        "experience_mode"
    ] = "continue_shared_fantasy"

    direcao[
        "response_scope"
    ] = "scene"

    direcao[
        "direction_reason"
    ] = (
        "active_scenario_integrated"
    )

    # O diretor geral continua decidindo personalidade,
    # intensidade, humor, romance e sexualidade.
    #
    # O cenário apenas aumenta a iniciativa quando houver
    # necessidade narrativa.
    if (
        should_create_hook
        or turns_without_advance >= 4
    ):
        direcao[
            "should_lead"
        ] = True

        direcao[
            "create_narrative_pending"
        ] = True

    # Se houve avanço criado pelo próprio usuário, Mary não
    # precisa imediatamente inventar outro acontecimento.
    if narrative_progress:
        direcao[
            "create_narrative_pending"
        ] = False

    # Uma saída clara do usuário não deve ser combatida.
    if user_disengaged:
        direcao[
            "should_lead"
        ] = False

        direcao[
            "create_narrative_pending"
        ] = False

        direcao[
            "avoid_question"
        ] = True

    direcao[
        "scenario_focus"
    ] = str(
        analise_cenario.get(
            "recommended_focus",
            "",
        )
        or ""
    ).strip()

    direcao[
        "scenario_hook_purpose"
    ] = str(
        analise_cenario.get(
            "hook_purpose",
            "",
        )
        or ""
    ).strip()

    direcao[
        "scenario_phase"
    ] = str(
        analise_cenario.get(
            "recommended_phase",
            scene_state.get(
                "current_phase",
                "opening",
            ),
        )
        or "opening"
    ).strip()

    return direcao


def analisar_turno_cenario(
    *,
    api_key: str,
    model: str,
    scenario_config: dict[str, Any],
    scene_state: dict[str, Any],
    user_text: str,
    last_mary_response: str,
    recent_messages: list[dict[str, Any]],
) -> dict[str, Any]:
    phases = scenario_config.get(
        "phases"
    )

    if not isinstance(
        phases,
        dict,
    ):
        phases = {}

    contexto = {
        "scenario": {
            "scenario_id": scenario_config.get(
                "scenario_id"
            ),
            "title": scenario_config.get(
                "title"
            ),
            "short_description": (
                scenario_config.get(
                    "short_description"
                )
            ),
            "phases": phases,
        },
        "scene_state": scene_state,
        "last_mary_response": (
            last_mary_response
        ),
        "user_text": user_text,
        "recent_messages": (
            recent_messages[-8:]
        ),
        "required_output": {
            "user_action": (
                "Resumo concreto e curto da ação "
                "ou decisão do usuário."
            ),
            "scene_changed": "boolean",
            "new_facts": [
                "Somente fatos confirmados"
            ],
            "resolved_elements": [
                "Problemas ou pendências resolvidas"
            ],
            "open_elements": [
                "Problemas, desejos ou situações ainda abertas"
            ],
            "relationship_effect": (
                "increased, decreased, unchanged ou mixed"
            ),
            "narrative_progress": "boolean",
            "recommended_phase": (
                "opening, familiarity, tension, intimacy, "
                "climax, aftercare ou ending"
            ),
            "recommended_focus": (
                "Foco imediato da próxima resposta, "
                "sem escrever a fala de Mary"
            ),
            "should_create_hook": (
                "boolean; verdadeiro apenas quando um "
                "pequeno movimento ajudaria a evitar estagnação"
            ),
            "hook_purpose": (
                "Objetivo abstrato do gancho, sem impor "
                "um acontecimento específico"
            ),
            "user_disengaged": "boolean",
            "climax_signal": "boolean",
            "satisfaction_signal": "boolean",
            "ending_signal": "boolean",
            "confidence": "número entre 0 e 1",
        },
    }

    messages = [
        {
            "role": "system",
            "content": (
                DIRECTOR_SYSTEM_PROMPT
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                contexto,
                ensure_ascii=False,
            ),
        },
    ]

    try:
        resposta = chamar_openrouter(
            messages=messages,
            model=model,
            api_key=api_key,
        )

        analise_bruta = (
            extrair_json_objeto(
                resposta
            )
        )

        return normalizar_analise_diretor(
            analise_bruta,
            scene_state=scene_state,
        )

    except (
        OpenRouterError,
        ValueError,
        json.JSONDecodeError,
    ):
        return criar_analise_diretor_padrao(
            scene_state
        )

  def adicionar_sem_duplicar(
    destino: list[str],
    novos_itens: list[str],
    *,
    limite: int = 30,
) -> list[str]:
    resultado = list(
        destino
    )

    for item in novos_itens:
        item = str(
            item or ""
        ).strip()

        if (
            item
            and item not in resultado
        ):
            resultado.append(
                item
            )

    return resultado[-limite:]


def aplicar_analise_ao_estado(
    *,
    scene_state: dict[str, Any],
    analise: dict[str, Any],
    interaction_number: int,
) -> dict[str, Any]:
    estado = deepcopy(
        scene_state
    )

    estado[
        "interaction_count"
    ] = interaction_number

    estado[
        "last_user_action"
    ] = analise.get(
        "user_action",
        "",
    )

    estado[
        "last_director_decision"
    ] = analise.get(
        "recommended_focus",
        "",
    )

    fatos = estado.get(
        "confirmed_facts"
    )

    if not isinstance(
        fatos,
        list,
    ):
        fatos = []

    estado[
        "confirmed_facts"
    ] = adicionar_sem_duplicar(
        fatos,
        analise.get(
            "new_facts",
            [],
        ),
    )

    elementos_abertos = estado.get(
        "open_elements"
    )

    if not isinstance(
        elementos_abertos,
        list,
    ):
        elementos_abertos = []

    resolvidos = set(
        analise.get(
            "resolved_elements",
            [],
        )
    )

    elementos_abertos = [
        item
        for item in elementos_abertos
        if item not in resolvidos
    ]

    estado[
        "open_elements"
    ] = adicionar_sem_duplicar(
        elementos_abertos,
        analise.get(
            "open_elements",
            [],
        ),
    )

    if (
        analise.get(
            "confidence",
            0.0,
        )
        >= 0.55
    ):
        estado[
            "current_phase"
        ] = analise.get(
            "recommended_phase",
            estado.get(
                "current_phase",
                "opening",
            ),
        )

    if analise.get(
        "narrative_progress"
    ):
        estado[
            "turns_since_story_advance"
        ] = 0

        estado[
            "last_story_advance_at"
        ] = interaction_number

    else:
        estado[
            "turns_since_story_advance"
        ] = (
            int(
                estado.get(
                    "turns_since_story_advance",
                    0,
                )
                or 0
            )
            + 1
        )

    estado[
        "climax_reached"
    ] = bool(
        estado.get(
            "climax_reached"
        )
        or analise.get(
            "climax_signal"
        )
    )

    estado[
        "satisfaction_detected"
    ] = bool(
        estado.get(
            "satisfaction_detected"
        )
        or analise.get(
            "satisfaction_signal"
        )
    )

    estado[
        "ending_ready"
    ] = bool(
        estado.get(
            "ending_ready"
        )
        or analise.get(
            "ending_signal"
        )
    )

    if analise.get(
        "user_disengaged"
    ):
        estado[
            "user_disengaged"
        ] = True

    return estadodef montar_direcao_narrativa(
    *,
    analise: dict[str, Any],
    scene_state: dict[str, Any],
) -> str:
    current_phase = str(
        scene_state.get(
            "current_phase",
            "opening",
        )
        or "opening"
    )

    turns_without_advance = int(
        scene_state.get(
            "turns_since_story_advance",
            0,
        )
        or 0
    )

    should_create_hook = bool(
        analise.get(
            "should_create_hook"
        )
    )

    # Proteção antimonotonia.
    if turns_without_advance >= 4:
        should_create_hook = True

    focus = str(
        analise.get(
            "recommended_focus",
            "",
        )
        or ""
    ).strip()

    hook_purpose = str(
        analise.get(
            "hook_purpose",
            "",
        )
        or ""
    ).strip()

    if should_create_hook:
        movimento = """
Neste turno, além de reagir ao usuário, Mary deve criar no máximo
um pequeno movimento narrativo coerente.

Ela decide livremente qual movimento combina com o momento.

Pode ser:
- uma vontade;
- uma observação concreta;
- uma pequena decisão;
- uma mudança de atitude;
- uma complicação natural;
- uma aproximação;
- uma hesitação;
- uma provocação;
- uma informação circunstancial;
- um pedido;
- um convite;
- uma recusa;
- uma escolha.

A lista é apenas ilustrativa. Não escolha mecanicamente um item.

O movimento deve nascer do que já aconteceu e deixar espaço para
o usuário responder.

Não crie acontecimentos aleatórios apenas para movimentar a trama.
Não resolva o movimento no mesmo turno em que ele surgir.
""".strip()

    else:
        movimento = """
Mary não precisa criar um acontecimento novo neste turno.

Ela pode aprofundar o momento atual por meio de reação, emoção,
humor, desconforto, curiosidade, silêncio implícito ou proximidade.

Mesmo sem um novo acontecimento, evite repetir a mesma ideia.
""".strip()

    return f"""
[DIREÇÃO NARRATIVA ADAPTATIVA]

Fase aproximada: {current_phase}
Foco imediato: {focus or "reagir ao movimento atual"}
Objetivo abstrato de eventual gancho:
{hook_purpose or "preservar interesse e continuidade"}
Turnos sem avanço narrativo confirmado:
{turns_without_advance}

{movimento}

REGRAS:

- A ação do usuário tem prioridade sobre qualquer plano anterior.
- Não force uma rota cadastrada.
- Não tente corrigir o usuário por ter escolhido uma solução inesperada.
- Incorpore soluções criativas quando forem coerentes.
- Os objetivos do cenário orientam, mas não determinam eventos específicos.
- A evolução pode ser prática, emocional, relacional, cômica ou sensual.
- Evolução não significa aumentar a intensidade em toda resposta.
- Alterne avanço e aprofundamento.
- Não repita o mesmo conflito apenas para prolongar a história.
- Não acelere artificialmente para atingir uma contagem de interações.
- A meta aproximada de duração não é uma obrigação matemática.
- Não mencione fase, roteiro, gancho ou direção narrativa.
""".strip()
