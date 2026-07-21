from __future__ import annotations

import unittest

from scenarios.service import (
    iniciar_cenario_para_usuario,
    listar_cenarios_para_usuario,
)
from ui.scenario_menu import (
    ACTION_PLAY,
    _resolver_card,
)


class ScenarioCardSmokeTest(unittest.TestCase):
    def test_catalogo_exibe_vizinha_como_degustacao_gratuita(
        self,
    ) -> None:
        cenarios = listar_cenarios_para_usuario(
            user_id="test_user",
        )

        self.assertEqual(
            len(cenarios),
            1,
        )

        cenario = cenarios[0]

        self.assertEqual(
            cenario["scenario_id"],
            "vizinha_porta_trancada",
        )
        self.assertTrue(
            cenario["allowed"]
        )
        self.assertEqual(
            cenario["access_status"],
            "free",
        )
        self.assertEqual(
            cenario["access_reason"],
            "free_scenario",
        )
        self.assertEqual(
            cenario["price_cents"],
            0,
        )

        card = _resolver_card(
            cenario
        )

        self.assertEqual(
            card["title"],
            "A vizinha presa do lado de fora",
        )
        self.assertEqual(
            card["badge"],
            "Degustação",
        )
        self.assertEqual(
            card["button_label_free"],
            "Jogar gratuitamente",
        )

    def test_vizinha_pode_ser_iniciada_pelo_service(
        self,
    ) -> None:
        instancia = iniciar_cenario_para_usuario(
            user_id="test_user",
            scenario_id="vizinha_porta_trancada",
        )

        self.assertEqual(
            instancia["user_id"],
            "test_user",
        )
        self.assertEqual(
            instancia["scenario_id"],
            "vizinha_porta_trancada",
        )
        self.assertEqual(
            instancia["access_status"],
            "free",
        )
        self.assertEqual(
            instancia["access_reason"],
            "free_scenario",
        )
        self.assertEqual(
            instancia["target_interactions"],
            48,
        )
        self.assertEqual(
            instancia["soft_ending_start"],
            40,
        )
        self.assertEqual(
            instancia["hard_ending_limit"],
            58,
        )
        self.assertEqual(
            instancia["max_interactions"],
            58,
        )
        self.assertEqual(
            instancia["current_phase"],
            "opening",
        )
        self.assertFalse(
            instancia["opening_sent"]
        )
        self.assertTrue(
            instancia["opening_message"]
        )

    def test_acao_esperada_para_card_liberado(
        self,
    ) -> None:
        cenarios = listar_cenarios_para_usuario(
            user_id="test_user",
        )

        cenario = cenarios[0]

        action = (
            ACTION_PLAY
            if cenario["allowed"]
            else "unlock"
        )

        self.assertEqual(
            action,
            ACTION_PLAY,
        )


if __name__ == "__main__":
    unittest.main()
