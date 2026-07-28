from __future__ import annotations

import re
import unicodedata
from copy import deepcopy
from typing import Any

from .beat_graph import obter_beat, proximo_beat_padrao
from .canonical_screenplay import linhas_canonicas_do_beat


SCREENPLAY_EXECUTOR_VERSION = "casada-frustrada-screenplay-executor-v2-canonical-lines"

MOTEL_SEQUENCE = [
    "motel_preparation",
    "motel_reunion",
    "ask_touch_butt",
    "ask_touch_breasts",
    "ask_remove_bra",
    "heels_and_panties",
    "offer_oral",
    "oral_admiration",
    "oral_climax_request",
    "oral_after_climax",
    "request_her_pleasure",
    "invite_cunnilingus",
    "guide_cunnilingus",
    "first_orgasm_build",
    "first_orgasm",
    "post_oral_tease",
    "praise_lover",
    "request_doggy",
    "ask_spank",
    "ask_lubricate",
    "penetration_start",
    "penetration_rhythm",
    "ask_anal_finger",
    "second_orgasm_build",
    "request_internal_climax",
    "shared_climax",
    "post_penetration",
    "clean_with_mouth",
    "final_departure",
]


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKD", _text(value).casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _history(messages: list[dict[str, Any]], role: str = "") -> str:
    parts: list[str] = []
    for item in messages[-120:]:
        if not isinstance(item, dict):
            continue
        item_role = _text(item.get("role"))
        if item_role not in {"user", "assistant"} or (role and item_role != role):
            continue
        content = _normalize(item.get("content"))
        if content:
            parts.append(content)
    return " ".join(parts)


def _contains(text: str, *markers: str) -> bool:
    return any(marker in text for marker in markers)


def observar_execucao_motel(
    messages: list[dict[str, Any]],
    previous: Any = None,
) -> dict[str, Any]:
    state = deepcopy(previous) if isinstance(previous, dict) else {}
    completed = set(state.get("completed_beats") or [])
    assistant = _history(messages, "assistant")
    user = _history(messages, "user")
    all_text = f"{assistant} {user}"

    evidence = {
        "motel_preparation": _contains(all_text, "motel status", "peguei uma suite", "estou na suite", "cheguei no motel"),
        "motel_reunion": _contains(user, "cheguei", "to entrando", "estou entrando", "aqui estou") and _contains(assistant, "me pega logo", "me beija", "entra logo"),
        "ask_touch_butt": _contains(assistant, "aperta minha bunda", "abre minhas nadegas", "me amassa") and _contains(user, "plaf", "tapa", "apertei", "amass", "bunda", "gostosa"),
        "ask_touch_breasts": _contains(assistant, "aperta meus seios", "aperta meu peito", "sente como sao firmes") and _contains(user, "seios", "peitos", "mamas", "chup", "slup", "perfeita"),
        "ask_remove_bra": _contains(assistant, "desprende o sutia", "liberta eles") and _contains(user, "tirei", "pronto", "sem sutia", "na minha boca", "chup"),
        "heels_and_panties": _contains(assistant, "so de calcinha e salto", "de salto e calcinha", "vou ficar de salto", "fiquei so de calcinha"),
        "offer_oral": _contains(assistant, "quero chupar seu pau", "na minha lingua", "pela garganta"),
        "oral_admiration": _contains(assistant, "rola grossa", "pau grosso", "grossa e dura"),
        "oral_climax_request": _contains(assistant, "goza na minha cara", "goza no meu rosto") and _contains(user, "vou gozar", "to gozando", "estou gozando", "gozei"),
        "oral_after_climax": _contains(user, "gozei", "to gozando", "estou gozando") and _contains(assistant, "engulo ou cuspo", "sobrou um pouco"),
        "request_her_pleasure": _contains(assistant, "eu quero gozar tambem", "vou deitar na cama"),
        "invite_cunnilingus": _contains(assistant, "chupa minha buceta", "vem sentir de perto", "pelinhos aparados"),
        "guide_cunnilingus": _contains(assistant, "enfia um dedo", "chupa meu clitoris") and _contains(user, "chup", "lingua", "dedo", "clitoris"),
        "first_orgasm_build": _contains(assistant, "vou gozar", "quase gozando") and not _contains(assistant, "gozei finalmente"),
        "first_orgasm": _contains(assistant, "gozei finalmente", "hummm gozei", "eu gozei"),
        "post_oral_tease": _contains(assistant, "olha sua cara", "me da sua lingua"),
        "praise_lover": _contains(assistant, "mais do que eu imaginei"),
        "request_doggy": _contains(assistant, "quero foder de quatro") and _contains(user, "duro", "erecao", "pau duro", "pronto de novo"),
        "ask_spank": _contains(assistant, "bate na minha bunda") and _contains(user, "plaf", "tapa", "bati", "batendo"),
        "ask_lubricate": _contains(assistant, "cospe no meu cu", "lubrifica mais") and _contains(user, "cuspi", "lubrif", "molhei"),
        "penetration_start": _contains(assistant, "mete na buceta") and _contains(user, "entrei", "to dentro", "estou dentro", "metendo"),
        "penetration_rhythm": _contains(assistant, "entra e sai", "ate o talo") and _contains(user, "entrando e saindo", "fundo", "talo", "metendo"),
        "ask_anal_finger": _contains(assistant, "dedo no meu cu", "poe um dedo") and _contains(user, "coloquei", "enfiei", "dedo"),
        "second_orgasm_build": _contains(assistant, "vou gozar de novo"),
        "request_internal_climax": _contains(assistant, "goza dentro") and _contains(user, "vou gozar", "to gozando", "estou gozando"),
        "shared_climax": _contains(user, "gozei", "to gozando", "estou gozando") and _contains(assistant, "eu to gozando", "estou gozando"),
        "post_penetration": _contains(assistant, "ta escorrendo", "estou sentindo escorrer"),
        "clean_with_mouth": _contains(assistant, "deixa eu chupar o resto"),
        "final_departure": _contains(assistant, "preciso ir", "eu saio primeiro", "esposa comportada precisa estar em casa"),
    }

    for beat_id, detected in evidence.items():
        if detected:
            completed.add(beat_id)

    furthest = -1
    for index, beat_id in enumerate(MOTEL_SEQUENCE):
        if beat_id in completed:
            furthest = max(furthest, index)
    if furthest >= 0:
        completed.update(MOTEL_SEQUENCE[: furthest + 1])

    state["version"] = SCREENPLAY_EXECUTOR_VERSION
    state["completed_beats"] = [beat for beat in MOTEL_SEQUENCE if beat in completed]
    state["evidence"] = {key: bool(value) for key, value in evidence.items()}
    return state


def proximo_beat_motel(execution: dict[str, Any]) -> str:
    completed = set(execution.get("completed_beats") or [])
    for beat_id in MOTEL_SEQUENCE:
        if beat_id not in completed:
            return beat_id
    return "final_departure"


def construir_trava_de_roteiro(beat_id: str) -> dict[str, Any]:
    beat = obter_beat(beat_id) or {}
    next_beat = proximo_beat_padrao(beat_id)
    next_data = obter_beat(next_beat) or {}
    canonical_lines = linhas_canonicas_do_beat(beat_id)
    return {
        "version": SCREENPLAY_EXECUTOR_VERSION,
        "current_beat": beat_id,
        "mandatory_objective": _text(beat.get("objective")),
        "canonical_lines": canonical_lines,
        "canonical_text_must_be_preserved": True,
        "current_route": _text(beat.get("route")),
        "next_beat_locked": next_beat,
        "next_objective_locked": _text(next_data.get("objective")),
        "rule": (
            "Responda naturalmente ao improviso do usuário e conduza para o beat atual. "
            "As canonical_lines pertencem ao roteiro imutável: devem ser interpretadas sem "
            "paráfrase, substituição ou alteração de sentido. O próximo beat permanece bloqueado."
        ),
    }


__all__ = [
    "SCREENPLAY_EXECUTOR_VERSION",
    "MOTEL_SEQUENCE",
    "observar_execucao_motel",
    "proximo_beat_motel",
    "construir_trava_de_roteiro",
]
