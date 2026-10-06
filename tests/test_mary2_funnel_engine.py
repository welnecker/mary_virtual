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
        "scene_id": "roteiro_step_01",
        "mission": "Descobrir onde o usuário mora.",
        "completion_criterion": "O usuário informou onde mora.",
        "completion_type": "USER",
        "min_turns": 1,
        "ideal_turns": 2,
        "max_turns": 3,
    },
    {
        "order": 2,
        "scene_id": "roteiro_step_02",
        "mission": "Mary reconhece que gostou da conversa.",
        "completion_criterion": "Mary reconheceu claramente que gostou da conversa.",
        "completion_type": "MARY",
        "min_turns": 1,
        "ideal_turns": 2,
        "max_turns": 3,
    },
]


def evaluation(*, complete=False, evidence=None, missing=None, facts=None):
    return {
        "boundary_ok": True,
        "violations": [],
        "step_complete": complete,
        "completion_evidence": list(evidence or []),
        "missing": list(missing or []),
        "mission_progress_ok": True,
        "semantic_markers": [],
        "physical_markers": [],
        "user_facts": list(facts or []),
        "consumed_topics": [],
        "user_stance": {},
        "summary": "O passo avançou.",
    }


def moving_scene():
    return {
        "event": "Texto humano livre.",
        "physical_state": {
            "location_type": "inside_vehicle",
            "vehicle_motion": "moving",
            "mary_position": "passenger_seat",
            "arrival_state": "en_route",
        },
    }


def test_generic_engine_replaces_legacy_runtime():
    narrative = {
        "hybrid_script": {"completed_orders": [1, 2]},
        "funnel_script": {"engine": "carona_funnel_v5"},
    }

    state = ensure_funnel_state(narrative, ROWS)

    assert "hybrid_script" not in narrative
    assert state["engine"] == "generic_script_v6"
    assert state["scene_id"] == "roteiro_step_01"
    assert state["step_complete"] is False
    assert state["step_evidence"] == []


def test_incomplete_step_stays_on_same_author_line():
    state = ensure_funnel_state({}, ROWS)

    result = apply_funnel_evaluation(
        rows=ROWS,
        state=state,
        row=ROWS[0],
        evaluation=evaluation(
            complete=False,
            evidence=[
                {
                    "source": "mary",
                    "detail": "Mary perguntou onde o usuário mora.",
                    "quote": "Onde você mora?",
                }
            ],
            missing=["resposta do usuário sobre residência"],
        ),
        scene=moving_scene(),
    )

    assert result["advanced"] is False
    assert state["scene_id"] == "roteiro_step_01"
    assert state["scene_turn"] == 1
    assert state["step_evidence"]
    assert state["step_missing"] == ["resposta do usuário sobre residência"]


def test_complete_step_advances_without_story_specific_markers():
    state = ensure_funnel_state({}, ROWS)

    result = apply_funnel_evaluation(
        rows=ROWS,
        state=state,
        row=ROWS[0],
        evaluation=evaluation(
            complete=True,
            evidence=[
                {
                    "source": "user",
                    "detail": "O usuário informou sua residência.",
                    "quote": "Moro em Jardim da Penha.",
                }
            ],
        ),
        scene=moving_scene(),
    )

    assert result["advanced"] is True
    assert result["advanced_to"] == "roteiro_step_02"
    assert state["scene_id"] == "roteiro_step_02"
    assert state["scene_turn"] == 0
    assert state["step_evidence"] == []
    assert state["step_missing"] == []


def test_boundary_failure_never_advances_even_if_step_complete():
    state = ensure_funnel_state({}, ROWS)
    bad = evaluation(complete=True)
    bad["boundary_ok"] = False
    bad["violations"] = ["Mary abriu assunto de linha futura."]

    result = apply_funnel_evaluation(
        rows=ROWS,
        state=state,
        row=ROWS[0],
        evaluation=bad,
        scene=moving_scene(),
    )

    assert result["advanced"] is False
    assert state["scene_id"] == "roteiro_step_01"


def test_physical_state_is_exposed_generically_not_as_story_marker():
    facts = derive_physical_markers(moving_scene())

    assert "physical:vehicle_motion=moving" in facts
    assert "physical:mary_position=passenger_seat" in facts
    assert "carro_em_movimento" not in facts


def test_event_text_does_not_create_physical_truth():
    scene = {
        "event": "O carro acelera, entra no fluxo e segue pela avenida.",
        "physical_state": {
            "location_type": "unknown",
            "vehicle_motion": "unknown",
            "mary_position": "unknown",
            "arrival_state": "unknown",
        },
    }

    assert derive_physical_markers(scene) == []


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


def test_question_is_not_accepted_as_user_fact():
    raw = [
        {
            "category": "moradia",
            "fact": "O usuário mora sozinho.",
            "modality": "confirmado",
            "source_quote": "onde você mora?",
        }
    ]

    assert _normalize_user_facts(raw, "Onde você mora?") == []


def test_stage_tightens_without_forcing_completion():
    state = {"scene_turn": 0}
    assert funnel_stage(ROWS[0], state) == "abertura"

    state["scene_turn"] = 1
    assert funnel_stage(ROWS[0], state) == "convergencia"

    state["scene_turn"] = 2
    assert funnel_stage(ROWS[0], state) == "fechamento"


def test_migrate_state_preserves_generic_runtime_state():
    original = {
        "narrative": {
            "chapter_id": "carona_camburi",
            "chapter_turns": 5,
            "funnel_script": {
                "engine": "generic_script_v6",
                "scene_index": 0,
                "scene_id": "roteiro_step_01",
                "scene_turn": 2,
                "completed_scene_ids": [],
                "markers": [],
                "step_complete": False,
                "step_evidence": [
                    {
                        "source": "mary",
                        "detail": "Mary perguntou sobre residência.",
                        "quote": "Onde você mora?",
                    }
                ],
                "step_missing": ["resposta do usuário"],
                "user_stance": {},
                "memory": {
                    "user_facts": [],
                    "mary_facts": [],
                    "consumed_topics": [],
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
