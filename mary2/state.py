from __future__ import annotations

from copy import deepcopy
import json


INITIAL_STATE = {
    "narrative": {
        "chapter_id": "confissao_inicial",
        "chapter_turns": 0,
        "chapter_opening_pending": False,
        "chapter_start_seq": 1,
        "prompt_start_seq": 1,
        "last_choice_id": "",
        "pending_auto_chapter": "",
        "handoff": {},
    },
    "story_ledger": [],
    "current_status": {
        "relationship_status": "casada com Janio",
        "living_situation": "vive com Janio",
    },
}


def new_state() -> dict:
    return deepcopy(INITIAL_STATE)


def story_ledger_text(state: dict) -> str:
    ledger = state.get("story_ledger", [])
    if not isinstance(ledger, list) or not ledger:
        return "(nenhum fato estrutural acumulado antes deste capítulo)"
    return "\n".join(f"- {str(item).strip()}" for item in ledger if str(item).strip())


def current_status_text(state: dict) -> str:
    status = state.get("current_status", {})
    if not isinstance(status, dict) or not status:
        return "(sem status estrutural definido)"
    return json.dumps(status, ensure_ascii=False, indent=2)


def migrate_state(state: dict | None) -> dict:
    """Migração mínima para o formato modular limpo."""
    current = new_state()
    if not isinstance(state, dict):
        return current

    narrative = state.get("narrative")
    if isinstance(narrative, dict):
        current["narrative"].update({
            "chapter_id": str(narrative.get("chapter_id", "confissao_inicial") or "confissao_inicial"),
            "chapter_turns": int(narrative.get("chapter_turns", 0) or 0),
            "chapter_opening_pending": bool(narrative.get("chapter_opening_pending", False)),
            "chapter_start_seq": max(1, int(narrative.get("chapter_start_seq", 1) or 1)),
            "prompt_start_seq": max(
                1,
                int(
                    narrative.get(
                        "prompt_start_seq",
                        narrative.get("chapter_start_seq", 1),
                    )
                    or 1
                ),
            ),
            "last_choice_id": str(narrative.get("last_choice_id", "") or ""),
            "pending_auto_chapter": str(
                narrative.get("pending_auto_chapter", "") or ""
            ),
            "handoff": (
                deepcopy(narrative.get("handoff"))
                if isinstance(narrative.get("handoff"), dict)
                else {}
            ),
        })

    ledger = state.get("story_ledger")
    if isinstance(ledger, list):
        current["story_ledger"] = [str(item).strip() for item in ledger if str(item).strip()]

    status = state.get("current_status")
    if isinstance(status, dict) and status:
        current["current_status"] = deepcopy(status)

    return current
