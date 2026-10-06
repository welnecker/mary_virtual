from copy import deepcopy

from mary2.funnel_script import (
    apply_funnel_evaluation,
    ensure_funnel_state,
    funnel_stage,
)
from mary2.state import migrate_state


ROWS = [
    {
        "order": 1,
        "scene_id": "entrada",
        "min_turns": 2,
        "ideal_turns": 3,
        "max_turns": 4,
    },
    {
        "order": 2,
        "scene_id": "conversa",
        "min_turns": 1,
        "ideal_turns": 2,
        "max_turns": 3,
    },
]


def evaluation(*, exit_met=False, stance=""):
    return {
        "boundary_ok": True,
        "violations": [],
        "exit_condition_met": exit_met,
        "user_facts": ["O usuário mora em Jardim da Penha."],
        "mary_facts": ["Mary entrou no carro."],
        "consumed_topics": ["moradia"],
        "consolidated_memory_candidates": [
            "O usuário mora em Jardim da Penha."
        ],
        "user_stance": stance,
        "summary": "A conversa avançou.",
    }


def test_funnel_drops_legacy_hybrid_state_and_starts_first_scene():
    narrative = {
        "hybrid_script": {
            "completed_orders": [1, 2],
            "breath_pending": True,
        }
    }

    state = ensure_funnel_state(narrative, ROWS)

    assert "hybrid_script" not in narrative
    assert narrative["funnel_script"] is state
    assert state["scene_id"] == "entrada"
    assert state["scene_turn"] == 0
    assert state["completed"] is False


def test_exit_condition_does_not_advance_before_minimum_turns():
    narrative = {}
    state = ensure_funnel_state(narrative, ROWS)
    row = ROWS[0]

    result = apply_funnel_evaluation(
        rows=ROWS,
        state=state,
        row=row,
        evaluation=evaluation(exit_met=True),
    )

    assert result["advanced"] is False
    assert state["scene_id"] == "entrada"
    assert state["scene_turn"] == 1


def test_funnel_advances_at_minimum_when_exit_is_really_met():
    narrative = {}
    state = ensure_funnel_state(narrative, ROWS)
    row = ROWS[0]

    apply_funnel_evaluation(
        rows=ROWS,
        state=state,
        row=row,
        evaluation=evaluation(exit_met=False),
    )
    result = apply_funnel_evaluation(
        rows=ROWS,
        state=state,
        row=row,
        evaluation=evaluation(
            exit_met=True,
            stance="talvez/incerto",
        ),
    )

    assert result["advanced"] is True
    assert result["advanced_to"] == "conversa"
    assert state["scene_id"] == "conversa"
    assert state["scene_turn"] == 0
    assert state["memory"]["user_facts"] == []
    assert state["memory"]["mary_facts"] == []
    assert state["memory"]["consumed_topics"] == []
    assert "O usuário mora em Jardim da Penha." in state["memory"]["consolidated"]
    assert any(
        "talvez/incerto" in item
        for item in state["memory"]["consolidated"]
    )


def test_stage_tightens_with_turn_budget():
    state = {"scene_turn": 0}
    assert funnel_stage(ROWS[0], state) == "abertura"

    state["scene_turn"] = 2
    assert funnel_stage(ROWS[0], state) == "convergencia"

    state["scene_turn"] = 3
    assert funnel_stage(ROWS[0], state) == "fechamento"


def test_migrate_state_preserves_funnel_runtime_state():
    original = {
        "narrative": {
            "chapter_id": "carona_camburi",
            "chapter_turns": 5,
            "funnel_script": {
                "engine": "carona_funnel_v1",
                "scene_index": 1,
                "scene_id": "conversa",
                "scene_turn": 2,
                "completed_scene_ids": ["entrada"],
                "memory": {
                    "user_facts": ["mora sozinho"],
                    "mary_facts": [],
                    "consumed_topics": ["moradia"],
                    "consolidated": ["mora em Jardim da Penha"],
                },
                "completed": False,
            },
        },
        "story_ledger": [],
        "current_status": {},
    }

    migrated = migrate_state(deepcopy(original))

    assert migrated["narrative"]["funnel_script"] == original["narrative"]["funnel_script"]
