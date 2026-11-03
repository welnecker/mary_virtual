"""Regressions for displaying QUADROS_INFORMATIVOS on direct-sheet opening."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mary2"))

from direct_script import _lookup_direct_info_board


class DirectInfoBoardLookupTests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            ["ROTEIRO", "QUADRO INICIAL"],
            ["Cruzeiro Caribe1", "Abertura do primeiro capítulo."],
            ["Cruzeiro Caribe2", "Abertura do segundo capítulo."],
        ]

    def test_ignores_spacing_before_number(self):
        self.assertEqual(
            _lookup_direct_info_board(self.rows, "Cruzeiro Caribe 1"),
            "Abertura do primeiro capítulo.",
        )

    def test_does_not_confuse_sequels(self):
        self.assertEqual(
            _lookup_direct_info_board(self.rows, "Cruzeiro Caribe 2"),
            "Abertura do segundo capítulo.",
        )

    def test_exact_match_takes_priority(self):
        rows = self.rows + [["Cruzeiro Caribe 1", "Quadro exato."]]
        self.assertEqual(
            _lookup_direct_info_board(rows, "Cruzeiro Caribe 1"),
            "Quadro exato.",
        )

    def test_ambiguous_normalized_names_fail_closed(self):
        rows = self.rows + [["Cruzeiro  Caribe1", "Outro quadro."]]
        with self.assertRaisesRegex(ValueError, "ambíguos"):
            _lookup_direct_info_board(rows, "Cruzeiro Caribe 1")

    def test_no_matching_chapter(self):
        self.assertEqual(
            _lookup_direct_info_board(self.rows, "Apartamento1"), "",
        )


if __name__ == "__main__":
    unittest.main()
