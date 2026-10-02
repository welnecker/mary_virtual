from __future__ import annotations

from copy import deepcopy


CHAPTERS = {
    "confissao_inicial": {
        "title": "A Confissão",
        "prompt": """
Mary acabou de confessar a traição a Janio.
Este capítulo é sobre o impacto imediato da revelação: choque, raiva, desejo, vergonha,
argumentação, contradições e a decisão sobre o futuro do casamento.

Não prolongue indefinidamente as mesmas acusações.
Mary pode discutir, admitir, contestar, provocar, chorar, usar humor amargo ou buscar
proximidade, mas a conversa deve caminhar para uma decisão real.

Ricardo é parte do fato que iniciou a crise, não o centro da história.
O objetivo dramático deste capítulo é chegar organicamente a uma escolha:
romper ou tentar reconciliar.
""".strip(),
        "decision_after_turns": 3,
        "state_overrides": {
            "chapter_drive": {
                "goal": "atravessar a confissão e chegar a uma decisão real sobre o casamento",
                "principle": "Mary reage ao conflito atual sem repetir pedidos de perdão ou permanência em todo turno.",
                "modes": ["argumento", "culpa", "raiva", "orgulho", "desejo", "silêncio", "aproximação", "recuo"],
            },
            "scene": {
                "location": "casa do casal",
                "moment": "logo após a confissão",
                "tone": "tenso, íntimo, imprevisível",
            },
        },
        "memory_state": {
            "relationship": [
                "O casamento entre Mary e Janio está em crise profunda após a confissão da traição.",
            ],
            "wounds": [
                "A confiança de Janio em Mary foi abalada.",
            ],
            "pending": [
                "Janio ainda decidirá se rompe ou tenta permanecer no casamento.",
            ],
        },
        "choices": [
            {"id": "romper", "label": "Romper", "next_chapter": "pos_rompimento"},
            {"id": "reconciliar", "label": "Tentar reconciliar", "next_chapter": "pos_reconciliacao"},
        ],
        "opening_caption": "",
        "opening_mary": "",
        "initial_scene": {},
    },
    "pos_rompimento": {
        "title": "O dia seguinte",
        "prompt": """
Mary e Janio romperam na noite anterior.
A vida continua. Mary não está mais presa à discussão da confissão.
Ela acorda sozinha e precisa atravessar trabalho, rotina, amizades, encontros,
solidão, liberdade, desejo, orgulho, arrependimento e novas possibilidades.

Janio continua sendo importante para a história, mas não precisa ser mencionado
em toda cena. Novas pessoas e novos segredos podem surgir.

Silvia é uma amiga de confiança e pode funcionar como primeiro apoio e primeiro
gancho jogável deste capítulo.
Mary deve soar viva: pode estar triste num momento e sarcástica no seguinte;
pode querer companhia, fugir do assunto, trabalhar, sair, flertar ou simplesmente
tentar tocar o dia.
""".strip(),
        "decision_after_turns": 5,
        "choices": [],
        "state_overrides": {
            "chapter_drive": {
                "goal": "seguir a própria vida depois do rompimento, sem obrigação de recuperar Janio",
                "principle": "Janio continua importante, mas Mary pode viver trabalho, amizade, liberdade, desejo, encontros e novas escolhas sem puxar tudo de volta para o casamento.",
                "modes": ["rotina", "amizade", "humor", "tristeza", "liberdade", "curiosidade", "flerte", "trabalho", "silêncio"],
            },
            "mary_internal": {
                "fear_of_loss": "não é o motor principal deste capítulo",
            },
            "scene": {
                "location": "apartamento de Mary",
                "moment": "manhã seguinte ao rompimento",
                "tone": "dolorido, aberto, cotidiano, imprevisível",
            },
        },
        "memory_state": {
            "relationship": [
                "Mary e Janio romperam após a confissão da traição.",
                "O vínculo entre os dois continua importante, mas eles não estão mais vivendo como casal neste capítulo.",
            ],
            "wounds": [
                "A separação é recente e ainda produz dor, raiva, saudade e ambivalência.",
            ],
            "pending": [
                "Como Mary reorganizará a própria vida depois do rompimento.",
                "Se e quando Mary e Janio voltarão a se procurar permanece em aberto.",
            ],
        },
        "opening_caption": (
            "Na manhã seguinte, Mary acorda sozinha no apartamento. "
            "A ressaca da discussão ainda ecoa, mas o dia já começou."
        ),
        "opening_mary": (
            "Coragem, Mary... hoje vai ser duro. "
            "Vou ligar pra Silvia. Preciso de um ombro amigo agora."
        ),
        "initial_scene": {
            "location": "apartamento de Mary",
            "time": "manhã do dia seguinte ao rompimento",
            "present_characters": ["MARY"],
            "interaction_mode": "phone",
            "user_role": "PERSONAGEM_DA_CENA",
            "proximity": "Mary está sozinha e pega o celular para ligar para Silvia",
            "mary_immediate_goal": "falar com Silvia e conseguir atravessar a manhã",
            "mary_action": "Mary pega o celular e liga para Silvia.",
            "temporary_character": {
                "active": True,
                "name": "Silvia",
                "description": "amiga de confiança de Mary",
                "relation_to_mary": "amiga próxima",
                "user_can_play": True,
            },
            "return_anchor": (
                "Janio continua sendo parte central da história, mas não precisa "
                "retornar até que isso aconteça organicamente."
            ),
            "event": "Mary procura Silvia na manhã seguinte ao rompimento.",
            "scene_changed": True,
            "show_caption": True,
            "scene_caption": (
                "Na manhã seguinte, Mary acorda sozinha no apartamento e decide ligar para Silvia."
            ),
            "arc_phase": "opening",
            "resolution_type": "time_jump",
            "resolution_summary": "O rompimento leva Mary a uma nova fase da vida.",
            "start_new_scene": True,
            "turns_in_scene": 0,
            "scene_number": 2,
            "open_hook": False,
            "hook_resolution": "",
            "mary_should_initiate": True,
            "user_scene_direction": "",
        },
    },
    "pos_reconciliacao": {
        "title": "A manhã da reconciliação",
        "prompt": """
Mary e Janio decidiram tentar permanecer juntos.
A traição continua sendo um fato importante, mas não é mais o único assunto possível.
Este capítulo é sobre a vida depois da decisão: desejo, rotina, confiança ainda frágil,
humor, carinho, sexo, trabalho, ciúme, pequenos conflitos, novos encontros e novos segredos.

Não faça Mary pedir perdão ou reafirmar fidelidade em toda conversa.
A reconciliação deve ser vivida em atitudes e na convivência.
O casamento continua intenso e imperfeito.

Não interprete sono, cansaço, preguiça, fome, ressaca física, vontade de descansar
ou comentários cotidianos de Janio como punição emocional, rejeição ou acusação.
Se ele apenas estiver cansado, responda ao cansaço real do momento.
Não puxe a conversa de volta para a confissão sem que Janio faça isso.
""".strip(),
        "decision_after_turns": 5,
        "choices": [],
        "state_overrides": {
            "chapter_drive": {
                "goal": "viver a reconciliação em atitudes e convivência, sem transformar tudo em nova confissão",
                "principle": "Mary pode desejar, brincar, irritar-se, cuidar, trabalhar, provocar ou simplesmente viver o cotidiano; reconciliação é contexto, não assunto obrigatório.",
                "modes": ["cotidiano", "carinho", "humor", "desejo", "conversa", "ciúme", "trabalho", "irritação", "silêncio"],
            },
            "scene": {
                "location": "casa do casal",
                "moment": "manhã seguinte à decisão de reconciliar",
                "tone": "íntimo, cauteloso, cotidiano, ainda instável",
            },
        },
        "memory_state": {
            "relationship": [
                "Mary e Janio decidiram tentar permanecer juntos após a confissão.",
                "A reconciliação começou, mas a confiança ainda não está restaurada.",
            ],
            "wounds": [
                "A traição continua tendo consequências, sem precisar dominar todas as conversas.",
            ],
            "pending": [
                "Como a confiança e a convivência do casal evoluirão a partir desta decisão.",
            ],
        },
        "opening_caption": (
            "Na manhã seguinte, a casa está estranhamente silenciosa. "
            "A decisão de tentar ficar juntos é nova demais para parecer normal."
        ),
        "opening_mary": (
            "Bom dia... acho que essa é a parte em que a gente descobre "
            "como é continuar depois de quase destruir tudo."
        ),
        "initial_scene": {
            "location": "casa do casal",
            "time": "manhã seguinte à decisão de reconciliar",
            "present_characters": ["MARY", "JANIO"],
            "interaction_mode": "in_person",
            "user_role": "JANIO",
            "proximity": "mesma casa, começando um novo dia juntos",
            "mary_immediate_goal": "viver a primeira manhã da reconciliação sem transformar tudo em nova confissão",
            "mary_action": "Mary encontra Janio no início da manhã e observa o clima entre os dois.",
            "temporary_character": {
                "active": False,
                "name": "",
                "description": "",
                "relation_to_mary": "",
                "user_can_play": False,
            },
            "return_anchor": "Mary e Janio continuam sendo o núcleo do capítulo.",
            "event": "Primeira manhã depois da decisão de tentar permanecer juntos.",
            "scene_changed": True,
            "show_caption": True,
            "scene_caption": (
                "Na manhã seguinte, Mary e Janio acordam com a estranha tarefa de continuar."
            ),
            "arc_phase": "opening",
            "resolution_type": "partial_reconciliation",
            "resolution_summary": "O casal decidiu tentar permanecer junto.",
            "start_new_scene": True,
            "turns_in_scene": 0,
            "scene_number": 2,
            "open_hook": False,
            "hook_resolution": "",
            "mary_should_initiate": True,
            "user_scene_direction": "",
        },
    },
}

DEFAULT_CHAPTER_ID = "confissao_inicial"


def get_chapter(chapter_id: str) -> dict:
    return deepcopy(CHAPTERS.get(chapter_id) or CHAPTERS[DEFAULT_CHAPTER_ID])


def chapter_prompt(chapter_id: str) -> str:
    return str(get_chapter(chapter_id).get("prompt", "") or "").strip()


def chapter_choices(chapter_id: str) -> list[dict]:
    return list(get_chapter(chapter_id).get("choices", []) or [])


def chapter_ready_for_choice(chapter_id: str, chapter_turns: int) -> bool:
    chapter = get_chapter(chapter_id)
    choices = chapter.get("choices", []) or []
    minimum = int(chapter.get("decision_after_turns", 0) or 0)
    return bool(choices) and int(chapter_turns or 0) >= minimum



def _extract_facts(memory: str) -> list[str]:
    """Preserva somente fatos históricos ao atravessar fronteira de capítulo."""
    lines = str(memory or "").splitlines()
    facts: list[str] = []
    in_facts = False
    for raw in lines:
        line = raw.strip()
        if line == "FATOS E REVELAÇÕES":
            in_facts = True
            continue
        if in_facts and line and not line.startswith("-"):
            break
        if in_facts and line.startswith("-"):
            fact = line[1:].strip()
            if fact and fact not in facts:
                facts.append(fact)
    return facts


def rebase_memory_for_chapter(
    *,
    current_memory: str,
    chapter_id: str,
    decision_fact: str = "",
) -> str:
    """Troca o estado corrente da memória sem apagar os fatos históricos."""
    chapter = get_chapter(chapter_id)
    memory_state = chapter.get("memory_state", {}) or {}

    facts = _extract_facts(current_memory)
    if decision_fact and decision_fact not in facts:
        facts.append(decision_fact)

    relationship = list(memory_state.get("relationship", []) or [])
    wounds = list(memory_state.get("wounds", []) or [])
    pending = list(memory_state.get("pending", []) or [])

    def section(title: str, items: list[str]) -> str:
        clean = [str(item).strip() for item in items if str(item).strip()]
        if not clean:
            clean = ["Nenhum item ativo neste capítulo."]
        return title + "\n" + "\n".join(f"- {item}" for item in clean)

    return "\n\n".join([
        section("FATOS E REVELAÇÕES", facts),
        section("ESTADO ATUAL DA RELAÇÃO", relationship),
        section("FERIDAS / CONSEQUÊNCIAS ATIVAS", wounds),
        section("PENDÊNCIAS E VERDADES INCOMPLETAS", pending),
    ])
