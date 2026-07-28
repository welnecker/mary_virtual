from core.story_engine import StoryEngine
from core.story_runtime import StoryRuntime
from stories.casada_frustrada import package


def _runtime_with(*responses: str) -> StoryRuntime:
    queue = list(responses)

    def caller(_prompt, _messages):
        return queue.pop(0)

    return StoryRuntime(caller)


def test_first_absurd_turn_realigns_without_advancing_cursor():
    chapter = package.get_chapter("full_story")
    session = StoryEngine().start_session(
        access_id="test_access",
        story_id=package.manifest.id,
        chapter=chapter,
    )
    original_beat = session.current_beat

    result = _runtime_with(
        "[[TURN_REALIGN]] Você está brincando comigo, né? Vamos voltar ao que estava acontecendo."
    ).respond(
        package=package,
        session=session,
        user_text="Um helicóptero pousou no mercado e seu marido saiu dele.",
    )

    assert result.session.current_beat == original_beat
    assert result.session.current_beat_emitted is False
    assert result.session.alignment_warning_active is True
    assert result.session.status == "active"
    assert "TURN_REALIGN" not in result.response


def test_second_consecutive_absurd_turn_closes_story():
    chapter = package.get_chapter("full_story")
    session = StoryEngine().start_session(
        access_id="test_access",
        story_id=package.manifest.id,
        chapter=chapter,
    )
    session.alignment_warning_active = True
    session.alignment_warning_reason = "off_script_or_world_control"

    result = _runtime_with(
        "[[TURN_REALIGN]] Isso também não está acontecendo."
    ).respond(
        package=package,
        session=session,
        user_text="Agora Mary virou uma alienígena e começou a voar.",
    )

    assert result.session.status == "closed"
    assert result.session.ending_reason == "repeated_narrative_deviation"
    assert result.session.alignment_warning_active is False


def test_valid_turn_after_warning_clears_warning_and_continues():
    chapter = package.get_chapter("full_story")
    session = StoryEngine().start_session(
        access_id="test_access",
        story_id=package.manifest.id,
        chapter=chapter,
    )
    session.alignment_warning_active = True
    session.alignment_warning_reason = "off_script_or_world_control"

    result = _runtime_with(
        "[[TURN_OK]] Tudo bem, ainda bem que você não se machucou de verdade."
    ).respond(
        package=package,
        session=session,
        user_text="Foi só um susto, estou bem.",
    )

    assert result.session.status == "active"
    assert result.session.alignment_warning_active is False
    assert result.session.current_beat_emitted is True
    assert "TURN_OK" not in result.response
