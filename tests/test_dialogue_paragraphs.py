"""Regression tests for display-only separation of multi-character speech."""

from pathlib import Path
import importlib.util


_module_path = Path(__file__).resolve().parents[1] / "mary2" / "output_filter.py"
_spec = importlib.util.spec_from_file_location("mary_dialogue_output_filter", _module_path)
_filter = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_filter)
format_dialogue_paragraphs = _filter.format_dialogue_paragraphs


def test_two_speakers_in_same_generated_speech():
    speech = (
        "Silvia: Viu só, Janio? O Donisete achou que ia ganhar um beijo. "
        "Ela não facilita pra ninguém! Mary: Pois é, Silvia. "
        "Mas ó, Donisete, eu quero desafio."
    )
    formatted = format_dialogue_paragraphs(speech)
    assert "**Silvia:**" in formatted
    assert "\n\n**Mary:**" in formatted
    assert formatted.index("Ela não facilita pra ninguém!") < formatted.index("**Mary:**")
    assert formatted.index("**Mary:**") < formatted.index("Pois é, Silvia.")


def test_speaker_after_original_newline_without_period():
    speech = "Silvia: Eu prefiro ficar aqui\nMary: Eu também."
    formatted = format_dialogue_paragraphs(speech)
    assert "\n\n**Mary:**" in formatted


def test_one_speaker_and_existing_paragraphs():
    speech = "Olha só, que engraçado.\n\nNão tinha pensado nisso."
    assert format_dialogue_paragraphs(speech) == speech


def test_no_false_split_on_lowercase_explanation():
    speech = "Mary gosta de uma coisa: conversar sem pressa."
    assert format_dialogue_paragraphs(speech) == speech


def test_different_character_names_without_hardcoded_cast():
    formatted = format_dialogue_paragraphs(
        "Camila: Eu concordo! Ricardo: Eu prefiro outro caminho."
    )
    assert "\n\n**Ricardo:**" in formatted
