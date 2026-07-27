from __future__ import annotations

import re
import unicodedata
from typing import Any


REFUSAL_LOCK_VERSION = "casada-frustrada-refusal-lock-v1"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKD", _text(value).casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


# Somente funções que dependem de adesão concreta do usuário podem encerrar a
# experiência. Reações narrativas ou perguntas casuais não entram nesta lista.
GUARDED_BEATS = {
    "injury_check": "first_contact",
    "recognize_plaza": "first_contact",
    "second_encounter": "conversation",
    "ask_wait_help_car": "groceries_help",
    "request_phone": "phone",
    "exchange_numbers": "phone",
    "offer_video": "answer_call",
    "camera_setup": "answer_call",
    "urge_user_climax": "call_completion",
    "react_user_climax": "call_completion",
    "midnight_return": "answer_call",
    "propose_motel": "meeting",
    "name_motel": "meeting",
    "ask_remove_shirt": "intimate_action",
    "ask_remove_pants": "intimate_action",
    "invite_bra_request": "intimate_action",
    "ask_remove_underwear": "intimate_action",
    "propose_mutual_masturbation": "intimate_action",
    "ask_touch_butt": "intimate_action",
    "ask_touch_breasts": "intimate_action",
    "ask_remove_bra": "intimate_action",
    "offer_oral": "intimate_action",
    "oral_climax_request": "intimate_action",
    "request_her_pleasure": "intimate_action",
    "invite_cunnilingus": "intimate_action",
    "request_doggy": "intimate_action",
    "ask_spank": "intimate_action",
    "ask_lubricate": "intimate_action",
    "penetration_start": "intimate_action",
}

# Negativas inequívocas. Marcadores como "não para" ficam explicitamente fora.
REFUSAL_MARKERS = (
    "nao quero",
    "nao vou",
    "nao posso",
    "prefiro nao",
    "melhor nao",
    "de jeito nenhum",
    "nem pensar",
    "recuso",
    "nao te dou",
    "nao passo meu numero",
    "nao vou ajudar",
    "nao vou levar",
    "nao vou atender",
    "nao aceito",
    "nao topo",
    "nao gosto disso",
    "para com isso",
    "me deixa em paz",
    "nao insista",
)

POSTPONE_MARKERS = (
    "depois eu vejo",
    "depois a gente ve",
    "quem sabe outro dia",
    "outro dia",
    "mais tarde talvez",
    "vou pensar",
    "preciso pensar",
    "deixa eu pensar",
    "nao sei ainda",
    "agora nao",
    "hoje nao",
    "vamos deixar pra depois",
    "vamos deixar para depois",
    "nao estou pronto",
    "nao to pronto",
    "talvez depois",
)

# Evita falsos positivos em comandos de continuidade sexual ou dramática.
NEGATION_EXCEPTIONS = (
    "nao para",
    "nao pare",
    "nao desliga",
    "nao vai embora",
    "nao demora",
    "nao precisa parar",
)

REACTIONS = {
    "first_contact": {
        "refusal": "Poxa... eu só tentei me desculpar. Não precisava ser tão grosso. Deixa pra lá.",
        "postpone": "Tudo bem... eu só tentei conversar um instante. Pelo jeito não é uma boa hora. Deixa pra lá.",
    },
    "conversation": {
        "refusal": "Nossa... eu só estava tentando ser simpática. Não precisa falar comigo desse jeito. Pode deixar.",
        "postpone": "Tá bom... eu só queria conversar um pouco. Não vou insistir. Fica bem.",
    },
    "groceries_help": {
        "refusal": "Entendi. Não se fazem cavalheiros como antigamente mesmo. Eu me viro sozinha.",
        "postpone": "Deixa... se é para pensar tanto, eu dou meu jeito com as compras. Não precisa mais.",
    },
    "phone": {
        "refusal": "Poxa... eu só queria seu número. Não precisava transformar isso numa coisa tão complicada. Esquece.",
        "postpone": "Tudo bem... se você precisa pensar tanto para me passar o número, melhor deixar pra lá.",
    },
    "answer_call": {
        "refusal": "Me atende... por favor. Droga, você não quer falar comigo. Tá bom. Desisto.",
        "postpone": "Eu fiquei esperando você atender, mas não vou ficar implorando. Deixa pra lá. Desisto.",
    },
    "call_completion": {
        "refusal": "Tá bom... eu me expus desse jeito e você resolveu parar agora. Que vergonha. Esquece que isso aconteceu.",
        "postpone": "Não. Depois de me deixar assim, você ainda quer adiar? Chega. Eu não vou continuar me humilhando.",
    },
    "meeting": {
        "refusal": "Entendi... eu criei coragem para propor isso e você não quer. Esquece. Não vou tocar nesse assunto de novo.",
        "postpone": "Eu não posso ficar esperando você decidir se me quer ou não. Melhor esquecer esse encontro.",
    },
    "intimate_action": {
        "refusal": "Tudo bem. Eu não vou insistir nem me expor mais. Para mim acabou aqui.",
        "postpone": "Não dá para parar e pensar em cada passo agora. Eu perdi a coragem. Melhor encerrar.",
    },
}


def _latest_user(messages: list[dict[str, Any]]) -> str:
    for item in reversed(messages):
        if isinstance(item, dict) and _text(item.get("role")) == "user":
            return _normalize(item.get("content"))
    return ""


def detectar_trava_psicologica(
    *,
    messages: list[dict[str, Any]],
    open_beat: str,
) -> dict[str, Any] | None:
    category = GUARDED_BEATS.get(_text(open_beat))
    if not category:
        return None

    user_text = _latest_user(messages)
    if not user_text or any(marker in user_text for marker in NEGATION_EXCEPTIONS):
        return None

    trigger = ""
    if any(marker in user_text for marker in REFUSAL_MARKERS):
        trigger = "refusal"
    elif any(marker in user_text for marker in POSTPONE_MARKERS):
        trigger = "postpone"
    if not trigger:
        return None

    reaction = REACTIONS[category][trigger]
    return {
        "version": REFUSAL_LOCK_VERSION,
        "trigger": trigger,
        "category": category,
        "open_beat": _text(open_beat),
        "final_direction": reaction,
        "ending_type": "psychological_refusal_lock",
        "ending_reason": f"user_{trigger}_{category}",
        "input_locked_after_response": True,
        "requires_new_paid_cycle": True,
        "authority": (
            "O usuário recusou ou postergou uma iniciativa decisiva de Mary. Responda com "
            "a reação final indicada, sem negociar, oferecer alternativa ou reabrir a cena."
        ),
    }


__all__ = [
    "REFUSAL_LOCK_VERSION",
    "GUARDED_BEATS",
    "detectar_trava_psicologica",
]
