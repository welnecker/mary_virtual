from catalog import clear_registry, register_story
from core import GateDecision, StoryEngine
from core.gate_classifier import classify_gate
from stories.casada_frustrada import package


def setup_function() -> None:
    clear_registry()
    register_story(package)


def test_opening_and_first_generated_line_are_distinct() -> None:
    chapter = package.get_chapter("chapter_01")
    engine = StoryEngine()
    session = engine.start_session(
        access_id="access_1",
        story_id=package.manifest.id,
        chapter=chapter,
    )

    assert engine.opening_message(chapter) == "Eita, caralho... desculpa!"
    plan = engine.plan_turn(session=session, chapter=chapter)
    assert plan.beat_id == "injury_check"
    assert plan.mary_lines == ("Tem certeza que tá tudo bem?",)


def test_confirmation_advances_only_to_plaza_question() -> None:
    chapter = package.get_chapter("chapter_01")
    engine = StoryEngine()
    session = engine.start_session(
        access_id="access_1",
        story_id=package.manifest.id,
        chapter=chapter,
    )

    first = engine.plan_turn(session=session, chapter=chapter)
    engine.record_mary_response(
        session=session,
        chapter=chapter,
        emitted_beat_id=first.beat_id,
    )
    decision = classify_gate("wellbeing_confirmation", "Sim, foi só um susto. Estou bem.")
    second = engine.plan_turn(
        session=session,
        chapter=chapter,
        gate_decision=decision,
    )

    assert decision is GateDecision.ACCEPTED
    assert session.current_beat == "recognize_plaza"
    assert second.mary_lines == (
        "Você por acaso mora no Plaza? Seu rosto não me é estranho...",
    )


def test_natural_short_confirmation_is_accepted() -> None:
    assert classify_gate(
        "wellbeing_confirmation",
        "Tenho sim... tá de boa.",
    ) is GateDecision.ACCEPTED


def test_negative_wording_that_confirms_no_injury_is_accepted() -> None:
    assert classify_gate(
        "wellbeing_confirmation",
        "Não, não machucou. É sério.",
    ) is GateDecision.ACCEPTED


def test_bare_negative_does_not_end_wellbeing_gate() -> None:
    assert classify_gate(
        "wellbeing_confirmation",
        "não",
    ) is GateDecision.UNCLEAR


def test_unclear_gate_holds_without_repeating_script() -> None:
    chapter = package.get_chapter("chapter_01")
    engine = StoryEngine()
    session = engine.start_session(
        access_id="access_1",
        story_id=package.manifest.id,
        chapter=chapter,
    )
    first = engine.plan_turn(session=session, chapter=chapter)
    engine.record_mary_response(
        session=session,
        chapter=chapter,
        emitted_beat_id=first.beat_id,
    )

    decision = classify_gate("wellbeing_confirmation", "Que mercado cheio hoje.")
    hold = engine.plan_turn(
        session=session,
        chapter=chapter,
        gate_decision=decision,
    )

    assert decision is GateDecision.UNCLEAR
    assert hold.mode == "hold"
    assert hold.mary_lines == ()
    assert session.current_beat == "injury_check"


def test_explicit_rejection_closes_execution() -> None:
    chapter = package.get_chapter("chapter_01")
    engine = StoryEngine()
    session = engine.start_session(
        access_id="access_1",
        story_id=package.manifest.id,
        chapter=chapter,
    )
    first = engine.plan_turn(session=session, chapter=chapter)
    engine.record_mary_response(
        session=session,
        chapter=chapter,
        emitted_beat_id=first.beat_id,
    )

    ending = engine.plan_turn(
        session=session,
        chapter=chapter,
        gate_decision=GateDecision.REJECTED,
    )

    assert ending.mode == "ending"
    assert ending.story_finished is True
    assert session.is_active is False
