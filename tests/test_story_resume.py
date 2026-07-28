from core.story_models import StorySession
from persistence.story_resume import catalog_story_state, hydrate_story_session


def test_active_session_shows_continue_state() -> None:
    row = {
        "status": "active",
        "active": True,
        "input_locked": False,
        "ending_sent": False,
    }
    assert catalog_story_state(row) == "active"


def test_finished_session_shows_restart_state() -> None:
    row = {
        "status": "completed",
        "active": False,
        "input_locked": True,
        "ending_sent": True,
    }
    assert catalog_story_state(row) == "finished"


def test_hydrate_story_session_restores_engine_cursor() -> None:
    row = {
        "scenario_session_id": "scn_123",
        "scenario_id": "casada_frustrada",
        "status": "active",
        "interaction_count": 12,
        "current_phase": "full_story",
        "current_beat": "home_first_message",
        "story_progress_json": (
            '{"access_id":"scn_123","chapter_id":"full_story",'
            '"completed_beats":["car_farewell"],'
            '"completed_facts":["phone_numbers_exchanged"],'
            '"engine":{"access_id":"scn_123",'
            '"story_id":"casada_frustrada",'
            '"chapter_id":"full_story",'
            '"current_beat":"home_first_message",'
            '"status":"active",'
            '"current_beat_emitted":false,'
            '"completed_beats":["car_farewell"],'
            '"completed_facts":["phone_numbers_exchanged"],'
            '"turn_count":12,"ending_reason":"",'
            '"alignment_warning_active":false,'
            '"alignment_warning_reason":""}}'
        ),
    }

    session = hydrate_story_session(row)

    assert isinstance(session, StorySession)
    assert session.access_id == "scn_123"
    assert session.chapter_id == "full_story"
    assert session.current_beat == "home_first_message"
    assert session.turn_count == 12
    assert session.completed_facts == ["phone_numbers_exchanged"]
