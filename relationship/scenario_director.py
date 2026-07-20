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
- se Mary precisa criar um pequeno gancho para evitar estagnação;
- se Mary precisa executar uma ação concreta, em vez de apenas cogitar;
- qual deve ser a intensidade da iniciativa de Mary no próximo turno.

Considere que não houve iniciativa efetiva de Mary quando ela apenas:
- disse que talvez faria alguma coisa;
- anunciou que estava quase agindo;
- perguntou se deveria agir;
- repetiu a mesma hesitação do turno anterior;
- descreveu uma vontade sem transformá-la em decisão;
- devolveu imediatamente a decisão ao usuário.

Quando Mary repetir duas vezes a mesma hesitação ou ameaça de ação,
defina mary_initiative_strength como pelo menos 2 no próximo turno.

Quando a cena permanecer no mesmo lugar, objetivo e dinâmica por
três turnos, use intensidade 3, salvo se houver aprofundamento novo
e relevante.

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
        "mary_should_add_affordance": False,
        "mary_initiative_strength": 0,
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
        "mary_should_add_affordance",
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
        initiative_strength = int(
            analise.get(
                "mary_initiative_strength",
                0,
            )
            or 0
        )

    except (
        TypeError,
        ValueError,
    ):
        initiative_strength = 0

    resultado[
        "mary_initiative_strength"
    ] = max(
        0,
        min(
            3,
            initiative_strength,
        ),
    )

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

    mary_should_add_affordance = bool(
        analise_cenario.get(
            "mary_should_add_affordance",
            False,
        )
    )

    mary_initiative_strength = int(
        analise_cenario.get(
            "mary_initiative_strength",
            0,
        )
        or 0
    )

    mary_initiative_strength = max(
        0,
        min(
            3,
            mary_initiative_strength,
        ),
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
    precisa_movimento_mary = bool(
        should_create_hook
        or mary_should_add_affordance
        or mary_initiative_strength >= 2
        or turns_without_advance >= 3
    )

    direcao[
        "scenario_initiative_strength"
    ] = mary_initiative_strength

    if precisa_movimento_mary:
        direcao[
            "should_lead"
        ] = True

        direcao[
            "create_narrative_pending"
        ] = True

        direcao[
            "avoid_question"
        ] = False

        if mary_initiative_strength >= 3:
            direcao[
                "response_scope"
            ] = "scene"

            direcao[
                "direction_reason"
            ] = (
                "active_scenario_strong_initiative"
            )

    elif narrative_progress:
        # O usuário já produziu avanço suficiente neste turno.
        # Mary pode aprofundar o acontecimento sem ser obrigada
        # a criar imediatamente outra pendência.
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
                "Foco imediato da próxima resposta. Quando houver necessidade "
                "de iniciativa, descreva uma ação que Mary deve efetivamente "
                "começar ou realizar, sem escrever a fala completa e sem "
                "determinar a reação do usuário."
            ),
            "should_create_hook": (
                "boolean; verdadeiro apenas quando um "
                "pequeno movimento ajudaria a evitar estagnação"
            ),
            "mary_should_add_affordance": (
                "boolean; verdadeiro quando a próxima resposta de Mary "
                "deve deixar uma ação, escolha, tensão ou pendência "
                "concreta à qual o usuário possa reagir"
            ),
            "mary_initiative_strength": (
                "Número inteiro de 0 a 3. "
                "0 = apenas reagir; "
                "1 = acrescentar atitude ou opinião; "
                "2 = executar um movimento concreto; "
                "3 = executar uma mudança narrativa marcante, ainda coerente "
                "e sem resolver toda a cena."
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

    estado[
        "last_mary_initiative_strength"
    ] = int(
        analise.get(
            "mary_initiative_strength",
            0,
        )
        or 0
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

    return estado


def montar_direcao_narrativa(
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

    mary_should_add_affordance = bool(
        analise.get(
            "mary_should_add_affordance"
        )
    )

    initiative_strength = int(
        analise.get(
            "mary_initiative_strength",
            0,
        )
        or 0
    )

    initiative_strength = max(
        0,
        min(
            3,
            initiative_strength,
        ),
    )

    precisa_movimento_mary = bool(
        should_create_hook
        or mary_should_add_affordance
        or initiative_strength >= 2
        or turns_without_advance >= 3
    )

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

    if precisa_movimento_mary:
        movimento = """
Além de reagir ao usuário, Mary deve executar exatamente um
movimento narrativo próprio e perceptível neste turno.

Ela não deve apenas cogitar, ameaçar, ensaiar ou perguntar se
deveria agir. Mary toma uma decisão compatível com o momento
e começa ou conclui uma ação concreta.

O movimento pode ser:

- mudar de posição ou ambiente;
- aproximar-se ou afastar-se;
- iniciar uma tarefa;
- fazer um pedido direto;
- estabelecer uma condição;
- recusar alguma coisa;
- revelar uma reação concreta;
- provocar deliberadamente;
- tomar uma pequena decisão;
- interromper uma situação;
- criar uma consequência natural;
- alterar o objetivo imediato da cena.

A lista é ilustrativa. Mary escolhe livremente o movimento
mais coerente com o histórico.

REGRAS DO MOVIMENTO:

- O movimento deve mudar alguma coisa observável na cena,
  na relação ou no objetivo imediato.
- Mary executa o movimento; não fica apenas pensando nele.
- Não use “quase”, “talvez”, “estou pensando em”, “vou acabar”,
  “quem sabe” ou “será que eu deveria” como substituto da ação.
- Mary não deve pedir ao usuário autorização para toda iniciativa
  não íntima e cotidiana.
- A ação de Mary não determina a reação do usuário.
- Mary pode abrir uma porta, aproximar-se, bater, chamar, sentar,
  levantar, escolher, pedir ou recusar; o usuário continua livre
  para reagir como desejar.
- Introduza apenas um movimento relevante.
- Não resolva toda a situação no mesmo turno.
- Não crie acontecimentos aleatórios ou desconectados.
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

Intensidade da iniciativa de Mary:
{initiative_strength}

INTERPRETAÇÃO DA INTENSIDADE:

- 0: Mary reage sem precisar criar movimento.
- 1: Mary acrescenta personalidade, opinião ou vontade.
- 2: Mary executa uma ação concreta que altera o momento.
- 3: Mary produz uma mudança narrativa perceptível, coerente
  com a fase, sem resolver toda a história.

Quando a intensidade for 2 ou 3, uma intenção não executada
não cumpre a direção.

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
