from copy import deepcopy

from mary2.funnel_script import (
    apply_funnel_evaluation,
    derive_physical_markers,
    ensure_funnel_state,
    funnel_stage,
    _normalize_user_facts,
)
from mary2.state import migrate_state


ROWS = [
    {
        "order": 1,
        "scene_id": "entrada",
        "min_turns": 2,
        "ideal_turns": 3,
        "max_turns": 4,
        "exit_markers": "carro_em_movimento; mary_passageira_instalada",
        "mission": "Colocar a carona em movimento.",
    },
    {
        "order": 2,
        "scene_id": "conversa",
        "min_turns": 1,
        "ideal_turns": 2,
        "max_turns": 3,
        "exit_markers": "usuario_residencia; usuario_vida_domestica; usuario_preferencia_noturna",
    },
]


def evaluation(*, markers=None, stance=None, facts=None):
    return {
        "boundary_ok": True,
        "violations": [],
        "semantic_markers": list(markers or []),
        "physical_markers": [],
        "user_facts": list(facts or []),
        "consumed_topics": [],
        "user_stance": dict(stance or {}),
        "summary": "A conversa avançou.",
    }


def moving_scene():
    return {
        "location": "interior do carro do personal, em movimento",
        "proximity": "sentada no banco do passageiro",
        "event": "O carro segue pela estrada rumo a Camburi.",
    }


def test_funnel_drops_legacy_hybrid_state_and_starts_v3():
    narrative = {
        "hybrid_script": {
            "completed_orders": [1, 2],
            "breath_pending": True,
        }
    }

    state = ensure_funnel_state(narrative, ROWS)

    assert "hybrid_script" not in narrative
    assert state["engine"] == "carona_funnel_v3"
    assert state["scene_id"] == "entrada"
    assert state["markers"] == []


def test_physical_scene_state_proves_vehicle_movement():
    assert "carro_em_movimento" in derive_physical_markers(
        moving_scene()
    )


def test_runtime_advances_immediately_when_mission_is_complete():
    state = ensure_funnel_state({}, ROWS)

    result = apply_funnel_evaluation(
        rows=ROWS,
        state=state,
        row=ROWS[0],
        evaluation=evaluation(),
        scene=moving_scene(),
    )

    assert result["exit_ready"] is True
    assert result["advanced"] is True
    assert result["advanced_to"] == "conversa"
    assert state["scene_id"] == "conversa"
    assert state["scene_turn"] == 0
    assert state["markers"] == []


def test_question_or_invitation_is_not_accepted_as_user_fact_without_literal_evidence():
    raw = [
        {
            "category": "moradia",
            "fact": "O usuário mora sozinho.",
            "modality": "confirmado",
            "source_quote": "moro sozinho",
        }
    ]

    assert _normalize_user_facts(raw, "Vamos nessa?") == []


def test_user_fact_requires_literal_support_and_preserves_modality():
    raw = [
        {
            "category": "lazer_noturno",
            "fact": "Talvez o usuário vá ao clube.",
            "modality": "talvez/incerto",
            "source_quote": "talvez eu apareça",
        }
    ]

    normalized = _normalize_user_facts(
        raw,
        "Bom... talvez eu apareça mais tarde.",
    )

    assert normalized[0]["modality"] == "talvez/incerto"
    assert normalized[0]["source_quote"] == "talvez eu apareça"


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
                "engine": "carona_funnel_v3",
                "scene_index": 1,
                "scene_id": "conversa",
                "scene_turn": 2,
                "completed_scene_ids": ["entrada"],
                "markers": ["usuario_residencia"],
                "user_stance": {
                    "value": "talvez/incerto",
                    "source_quote": "talvez",
                },
                "memory": {
                    "user_facts": [],
                    "mary_facts": [],
                    "consumed_topics": ["moradia"],
                    "consolidated": [],
                },
                "completed": False,
            },
        },
        "story_ledger": [],
        "current_status": {},
    }

    migrated = migrate_state(deepcopy(original))

    assert (
        migrated["narrative"]["funnel_script"]
        == original["narrative"]["funnel_script"]
    )


def test_second_funnel_requires_all_three_deliveries():
    state = ensure_funnel_state({}, ROWS)
    state["scene_index"] = 1
    state["scene_id"] = "conversa"
    row = ROWS[1]

    partial = apply_funnel_evaluation(
        rows=ROWS,
        state=state,
        row=row,
        evaluation=evaluation(
            markers=["usuario_residencia", "usuario_vida_domestica"]
        ),
        scene=moving_scene(),
    )

    assert partial["advanced"] is False
    assert "usuario_preferencia_noturna" in partial["pending_markers"]

    complete = apply_funnel_evaluation(
        rows=ROWS,
        state=state,
        row=row,
        evaluation=evaluation(
            markers=["usuario_preferencia_noturna"]
        ),
        scene=moving_scene(),
    )

    assert complete["advanced"] is True
