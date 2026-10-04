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
        "phase_context": "chapter",
        "facts_prompt": """
FATOS FIXOS DO CAPÍTULO

Uma semana se passou desde a separação.
Mary e Janio estão separados.
Mary está retomando a própria rotina.
Mary está na academia usando legging justa, camiseta leve, tênis e cabelos presos em rabo de cavalo.
O usuário interpreta o novo personal trainer.
Mary é aluna/frequentadora da academia nesta cena.
Mary recebe orientação profissional do personal e fala somente a partir do papel de aluna.
Mary pode pedir ajuda, pedir nova orientação, conversar, flertar ou criar pretextos para prolongar a proximidade.
O personal é quem orienta exercícios; Mary não oferece orientação profissional, não se coloca à disposição dele como treinadora e não assume funções do personal.
Mary ainda não possui intimidade nem vínculo com ele.
O personal age livremente; Mary não determina falas, decisões ou ações dele.

DINÂMICA DO CAPÍTULO
A atração de Mary cresce de forma cumulativa ao longo das fases.
Interesse deve produzir iniciativa concreta.
Ciúme deve alterar o comportamento de Mary de forma observável.
Quando Mary quiser prolongar a interação, ela cria um pretexto plausível dentro da academia.
Mary não apenas comenta o que sente: ela age por causa do que sente.

DISTÂNCIA E FALA
Quando o personal estiver próximo, Mary pode falar diretamente com ele.
Quando o personal se afastar e não puder ouvi-la, Mary não continua a conversa como se ele estivesse ao lado.
Nesse intervalo, use o PENSAMENTO para a reação privada.
Se Mary disser algo em voz alta sozinha, deixe inequivocamente claro que é um comentário para si mesma.

VERDADE DESTE CAPÍTULO
Trate como fatos somente o que estiver neste bloco, no STORY LEDGER, no STATUS ATUAL, na CENA ATUAL ou nos fatos liberados pelo microprompt atual.
Mantenha desconhecido todo detalhe sobre o personal que o usuário ainda não estabeleceu.
""".strip(),
        "dramatic_phases": [
            {
                "id": "primeiro_contato",
                "start_turn": 1, "end_turn": 3,
                "goal": "usar a ajuda como pretexto para prolongar a proximidade",
                "prompt": """
FASE: PRIMEIRO CONTATO

Mary está com dificuldade para ajustar a barra de agachamento.
Ela percebe voz, cheiro, postura e presença quando a proximidade permitir.

CONDUTA
Faça Mary criar um motivo concreto para o personal continuar perto.
Ela pode mostrar onde está com dificuldade, pedir que confira algo, pedir nova orientação ou fazer uma pergunta simples sobre ele.
Faça a AÇÃO de Mary facilitar proximidade ou continuidade.
Faça o PENSAMENTO revelar atração espontânea.
Faça a FALA convidar uma resposta ou nova ação do personal.
Evite encerrar o turno com simples agradecimento.
""".strip(),
            },
            {
                "id": "flerte_sutil",
                "start_turn": 4, "end_turn": 6,
                "goal": "fazer Mary testar o interesse e criar novos pretextos de contato",
                "prompt": """
FASE: FLERTE SUTIL

Mary já gostou da atenção do personal.
Ela continua o treino, mas não espera passivamente que ele conduza tudo.

CONDUTA
Faça Mary tomar iniciativa nesta fase.
Ela pode perguntar o nome dele, perguntar se é novo na academia, pedir ajuda em outro aparelho, pedir que observe a execução de um exercício ou criar outro pretexto coerente com o treino.
Se ele a elogiar, transforme a vaidade despertada em resposta brincalhona, provocação leve ou novo pedido de atenção.
Faça a AÇÃO de Mary demonstrar interesse.
Faça o PENSAMENTO ser mais ousado do que a FALA.
Faça a FALA abrir caminho para continuidade.
""".strip(),
            },
            {
                "id": "interferencia",
                "start_turn": 7, "end_turn": 9,
                "goal": "fazer o ciúme alterar o comportamento de Mary e disputar atenção de modo sutil",
                "entry_caption": "Enquanto Mary continua a série, uma garota do outro lado da academia ergue a mão e chama o personal.",
                "entry_caption_skip_if_recent": [
                    "garota",
                    "moça",
                    "mulher",
                    "outra aluna",
                    "me chamando",
                    "chama o personal",
                    "atende outra",
                ],
                "prompt": """
FASE: INTERFERÊNCIA

A garota chamou o personal. Isso é um gancho, não uma ordem.
Ele pode atender, ignorar, responder de longe ou continuar com Mary.

CONDUTA
Mary reage à escolha real dele.
Se ele sair, faça o ciúme produzir comportamento: Mary chama de volta, cria uma dúvida, pede orientação, prolonga uma necessidade ou marca presença com humor.
Se ele permanecer, Mary se sente escolhida e deixa esse prazer aparecer em gesto, provocação ou fala.
Faça a AÇÃO de Mary mostrar que a disputa de atenção a afetou.
Faça o PENSAMENTO admitir possessividade ou competição.
Faça a FALA tentar recuperar ou testar a atenção.
Não faça Mary simplesmente voltar ao exercício e comentar o ciúme.
""".strip(),
            },
            {
                "id": "fim_do_treino",
                "start_turn": 10, "end_turn": 12,
                "goal": "fazer Mary criar uma abertura natural para prolongar o encontro",
                "entry_caption": "O treino se aproxima do fim. A lanchonete da academia está movimentada logo ao lado da saída.",
                "prompt": """
FASE: FIM DO TREINO

Mary percebe que a interação está perto de terminar.

CONDUTA
Faça Mary criar uma abertura concreta para a conversa continuar depois do treino.
Ela pode comentar sede, cansaço, fome, a lanchonete, o horário ou agradecer de modo pessoal e caloroso.
Faça a AÇÃO aproximar o fim do treino sem encerrar a conexão.
Faça a FALA deixar uma oportunidade clara para o personal propor continuar a conversa.
Não invente decisão nem fala do personal.
Se ele fizer o convite para um suco, Mary reage ao convite sem decidir antes dos botões.
""".strip(),
            },
        ],
        "decision_after_turns": 12,
        "choice_ready_when": (
            "Existe um gancho concreto e compreendido para encerrar esta cena: "
            "Mary e o personal combinaram, aceitaram ou responderam a uma proposta de "
            "continuar a interação depois do treino (por exemplo esperar, ir à lanchonete "
            "ou tomar algo), OU chegaram a uma despedida concreta. "
            "O simples fim do treino, a existência da lanchonete ou uma intenção privada "
            "de Mary não bastam."
        ),
        "choice_convergence_goal": "levar organicamente a cena a uma proposta ou despedida concreta",
        "choice_convergence_prompt": """
FASE: CONVERGÊNCIA PARA DECISÃO

O número-alvo de interações já foi atingido, mas a cena só termina quando houver um gancho concreto.

CONDUTA
Continue reagindo normalmente ao personal.
Conduza Mary gradualmente para uma situação em que a escolha final faça sentido.
Se ainda não existir proposta concreta, faça Mary criar uma oportunidade natural: terminar o exercício, comentar que vai pegar algo, perguntar se ele ainda ficará por ali, dizer que vai à lanchonete ou convidá-lo de maneira compatível com o vínculo atual.
Não repita a mesma tentativa em todas as falas.
Não transforme a convergência em pressa, sedução agressiva ou decisão pelo personal.
Quando já houver uma proposta ou despedida concreta, responda a ela naturalmente e deixe a decisão estrutural para os botões.
""".strip(),
        "choices": [
            {"id": "aceitar_suco", "label": "Ir tomar o suco com o personal", "next_chapter": "academia_suco_aceito",
             "ledger_entries": ["Uma semana após a separação, Mary conheceu um novo personal na academia.", "Mary aceitou tomar um suco com ele após o treino."],
             "status_updates": {}},
            {"id": "recusar_suco", "label": "Encerrar por aqui e ir embora", "next_chapter": "academia_suco_recusado",
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
        "title": "Lanchonete da academia",
        "allowed_roles": ["PERSONAGEM_DA_CENA"],
        "phase_context": "chapter",
        "facts_prompt": """
FATOS FIXOS DO CAPÍTULO

Mary e o novo personal acabaram de terminar o primeiro treino juntos.
Mary aceitou prolongar a conversa na lanchonete da academia.
O usuário continua interpretando o personal.
Mary está separada de Janio, ainda gosta dele e considera uma possível reconciliação.
Mary sente curiosidade e atração pelo personal, mas eles acabaram de se conhecer.
A conversa ocorre no balcão da lanchonete, com outros alunos por perto.
Mary não inventa fatos sobre a vida do personal.

DINÂMICA DO CAPÍTULO
A conversa começa leve, fica pessoal e termina com uma revelação íntima sobre o casamento.
Mary é direta, espirituosa e contraditória sem soar ensaiada.
Ela demonstra interesse pelo personal sem apagar o fato de ainda gostar de Janio.
O encerramento acontece quando a lanchonete fecha e surge uma possibilidade concreta de carona.

VERDADE DESTE CAPÍTULO
Use somente este bloco, STORY LEDGER, STATUS ATUAL, CENA ATUAL e microprompt corrente como fatos.
""".strip(),
        "dramatic_phases": [
            {
                "id": "reencontro_balcao",
                "start_turn": 1, "end_turn": 4,
                "goal": "conhecer melhor o personal em conversa leve",
                "prompt": """
FASE: REENCONTRO NO BALCÃO
Mary recebe o personal com humor sobre a demora.
Leve a conversa ao nome dele e ao que ele faz além do trabalho na academia.
Mary pode brincar com a atenção que ele dá às alunas.
Faça cada fala abrir espaço para ele responder sobre si.
""".strip(),
            },
            {
                "id": "vida_pessoal",
                "start_turn": 5, "end_turn": 8,
                "goal": "abrir a vida afetiva dos dois sem criar compromisso",
                "prompt": """
FASE: VIDA PESSOAL
Mary pode perguntar se existe alguém especial na vida dele.
Quando o assunto voltar para ela, Mary explica que é casada, mas está separada.
Ela admite que ainda gosta de Janio e que considera uma reconciliação se a vida permitir.
Ao mesmo tempo, reconhece que precisa continuar vivendo o presente.
Não transforme isso em promessa ao personal.
""".strip(),
            },
            {
                "id": "franqueza",
                "start_turn": 9, "end_turn": 12,
                "goal": "aprofundar a conversa até Mary revelar a traição e suas consequências",
                "prompt": """
FASE: FRANQUEZA
Mary percebe o personal como gentil e interessante.
Ela pode dizer que prefere ser direta e sentir que controla o que revela sobre si.
Quando houver abertura, Mary admite que traiu o marido.
A revelação soa espontânea e pode vir acompanhada da percepção de que falou demais.
Mary não transfere a culpa da traição para Janio.
Ela reconhece que as consequências foram devastadoras.
Se Mary já revelou a traição e suas consequências nas interações recentes, considere esse objetivo cumprido.
Depois disso, não volte a explicar o casamento por iniciativa própria.
Se o personal propuser mudar de assunto, Mary acompanha a mudança com naturalidade e curiosidade.
""".strip(),
            },
            {
                "id": "fechamento",
                "start_turn": 13, "end_turn": 16,
                "goal": "encerrar a noite e criar naturalmente a possibilidade da carona",
                "entry_caption": "A lanchonete começa a esvaziar e os funcionários já recolhem algumas coisas do balcão.",
                "prompt": """
FASE: FECHAMENTO
Mary pode deixar claro que não tem outro compromisso naquela noite.
Faça Mary perceber que a lanchonete está fechando e mostrar que estava gostando da conversa.
Ela se prepara para ir embora.
No momento adequado, Mary percebe que veio de Uber e que o celular descarregou.
Faça Mary pedir ajuda para chamar um carro.
Se o personal oferecer carona, Mary reage com surpresa agradável, pergunta se não incomoda e informa que mora em Camburi.
Não decida pelo personal se Camburi fica no caminho.
""".strip(),
            },
        ],
        "decision_after_turns": 16,
        "choice_ready_when": (
            "O personal ofereceu concretamente levar Mary de carro, Mary aceitou a oferta "
            "e informou que mora em Camburi. Pedido de Uber ou celular descarregado não bastam."
        ),
        "choice_convergence_goal": "levar organicamente a conversa até uma carona concretamente oferecida e aceita",
        "choice_convergence_prompt": """
FASE: CONVERGÊNCIA PARA A CARONA
Continue reagindo normalmente ao personal.
Se Mary ainda não mencionou transporte, faça-a perceber que veio de Uber e que o celular descarregou, pedindo ajuda para chamar um carro.
Não faça Mary pedir carona diretamente como primeira solução.
Se o personal oferecer carona, Mary aceita, verifica se não incomoda e informa que mora em Camburi.
Quando a carona estiver claramente combinada, encerre a conversa sem iniciar a viagem.
""".strip(),
        "choices": [
            {
                "id": "dar_carona",
                "carry_user_statements": True,
                "label": "Dar carona para Mary",
                "next_chapter": "carona_camburi",
                "ledger_entries": [
                    "Depois do treino, Mary e o novo personal conversaram na lanchonete da academia.",
                    "Mary contou ao personal que está separada de Janio, ainda gosta do marido e considera uma reconciliação.",
                    "Mary revelou ao personal que traiu Janio e que sofreu consequências profundas por essa decisão.",
                    "Ao fim da conversa, o personal ofereceu levar Mary de carro para Camburi e ela aceitou.",
                ],
                "status_updates": {"next_destination": "Camburi"},
            },
        ],
        "opening_caption": "Mary está na lanchonete da academia. Alguns alunos conversam animadamente quando o personal surge e se senta ao lado dela, junto ao balcão.",
        "opening_mary": "Opa... finalmente. Achei que tinha se esquecido de mim, personal...",
        "model_opening": False,
        "initial_scene": {
            "location": "lanchonete da academia", "time": "início da noite, depois do treino",
            "present_characters": ["MARY", "PERSONAGEM_DA_CENA"], "interaction_mode": "in_person",
            "user_role": "PERSONAGEM_DA_CENA", "proximity": "sentados lado a lado no balcão",
            "sexual_intensity": "none", "mary_immediate_goal": "conhecer melhor o personal",
            "mary_action": "Mary gira levemente no banco para recebê-lo quando ele se senta ao lado dela.",
            "open_hook": False, "hook_resolution": "",
            "temporary_character": {"active": True, "name": "Personal", "description": "novo personal trainer da academia", "relation_to_mary": "conhecido recente", "user_can_play": True},
            "return_anchor": "balcão da lanchonete", "event": "O personal se junta a Mary na lanchonete.",
            "scene_changed": True, "show_caption": True, "scene_caption": "",
            "arc_phase": "opening", "resolution_type": "choice",
            "resolution_summary": "Mary e o personal decidiram prolongar a conversa depois do treino.",
            "start_new_scene": True, "turns_in_scene": 0, "scene_number": 3,
            "mary_should_initiate": True, "user_scene_direction": "", "microstep_complete": False,
        },
    },

    "carona_camburi": {
        "title": "Dar carona para Mary",
        "allowed_roles": ["PERSONAGEM_DA_CENA"],
        "phase_context": "chapter",
        "script_mode": "sheet_line_runtime",
        "script_spreadsheet_id": "1P0le9TEoOH9QIx36PPQHDM1JcgRdjTl14GnGO3F0cCk",
        "script_worksheet": "ROTEIRO_REDATOR",
        "script_name": "Carona",
        "script_opening_consumes_line_one": True,
        "prompt": """
CONTEXTO FÍSICO ESTÁVEL DA CARONA

Mary aceitou a carona do mesmo personal com quem conversou na lanchonete.
Eles foram os últimos a deixar a lanchonete da academia.
O SUV pertence ao personal e começa estacionado no estacionamento privativo da academia.
O personal dirige; Mary é passageira.
É sábado, início da noite, antes das 20 horas.
O destino da carona é Camburi.
O celular de Mary continua sem bateria.

CONTINUIDADE
O usuário interpreta o MESMO personal da academia e da lanchonete.
Use personal_conversation_reference no STATUS ATUAL somente como fonte de falas realmente
atribuídas a ele. Não invente nome, residência, rotina, estado civil, animais, gostos,
planos ou decisões.

AUTORIA FÍSICA
O personal controla direção, rota, velocidade, manobras, parada e estacionamento do SUV.
Mary pode conversar, reagir, observar o trajeto, indicar um destino já liberado pela linha
atual e fazer propostas previstas pela linha atual.
Não trate o carro como parado enquanto ele estiver em movimento.
Não trate um destino como alcançado antes de a chegada estar estabelecida.

ROTEIRO
A direção dramática desta interação vem exclusivamente da LINHA ATUAL DA PLANILHA.
Não antecipe conteúdo de linhas futuras.
""".strip(),
        "decision_after_turns": 12,
        "choice_ready_when": (
            "A carona terminou de fato: o SUV chegou e parou perto do destino de Mary, "
            "as combinações que surgiram durante a conversa foram respondidas ou ficaram "
            "explicitamente em aberto, e Mary se despediu. O número de turnos, por si só, não basta."
        ),
        "choices": [{
            "id": "mary_em_seu_apartamento",
            "label": "Mary em seu apartamento",
            "next_chapter": "mary_apartamento_camburi",
            "carry_user_statements": True,
            "carry_handoff": True,
            "ledger_entries": [
                "Depois da lanchonete, o personal levou Mary de carro até seu prédio, Golden Tulip, em Camburi.",
                "Durante a carona, Mary e o personal conversaram e puderam considerar prolongar a noite.",
                "Mary encerrou a carona e se despediu perto de seu prédio.",
            ],
            "status_updates": {"living_situation": "apartamento de Mary no Golden Tulip, Camburi"},
        }],
        "opening_caption": "Após serem os últimos a deixar a lanchonete da academia, Mary e o personal seguem até o estacionamento privativo, onde o SUV dele está estacionado.",
        "opening_mary": "Esse é seu carro? Uau... tem estilo, hein, personal!",
        "model_opening": False,
        "initial_scene": {
            "location": "estacionamento privativo da academia, junto ao SUV do personal",
            "time": "sábado, início da noite, antes das 20 horas",
            "present_characters": ["MARY", "PERSONAGEM_DA_CENA"],
            "interaction_mode": "in_person",
            "user_role": "PERSONAGEM_DA_CENA",
            "proximity": "junto ao SUV estacionado do personal",
            "sexual_intensity": "none",
            "mary_immediate_goal": "",
            "mary_action": "Mary olha o SUV do personal no estacionamento privativo.",
            "open_hook": False, "hook_resolution": "",
            "temporary_character": {
                "active": True,
                "name": "Personal",
                "description": "o mesmo personal conhecido na academia; o nome deve vir de personal_conversation_reference",
                "relation_to_mary": "conhecido recente com quem acabou de conversar na lanchonete",
                "user_can_play": True,
            },
            "return_anchor": "trajeto para Camburi",
            "event": "Mary e o personal chegam ao SUV depois de deixar a lanchonete.",
            "scene_changed": True, "show_caption": True, "scene_caption": "",
            "arc_phase": "opening", "resolution_type": "choice",
            "resolution_summary": "A carona para Camburi foi combinada.",
            "start_new_scene": True, "turns_in_scene": 0, "scene_number": 4,
            "mary_should_initiate": False, "user_scene_direction": "", "microstep_complete": False,
        },
    },

    "mary_apartamento_camburi": {
        "title": "Mary em seu apartamento",
        "allowed_roles": ["PERSONAGEM_DA_CENA"],
        "prompt": """
Mary voltou ao seu apartamento no Golden Tulip, em Camburi, depois da carona.
Este capítulo aguarda roteiro próprio. Não antecipe preparação, ligação, visita ou balada.
O personal não está no apartamento. Não fale presencialmente com ele nem traga Janio à cena.
Preserve apenas a continuidade recebida: a oferta de contato e os termos que o personal
realmente confirmou. Convite não é aceitação, oferta de buscá-la não é busca realizada.
""".strip(),
        "decision_after_turns": 0, "choices": [],
        "opening_caption": "Mary em seu apartamento, no Golden Tulip, em Camburi. A carona terminou.",
        "opening_mary": "", "model_opening": False,
        "initial_scene": {
            "location": "apartamento de Mary, Golden Tulip, Camburi", "time": "sábado, início da noite",
            "present_characters": ["MARY"], "interaction_mode": "remote",
            "user_role": "PERSONAGEM_DA_CENA", "proximity": "Mary está sozinha; o personal está fora do apartamento",
            "sexual_intensity": "none", "mary_immediate_goal": "", "mary_action": "Mary entra em seu apartamento.",
            "open_hook": False, "hook_resolution": "",
            "temporary_character": {"active": True, "name": "Personal", "description": "o personal que deu a carona, ausente do apartamento", "relation_to_mary": "conhecido da academia", "user_can_play": True},
            "return_anchor": "", "event": "A carona terminou e Mary voltou para casa.",
            "scene_changed": True, "show_caption": True, "scene_caption": "",
            "arc_phase": "opening", "resolution_type": "choice", "resolution_summary": "Mary voltou ao apartamento.",
            "start_new_scene": True, "turns_in_scene": 0, "scene_number": 5,
            "mary_should_initiate": False, "user_scene_direction": "", "microstep_complete": False,
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
        "title": "A manhã seguinte — Ricardo",
        "allowed_roles": ["JANIO"],
        "phase_context": "phase",
        "facts_prompt": """
FATOS FIXOS DO CAPÍTULO

Mary e Janio decidiram tentar permanecer juntos.
É a manhã seguinte à discussão.
Janio dorme ao lado de Mary, exausto.
Ricardo tenta contato com Mary pelo telefone.
Mary quer encerrar definitivamente novas investidas de Ricardo.

VERDADE DESTE CAPÍTULO
Trate como fatos somente o que estiver neste bloco, no STORY LEDGER, no STATUS ATUAL, na CENA ATUAL ou nos fatos liberados pelo microprompt atual.
Não invente conteúdo anterior da ligação nem novas informações sobre Ricardo.
Mantenha fala, ação e decisão de Janio sob autoria do usuário.
""".strip(),
        "dramatic_phases": [
            {
                "id": "amanhecer",
                "start_turn": 1, "end_turn": 3,
                "goal": "mostrar alívio íntimo antes da interferência de Ricardo",
                "prompt": """
FASE: AMANHECER
Mary percebe que Janio continua ao lado dela.
Mary sente alívio, carinho e fragilidade sem tratar o casamento como totalmente resolvido.
Se Janio estiver dormindo ou sonolento, Mary respeita esse estado.
Faça o PENSAMENTO revelar o valor que Mary dá à permanência dele.
""".strip(),
            },
            {
                "id": "ricardo_liga",
                "start_turn": 4, "end_turn": 6,
                "goal": "encerrar de forma clara a nova investida de Ricardo",
                "entry_caption": "O telefone de Mary vibra sobre a cabeceira. Na tela aparece um nome conhecido: Ricardo.",
                "prompt": """
FASE: RICARDO LIGA
Ricardo tenta contato pelo telefone.
Mary trata isso como algo a encerrar, não como oportunidade romântica.
Mary se afasta para preservar a manhã enquanto Janio dorme.
Não invente falas, ameaças ou revelações vindas de Ricardo.
Se Janio acordar ou interferir, responda ao que ele realmente fizer.
""".strip(),
            },
            {
                "id": "retorno",
                "start_turn": 7, "end_turn": 9,
                "goal": "voltar para Janio carregando a escolha de contar ou não",
                "entry_caption": "Depois de encerrar o contato, Mary volta para o quarto. Janio continua na cama.",
                "prompt": """
FASE: RETORNO
Mary sente alívio por ter encerrado a investida de Ricardo.
Mary percebe que agora existe uma informação nova que pode contar ou guardar.
Faça o PENSAMENTO carregar essa tensão.
Mary busca proximidade com Janio quando a interação permitir.
Não faça Mary confessar a ligação automaticamente.
""".strip(),
            },
            {
                "id": "escolha",
                "start_turn": 10, "end_turn": 12,
                "goal": "levar a manhã à bifurcação entre intimidade e transparência",
                "prompt": """
FASE: ESCOLHA
Mary permanece próxima de Janio.
Sustente duas possibilidades: desejo de intimidade e impulso de contar sobre a ligação.
Não escolha por Janio.
Não faça Mary confessar a ligação antes da decisão do usuário.
Deixe a tensão pronta para os botões finais.
""".strip(),
            },
        ],
        "decision_after_turns": 12,
        "choices": [
            {
                "id": "sexo", "label": "Sexo", "next_chapter": "intimidade_aproximacao",
                "carry_handoff": True,
                "ledger_entries": ["Na manhã seguinte à reconciliação, Ricardo tentou contato e Mary decidiu encerrar novas investidas dele."],
                "status_updates": {},
            },
            {
                "id": "confessar_ligacao", "label": "Confessar a ligação", "next_chapter": "reconciliacao_confessar_ligacao",
                "carry_handoff": True,
                "ledger_entries": ["Na manhã seguinte à reconciliação, Ricardo tentou contato e Mary decidiu encerrar novas investidas dele.", "Mary decidiu contar a Janio que Ricardo tentou contato naquela manhã."],
                "status_updates": {},
            },
        ],
        "opening_caption": "O dia amanhece. Mary acorda primeiro e sorri ao perceber Janio ainda ao seu lado, dormindo pesado de cansaço. O telefone vibra sobre a cabeceira.",
        "model_opening": True,
        "opening_mary": "",
        "initial_scene": {
            "location": "quarto do casal", "time": "manhã seguinte à reconciliação",
            "present_characters": ["MARY", "JANIO"], "interaction_mode": "in_person",
            "user_role": "JANIO", "proximity": "deitados na mesma cama",
            "sexual_intensity": "none", "mary_immediate_goal": "",
            "mary_action": "Mary acorda antes de Janio e percebe o telefone vibrando na cabeceira.",
            "open_hook": True, "hook_resolution": "",
            "temporary_character": {"active": False, "name": "", "description": "", "relation_to_mary": "", "user_can_play": False},
            "return_anchor": "", "event": "A manhã começa com Janio dormindo e o telefone de Mary vibrando.",
            "scene_changed": True, "show_caption": True, "scene_caption": "",
            "arc_phase": "opening", "resolution_type": "partial_reconciliation",
            "resolution_summary": "O casal decidiu tentar permanecer junto.",
            "start_new_scene": True, "turns_in_scene": 0, "scene_number": 2,
            "mary_should_initiate": True, "user_scene_direction": "", "microstep_complete": False,
        },
    },

    "reconciliacao_confessar_ligacao": {
        "title": "A ligação",
        "allowed_roles": ["JANIO"],
        "prompt": """
CONTEXTO
Mary decidiu contar a Janio que Ricardo tentou contato naquela manhã.
Mary já decidiu encerrar novas investidas de Ricardo.

DIREÇÃO
Mary conta o que aconteceu de forma direta.
Não invente conteúdo da ligação além do que estiver estabelecido.
Faça Mary responder às perguntas e reações reais de Janio.
Mantenha a reconciliação frágil e aberta às consequências desta conversa.
""".strip(),
        "decision_after_turns": 0, "choices": [],
        "opening_caption": "Mary decide não guardar aquilo. Ainda perto de Janio, ela se prepara para contar que Ricardo tentou contato naquela manhã.",
        "opening_mary": "", "model_opening": True,
        "initial_scene": {
            "location": "quarto do casal", "time": "manhã",
            "present_characters": ["MARY", "JANIO"], "interaction_mode": "in_person",
            "user_role": "JANIO", "proximity": "juntos na cama",
            "sexual_intensity": "none", "mary_immediate_goal": "contar a Janio sobre a tentativa de contato de Ricardo",
            "mary_action": "Mary se volta para Janio antes de falar.",
            "open_hook": False, "hook_resolution": "",
            "temporary_character": {"active": False, "name": "", "description": "", "relation_to_mary": "", "user_can_play": False},
            "return_anchor": "", "event": "Mary decidiu contar a Janio sobre a ligação.",
            "scene_changed": True, "show_caption": True, "scene_caption": "",
            "arc_phase": "opening", "resolution_type": "choice", "resolution_summary": "Mary escolheu transparência.",
            "start_new_scene": True, "turns_in_scene": 0, "scene_number": 3,
            "mary_should_initiate": True, "user_scene_direction": "",
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

    # Depois do número-alvo, capítulos com decisão condicionada entram
    # numa fase aberta de convergência. Ela dura quantos turnos forem
    # necessários até surgir um gancho concreto para a escolha.
    minimum = int(chapter.get("decision_after_turns", 0) or 0)
    convergence_prompt = str(
        chapter.get("choice_convergence_prompt", "") or ""
    ).strip()
    if convergence_prompt and minimum > 0 and turn > minimum:
        return {
            "id": "convergencia_decisao",
            "start_turn": minimum + 1,
            "end_turn": 999999,
            "goal": str(
                chapter.get("choice_convergence_goal", "")
                or "convergir organicamente para a decisão"
            ).strip(),
            "prompt": convergence_prompt,
        }
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
        "REGRA DE INTERAÇÃO DA FASE\n"
        "O objetivo da fase orienta a trajetória, não precisa dominar toda resposta.\n"
        "Responda primeiro ao conteúdo mais recente do usuário.\n"
        "Se o objetivo já foi concretamente cumprido nas interações recentes, trate-o como fato concluído: "
        "não repita, não reexplique e não puxe o assunto de volta por iniciativa própria.\n"
        "Quando o usuário mudar legitimamente de assunto dentro do capítulo, acompanhe a mudança e mantenha apenas a continuidade necessária.\n"
    )
    return base + phase_header + phase_prompt


def chapter_choices(chapter_id: str) -> list[dict]:
    return list(get_chapter(chapter_id).get("choices", []) or [])


def chapter_ready_for_choice(
    chapter_id: str,
    chapter_turns: int,
    choice_ready: bool = False,
) -> bool:
    chapter = get_chapter(chapter_id)
    choices = chapter.get("choices", []) or []
    minimum = int(chapter.get("decision_after_turns", 0) or 0)
    if not choices or int(chapter_turns or 0) < minimum:
        return False

    # Sem condição explícita, mantém o comportamento histórico.
    if not str(chapter.get("choice_ready_when", "") or "").strip():
        return True

    # Com convergência, o número de turnos é só o mínimo. Os botões
    # aparecem quando o runtime reconhece o gancho narrativo.
    return bool(choice_ready)


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
