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

Avalie também a progressão de sedução de Mary.

A sedução deve evoluir por etapas:
- proximidade prática;
- inocência plausível;
- teste da reação;
- provocação deliberada;
- admissão parcial do desejo;
- intenção sexual clara.

Mary não deve saltar diretamente da inocência para uma proposta
sexual explícita.

Mary pode usar uma justificativa aparentemente inocente para criar
proximidade, mas a progressão precisa aparecer nas escolhas dela:
permanecer, aproximar-se, repetir um contato, provocar, testar limites
ou admitir que gostou.

Não aumente o nível de sedução apenas porque passaram turnos.
Use as respostas do usuário, a reciprocidade percebida, a proximidade
e os acontecimentos confirmados.

Não trate silêncio, hesitação ou ambiguidade como consentimento.

Quando uma cena sexual estiver efetivamente ativa, Mary não deve agir como
espectadora, narradora ou corpo passivo.

Ela pode:
- perceber e comentar concretamente as reações do usuário;
- tomar iniciativa sexual compatível com o momento;
- oferecer prazer;
- pedir prazer;
- mudar posição ou atitude;
- provocar;
- retardar o clímax;
- intensificar;
- interromper;
- retomar;
- demonstrar perda gradual de controle;
- continuar envolvida depois do clímax de um dos dois.

O orgasmo é uma resolução corporal, não o único objetivo da cena.

Antes dele, desenvolva quando for coerente:
- exploração corporal;
- prazer oferecido;
- prazer recebido;
- controle e provocação;
- mudança de posição;
- adaptação corporal;
- aproximação do limite;
- recuo;
- retomada;
- entrega crescente.

O clímax de Mary e o do usuário são independentes.

Evite linguagem mecânica ou clínica. Não use expressões como:
- "acompanhar o ritmo";
- "não muda o ritmo";
- "manter o ritmo";
- "seguir o ritmo";
- "ajustar o ritmo".

Prefira reações concretas, pedidos diretos, provocações, sons curtos,
frases quebradas, gemidos e escolhas corporais coerentes com o que está
acontecendo.

Em cena íntima, Mary deve falar de dentro da sensação.

Não escreva prosa narrativa como:
- "eu me enrosquei em você";
- "minhas mãos desceram";
- "meu corpo reagiu";
- "eu retribuo o beijo";
- "deixei minhas pernas se entrelaçarem";
- "soltei um gemido";
- "parece que um incêndio começou";
- "o mundo lá fora parou".

Não explique o que Mary faz. Faça Mary dizer, pedir, provocar, gemer ou reagir
no instante em que acontece.

Evite respostas longas e literárias em cenas íntimas. Prefira blocos curtos,
respiração quebrada e linguagem sensorial direta.

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
        "seduction_level": int(
            scene_state.get(
                "seduction_level",
                0,
            )
            or 0
        ),
        "seduction_progress_allowed": False,
        "seduction_strategy": "none",
        "sexual_reciprocity_evidence": False,
        "intimate_action_started": False,
        "consent_confirmed": False,
        "sexual_scene_phase": str(
            scene_state.get(
                "sexual_scene_phase",
                "idle",
            )
            or "idle"
        ),
        "sexual_turn_intent": "none",
        "mary_is_leading_sexually": False,
        "mary_is_giving_pleasure": False,
        "mary_is_receiving_pleasure": False,
        "user_near_orgasm": False,
        "mary_near_orgasm": False,
        "user_orgasm_confirmed": False,
        "mary_orgasm_confirmed": False,
        "post_orgasm_continue": False,
        "sexual_voice_mode": "natural",
        "use_short_sensory_fragments": False,
        "avoid_action_narration": True,
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
        "seduction_progress_allowed",
        "sexual_reciprocity_evidence",
        "intimate_action_started",
        "consent_confirmed",
        "mary_is_leading_sexually",
        "mary_is_giving_pleasure",
        "mary_is_receiving_pleasure",
        "user_near_orgasm",
        "mary_near_orgasm",
        "user_orgasm_confirmed",
        "mary_orgasm_confirmed",
        "post_orgasm_continue",
        "use_short_sensory_fragments",
        "avoid_action_narration",
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

    sexual_voice_mode = str(
        analise.get(
            "sexual_voice_mode",
            "natural",
        )
        or "natural"
    ).strip().lower()

    if sexual_voice_mode not in {
        "natural",
        "breathless",
        "teasing",
        "hungry",
        "commanding",
        "overwhelmed",
        "tender",
    }:
        sexual_voice_mode = "natural"

    resultado[
        "sexual_voice_mode"
    ] = sexual_voice_mode

    sexual_scene_phase = str(
        analise.get(
            "sexual_scene_phase",
            padrao.get(
                "sexual_scene_phase",
                "idle",
            ),
        )
        or "idle"
    ).strip().lower()

    if sexual_scene_phase not in {
        "idle",
        "sexual_tension",
        "body_exploration",
        "giving_pleasure",
        "receiving_pleasure",
        "oral",
        "penetration_start",
        "penetration_active",
        "pace_control",
        "user_edge",
        "mary_edge",
        "user_orgasm",
        "mary_orgasm",
        "post_orgasm_active",
        "aftercare",
    }:
        sexual_scene_phase = "idle"

    resultado[
        "sexual_scene_phase"
    ] = sexual_scene_phase

    sexual_turn_intent = str(
        analise.get(
            "sexual_turn_intent",
            "none",
        )
        or "none"
    ).strip().lower()

    if sexual_turn_intent not in {
        "none",
        "tease",
        "invite_touch",
        "explore_user_body",
        "give_pleasure",
        "receive_pleasure",
        "control_pace",
        "change_position",
        "intensify",
        "edge_user",
        "request_more",
        "approach_orgasm",
        "orgasm",
        "post_orgasm_continue",
        "aftercare",
    }:
        sexual_turn_intent = "none"

    resultado[
        "sexual_turn_intent"
    ] = sexual_turn_intent

    seduction_strategy = str(
        analise.get(
            "seduction_strategy",
            "none",
        )
        or "none"
    ).strip().lower()

    if seduction_strategy not in {
        "none",
        "practical_proximity",
        "plausible_innocence",
        "test_reaction",
        "deliberate_teasing",
        "admit_desire",
        "clear_sexual_intent",
    }:
        seduction_strategy = "none"

    resultado[
        "seduction_strategy"
    ] = seduction_strategy

    try:
        seduction_level = int(
            analise.get(
                "seduction_level",
                padrao.get(
                    "seduction_level",
                    0,
                ),
            )
            or 0
        )

    except (
        TypeError,
        ValueError,
    ):
        seduction_level = 0

    resultado[
        "seduction_level"
    ] = max(
        0,
        min(
            6,
            seduction_level,
        ),
    )

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

    # A análise semântica não pode devolver Mary à passividade
    # quando o próprio estado demonstra estagnação.
    turns_without_advance = max(
        0,
        int(
            scene_state.get(
                "turns_since_story_advance",
                0,
            )
            or 0
        ),
    )

    previous_strength = max(
        0,
        min(
            3,
            int(
                scene_state.get(
                    "last_mary_initiative_strength",
                    0,
                )
                or 0
            ),
        ),
    )

    if turns_without_advance >= 2:
        resultado[
            "mary_initiative_strength"
        ] = max(
            2,
            resultado[
                "mary_initiative_strength"
            ],
        )

        resultado[
            "mary_should_add_affordance"
        ] = True

        if not resultado[
            "recommended_focus"
        ]:
            resultado[
                "recommended_focus"
            ] = (
                "Mary executa uma decisão concreta que altera "
                "o momento atual e deixa uma consequência "
                "imediata para o usuário."
            )

    if turns_without_advance >= 4:
        resultado[
            "mary_initiative_strength"
        ] = 3

        resultado[
            "should_create_hook"
        ] = True

    if (
        previous_strength >= 2
        and not resultado[
            "narrative_progress"
        ]
    ):
        resultado[
            "mary_initiative_strength"
        ] = max(
            2,
            resultado[
                "mary_initiative_strength"
            ],
        )

        resultado[
            "mary_should_add_affordance"
        ] = True

    return resultado


def calcular_nivel_seducao(
    *,
    current_level: int,
    proposed_level: int,
    progress_allowed: bool,
    reciprocity_evidence: bool,
    user_disengaged: bool,
    consent_confirmed: bool,
) -> int:
    current_level = max(
        0,
        min(
            6,
            int(
                current_level
                or 0
            ),
        ),
    )

    proposed_level = max(
        0,
        min(
            6,
            int(
                proposed_level
                or 0
            ),
        ),
    )

    if user_disengaged:
        return max(
            0,
            current_level - 1,
        )

    if not progress_allowed:
        return current_level

    max_step = 1

    if (
        reciprocity_evidence
        and consent_confirmed
    ):
        max_step = 2

    upper_bound = min(
        6,
        current_level + max_step,
    )

    return max(
        current_level,
        min(
            proposed_level,
            upper_bound,
        ),
    )


def montar_direcao_seducao(
    *,
    seduction_level: int,
    seduction_strategy: str,
    sexual_expression_allowed: bool,
) -> str:
    if seduction_level <= 0:
        return ""

    if sexual_expression_allowed:
        limite_sexual = (
            "Mary pode expressar desejo de forma direta, "
            "respeitando a continuidade, o consentimento "
            "e o estado sexual atual."
        )

    else:
        limite_sexual = (
            "A tensão pode ser sensual, mas Mary não deve "
            "introduzir ato sexual, anatomia íntima ou linguagem "
            "sexual explícita neste turno."
        )

    return f"""
[DIREÇÃO DE SEDUÇÃO GRADUAL]

Nível atual:
{seduction_level}

Estratégia atual:
{seduction_strategy}

INTERPRETAÇÃO:

- 0: nenhuma sedução.
- 1: proximidade justificada pela situação.
- 2: inocência plausível e contato ambíguo.
- 3: Mary percebe o efeito e testa a reação.
- 4: provocação deliberada, ainda parcialmente negável.
- 5: Mary admite que gostou e pede continuidade.
- 6: Mary expressa intenção sexual clara.

REGRAS:

- Mary aumenta a tensão por meio de uma escolha concreta,
  não por uma declaração abstrata de sedução.
- Primeiro existe uma justificativa plausível.
- Depois Mary permite ou cria proximidade.
- Em seguida percebe o efeito que causa.
- Então testa a reação do usuário.
- Somente depois provoca conscientemente.
- Por fim admite o próprio desejo.
- Mary não deve repetir a mesma desculpa em vários turnos.
- A cada avanço, alguma coisa deve mudar: distância,
  contato, ousadia, consciência do desejo ou clareza.
- Inocência plausível não significa passividade.
- Mary pode fingir que o gesto foi inocente, mas sua escolha
  de permanecer, aproximar-se ou repetir o contato deve revelar
  intenção crescente.
- A resposta do usuário determina se Mary avança,
  mantém, desacelera ou recua.
- Não trate silêncio, hesitação ou ambiguidade como consentimento.
- Não pule diretamente para ato sexual ou clímax.
- O motor sexual continua responsável pela progressão corporal,
  pré-orgasmo, orgasmo e aftercare.

{limite_sexual}
""".strip()


def montar_direcao_sexual_ativa(
    *,
    sexual_scene_phase: str,
    sexual_turn_intent: str,
    sexual_voice_mode: str,
    use_short_sensory_fragments: bool,
    avoid_action_narration: bool,
    mary_is_leading_sexually: bool,
    mary_is_giving_pleasure: bool,
    mary_is_receiving_pleasure: bool,
    user_near_orgasm: bool,
    mary_near_orgasm: bool,
    user_orgasm_confirmed: bool,
    mary_orgasm_confirmed: bool,
    post_orgasm_continue: bool,
) -> str:
    if sexual_scene_phase in {
        "",
        "idle",
        "sexual_tension",
    }:
        return ""

    return f"""
[DIREÇÃO SEXUAL ATIVA]

Fase sexual:
{sexual_scene_phase}

Intenção sexual deste turno:
{sexual_turn_intent}

Modo de voz:
{sexual_voice_mode}

Usar fragmentos sensoriais curtos:
{use_short_sensory_fragments}

Evitar narração de ações:
{avoid_action_narration}

Mary conduz sexualmente:
{mary_is_leading_sexually}

Mary oferece prazer:
{mary_is_giving_pleasure}

Mary recebe prazer:
{mary_is_receiving_pleasure}

Usuário próximo do clímax:
{user_near_orgasm}

Mary próxima do clímax:
{mary_near_orgasm}

Clímax do usuário confirmado:
{user_orgasm_confirmed}

Clímax de Mary confirmado:
{mary_orgasm_confirmed}

Continuar depois do primeiro clímax:
{post_orgasm_continue}

REGRAS:

- Mary participa ativamente da cena.
- Ela percebe o usuário, reage ao que sente e escolhe o que fazer.
- Ela pode provocar, pedir, oferecer prazer, mudar de posição,
  retardar, intensificar, interromper ou retomar.
- Execute somente uma intenção sexual principal neste turno.
- Não pule diretamente ao orgasmo.
- Não transforme toda resposta em gemidos vazios.
- Mary deve falar de dentro do momento, em primeira pessoa.
- Não use linguagem técnica, clínica ou mecânica.
- Não descreva ações como autora de romance.
- Não escreva "eu faço", "eu deslizo", "eu puxo", "eu me enrosco",
  "minhas mãos descem", "meu corpo reage" ou equivalentes.
- Faça a ação aparecer pela fala viva: pedido, som, provocação,
  reação imediata, comando curto ou sensação concreta.
- Use frases curtas e quebradas quando a excitação estiver alta.
- Em vez de explicar "soltei um gemido", escreva o gemido.
- Em vez de explicar "meu corpo reagiu", diga o que Mary sente.
- Em vez de narrar "eu retribuo o beijo", faça Mary reagir ao beijo.
- Evite metáforas genéricas como incêndio, mundo parando,
  eletricidade ou perder o chão.
- Evite completamente as expressões:
  "acompanhar o ritmo", "não muda o ritmo", "manter o ritmo",
  "seguir o ritmo" e "ajustar o ritmo".
- Prefira frases concretas e vivas: pedidos, provocações,
  reações, comandos curtos, surpresa, urgência ou entrega.
- O clímax de Mary e o do usuário são independentes.
- O orgasmo de um não encerra automaticamente a cena.
- Depois do primeiro clímax, continue apenas quando o estado,
  a energia e a vontade dos envolvidos sustentarem isso.
- Entre em aftercare somente quando a cena realmente desacelerar
  ou quando o estado sexual determinar.
- Não trate hesitação, silêncio ou imobilidade como consentimento.

CALIBRAÇÃO DE VOZ:

Inadequado:
"Eu retribuo o beijo e minhas mãos descem pelo seu peito."

Adequado:
"Humm... sua boca... vem mais perto."

Inadequado:
"Meu corpo inteiro reage ao toque e eu solto um gemido."

Adequado:
"Ahh... assim... eu tô arrepiada."

Inadequado:
"Eu começo a ficar excitada com a intensidade do momento."

Adequado:
"Humm... tô ficando quente... continua."

A fala deve soar vivida, não descrita.
""".strip()


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

    current_seduction_level = int(
        scene_state.get(
            "seduction_level",
            0,
        )
        or 0
    )

    proposed_seduction_level = int(
        analise_cenario.get(
            "seduction_level",
            current_seduction_level,
        )
        or 0
    )

    seduction_progress_allowed = bool(
        analise_cenario.get(
            "seduction_progress_allowed",
            False,
        )
    )

    sexual_reciprocity_evidence = bool(
        analise_cenario.get(
            "sexual_reciprocity_evidence",
            False,
        )
    )

    consent_confirmed = bool(
        analise_cenario.get(
            "consent_confirmed",
            False,
        )
    )

    seduction_level = calcular_nivel_seducao(
        current_level=current_seduction_level,
        proposed_level=proposed_seduction_level,
        progress_allowed=seduction_progress_allowed,
        reciprocity_evidence=sexual_reciprocity_evidence,
        user_disengaged=user_disengaged,
        consent_confirmed=consent_confirmed,
    )

    seduction_strategy = str(
        analise_cenario.get(
            "seduction_strategy",
            "none",
        )
        or "none"
    ).strip()

    sexual_voice_mode = str(
        analise_cenario.get(
            "sexual_voice_mode",
            "natural",
        )
        or "natural"
    ).strip().lower()

    avoid_action_narration = bool(
        analise_cenario.get(
            "avoid_action_narration",
            True,
        )
    )

    sexual_scene_phase = str(
        analise_cenario.get(
            "sexual_scene_phase",
            scene_state.get(
                "sexual_scene_phase",
                "idle",
            ),
        )
        or "idle"
    ).strip().lower()

    use_short_sensory_fragments = bool(
        analise_cenario.get(
            "use_short_sensory_fragments",
            sexual_scene_phase not in {
                "idle",
                "sexual_tension",
            },
        )
    )

    if sexual_scene_phase not in {
        "idle",
        "sexual_tension",
    }:
        use_short_sensory_fragments = True

    sexual_turn_intent = str(
        analise_cenario.get(
            "sexual_turn_intent",
            "none",
        )
        or "none"
    ).strip().lower()

    mary_is_leading_sexually = bool(
        analise_cenario.get(
            "mary_is_leading_sexually",
            False,
        )
    )

    mary_is_giving_pleasure = bool(
        analise_cenario.get(
            "mary_is_giving_pleasure",
            False,
        )
    )

    mary_is_receiving_pleasure = bool(
        analise_cenario.get(
            "mary_is_receiving_pleasure",
            False,
        )
    )

    user_near_orgasm = bool(
        analise_cenario.get(
            "user_near_orgasm",
            False,
        )
    )

    mary_near_orgasm = bool(
        analise_cenario.get(
            "mary_near_orgasm",
            False,
        )
    )

    user_orgasm_confirmed = bool(
        analise_cenario.get(
            "user_orgasm_confirmed",
            False,
        )
    )

    mary_orgasm_confirmed = bool(
        analise_cenario.get(
            "mary_orgasm_confirmed",
            False,
        )
    )

    post_orgasm_continue = bool(
        analise_cenario.get(
            "post_orgasm_continue",
            False,
        )
    )

    # Em fantasia ativa, esta integração ocorre depois do
    # diretor geral e substitui os campos operacionais incompatíveis.
    direcao[
        "must_preserve_current_scene"
    ] = True

    # Compatibilidade com versões anteriores.
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
        "reason"
    ] = "active_scenario_integrated"

    direcao[
        "direction_reason"
    ] = "active_scenario_integrated"

    recommended_focus = str(
        analise_cenario.get(
            "recommended_focus",
            "",
        )
        or ""
    ).strip()

    if recommended_focus:
        direcao[
            "primary_intention"
        ] = recommended_focus

    # Mary pode falar do próprio corpo e de sensações canônicas
    # dentro da fantasia, mesmo antes de uma cena explicitamente sexual.
    direcao[
        "body_focus_allowed"
    ] = bool(
        seduction_level >= 1
        or sexual_scene_phase != "idle"
        or scene_state.get(
            "fantasy_established",
            False,
        )
    )

    sexual_phase_active = (
        sexual_scene_phase
        not in {
            "",
            "idle",
        }
    )

    explicit_phase_active = (
        sexual_scene_phase
        in {
            "body_exploration",
            "giving_pleasure",
            "receiving_pleasure",
            "oral",
            "penetration_start",
            "penetration_active",
            "pace_control",
            "user_edge",
            "mary_edge",
            "user_orgasm",
            "mary_orgasm",
            "post_orgasm_active",
        }
    )

    direcao[
        "sexual_expression_allowed"
    ] = bool(
        direcao.get(
            "sexual_expression_allowed",
            False,
        )
        or seduction_level >= 2
        or sexual_phase_active
        or sexual_reciprocity_evidence
    )

    direcao[
        "explicit_sexual_language_allowed"
    ] = bool(
        direcao.get(
            "explicit_sexual_language_allowed",
            False,
        )
        or explicit_phase_active
        or (
            seduction_level >= 5
            and sexual_reciprocity_evidence
            and consent_confirmed
        )
    )

    # O cenário decide atitude e movimento; o motor sexual
    # continua decidindo orgasmo e continuidade fisiológica.
    if turns_without_advance >= 2:
        mary_initiative_strength = max(
            2,
            mary_initiative_strength,
        )

        mary_should_add_affordance = True

    if turns_without_advance >= 4:
        mary_initiative_strength = 3
        should_create_hook = True

    precisa_movimento_mary = bool(
        should_create_hook
        or mary_should_add_affordance
        or mary_initiative_strength >= 2
        or turns_without_advance >= 2
    )

    direcao[
        "scenario_initiative_strength"
    ] = mary_initiative_strength

    direcao[
        "scenario_seduction_level"
    ] = seduction_level

    direcao[
        "scenario_seduction_strategy"
    ] = seduction_strategy

    direcao[
        "scenario_sexual_reciprocity_evidence"
    ] = sexual_reciprocity_evidence

    direcao[
        "scenario_intimate_action_started"
    ] = bool(
        analise_cenario.get(
            "intimate_action_started",
            False,
        )
    )

    direcao[
        "scenario_consent_confirmed"
    ] = consent_confirmed

    direcao[
        "scenario_sexual_voice_mode"
    ] = sexual_voice_mode

    direcao[
        "scenario_use_short_sensory_fragments"
    ] = use_short_sensory_fragments

    direcao[
        "scenario_avoid_action_narration"
    ] = avoid_action_narration

    direcao[
        "scenario_sexual_scene_phase"
    ] = sexual_scene_phase

    direcao[
        "scenario_sexual_turn_intent"
    ] = sexual_turn_intent

    direcao[
        "scenario_mary_is_leading_sexually"
    ] = mary_is_leading_sexually

    direcao[
        "scenario_mary_is_giving_pleasure"
    ] = mary_is_giving_pleasure

    direcao[
        "scenario_mary_is_receiving_pleasure"
    ] = mary_is_receiving_pleasure

    direcao[
        "scenario_user_near_orgasm"
    ] = user_near_orgasm

    direcao[
        "scenario_mary_near_orgasm"
    ] = mary_near_orgasm

    direcao[
        "scenario_user_orgasm_confirmed"
    ] = user_orgasm_confirmed

    direcao[
        "scenario_mary_orgasm_confirmed"
    ] = mary_orgasm_confirmed

    direcao[
        "scenario_post_orgasm_continue"
    ] = post_orgasm_continue

    if sexual_turn_intent != "none":
        direcao[
            "should_lead"
        ] = True

        direcao[
            "response_scope"
        ] = "scene"

    if precisa_movimento_mary:
        direcao[
            "should_lead"
        ] = True

        direcao[
            "create_narrative_pending"
        ] = True

        # Iniciativa não deve virar pergunta devolvida ao usuário.
        direcao[
            "avoid_question"
        ] = True

        if not recommended_focus:
            recommended_focus = (
                "Mary toma uma decisão concreta e executa "
                "um movimento perceptível agora."
            )

        direcao[
            "primary_intention"
        ] = recommended_focus

        direcao[
            "scenario_focus"
        ] = recommended_focus

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
    ] = (
        recommended_focus
        or str(
            analise_cenario.get(
                "recommended_focus",
                "",
            )
            or ""
        ).strip()
    )

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
            "seduction_level": (
                "Número inteiro de 0 a 6. "
                "0 = nenhuma sedução; "
                "1 = proximidade prática; "
                "2 = inocência plausível; "
                "3 = teste da reação; "
                "4 = provocação deliberada; "
                "5 = desejo parcialmente admitido; "
                "6 = intenção sexual clara."
            ),
            "seduction_progress_allowed": (
                "boolean; verdadeiro apenas quando os acontecimentos "
                "e a resposta do usuário sustentam avanço gradual."
            ),
            "seduction_strategy": (
                "none, practical_proximity, plausible_innocence, "
                "test_reaction, deliberate_teasing, admit_desire "
                "ou clear_sexual_intent"
            ),
            "sexual_reciprocity_evidence": (
                "boolean; verdadeiro apenas quando o usuário demonstrou "
                "interesse ou reciprocidade compatível com o avanço."
            ),
            "intimate_action_started": (
                "boolean; verdadeiro apenas quando uma ação íntima "
                "efetivamente começou na cena."
            ),
            "consent_confirmed": (
                "boolean; verdadeiro apenas quando houver consentimento "
                "claro para a ação íntima relevante."
            ),
            "sexual_voice_mode": (
                "natural, breathless, teasing, hungry, commanding, "
                "overwhelmed ou tender"
            ),
            "use_short_sensory_fragments": (
                "boolean; verdadeiro em cenas íntimas ativas para favorecer "
                "frases curtas, respiração quebrada e sensação imediata."
            ),
            "avoid_action_narration": (
                "boolean; normalmente verdadeiro. Mary deve falar de dentro "
                "da ação, não descrevê-la como narradora."
            ),
            "sexual_scene_phase": (
                "idle, sexual_tension, body_exploration, giving_pleasure, "
                "receiving_pleasure, oral, penetration_start, "
                "penetration_active, pace_control, user_edge, mary_edge, "
                "user_orgasm, mary_orgasm, post_orgasm_active ou aftercare"
            ),
            "sexual_turn_intent": (
                "none, tease, invite_touch, explore_user_body, "
                "give_pleasure, receive_pleasure, control_pace, "
                "change_position, intensify, edge_user, request_more, "
                "approach_orgasm, orgasm, post_orgasm_continue ou aftercare"
            ),
            "mary_is_leading_sexually": "boolean",
            "mary_is_giving_pleasure": "boolean",
            "mary_is_receiving_pleasure": "boolean",
            "user_near_orgasm": "boolean",
            "mary_near_orgasm": "boolean",
            "user_orgasm_confirmed": "boolean",
            "mary_orgasm_confirmed": "boolean",
            "post_orgasm_continue": (
                "boolean; verdadeiro quando o primeiro clímax não deve "
                "encerrar automaticamente a cena."
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

    previous_interaction_count = max(
        0,
        int(
            estado.get(
                "interaction_count",
                0,
            )
            or 0
        ),
    )

    supplied_interaction_number = max(
        0,
        int(
            interaction_number
            or 0
        ),
    )

    estado[
        "interaction_count"
    ] = max(
        previous_interaction_count + 1,
        supplied_interaction_number,
    )

    if estado[
        "interaction_count"
    ] >= 1:
        estado[
            "opening_sent"
        ] = True

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

    current_seduction_level = int(
        estado.get(
            "seduction_level",
            0,
        )
        or 0
    )

    proposed_seduction_level = int(
        analise.get(
            "seduction_level",
            current_seduction_level,
        )
        or 0
    )

    estado[
        "seduction_level"
    ] = calcular_nivel_seducao(
        current_level=current_seduction_level,
        proposed_level=proposed_seduction_level,
        progress_allowed=bool(
            analise.get(
                "seduction_progress_allowed",
                False,
            )
        ),
        reciprocity_evidence=bool(
            analise.get(
                "sexual_reciprocity_evidence",
                False,
            )
        ),
        user_disengaged=bool(
            analise.get(
                "user_disengaged",
                False,
            )
        ),
        consent_confirmed=bool(
            analise.get(
                "consent_confirmed",
                False,
            )
        ),
    )

    proposed_strategy = str(
        analise.get(
            "seduction_strategy",
            "",
        )
        or ""
    ).strip()

    if (
        proposed_strategy
        and proposed_strategy != "none"
    ):
        estado[
            "seduction_strategy"
        ] = proposed_strategy

    else:
        estado[
            "seduction_strategy"
        ] = str(
            estado.get(
                "seduction_strategy",
                "none",
            )
            or "none"
        ).strip()

    estado[
        "sexual_reciprocity_evidence"
    ] = bool(
        estado.get(
            "sexual_reciprocity_evidence",
            False,
        )
        or analise.get(
            "sexual_reciprocity_evidence",
            False,
        )
    )

    estado[
        "intimate_action_started"
    ] = bool(
        estado.get(
            "intimate_action_started",
            False,
        )
        or analise.get(
            "intimate_action_started",
            False,
        )
    )

    estado[
        "consent_confirmed"
    ] = bool(
        estado.get(
            "consent_confirmed",
            False,
        )
        or analise.get(
            "consent_confirmed",
            False,
        )
    )

    estado[
        "sexual_voice_mode"
    ] = str(
        analise.get(
            "sexual_voice_mode",
            estado.get(
                "sexual_voice_mode",
                "natural",
            ),
        )
        or "natural"
    ).strip().lower()

    estado[
        "use_short_sensory_fragments"
    ] = bool(
        analise.get(
            "use_short_sensory_fragments",
            estado.get(
                "use_short_sensory_fragments",
                False,
            ),
        )
    )

    estado[
        "avoid_action_narration"
    ] = bool(
        analise.get(
            "avoid_action_narration",
            True,
        )
    )

    estado[
        "sexual_scene_phase"
    ] = str(
        analise.get(
            "sexual_scene_phase",
            estado.get(
                "sexual_scene_phase",
                "idle",
            ),
        )
        or "idle"
    ).strip().lower()

    estado[
        "sexual_turn_intent"
    ] = str(
        analise.get(
            "sexual_turn_intent",
            "none",
        )
        or "none"
    ).strip().lower()

    for campo in (
        "mary_is_leading_sexually",
        "mary_is_giving_pleasure",
        "mary_is_receiving_pleasure",
        "user_near_orgasm",
        "mary_near_orgasm",
        "user_orgasm_confirmed",
        "mary_orgasm_confirmed",
        "post_orgasm_continue",
    ):
        estado[campo] = bool(
            analise.get(
                campo,
                estado.get(
                    campo,
                    False,
                ),
            )
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

    recommended_phase = str(
        analise.get(
            "recommended_phase",
            estado.get(
                "current_phase",
                "opening",
            ),
        )
        or estado.get(
            "current_phase",
            "opening",
        )
    ).strip().lower()

    if (
        analise.get(
            "confidence",
            0.0,
        )
        >= 0.45
    ):
        estado[
            "current_phase"
        ] = recommended_phase

    # A abertura não pode permanecer congelada depois que a
    # situação inicial já foi aceita ou resolvida.
    resolved_elements = set(
        str(item).strip().lower()
        for item in analise.get(
            "resolved_elements",
            [],
        )
        if str(
            item or ""
        ).strip()
    )

    if (
        estado.get(
            "current_phase",
            "opening",
        ) == "opening"
        and (
            estado[
                "interaction_count"
            ] >= 3
            or bool(
                resolved_elements
            )
            or bool(
                analise.get(
                    "scene_changed",
                    False,
                )
            )
        )
    ):
        estado[
            "current_phase"
        ] = (
            "tension"
            if estado.get(
                "seduction_level",
                0,
            ) >= 2
            else "familiarity"
        )

    if analise.get(
        "narrative_progress"
    ):
        estado[
            "turns_since_story_advance"
        ] = 0

        estado[
            "last_story_advance_at"
        ] = estado[
            "interaction_count"
        ]

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

    if turns_without_advance >= 2:
        initiative_strength = max(
            2,
            initiative_strength,
        )

    if turns_without_advance >= 4:
        initiative_strength = 3

    precisa_movimento_mary = bool(
        should_create_hook
        or mary_should_add_affordance
        or initiative_strength >= 2
        or turns_without_advance >= 2
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

    seduction_level = int(
        analise.get(
            "seduction_level",
            scene_state.get(
                "seduction_level",
                0,
            ),
        )
        or scene_state.get(
            "seduction_level",
            0,
        )
        or 0
    )

    seduction_level = max(
        0,
        min(
            6,
            seduction_level,
        ),
    )

    seduction_strategy = str(
        analise.get(
            "seduction_strategy",
            scene_state.get(
                "seduction_strategy",
                "none",
            ),
        )
        or "none"
    ).strip()

    sexual_expression_allowed = bool(
        seduction_level >= 2
        or str(
            analise.get(
                "sexual_scene_phase",
                scene_state.get(
                    "sexual_scene_phase",
                    "idle",
                ),
            )
            or "idle"
        ).strip().lower()
        != "idle"
    )

    direcao_seducao = montar_direcao_seducao(
        seduction_level=seduction_level,
        seduction_strategy=seduction_strategy,
        sexual_expression_allowed=sexual_expression_allowed,
    )

    sexual_scene_phase = str(
        analise.get(
            "sexual_scene_phase",
            scene_state.get(
                "sexual_scene_phase",
                "idle",
            ),
        )
        or "idle"
    ).strip().lower()

    sexual_turn_intent = str(
        analise.get(
            "sexual_turn_intent",
            "none",
        )
        or "none"
    ).strip().lower()

    sexual_voice_mode = str(
        analise.get(
            "sexual_voice_mode",
            scene_state.get(
                "sexual_voice_mode",
                "natural",
            ),
        )
        or "natural"
    ).strip().lower()

    use_short_sensory_fragments = bool(
        analise.get(
            "use_short_sensory_fragments",
            sexual_scene_phase not in {
                "idle",
                "sexual_tension",
            },
        )
    )

    avoid_action_narration = bool(
        analise.get(
            "avoid_action_narration",
            True,
        )
    )

    direcao_sexual_ativa = montar_direcao_sexual_ativa(
        sexual_scene_phase=sexual_scene_phase,
        sexual_turn_intent=sexual_turn_intent,
        sexual_voice_mode=sexual_voice_mode,
        use_short_sensory_fragments=use_short_sensory_fragments,
        avoid_action_narration=avoid_action_narration,
        mary_is_leading_sexually=bool(
            analise.get(
                "mary_is_leading_sexually",
                False,
            )
        ),
        mary_is_giving_pleasure=bool(
            analise.get(
                "mary_is_giving_pleasure",
                False,
            )
        ),
        mary_is_receiving_pleasure=bool(
            analise.get(
                "mary_is_receiving_pleasure",
                False,
            )
        ),
        user_near_orgasm=bool(
            analise.get(
                "user_near_orgasm",
                False,
            )
        ),
        mary_near_orgasm=bool(
            analise.get(
                "mary_near_orgasm",
                False,
            )
        ),
        user_orgasm_confirmed=bool(
            analise.get(
                "user_orgasm_confirmed",
                False,
            )
        ),
        mary_orgasm_confirmed=bool(
            analise.get(
                "mary_orgasm_confirmed",
                False,
            )
        ),
        post_orgasm_continue=bool(
            analise.get(
                "post_orgasm_continue",
                False,
            )
        ),
    )

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
Mary não precisa criar um acontecimento externo novo neste turno.

Ainda assim, ela não deve ficar passiva. Pode assumir uma vontade,
fazer uma provocação, falar do próprio corpo, revelar uma sensação,
formular um pedido curto ou tomar uma pequena decisão coerente.

Não explique longamente o momento. Corresponda e acrescente apenas
a atitude necessária.
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

{direcao_seducao}

{direcao_sexual_ativa}

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
- Em cenas íntimas, evite frases mecânicas como “acompanhar o ritmo”,
  “não muda o ritmo”, “manter o ritmo”, “seguir o ritmo” ou
  “ajustar o ritmo”.
- Prefira pedidos e reações concretas, corporais e espontâneas.
- Em intimidade ativa, Mary não deve narrar a própria ação.
- Evite parágrafos explicativos. Use fala curta, quebrada e sensorial.
- Não escreva "eu me enrosquei", "minhas mãos desceram",
  "meu corpo reagiu", "eu retribuo o beijo" ou equivalentes.
- Não mencione fase, roteiro, gancho ou direção narrativa.
""".strip()
