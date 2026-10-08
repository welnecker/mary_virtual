from __future__ import annotations

import json
import re

from openrouter_client import chat


EMPTY_CONVERSATION_STATE = {
    "speaker": "",
    "move": "",
    "target": "",
    "topic": "",
    "meaning": "",
    "tone": "",
    "open_thread": "",
    "facts_created": [],
    "decisions_created": [],
}


def _clean(value) -> str:
    return str(value or "").strip()


def _parse_json_object(value: str) -> tuple[dict, str]:
    try:
        text = _clean(value)
        text = re.sub(r"^\s*```(?:json)?\s*", "", text, flags=re.I)
        text = re.sub(r"\s*```\s*$", "", text)
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end >= start:
            text = text[start : end + 1]
        parsed = json.loads(text)
        if not isinstance(parsed, dict):
            raise ValueError("conversation state response is not a JSON object")
        return parsed, ""
    except Exception as exc:
        return {}, str(exc)


def normalize_conversation_state(value: dict | None) -> dict:
    source = value if isinstance(value, dict) else {}
    facts = source.get("facts_created", [])
    decisions = source.get("decisions_created", [])
    if not isinstance(facts, list):
        facts = []
    if not isinstance(decisions, list):
        decisions = []
    return {
        "speaker": _clean(source.get("speaker")),
        "move": _clean(source.get("move")),
        "target": _clean(source.get("target")),
        "topic": _clean(source.get("topic")),
        "meaning": _clean(source.get("meaning")),
        "tone": _clean(source.get("tone")),
        "open_thread": _clean(source.get("open_thread")),
        "facts_created": [_clean(x) for x in facts if _clean(x)][:8],
        "decisions_created": [_clean(x) for x in decisions if _clean(x)][:8],
    }


def format_conversation_state(value: dict | None) -> str:
    state = normalize_conversation_state(value)
    if not any(state.values()):
        return "(nenhum movimento anterior interpretado)"
    lines = [
        "Quem falou: " + (state["speaker"] or "(não determinado)"),
        "Movimento: " + (state["move"] or "(não determinado)"),
        "Alvo: " + (state["target"] or "(não determinado)"),
        "Assunto: " + (state["topic"] or "(não determinado)"),
        "Significado: " + (state["meaning"] or "(não determinado)"),
        "Tom: " + (state["tone"] or "(não determinado)"),
        "Fio aberto: " + (state["open_thread"] or "(nenhum)"),
        "Fatos criados: " + ("; ".join(state["facts_created"]) or "(nenhum)"),
        "Decisões criadas: " + ("; ".join(state["decisions_created"]) or "(nenhuma)"),
    ]
    return "\n".join(lines)


def analyze_mary_move(
    *,
    api_key: str,
    model: str,
    fallback_model: str | None,
    mary_text: str,
    user_text: str,
    user_understanding: dict | None = None,
    previous_conversation_state: dict | None = None,
    active_interlocutor: str = "",
) -> dict:
    """Interpreta o movimento conversacional que a própria Mary acabou de criar."""
    understanding = user_understanding if isinstance(user_understanding, dict) else {}
    previous_state = normalize_conversation_state(previous_conversation_state)

    payload = (
        "ESTADO CONVERSACIONAL ANTERIOR\n"
        + format_conversation_state(previous_state)
        + "\n\nINTERLOCUTOR ATIVO\n"
        + (_clean(active_interlocutor) or "(não especificado)")
        + "\n\nFALA DO USUÁRIO QUE ORIGINOU A RESPOSTA\n"
        + (_clean(user_text) or "(sem fala verbal)")
        + "\n\nCOMPREENSÃO JÁ FEITA DA FALA DO USUÁRIO\n"
        + json.dumps(understanding, ensure_ascii=False)
        + "\n\nRESPOSTA FINAL DE MARY\n"
        + (_clean(mary_text) or "(vazia)")
        + "\n\nTAREFA\n"
        "Interprete SOMENTE o movimento conversacional produzido por Mary nesta resposta. "
        "Não avalie estilo, não reescreva a fala, não julgue o roteiro e não invente acontecimentos. "
        "Descreva o ato conversacional de Mary e o que ele deixa semanticamente aberto para o próximo turno. "
        "Separe significado conversacional de fatos persistentes. Brincadeira, pergunta retórica, provocação, elogio, "
        "ironia, hesitação e comentário não viram automaticamente fatos ou decisões. "
        "facts_created deve conter apenas fatos novos explicitamente afirmados por Mary que possam continuar verdadeiros. "
        "decisions_created deve conter apenas decisões/aceites/recusas explícitos de Mary que alterem o estado. "
        "Retorne somente JSON curto no formato "
        '{"speaker":"MARY","move":"","target":"","topic":"","meaning":"","tone":"","open_thread":"","facts_created":[],"decisions_created":[]}.'
    )

    raw = chat(
        api_key=api_key,
        model=model,
        fallback_model=fallback_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "Você interpreta movimentos conversacionais. "
                    "Transforme a fala final de Mary em estado semântico curto e reutilizável no próximo turno. "
                    "Não resuma a história inteira e não invente fatos."
                ),
            },
            {"role": "user", "content": payload},
        ],
        temperature=0.0,
        max_tokens=360,
    )
    parsed, error = _parse_json_object(raw)
    if error:
        repair = chat(
            api_key=api_key,
            model=model,
            fallback_model=fallback_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Retorne SOMENTE JSON válido no formato "
                        '{"speaker":"MARY","move":"","target":"","topic":"","meaning":"","tone":"","open_thread":"","facts_created":[],"decisions_created":[]}.'
                    ),
                },
                {"role": "user", "content": payload},
            ],
            temperature=0.0,
            max_tokens=360,
        )
        parsed, error = _parse_json_object(repair)

    if error:
        return {
            **EMPTY_CONVERSATION_STATE,
            "speaker": "MARY",
            "meaning": _clean(mary_text),
            "open_thread": "Interpretar a próxima fala do usuário sem inventar continuidade.",
            "_parse_error": error,
        }

    state = normalize_conversation_state(parsed)
    state["speaker"] = "MARY"
    return state
