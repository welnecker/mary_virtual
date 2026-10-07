from __future__ import annotations

import json
import re

from openrouter_client import chat
from persistence import _audit_cell, _ensure_worksheet, _now, open_or_create_book


SHEET = "USER_UNDERSTANDING_AUDIT"
HEADERS = [
    "created_at",
    "run_id",
    "chapter_id",
    "chapter_instance_id",
    "chapter_turn",
    "line_id",
    "line_order",
    "user_text",
    "previous_mary_text",
    "literal_meaning",
    "reference",
    "intent",
    "emotional_reaction",
    "subtext",
    "ambiguity",
    "confidence",
    "unclear_point",
    "expected_mary_reaction",
    "raw_interpreter_json",
    "parse_error",
]


def analyze_user_understanding(
    *,
    api_key: str,
    model: str,
    fallback_model: str | None,
    user_text: str,
    previous_mary_text: str,
    instant_memory: str = "",
) -> dict:
    """Auditoria independente: interpreta a fala do usuário sem receber a fala-guia."""
    payload = (
        "ULTIMA FALA DE MARY\n"
        + (str(previous_mary_text or "").strip() or "(nenhuma)")
        + "\n\nESTADO OBJETIVO ATUAL\n"
        + (str(instant_memory or "").strip() or "(nao informado)")
        + "\n\nFALA ATUAL DO USUARIO\n"
        + (str(user_text or "").strip() or "(sem fala verbal)")
        + "\n\nTAREFA\n"
        "Explique somente o que voce entendeu da fala atual do usuario no contexto imediato. "
        "Nao escreva a resposta de Mary. Nao use roteiro futuro e nao invente motivo oculto. "
        "Se houver ambiguidade real, declare-a em vez de escolher uma interpretacao. "
        "Informe: significado literal; a que a fala se refere; intencao conversacional; "
        "reacao emocional observavel, se houver; subtexto apenas quando sustentado; "
        "se ha ambiguidade; confianca de 0 a 1; o que ficou incerto; "
        "e qual tipo de reacao de Mary seria adequado. "
        "Retorne somente um objeto JSON com as chaves: "
        "literal_meaning, reference, intent, emotional_reaction, subtext, ambiguity, "
        "confidence, unclear_point, expected_mary_reaction."
    )

    raw = chat(
        api_key=api_key,
        model=model,
        fallback_model=fallback_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "Voce e um auditor de compreensao conversacional. "
                    "Seu trabalho e dizer o que a fala do usuario significa, sem escrever por Mary. "
                    "Quando nao souber, declare a incerteza."
                ),
            },
            {"role": "user", "content": payload},
        ],
        temperature=0.0,
        max_tokens=320,
    )

    parsed: dict = {}
    parse_error = ""
    try:
        text = str(raw or "").strip()
        text = re.sub(r"^\s*```(?:json)?\s*", "", text, flags=re.I)
        text = re.sub(r"\s*```\s*$", "", text)
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end >= start:
            text = text[start : end + 1]
        parsed = json.loads(text)
        if not isinstance(parsed, dict):
            raise ValueError("audit response is not a JSON object")
    except Exception as exc:
        parse_error = str(exc)
        parsed = {}

    return {
        "literal_meaning": str(parsed.get("literal_meaning", "") or "").strip(),
        "reference": str(parsed.get("reference", "") or "").strip(),
        "intent": str(parsed.get("intent", "") or "").strip(),
        "emotional_reaction": str(parsed.get("emotional_reaction", "") or "").strip(),
        "subtext": str(parsed.get("subtext", "") or "").strip(),
        "ambiguity": bool(parsed.get("ambiguity", False)),
        "confidence": parsed.get("confidence", ""),
        "unclear_point": str(parsed.get("unclear_point", "") or "").strip(),
        "expected_mary_reaction": str(parsed.get("expected_mary_reaction", "") or "").strip(),
        "raw_response": raw,
        "parse_error": parse_error,
    }


def save_user_understanding_audit(
    *,
    service_account_info: dict,
    spreadsheet_id: str,
    spreadsheet_title: str,
    owner_email: str,
    run_id: str,
    chapter_id: str,
    chapter_instance_id: str,
    chapter_turn: int,
    row: dict,
    user_text: str,
    previous_mary_text: str,
    audit: dict,
) -> None:
    book = open_or_create_book(
        service_account_info=service_account_info,
        spreadsheet_id=spreadsheet_id,
        spreadsheet_title=spreadsheet_title,
        owner_email=owner_email,
    )
    ws = _ensure_worksheet(book, SHEET, HEADERS)
    ws.append_row(
        [
            _now(),
            run_id,
            chapter_id,
            chapter_instance_id,
            int(chapter_turn or 0),
            str(row.get("line_id", "") or ""),
            int(row.get("order", 0) or 0),
            _audit_cell(user_text),
            _audit_cell(previous_mary_text),
            _audit_cell(audit.get("literal_meaning", "")),
            _audit_cell(audit.get("reference", "")),
            _audit_cell(audit.get("intent", "")),
            _audit_cell(audit.get("emotional_reaction", "")),
            _audit_cell(audit.get("subtext", "")),
            bool(audit.get("ambiguity", False)),
            audit.get("confidence", ""),
            _audit_cell(audit.get("unclear_point", "")),
            _audit_cell(audit.get("expected_mary_reaction", "")),
            _audit_cell(audit.get("raw_response", "")),
            str(audit.get("parse_error", "") or ""),
        ],
        value_input_option="RAW",
    )
