from catalog import clear_registry, get_story, list_stories
from commerce.story_access import StoryAccess, bind_access_to_session, consume_access
from core import GateDecision, StoryEngine
from stories import register_builtin_stories


def setup_function() -> None:
    clear_registry()
    register_builtin_stories()


def _start():
    package = get_story("casada_frustrada")
    chapter = package.get_chapter("chapter_01")
    engine = StoryEngine()
    session = engine.start_session(
        access_id="access-1",
        story_id=package.manifest.id,
        chapter=chapter,
    )
    return package, chapter, engine, session


def test_catalog_registers_independent_story_package() -> None:
    packages = list_stories()
    assert [item.manifest.id for item in packages] == ["casada_frustrada"]
    assert packages[0].manifest.price_cents == 990
    assert packages[0].profile.physical["age"] == 25


def test_opening_is_not_repeated_by_first_generated_beat() -> None:
    _, chapter, engine, session = _start()

    assert engine.opening_message(chapter) == "Eita, caralho... desculpa!"
    plan = engine.plan_turn(session=session, chapter=chapter)

    assert plan.beat_id == "injury_check"
    assert plan.mary_lines == ("Tem certeza que tá tudo bem?",)


def test_cursor_advances_only_after_emission_and_accepted_gate() -> None:
    _, chapter, engine, session = _start()

    first = engine.plan_turn(session=session, chapter=chapter)
    engine.record_mary_response(
        session=session,
        chapter=chapter,
        emitted_beat_id=first.beat_id,
    )

    hold = engine.plan_turn(
        session=session,
        chapter=chapter,
        gate_decision=GateDecision.UNCLEAR,
    )
    assert hold.mode == "hold"
    assert session.current_beat == "injury_check"
    assert hold.mary_lines == ()

    second = engine.plan_turn(
        session=session,
        chapter=chapter,
        gate_decision=GateDecision.ACCEPTED,
    )
    assert second.beat_id == "recognize_plaza"
    assert session.current_beat == "recognize_plaza"
    assert session.completed_beats == ["injury_check"]


def test_completed_beat_never_returns_after_reencontro() -> None:
    _, chapter, engine, session = _start()

    expected = [
        ("injury_check", GateDecision.ACCEPTED),
        ("recognize_plaza", GateDecision.ACCEPTED),
        ("first_farewell", None),
        ("second_encounter", None),
        ("market_crowded", None),
    ]

    visited = []
    for expected_beat, decision_for_next_turn in expected:
        plan = engine.plan_turn(session=session, chapter=chapter)
        assert plan.beat_id == expected_beat
        visited.append(plan.beat_id)
        engine.record_mary_response(
            session=session,
            chapter=chapter,
            emitted_beat_id=plan.beat_id,
        )
        if decision_for_next_turn is not None:
            next_plan = engine.plan_turn(
                session=session,
                chapter=chapter,
                gate_decision=decision_for_next_turn,
            )
            if expected_beat != expected[-1][0]:
                # O plano já abriu o sucessor; apenas registre-o na próxima iteração.
                assert next_plan.beat_id == chapter.beats[expected_beat].next_beat

    assert len(visited) == len(set(visited))
    assert "injury_check" not in visited[1:]


def test_rejected_gate_closes_story_without_advancing() -> None:
    _, chapter, engine, session = _start()
    plan = engine.plan_turn(session=session, chapter=chapter)
    engine.record_mary_response(
        session=session,
        chapter=chapter,
        emitted_beat_id=plan.beat_id,
    )

    ending = engine.plan_turn(
        session=session,
        chapter=chapter,
        gate_decision=GateDecision.REJECTED,
    )

    assert ending.story_finished is True
    assert session.status == "closed"
    assert session.current_beat == "injury_check"


def test_one_purchase_creates_only_one_story_session() -> None:
    access = StoryAccess(
        id="access-1",
        user_id="user-1",
        story_id="casada_frustrada",
        chapter_id="chapter_01",
        payment_id="payment-1",
    )

    bind_access_to_session(access, session_id="session-1")
    consume_access(access, reason="user_abandoned")

    assert access.status == "consumed"
    assert access.can_start is False

    try:
        bind_access_to_session(access, session_id="session-2")
    except ValueError:
        pass
    else:
        raise AssertionError("Acesso consumido não pode iniciar uma nova sessão.")
