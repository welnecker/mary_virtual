from __future__ import annotations

from copy import deepcopy
import json


INITIAL_STATE = {
    "narrative": {
        "chapter_id": "sheet:Confissão1",
        "chapter_turns": 0,
        "chapter_opening_pending": False,
        "chapter_start_seq": 1,
        "prompt_start_seq": 1,
        "last_choice_id": "",
        "pending_auto_chapter": "",
        "handoff": {},
        "branch_id": "main",
        "parent_branch_id": "",
        "parent_checkpoint_id": "",
        "chapter_instance_id": "sheet_Confissão1_001",
        "chapter_entry_checkpoint_id": "",
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
            "chapter_id": str(narrative.get("chapter_id", "sheet:Confissão1") or "sheet:Confissão1"),
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
            "branch_id": str(narrative.get("branch_id", "main") or "main"),
            "parent_branch_id": str(narrative.get("parent_branch_id", "") or ""),
            "parent_checkpoint_id": str(narrative.get("parent_checkpoint_id", "") or ""),
            "chapter_instance_id": str(
                narrative.get("chapter_instance_id", "")
                or f"{str(narrative.get('chapter_id', 'sheet:Confissão1') or 'sheet:Confissão1')}_legacy"
            ),
            "chapter_entry_checkpoint_id": str(
                narrative.get("chapter_entry_checkpoint_id", "") or ""
            ),
        })

        if isinstance(narrative.get("funnel_script"), dict):
            current["narrative"]["funnel_script"] = deepcopy(
                narrative.get("funnel_script")
            )
        if isinstance(narrative.get("direct_script"), dict):
            current["narrative"]["direct_script"] = deepcopy(
                narrative.get("direct_script")
            )
        if "choice_ready" in narrative:
            current["narrative"]["choice_ready"] = bool(
                narrative.get("choice_ready", False)
            )
        if "active_phase_id" in narrative:
            current["narrative"]["active_phase_id"] = str(
                narrative.get("active_phase_id", "") or ""
            )
        if "phase_start_message_index" in narrative:
            current["narrative"]["phase_start_message_index"] = max(
                0,
                int(narrative.get("phase_start_message_index", 0) or 0),
            )

    ledger = state.get("story_ledger")
    if isinstance(ledger, list):
        current["story_ledger"] = [str(item).strip() for item in ledger if str(item).strip()]

    status = state.get("current_status")
    if isinstance(status, dict) and status:
        current["current_status"] = deepcopy(status)

    return current
