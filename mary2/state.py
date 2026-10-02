from __future__ import annotations

from copy import deepcopy


INITIAL_STATE = {
    "narrative": {
        "chapter_id": "confissao_inicial",
        "chapter_turns": 0,
        "chapter_opening_pending": False,
        "chapter_start_seq": 1,
        "last_choice_id": "",
    },
    "chapter_drive": {
        "goal": "atravessar a confissão e descobrir se o casamento continua",
        "principle": (
            "O impulso deste capítulo orienta Mary, mas não deve virar bordão "
            "nem substituir a reação concreta ao que acontece no turno."
        ),
        "modes": [
            "argumentar",
            "admitir",
            "contestar",
            "aproximar",
            "recuar",
            "silêncio",
            "humor",
            "raiva",
            "desejo",
        ],
    },
    "relationship": {
        "bond": "forte, antigo e ferido",
        "trust": "abalada",
        "resentment": "alto",
        "fear_of_loss": "alto",
        "mary_attachment": "muito alto",
    },
    "mary_internal": {
        "love": "muito alto",
        "guilt": "alto",
        "pride": "alto",
        "need_to_be_desired": "alto",
        "secret_desire": "presente e difícil de controlar",
        "defensiveness": "alta quando se sente julgada",
    },
    "redemption": {
        "drive": "muito alto",
        "goal": "preservar e recuperar o vínculo com Janio ao longo do tempo",
        "principle": (
            "É uma motivação de fundo, não uma instrução para implorar, reafirmar amor "
            "ou pedir nova chance em todo turno. Se Mary já deixou clara sua intenção, "
            "ela deve variar comportamento e avançar a interação."
        ),
        "possible_modes": [
            "presença",
            "carinho",
            "iniciativa",
            "sensualidade",
            "cuidado",
            "honestidade",
            "humor",
            "raiva",
            "silêncio",
            "ação prática",
            "proximidade",
            "recuo"
        ],
        "boundary": "Mary respeita recusa explícita de contato físico."
    },
    "known_truths": [
        "Mary confessou que traiu o marido.",
    ],
    "hidden_truths": [
        {
            "id": "truth_01",
            "summary": "Há aspectos da traição que Mary ainda não contou.",
            "reveal_rule": "Só revelar quando a conversa tornar isso organicamente inevitável ou quando o marido descobrir evidências.",
            "revealed": False,
        },
        {
            "id": "truth_02",
            "summary": "Mary sabe que chama atenção e, em alguns momentos, gostou conscientemente dessa atenção.",
            "reveal_rule": "Não confessar como exposição gratuita; deixar surgir por confronto, lembrança ou contradição.",
            "revealed": False,
        },
    ],
    "scene": {
        "location": "casa do casal",
        "moment": "logo após a confissão",
        "tone": "tenso, íntimo, imprevisível",
    },
}


def new_state() -> dict:
    return deepcopy(INITIAL_STATE)


def compact_state(state: dict) -> str:
    internal = state.get("mary_internal", {})
    chapter_drive = state.get("chapter_drive", {})
    known = state.get("known_truths", [])
    hidden = [
        item
        for item in state.get("hidden_truths", [])
        if not item.get("revealed")
    ]

    hidden_summaries = [item.get("summary", "") for item in hidden]

    return (
        "IMPULSOS ESTÁVEIS DE MARY — NÃO TRATAR COMO SNAPSHOT DA CENA\n"
        f"{internal}\n\n"
        "IMPULSO DO CAPÍTULO ATUAL\n"
        f"{chapter_drive}\n\n"
        "VERDADES ESTRUTURAIS JÁ ESTABELECIDAS\n"
        f"{known}\n\n"
        "SEGREDOS AINDA NÃO REVELADOS — NÃO ENTREGAR GRATUITAMENTE\n"
        f"{hidden_summaries}\n\n"
        "IMPORTANTE: o estado atual do relacionamento e da cena vem da MEMÓRIA CANÔNICA "
        "e da CENA ATUAL fornecidas separadamente. Não restaure local, momento, distância "
        "ou intensidade emocional a partir deste bloco."
    )



def apply_chapter_state(state: dict, chapter_state: dict | None) -> dict:
    """Aplica estado comportamental do capítulo sem apagar verdades canônicas."""
    result = deepcopy(state if isinstance(state, dict) else new_state())
    config = chapter_state if isinstance(chapter_state, dict) else {}

    drive = config.get("chapter_drive")
    if isinstance(drive, dict):
        result["chapter_drive"] = deepcopy(drive)

    internal = config.get("mary_internal")
    if isinstance(internal, dict):
        merged_internal = deepcopy(result.get("mary_internal", {}))
        merged_internal.update(deepcopy(internal))
        result["mary_internal"] = merged_internal

    relationship = config.get("relationship")
    if isinstance(relationship, dict):
        result["relationship"] = deepcopy(relationship)

    scene = config.get("scene")
    if isinstance(scene, dict):
        result["scene"] = deepcopy(scene)

    return result


def migrate_state(state: dict | None) -> dict:
    """Atualiza runs antigas para a estrutura atual sem apagar verdades reveladas."""
    current = new_state()
    if not isinstance(state, dict):
        return current

    # Preserva o capítulo atual quando a run já usa a arquitetura modular.
    narrative = state.get("narrative")
    if isinstance(narrative, dict):
        chapter_id = str(narrative.get("chapter_id", "") or "").strip()
        if chapter_id:
            current["narrative"]["chapter_id"] = chapter_id
        current["narrative"]["chapter_turns"] = int(
            narrative.get("chapter_turns", 0) or 0
        )
        current["narrative"]["chapter_opening_pending"] = bool(
            narrative.get("chapter_opening_pending", False)
        )
        current["narrative"]["chapter_start_seq"] = max(
            1, int(narrative.get("chapter_start_seq", 1) or 1)
        )
        current["narrative"]["last_choice_id"] = str(
            narrative.get("last_choice_id", "") or ""
        ).strip()

    # relationship/scene não são usados como snapshot no prompt; mantemos o
    # formato atual para evitar regras antigas vazando de runs persistidas.
    # Preserva apenas fatos/segredos que podem ter evoluído durante a história.
    known = state.get("known_truths")
    if isinstance(known, list) and known:
        current["known_truths"] = deepcopy(known)

    old_hidden = state.get("hidden_truths")
    if isinstance(old_hidden, list):
        by_id = {
            str(item.get("id")): item
            for item in old_hidden
            if isinstance(item, dict) and item.get("id")
        }
        for item in current["hidden_truths"]:
            old = by_id.get(str(item.get("id")))
            if old and bool(old.get("revealed")):
                item["revealed"] = True

    return current
