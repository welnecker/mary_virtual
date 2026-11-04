"""Regression: visual emphasis in speaker labels must not block script progress."""

import importlib.util
import sys
import types
from pathlib import Path


# The evidence utilities are pure; do not require a network call to import them.
module_path = Path(__file__).resolve().parents[1] / "mary2" / "direct_semantic_director.py"
spec = importlib.util.spec_from_file_location("mary_director_evidence", module_path)
module = importlib.util.module_from_spec(spec)
stub = types.ModuleType("openrouter_client")
stub.chat = lambda **_: None
previous_client = sys.modules.get("openrouter_client")
try:
    sys.modules["openrouter_client"] = stub
    spec.loader.exec_module(module)
finally:
    if previous_client is None:
        sys.modules.pop("openrouter_client", None)
    else:
        sys.modules["openrouter_client"] = previous_client


def test_bold_speaker_label_matches_unformatted_evidence():
    entries = [("MARY", "**Silvia:** Viu só, Janio? O seu primo é um show à parte!")]
    assert module._evidence_source(
        "Silvia: Viu só, Janio? O seu primo é um show à parte!", entries
    ) == "MARY"


def test_variant_bold_format_and_whitespace():
    entries = [("MARY", "**Mary**: Pois é, Silvia,\n  ele achou que eu ia tremer.")]
    assert module._evidence_source(
        "Mary: Pois é, Silvia, ele achou que eu ia tremer.", entries
    ) == "MARY"


def test_abbreviated_evidence_with_bold_label():
    entries = [(
        "MARY",
        "**Silvia:** Viu só, Janio? O seu primo é um show à parte! "
        "Mas a gente também gosta de surpresas.",
    )]
    assert module._evidence_source(
        "Silvia: Viu só, Janio? ... a gente também gosta de surpresas.", entries
    ) == "MARY"


def test_different_speaker_is_not_accepted():
    entries = [("MARY", "**Silvia:** Viu só, Janio?")]
    assert module._evidence_source("Mary: Viu só, Janio?", entries) == ""


def test_invented_content_stays_invalid():
    entries = [("MARY", "**Silvia:** Viu só, Janio?")]
    assert module._evidence_source("Silvia: Ele já saiu do bar.", entries) == ""


def test_scene_evidence_normalization_same_words():
    response = "**Mary:** Tudo bem, eu aceito o desafio."
    evidence = "Mary: Tudo bem, eu aceito o desafio."
    assert module._normalize_evidence_text(evidence) in module._normalize_evidence_text(response)
