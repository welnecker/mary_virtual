from scenarios.stories.casada_frustrada.beat_graph import BEAT_ORDER
from stories.casada_frustrada import package


def test_new_package_contains_every_canonical_beat() -> None:
    chapter = package.get_chapter("full_story")
    assert list(chapter.beats) == BEAT_ORDER
    assert len(chapter.beats) > 60


def test_supermarket_flows_into_private_messages() -> None:
    chapter = package.get_chapter("full_story")
    assert chapter.beats["car_farewell"].next_beat == "home_first_message"
    assert chapter.beats["home_first_message"].route == "messages"


def test_only_final_departure_completes_story() -> None:
    chapter = package.get_chapter("full_story")
    assert chapter.beats["car_farewell"].next_beat is not None
    assert chapter.beats["final_departure"].next_beat is None
    assert "story_completed" in chapter.beats["final_departure"].completes
