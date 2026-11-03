"""Testes isolados: não exigem Streamlit, API, credenciais nem Google Sheets."""
import importlib.util
from pathlib import Path
import unittest

MODULE = Path(__file__).resolve().parents[1] / "mary2" / "episodic_memory_shadow.py"
spec = importlib.util.spec_from_file_location("episodic_memory_shadow", MODULE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
select = module.select_episodic_candidates


def row(seq, user, mary, *, run="r1", chapter="cap1", branch="main"):
    return {
        "seq": seq, "user_text": user, "mary_text": mary,
        "run_id": run, "chapter_instance_id": chapter, "branch_id": branch,
    }


class EpisodicShadowTests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            row(1, "Olha o meu carro novo, parece um carro de milionário", "Calma, milionário!"),
            row(2, "Você gostou da piada do milionário e do carro?", "Gostei da brincadeira."),
            row(3, "Vamos sentar perto da piscina?", "Vamos, sim."),
            row(4, "Gostei de estar aqui.", "Também gostei."),
            row(5, "Olha o carro outra vez", "Lá vem você."),
        ]

    def run_select(self, **kwargs):
        return select(self.rows, run_id="r1", chapter_instance_id="cap1",
                      branch_id="main", before_seq=6, current_user_text="E o carro do milionário?", **kwargs)

    def test_retrieves_older_literal_evidence(self):
        result = self.run_select()
        self.assertTrue(result)
        self.assertEqual(result[0]["seq"], 1)
        self.assertEqual(result[0]["source"], "INTERACTIONS")
        self.assertIn("milionário", result[0]["user_evidence"])

    def test_excludes_recent_turns(self):
        self.assertTrue(all(item["seq"] < 4 for item in self.run_select()))

    def test_separates_other_runs_chapters_and_branches(self):
        others = [
            row(1, "carro de milionário", "Olha o carro de milionário", run="outro"),
            row(1, "carro de milionário", "Olha o carro de milionário", chapter="outro"),
            row(1, "carro de milionário", "Olha o carro de milionário", branch="outra"),
        ]
        result = select(others, run_id="r1", chapter_instance_id="cap1",
                        branch_id="main", before_seq=10,
                        current_user_text="carro de milionário")
        self.assertEqual(result, [])

    def test_no_future_leak(self):
        future = [row(8, "carro de milionário", "O carro de milionário chegou")]
        result = select(future, run_id="r1", chapter_instance_id="cap1",
                        branch_id="main", before_seq=7,
                        current_user_text="carro de milionário")
        self.assertEqual(result, [])

    def test_no_match_returns_empty(self):
        self.assertEqual(self.run_select(current_user_text="Abacaxi no jardim"), [])

    def test_no_single_term_trigger(self):
        self.assertEqual(self.run_select(current_user_text="Carro!"), [])

    def test_context_alone_does_not_trigger(self):
        result = select(self.rows, run_id="r1", chapter_instance_id="cap1",
                        branch_id="main", before_seq=6,
                        current_user_text="Que tal viajarmos amanhã?",
                        recent_context="carro de milionário")
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
