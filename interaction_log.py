from __future__ import annotations

import json
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any


PROMPT_VERSION = "mary-prompt-v1"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def criar_session_id() -> str:
    return str(uuid.uuid4())


def criar_registro_interacao(
    *,
    session_id: str,
    model: str,
    user_text: str,
    mary_response: str,
    user_profile: dict[str, Any] | None,
    image_metadata: dict[str, Any] | None = None,
    turn_direction: dict[str, Any] | None = None,
    mary_asked_name: bool = False,
    response_time_ms: int | None = None,
    error: str = "",
) -> dict[str, Any]:
    profile = user_profile or {}
    visual_profile = profile.get("visual_profile", {}) or {}

    nome = str(
        profile.get("preferred_name")
        or profile.get("name")
        or ""
    ).strip()

    image_metadata = image_metadata or {}
    turn_direction = turn_direction or {}

    return {
        "timestamp": utc_now_iso(),
        "session_id": session_id,
        "prompt_version": PROMPT_VERSION,
        "model": model,
        "user_text": str(user_text or "").strip(),
        "mary_response": str(mary_response or "").strip(),
        "user_name": nome,
        "onboarding_stage": str(
            profile.get("onboarding_stage", "")
        ),
        "visual_reference_confirmed": bool(
            visual_profile.get("reference_confirmed")
        ),
        "visual_reference_version": int(
            visual_profile.get("reference_version", 0) or 0
        ),
        "image_sent": bool(image_metadata),
        "image_width": image_metadata.get("width"),
        "image_height": image_metadata.get("height"),
        "image_size_bytes": image_metadata.get("size_bytes"),
        "image_mime_type": image_metadata.get("mime_type"),
        "mary_asked_name": bool(mary_asked_name),
        "experience_mode": str(
            turn_direction.get(
                "experience_mode",
                "",
            )
        ),
        "primary_intention": str(
            turn_direction.get(
                "primary_intention",
                "",
            )
        ),
        "response_scope": str(
            turn_direction.get(
                "response_scope",
                "",
            )
        ),
        "avoid_question": bool(
            turn_direction.get(
                "avoid_question",
                False,
            )
        ),
        "should_lead": bool(
            turn_direction.get(
                "should_lead",
                False,
            )
        ),
        "should_reveal_something": bool(
            turn_direction.get(
                "should_reveal_something",
                False,
            )
        ),
        "romantic_expression_allowed": bool(
            turn_direction.get(
                "romantic_expression_allowed",
                False,
            )
        ),
        "sexual_expression_allowed": bool(
            turn_direction.get(
                "sexual_expression_allowed",
                False,
            )
        ),
        "explicit_sexual_language_allowed": bool(
            turn_direction.get(
                "explicit_sexual_language_allowed",
                False,
            )
        ),
        "direction_reason": str(
            turn_direction.get(
                "reason",
                "",
            )
        ),
        "response_time_ms": response_time_ms,
        "error": str(error or "").strip(),
    }


def adicionar_registro_sessao(
    registros: list[dict[str, Any]],
    registro: dict[str, Any],
) -> list[dict[str, Any]]:
    atualizados = list(registros)
    atualizados.append(deepcopy(registro))
    return atualizados


def exportar_logs_json(
    registros: list[dict[str, Any]],
) -> str:
    return json.dumps(
        registros,
        ensure_ascii=False,
        indent=2,
    )


def exportar_logs_jsonl(
    registros: list[dict[str, Any]],
) -> str:
    return "\n".join(
        json.dumps(
            registro,
            ensure_ascii=False,
        )
        for registro in registros
    )
