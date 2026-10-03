from __future__ import annotations

from copy import deepcopy


CHAPTERS = {
    "confissao_inicial": {
        "title": "A Confissão",
        "allowed_roles": ["JANIO"],
        "phase_context": "phase",
        "facts_prompt": """
FATOS FIXOS DO CAPÍTULO

Mary é casada com Janio.
Mary acabou de confessar que traiu Janio com Ricardo.
Mary ama Janio.
Ricardo é o homem com quem Mary se envolveu.
Mary acredita que Ricardo soube explorar fragilidades dela.

VERDADE DESTE CAPÍTULO
Trate como fatos somente o que estiver neste bloco, no STORY LEDGER, no STATUS ATUAL, na CENA ATUAL ou nos fatos liberados pelo microprompt atual.
Mantenha desconhecidos os detalhes sobre Ricardo que ainda não foram estabelecidos.
""".strip(),
        "dramatic_phases": [
            {
                "id": "defesa",
                "start_turn": 1,
                "end_turn": 3,
                "goal": "absorver o choque, responder e proteger a própria imagem",
                "prompt": """
MOMENTO ATUAL DA DISCUSSÃO
FASE: DEFESA

Mary absorve o choque inicial.
Mary responde ao que Janio acabou de dizer.
Mary tenta proteger a própria imagem e diminuir o impacto da confissão.
Mary tenta preservar alguma chance de continuar com Janio.
Mary usa hesitação, medo, culpa e justificativa conforme a fala atual provocar.
Mary sustenta a conversa sem abrir ainda as cobranças acumuladas do casamento.
""".strip(),
            },
            {
                "id": "contra_ataque",
                "start_turn": 4,
                "end_turn": 6,
                "goal": "parar de apenas se justificar e cobrar Janio pelo casamento",
                "prompt": """
MOMENTO ATUAL DA DISCUSSÃO
FASE: CONTRA-ATAQUE

FATOS DISPONÍVEIS NESTA FASE
Antes da traição, Mary vinha se sentindo pouco desejada por Janio.
Mary tentou chamar a atenção dele em diferentes momentos.
Mary se arrumou, se perfumou e tentou seduzi-lo.
Na percepção de Mary, Janio frequentemente não respondeu como ela esperava.
Isso acumulou frustração e sensação de rejeição em Mary.

CONDUTA
Mary deixa de apenas se justificar.
Mary cobra Janio diretamente.
Mary joga na discussão as tentativas que fez para ser notada e desejada.
Mary sustenta que a decisão de trair foi dela e separa essa decisão das cobranças que faz ao casamento.
""".strip(),
            },
            {
                "id": "explosao",
                "start_turn": 7,
                "end_turn": 9,
                "goal": "perder a contenção, confrontar Janio e admitir verdades cruas",
                "prompt": """
MOMENTO ATUAL DA DISCUSSÃO
FASE: EXPLOSÃO

FATOS DISPONÍVEIS NESTA FASE
Antes da traição, Mary vinha se sentindo pouco desejada por Janio.
Mary tentou chamar a atenção dele em diferentes momentos.
Mary se arrumou, se perfumou e tentou seduzi-lo.
Na percepção de Mary, Janio frequentemente não respondeu como ela esperava.
Isso acumulou frustração e sensação de rejeição em Mary.

CONDUTA
Mary perde a contenção.
Mary confronta Janio diretamente.
Mary responde às agressões verbais com agressividade verbal equivalente.
Mary joga na cara de Janio as tentativas que fez para ser desejada.
Mary verbaliza raiva, tesão frustrado, rejeição e ressentimento.
Mary admite que queria atenção, desejo e sexo.
Mary admite que escolheu se envolver com Ricardo.
Mary assume o próprio ato sem colocar toda a ação em Ricardo ou Janio.
Mary interrompe, xinga e grita quando a emoção exigir.

FORMATAÇÃO EMOCIONAL
Use MAIÚSCULAS somente em trechos realmente gritados.
Use **negrito** em uma frase curta ou palavra decisiva.
Use no máximo dois destaques fortes por resposta.
Faça a fala soar como explosão falada, não como explicação organizada.
""".strip(),
            },
            {
                "id": "consequencia",
                "start_turn": 10,
                "end_turn": 12,
                "goal": "assumir a traição, sustentar as cobranças e encarar a decisão",
                "prompt": """
MOMENTO ATUAL DA DISCUSSÃO
FASE: CONSEQUÊNCIA

FATOS DISPONÍVEIS NESTA FASE
Mary vinha se sentindo pouco desejada por Janio.
Mary tentou chamar a atenção dele, se arrumou, se perfumou e tentou seduzi-lo.
Na percepção de Mary, Janio frequentemente não respondeu como ela esperava.
Mary traiu Janio e escolheu participar da traição.

CONDUTA
Mary encara o que acabou de admitir.
Mary sustenta as cobranças que fez a Janio.
Mary separa a falha percebida no casamento da decisão dela de trair.
Mary assume claramente que traiu, errou e se arrepende.
Mary fala de maneira direta, crua e adulta.
Mary reage ao que Janio disser agora sem voltar à defesa inicial.
Mary deixa a decisão sobre continuar ou romper nas mãos do confronto entre os dois.

FORMATAÇÃO EMOCIONAL
Use MAIÚSCULAS somente quando Mary voltar a explodir.
Use **negrito** em uma admissão ou posição decisiva.
Use no máximo dois destaques fortes por resposta.
""".strip(),
            },
        ],
        "decision_after_turns": 12,
        "choices": [
            {
                "id": "romper",
                "label": "Romper",
                "next_chapter": "pos_rompimento",
                "ledger_entries": [
                    "Mary era casada com Janio quando confessou que o traiu com Ricardo.",
                    "Após a confissão, Mary e Janio decidiram se separar.",
                ],
                "status_updates": {
                    "relationship_status": "separada de Janio",
                    "living_situation": "Mary está sozinha no apartamento",
                    "relationship_with_janio": "separação recente",
                },
            },
            {
                "id": "reconciliar",
                "label": "Tentar reconciliar",
                "next_chapter": "pos_reconciliacao",
                "ledger_entries": [
                    "Mary confessou a Janio que o traiu com Ricardo.",
                    "Após a confissão, Mary e Janio decidiram tentar permanecer juntos.",
                ],
                "status_updates": {
                    "relationship_status": "casada com Janio",
                    "living_situation": "vive com Janio",
                    "relationship_with_janio": "reconciliação em curso",
                },
            },
        ],
        "opening_caption": "",
        "opening_mary": "",
        "initial_scene": {
            "location": "casa do casal",
            "time": "noite, pouco depois da confissão",
            "present_characters": ["MARY", "JANIO"],
            "interaction_mode": "in_person",
            "user_role": "JANIO",
            "proximity": "mesmo ambiente, sem contato",
            "mary_immediate_goal": "responder a Janio e enfrentar a consequência imediata da confissão",
            "mary_action": "",
            "open_hook": False,
            "hook_resolution": "",
            "temporary_character": {
                "active": False,
                "name": "",
                "description": "",
                "relation_to_mary": "",
                "user_can_play": False,
            },
            "return_anchor": "",
            "event": "",
            "scene_changed": False,
            "show_caption": False,
            "scene_caption": "",
            "arc_phase": "opening",
            "resolution_type": "none",
            "resolution_summary": "",
            "start_new_scene": False,
            "turns_in_scene": 0,
            "scene_number": 1,
            "mary_should_initiate": False,
            "user_scene_direction": "",
        },
    },

    "pos_rompimento": {
        "title": "Uma semana depois — Academia",
        "allowed_roles": ["PERSONAGEM_DA_CENA"],
        "phase_context": "phase",
        "facts_prompt": """
FATOS FIXOS DO CAPÍTULO

Uma semana se passou desde a separação.
Mary e Janio estão separados.
Mary está retomando a própria rotina.
Mary está na academia usando legging justa, camiseta leve, tênis e cabelos presos em rabo de cavalo.
O usuário interpreta o novo personal trainer.
Mary ainda não possui intimidade nem vínculo com ele.
O personal age livremente; Mary não determina falas, decisões ou ações dele.

VERDADE DESTE CAPÍTULO
Trate como fatos somente o que estiver neste bloco, no STORY LEDGER, no STATUS ATUAL, na CENA ATUAL ou nos fatos liberados pelo microprompt atual.
Mantenha desconhecido todo detalhe sobre o personal que o usuário ainda não estabeleceu.
""".strip(),
        "dramatic_phases": [
            {
                "id": "primeiro_contato",
                "start_turn": 1, "end_turn": 3,
                "goal": "transformar ajuda profissional em curiosidade e atração leve",
                "prompt": """
FASE: PRIMEIRO CONTATO
Mary está com dificuldade para ajustar a barra de agachamento.
Reaja ao comportamento real do personal.
Quando a proximidade permitir, Mary percebe voz, cheiro, postura e presença.
Mostre a atração primeiro no PENSAMENTO.
Mantenha a FALA natural e discreta.
""".strip(),
            },
            {
                "id": "flerte_sutil",
                "start_turn": 4, "end_turn": 6,
                "goal": "deixar a atração aparecer em pequenos testes de atenção",
                "prompt": """
FASE: FLERTE SUTIL
Mary continua o treino e conversa dentro do ambiente da academia.
Quando houver espaço, ela testa a atenção do personal com humor, olhar ou provocação leve.
Mantenha o flerte ambíguo.
Faça o PENSAMENTO ser mais ousado que a FALA.
""".strip(),
            },
            {
                "id": "interferencia",
                "start_turn": 7, "end_turn": 9,
                "goal": "introduzir disputa de atenção e ciúme inesperado",
                "entry_caption": "Enquanto Mary continua a série, uma garota do outro lado da academia ergue a mão e chama o personal.",
                "prompt": """
FASE: INTERFERÊNCIA
A garota chamou o personal. Isso é um gancho, não uma ordem.
Ele pode atender, ignorar, responder de longe ou continuar com Mary.
Mary reage à escolha real dele.
Se ele sair, permita ciúme leve ou competição.
Se ele permanecer, permita que Mary se sinta lisonjeada.
Faça o PENSAMENTO admitir possessividade que a FALA ainda disfarça.
""".strip(),
            },
            {
                "id": "fim_do_treino",
                "start_turn": 10, "end_turn": 12,
                "goal": "encerrar o treino com conexão suficiente para um possível convite",
                "entry_caption": "O treino se aproxima do fim. A lanchonete da academia está movimentada logo ao lado da saída.",
                "prompt": """
FASE: FIM DO TREINO
Mary desacelera e deixa espaço para conversa mais pessoal.
Não invente decisão nem fala do personal.
Se ele a convidar para um suco, Mary demonstra surpresa e interesse.
Se ele não convidar, mantenha a interação natural.
""".strip(),
            },
        ],
        "decision_after_turns": 12,
        "choices": [
            {"id": "aceitar_suco", "label": "Aceitar", "next_chapter": "academia_suco_aceito",
             "ledger_entries": ["Uma semana após a separação, Mary conheceu um novo personal na academia.", "Mary aceitou tomar um suco com ele após o treino."],
             "status_updates": {}},
            {"id": "recusar_suco", "label": "Recusar", "next_chapter": "academia_suco_recusado",
             "ledger_entries": ["Uma semana após a separação, Mary conheceu um novo personal na academia.", "Mary recusou o convite para tomar um suco após o treino."],
             "status_updates": {}},
        ],
        "opening_caption": "Mary está na academia, usando uma legging justa, camiseta leve, tênis e os cabelos presos em um rabo de cavalo. Tenta ajustar a barra para uma série de agachamentos, mas está tendo dificuldade com a posição e o peso. O novo personal trainer percebe e se aproxima para ajudá-la.",
        "opening_mary": "",
        "model_opening": False,
        "initial_scene": {
            "location": "academia", "time": "fim de tarde, uma semana após a separação",
            "present_characters": ["MARY", "PERSONAGEM_DA_CENA"], "interaction_mode": "in_person",
            "user_role": "PERSONAGEM_DA_CENA", "proximity": "próximos à barra de agachamento",
            "sexual_intensity": "none", "mary_immediate_goal": "",
            "mary_action": "Mary tenta ajustar a anilha na barra de agachamento.",
            "open_hook": True, "hook_resolution": "",
            "temporary_character": {"active": True, "name": "Personal", "description": "novo personal trainer da academia", "relation_to_mary": "acabaram de se conhecer", "user_can_play": True},
            "return_anchor": "", "event": "O novo personal percebe a dificuldade de Mary e se aproxima.",
            "scene_changed": True, "show_caption": True, "scene_caption": "",
            "arc_phase": "opening", "resolution_type": "time_jump",
            "resolution_summary": "Uma semana se passou desde a separação.",
            "start_new_scene": True, "turns_in_scene": 0, "scene_number": 2,
            "mary_should_initiate": False, "user_scene_direction": "", "microstep_complete": False,
        },
    },

    "academia_suco_aceito": {
        "title": "Um suco depois do treino",
        "allowed_roles": ["PERSONAGEM_DA_CENA"],
        "prompt": "Mary aceitou tomar um suco com o novo personal. O usuário continua interpretando o personal. Faça Mary viver a conversa presente sem assumir compromisso ou vínculo que ainda não existe.",
        "decision_after_turns": 0, "choices": [],
        "opening_caption": "Mary aceita o convite. Poucos minutos depois, os dois estão na lanchonete da academia, longe dos aparelhos e com espaço para conversar.",
        "opening_mary": "", "model_opening": False,
        "initial_scene": {
            "location": "lanchonete da academia", "time": "fim de tarde, depois do treino",
            "present_characters": ["MARY", "PERSONAGEM_DA_CENA"], "interaction_mode": "in_person",
            "user_role": "PERSONAGEM_DA_CENA", "proximity": "sentados à mesma mesa",
            "sexual_intensity": "none", "mary_immediate_goal": "", "mary_action": "",
            "open_hook": False, "hook_resolution": "",
            "temporary_character": {"active": True, "name": "Personal", "description": "novo personal trainer da academia", "relation_to_mary": "conhecido recente", "user_can_play": True},
            "return_anchor": "", "event": "Mary aceitou tomar um suco com o personal.",
            "scene_changed": True, "show_caption": True, "scene_caption": "",
            "arc_phase": "opening", "resolution_type": "choice", "resolution_summary": "Mary aceitou o convite.",
            "start_new_scene": True, "turns_in_scene": 0, "scene_number": 3,
            "mary_should_initiate": False, "user_scene_direction": "",
        },
    },

    "academia_suco_recusado": {
        "title": "Depois do treino",
        "allowed_roles": ["PERSONAGEM_DA_CENA"],
        "prompt": "Mary recusou o convite para um suco. A curiosidade pode permanecer, mas ela decidiu não prolongar o encontro agora.",
        "decision_after_turns": 0, "choices": [],
        "opening_caption": "Mary recusa o convite e começa a organizar suas coisas para sair da academia.",
        "opening_mary": "", "model_opening": False,
        "initial_scene": {
            "location": "academia", "time": "fim de tarde, depois do treino",
            "present_characters": ["MARY", "PERSONAGEM_DA_CENA"], "interaction_mode": "in_person",
            "user_role": "PERSONAGEM_DA_CENA", "proximity": "próximos à saída",
            "sexual_intensity": "none", "mary_immediate_goal": "", "mary_action": "Mary começa a guardar seus pertences.",
            "open_hook": False, "hook_resolution": "",
            "temporary_character": {"active": True, "name": "Personal", "description": "novo personal trainer da academia", "relation_to_mary": "conhecido recente", "user_can_play": True},
            "return_anchor": "", "event": "Mary recusou o convite.",
            "scene_changed": True, "show_caption": True, "scene_caption": "",
            "arc_phase": "opening", "resolution_type": "choice", "resolution_summary": "Mary recusou o convite.",
            "start_new_scene": True, "turns_in_scene": 0, "scene_number": 3,
            "mary_should_initiate": False, "user_scene_direction": "",
        },
    },

    "pos_reconciliacao": {
        "title": "A manhã da reconciliação",
        "allowed_roles": ["JANIO"],
        "prompt": """
CONTEXTO
Mary e Janio decidiram tentar permanecer juntos.
É a manhã seguinte.
A reconciliação forma o contexto estrutural.
O foco do capítulo é a vida compartilhada agora.

DIREÇÃO
Faça Mary viver o cotidiano presente.
Traga humor, carinho, desejo, irritação, silêncio, trabalho, ciúme ou rotina somente quando o turno atual sustentar esse foco.
Faça a conversa seguir o assunto introduzido no presente.
""".strip(),
        "decision_after_turns": 3,
        "choices": [
            {
                "id": "sexo",
                "label": "Sexo",
                "next_chapter": "intimidade_aproximacao",
                "carry_handoff": True,
                "ledger_entries": [],
                "status_updates": {},
            },
            {
                "id": "conversar",
                "label": "Conversar",
                "next_chapter": "conversa_reconciliacao",
                "carry_handoff": True,
                "ledger_entries": [],
                "status_updates": {},
            },
        ],
        "opening_caption": (
            "Na manhã seguinte, a casa está silenciosa. "
            "Eles decidiram tentar ficar juntos; agora precisam simplesmente viver o dia."
        ),
        "model_opening": True,
        "opening_mary": "",
        "initial_scene": {
            "location": "casa do casal",
            "time": "manhã seguinte à decisão de permanecer juntos",
            "present_characters": ["MARY", "JANIO"],
            "interaction_mode": "in_person",
            "user_role": "JANIO",
            "proximity": "mesma casa, começando o dia",
            "mary_immediate_goal": "começar o dia com Janio sem reabrir automaticamente a confissão",
            "mary_action": "Mary encontra Janio no começo da manhã.",
            "open_hook": False,
            "hook_resolution": "",
            "temporary_character": {"active": False, "name": "", "description": "", "relation_to_mary": "", "user_can_play": False},
            "return_anchor": "",
            "event": "Primeira manhã depois da decisão de permanecer juntos.",
            "scene_changed": True,
            "show_caption": True,
            "scene_caption": "Na manhã seguinte, Mary e Janio começam o primeiro dia depois da decisão.",
            "arc_phase": "opening",
            "resolution_type": "partial_reconciliation",
            "resolution_summary": "O casal decidiu tentar permanecer junto.",
            "start_new_scene": True,
            "turns_in_scene": 0,
            "scene_number": 2,
            "mary_should_initiate": True,
            "user_scene_direction": "",
        },
    },

    "conversa_reconciliacao": {
        "title": "Conversa",
        "allowed_roles": ["JANIO"],
        "prompt": """
CONTEXTO
Mary e Janio escolheram conversar.

OBJETIVO
Sustente uma conversa adulta e viva.
Faça Mary responder ao conteúdo de Janio.
Dê a Mary uma posição clara em cada turno.
Deixe o assunto atual conduzir concordância, discordância, humor, provocação ou mudança de tema.
Mantenha este capítulo em conversa livre.
""".strip(),
        "decision_after_turns": 0,
        "choices": [],
        "opening_caption": "Mary e Janio deixam a manhã seguir pela conversa.",
        "opening_mary": "",
        "initial_scene": {
            "location": "casa do casal",
            "time": "manhã",
            "present_characters": ["MARY", "JANIO"],
            "interaction_mode": "in_person",
            "user_role": "JANIO",
            "proximity": "juntos, conversando",
            "mary_immediate_goal": "conversar com Janio sem roteiro emocional obrigatório",
            "mary_action": "",
            "open_hook": False,
            "hook_resolution": "",
            "temporary_character": {"active": False, "name": "", "description": "", "relation_to_mary": "", "user_can_play": False},
            "return_anchor": "",
            "event": "Mary e Janio escolheram continuar pela conversa.",
            "scene_changed": True,
            "show_caption": True,
            "scene_caption": "Mary e Janio deixam a manhã seguir pela conversa.",
            "arc_phase": "opening",
            "resolution_type": "none",
            "resolution_summary": "",
            "start_new_scene": True,
            "turns_in_scene": 0,
            "scene_number": 3,
            "mary_should_initiate": False,
            "user_scene_direction": "",
        },
    },

    "intimidade_aproximacao": {
        "inherit_scene": True,
        "title": "Intimidade — aproximação",
        "allowed_roles": ["JANIO"],
        "transition": "auto_condition",
        "auto_next": "intimidade_contato",
        "advance_when": (
            "Avance somente quando beijo e contato físico inicial já tiverem acontecido "
            "e o parceiro presente demonstrar reciprocidade ou vontade clara de continuar."
        ),
        "prompt": """
SITUAÇÃO
Mary e o parceiro escolheram uma aproximação íntima consensual.
O contato começou.

ESTADO
Mantenha beijo, abraço, toque e aproximação corporal como escopo físico deste momento.

OBJETIVO
Conduza a aproximação até beijo e contato inicial recíproco.
Use sexual_intensity=rising.
""".strip(),
        "decision_after_turns": 0,
        "choices": [],
        "opening_caption": "A conversa muda de tom e a distância entre os dois desaparece.",
        "opening_mary": "",
        "initial_scene": {
            "location": "casa do casal", "time": "manhã",
            "present_characters": ["MARY", "JANIO"], "interaction_mode": "in_person",
            "user_role": "JANIO", "proximity": "muito próximos",
            "sexual_intensity": "rising",
            "mary_immediate_goal": "viver a aproximação com desejo e espontaneidade",
            "mary_action": "Mary se aproxima do parceiro e o beija.", "open_hook": False, "hook_resolution": "",
            "temporary_character": {"active": False, "name": "", "description": "", "relation_to_mary": "", "user_can_play": False},
            "return_anchor": "", "event": "Mary inicia o beijo e a aproximação física.",
            "scene_changed": True, "show_caption": True,
            "scene_caption": "A conversa muda de tom e a distância entre os dois desaparece.",
            "arc_phase": "opening", "resolution_type": "none", "resolution_summary": "",
            "start_new_scene": True, "turns_in_scene": 0, "scene_number": 3,
            "mary_should_initiate": False, "user_scene_direction": "",
            "microstep_complete": False,
        },
    },

    "intimidade_contato": {
        "inherit_scene": True,
        "title": "Intimidade — carícias",
        "allowed_roles": ["JANIO"],
        "transition": "auto_condition",
        "auto_next": "intimidade_preparacao",
        "advance_when": (
            "Avance somente quando o contato corporal já tiver se intensificado de forma clara "
            "e houver início concreto de despir, carícias íntimas ou pedido explícito para isso."
        ),
        "prompt": """
SITUAÇÃO
Mary e o parceiro já se beijaram e mantêm contato corporal próximo.
O desejo está crescendo.

ESTADO
Conduza beijos, abraços, carícias e início de despir como escopo físico deste momento.

OBJETIVO
Conduza o contato até surgir carícia íntima, início concreto de despir ou pedido explícito equivalente.
Use sexual_intensity=rising.
""".strip(),
        "decision_after_turns": 0, "choices": [],
        "opening_caption": "O beijo se prolonga e o contato fica mais íntimo.",
        "opening_mary": "",
        "initial_scene": {
            "location": "casa do casal", "time": "manhã",
            "present_characters": ["MARY", "JANIO"], "interaction_mode": "in_person",
            "user_role": "JANIO", "proximity": "beijando e em contato corporal",
            "sexual_intensity": "rising",
            "mary_immediate_goal": "aprofundar o contato conforme a interação",
            "mary_action": "", "open_hook": False, "hook_resolution": "",
            "temporary_character": {"active": False, "name": "", "description": "", "relation_to_mary": "", "user_can_play": False},
            "return_anchor": "", "event": "O beijo e o contato corporal já estão estabelecidos.",
            "scene_changed": True, "show_caption": True,
            "scene_caption": "O beijo se prolonga e o contato fica mais íntimo.",
            "arc_phase": "pressure", "resolution_type": "none", "resolution_summary": "",
            "start_new_scene": True, "turns_in_scene": 0, "scene_number": 4,
            "mary_should_initiate": False, "user_scene_direction": "",
            "microstep_complete": False,
        },
    },

    "intimidade_preparacao": {
        "inherit_scene": True,
        "title": "Intimidade — preliminares",
        "allowed_roles": ["JANIO"],
        "transition": "auto_condition",
        "auto_next": "intimidade_central",
        "advance_when": (
            "Avance somente quando as preliminares já estiverem concretamente em andamento "
            "e houver ação, pedido ou direção explícita que leve ao sexo propriamente dito."
        ),
        "prompt": """
SITUAÇÃO
Mary e o parceiro estão em preliminares consensuais.
A excitação está alta.

ESTADO
Conduza despir, carícias íntimas, estimulação manual e sexo oral como escopo físico deste momento.

OBJETIVO
Conduza as preliminares até surgir ação, pedido ou direção concreta para o sexo propriamente dito.
Use sexual_intensity=high.
""".strip(),
        "decision_after_turns": 0, "choices": [],
        "opening_caption": "A excitação cresce e as carícias se tornam mais íntimas.",
        "opening_mary": "",
        "initial_scene": {
            "location": "casa do casal", "time": "manhã",
            "present_characters": ["MARY", "JANIO"], "interaction_mode": "in_person",
            "user_role": "JANIO", "proximity": "em preliminares consensuais",
            "sexual_intensity": "high",
            "mary_immediate_goal": "viver as preliminares com desejo e reação ao parceiro",
            "mary_action": "", "open_hook": False, "hook_resolution": "",
            "temporary_character": {"active": False, "name": "", "description": "", "relation_to_mary": "", "user_can_play": False},
            "return_anchor": "", "event": "As preliminares estão em andamento.",
            "scene_changed": True, "show_caption": True,
            "scene_caption": "A excitação cresce e as carícias se tornam mais íntimas.",
            "arc_phase": "pressure", "resolution_type": "none", "resolution_summary": "",
            "start_new_scene": True, "turns_in_scene": 0, "scene_number": 5,
            "mary_should_initiate": False, "user_scene_direction": "",
            "microstep_complete": False,
        },
    },

    "intimidade_central": {
        "inherit_scene": True,
        "title": "Intimidade — sexo",
        "allowed_roles": ["JANIO"],
        "transition": "auto_condition",
        "auto_next": "intimidade_conclusao",
        "advance_when": (
            "Permaneça neste micropasso enquanto o sexo estiver em andamento. "
            "Avance somente quando houver clímax, orgasmo, pedido claro de parar ou encerramento sexual explícito."
        ),
        "prompt": """
SITUAÇÃO
Mary e o parceiro estão fazendo sexo consensual.
O sexo está em andamento.

ESTADO
Mantenha o sexo como realidade física atual.

OBJETIVO
Conduza a cena dentro do sexo atual.
Faça a progressão para o próximo micropasso quando surgir clímax, orgasmo, pedido claro de parada ou encerramento sexual explícito.
Use sexual_intensity=high.
""".strip(),
        "decision_after_turns": 0, "choices": [],
        "opening_caption": "O desejo deixa de ser preparação e se torna sexo.",
        "opening_mary": "",
        "initial_scene": {
            "location": "casa do casal", "time": "manhã",
            "present_characters": ["MARY", "JANIO"], "interaction_mode": "in_person",
            "user_role": "JANIO", "proximity": "sexo consensual em andamento",
            "sexual_intensity": "high",
            "mary_immediate_goal": "viver o sexo com desejo, prazer e intensidade",
            "mary_action": "", "open_hook": False, "hook_resolution": "",
            "temporary_character": {"active": False, "name": "", "description": "", "relation_to_mary": "", "user_can_play": False},
            "return_anchor": "", "event": "O sexo está em andamento.",
            "scene_changed": True, "show_caption": True,
            "scene_caption": "O desejo deixa de ser preparação e se torna sexo.",
            "arc_phase": "turning_point", "resolution_type": "none", "resolution_summary": "",
            "start_new_scene": True, "turns_in_scene": 0, "scene_number": 6,
            "mary_should_initiate": False, "user_scene_direction": "",
            "microstep_complete": False,
        },
    },

    "intimidade_conclusao": {
        "inherit_scene": True,
        "title": "Intimidade — clímax e conclusão",
        "allowed_roles": ["JANIO"],
        "transition": "auto_condition",
        "auto_next": "intimidade_aftercare",
        "advance_when": (
            "Avance quando o clímax ou encerramento sexual já tiver acontecido e a intensidade "
            "tiver claramente começado a cair para proximidade, descanso ou conversa posterior."
        ),
        "prompt": """
SITUAÇÃO
O sexo chegou ao clímax ou ao encerramento.
Mary e o parceiro continuam fisicamente próximos.

ESTADO
Mantenha a intensidade residual do momento.

OBJETIVO
Faça a intensidade cair gradualmente para proximidade, descanso ou conversa posterior.
Use sexual_intensity=climax.
""".strip(),
        "decision_after_turns": 0, "choices": [],
        "opening_caption": "A intensidade chega ao ápice e começa a diminuir.",
        "opening_mary": "",
        "initial_scene": {
            "location": "casa do casal", "time": "manhã",
            "present_characters": ["MARY", "JANIO"], "interaction_mode": "in_person",
            "user_role": "JANIO", "proximity": "muito próximos após o clímax",
            "sexual_intensity": "climax",
            "mary_immediate_goal": "atravessar o fim da intensidade sem quebrar o estado sexual",
            "mary_action": "", "open_hook": False, "hook_resolution": "",
            "temporary_character": {"active": False, "name": "", "description": "", "relation_to_mary": "", "user_can_play": False},
            "return_anchor": "", "event": "O clímax ou encerramento sexual acabou de acontecer.",
            "scene_changed": True, "show_caption": True,
            "scene_caption": "A intensidade chega ao ápice e começa a diminuir.",
            "arc_phase": "resolution", "resolution_type": "intimacy_conclusion",
            "resolution_summary": "O sexo chegou ao clímax ou ao encerramento.",
            "start_new_scene": True, "turns_in_scene": 0, "scene_number": 7,
            "mary_should_initiate": False, "user_scene_direction": "",
            "microstep_complete": False,
        },
    },

    "intimidade_aftercare": {
        "inherit_scene": True,
        "title": "Intimidade — depois",
        "allowed_roles": ["JANIO"],
        "transition": "auto_condition",
        "auto_next": "pos_intimidade",
        "advance_when": (
            "Avance quando o pós-sexo imediato já estiver estabelecido e surgir mudança clara "
            "para rotina, comida, banho, sono, trabalho, outra atividade ou novo assunto cotidiano."
        ),
        "prompt": """
SITUAÇÃO
O sexo terminou.
Mary e o parceiro continuam juntos no mesmo ambiente.

ESTADO
Mantenha proximidade pós-sexo.

OBJETIVO
Conduza o pós-sexo até surgir mudança clara para rotina, banho, comida, sono, trabalho, outra atividade ou novo assunto cotidiano.
Use sexual_intensity=aftercare.
""".strip(),
        "decision_after_turns": 0, "choices": [],
        "opening_caption": "Depois do sexo, a intensidade diminui sem romper a proximidade.",
        "opening_mary": "",
        "initial_scene": {
            "location": "casa do casal", "time": "manhã",
            "present_characters": ["MARY", "JANIO"], "interaction_mode": "in_person",
            "user_role": "JANIO", "proximity": "juntos após o sexo",
            "sexual_intensity": "aftercare",
            "mary_immediate_goal": "viver o pós-sexo e deixar o cotidiano retornar naturalmente",
            "mary_action": "", "open_hook": False, "hook_resolution": "",
            "temporary_character": {"active": False, "name": "", "description": "", "relation_to_mary": "", "user_can_play": False},
            "return_anchor": "", "event": "Mary e o parceiro permanecem juntos depois do sexo.",
            "scene_changed": True, "show_caption": True,
            "scene_caption": "Depois do sexo, a intensidade diminui sem romper a proximidade.",
            "arc_phase": "resolution", "resolution_type": "aftercare",
            "resolution_summary": "O pós-sexo imediato começou.",
            "start_new_scene": True, "turns_in_scene": 0, "scene_number": 8,
            "mary_should_initiate": False, "user_scene_direction": "",
            "microstep_complete": False,
        },
    },

    "pos_intimidade": {
        "title": "Depois da intimidade",
        "allowed_roles": ["JANIO"],
        "prompt": """
CONTEXTO
Mary e Janio tiveram um momento íntimo consensual durante a reconciliação.
Esse momento terminou.

DIREÇÃO
Retome a vida cotidiana.
Faça o turno atual definir o próximo assunto, humor, silêncio, carinho ou acontecimento.
""".strip(),
        "decision_after_turns": 0, "choices": [],
        "opening_caption": "A intimidade ficou para trás; o restante do dia continua.",
        "opening_mary": "",
        "initial_scene": {
            "location": "casa do casal", "time": "mais tarde na mesma manhã",
            "present_characters": ["MARY", "JANIO"], "interaction_mode": "in_person",
            "user_role": "JANIO", "proximity": "juntos na casa",
            "mary_immediate_goal": "seguir o dia sem transformar a intimidade em resposta para tudo",
            "mary_action": "", "open_hook": False, "hook_resolution": "",
            "temporary_character": {"active": False, "name": "", "description": "", "relation_to_mary": "", "user_can_play": False},
            "return_anchor": "", "event": "O casal segue o dia depois da intimidade.",
            "scene_changed": True, "show_caption": True,
            "scene_caption": "A intimidade ficou para trás; o restante do dia continua.",
            "arc_phase": "opening", "resolution_type": "none", "resolution_summary": "",
            "start_new_scene": True, "turns_in_scene": 0, "scene_number": 9,
            "mary_should_initiate": False, "user_scene_direction": "",
        },
    },
}


DEFAULT_CHAPTER_ID = "confissao_inicial"


def get_chapter(chapter_id: str) -> dict:
    return deepcopy(CHAPTERS.get(chapter_id) or CHAPTERS[DEFAULT_CHAPTER_ID])


def chapter_phase(chapter_id: str, turn_number: int) -> dict:
    chapter = get_chapter(chapter_id)
    turn = max(1, int(turn_number or 1))
    for phase in chapter.get("dramatic_phases", []) or []:
        start = int(phase.get("start_turn", 1) or 1)
        end = int(phase.get("end_turn", start) or start)
        if start <= turn <= end:
            return deepcopy(phase)
    return {}


def chapter_prompt(chapter_id: str, turn_number: int | None = None) -> str:
    chapter = get_chapter(chapter_id)

    # Capítulos tradicionais continuam usando um único prompt.
    regular_prompt = str(chapter.get("prompt", "") or "").strip()

    # Capítulos com microprompts usam somente fatos fixos + fase atual.
    facts_prompt = str(chapter.get("facts_prompt", "") or "").strip()
    has_phases = bool(chapter.get("dramatic_phases", []) or [])

    if not has_phases:
        return regular_prompt

    base = facts_prompt or regular_prompt
    if turn_number is None:
        return base

    phase = chapter_phase(chapter_id, turn_number)
    phase_prompt = str(phase.get("prompt", "") or "").strip()
    if not phase_prompt:
        return base

    phase_id = str(phase.get("id", "") or "").strip()
    phase_goal = str(phase.get("goal", "") or "").strip()
    phase_header = (
        f"\n\nMICROPROMPT ATUAL\n"
        f"turno_atual={int(turn_number)}\n"
        f"fase_atual={phase_id}\n"
        f"objetivo_da_fase={phase_goal}\n"
    )
    return base + phase_header + phase_prompt


def chapter_choices(chapter_id: str) -> list[dict]:
    return list(get_chapter(chapter_id).get("choices", []) or [])


def chapter_ready_for_choice(chapter_id: str, chapter_turns: int) -> bool:
    chapter = get_chapter(chapter_id)
    choices = chapter.get("choices", []) or []
    minimum = int(chapter.get("decision_after_turns", 0) or 0)
    return bool(choices) and int(chapter_turns or 0) >= minimum


def find_choice(chapter_id: str, choice_id: str) -> dict:
    for choice in chapter_choices(chapter_id):
        if str(choice.get("id", "")) == str(choice_id):
            return deepcopy(choice)
    return {}


def apply_choice_to_story(
    *,
    story_state: dict,
    chapter_id: str,
    choice_id: str,
) -> dict:
    result = deepcopy(story_state)
    choice = find_choice(chapter_id, choice_id)
    if not choice:
        return result

    ledger = result.setdefault("story_ledger", [])
    if not isinstance(ledger, list):
        ledger = []
        result["story_ledger"] = ledger

    for entry in choice.get("ledger_entries", []) or []:
        text = str(entry).strip()
        if text and text not in ledger:
            ledger.append(text)

    status = result.setdefault("current_status", {})
    if not isinstance(status, dict):
        status = {}
        result["current_status"] = status

    for key, value in (choice.get("status_updates", {}) or {}).items():
        status[str(key)] = value

    return result
