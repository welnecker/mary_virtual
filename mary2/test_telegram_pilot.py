"""Testes isolados de contratos Telegram; nunca acessam APIs reais."""
from __future__ import annotations

import unittest
from unittest.mock import patch

import telegram_pilot as tg


def _rows():
    return [
        {
            "order": 1, "line_id": "linha_01", "script_name": "Celular1",
            "interaction_mode": "bloqueado", "speech_guide": "Mary cumprimenta Donisete.",
        },
        {
            "order": 2, "line_id": "linha_02", "script_name": "Celular1",
            "interaction_mode": "", "speech_guide": (
                "ACEITE: Mary confirma o encontro e se despede.\n"
                "RECUO: Mary agradece e encerra sem encontro."
            ),
        },
    ]


def _state(incoming=False):
    return {
        "index": 0, "history": [], "offset": 0, "last_message_id": 0,
        "status": "active", "script_name": "Recebido1" if incoming else "Celular1",
        "worksheet_name": (
            "MARY_CELULAR_RECEBIDO" if incoming else "MARY_CELULAR"
        ),
        "trigger_id": "test", "incoming": incoming,
        "loop": {"active": False, "attempts": 0},
    }


class TelegramNarrativeContractTest(unittest.TestCase):
    def _send_stub(self, method, payload):
        self.assertEqual(method, "sendMessage")
        self.assertEqual(payload["chat_id"], 123)
        return {"ok": True, "result": {"message_id": self.message_id}}

    def test_outgoing_waits_for_real_reply_and_approves_acceptance(self):
        self.message_id = 10
        state = _state()
        with patch.object(tg, "_generate", return_value="Oi, Doni."), \
             patch.object(tg, "_telegram", side_effect=self._send_stub), \
             patch.object(tg, "_classify_final_reply", return_value="ACEITE"):
            tg._send_line(_rows(), state, 123, "fake-model")
            self.assertEqual(state["status"], "active")
            self.assertEqual(state["direct_script"]["awaiting_reply_order"], 1)
            self.assertFalse(state["direct_script"]["completed"])
            self.message_id = 12
            tg._send_line(_rows(), state, 123, "fake-model", "Sim, aceito.")
        self.assertEqual(state["status"], "approved")
        self.assertTrue(state["direct_script"]["completed"])
        self.assertEqual(state["outcome"], "ACEITE")

    def test_outgoing_rejection_keeps_result_rejected(self):
        self.message_id = 30
        state = _state()
        with patch.object(tg, "_generate", return_value="Até mais."), \
             patch.object(tg, "_telegram", side_effect=self._send_stub), \
             patch.object(tg, "_classify_final_reply", return_value="RECUO"):
            tg._send_line(_rows(), state, 123, "fake-model")
            tg._send_line(_rows(), state, 123, "fake-model", "Não.")
        self.assertEqual(state["status"], "rejected")
        self.assertEqual(state["outcome"], "RECUO")

    def test_received_closes_without_advancing_main_story(self):
        self.message_id = 50
        state = _state(incoming=True)
        with patch.object(tg, "_generate", return_value="Até mais."), \
             patch.object(tg, "_telegram", side_effect=self._send_stub), \
             patch.object(tg, "_classify_final_reply", return_value="RECUO"):
            tg._send_line(_rows(), state, 123, "fake-model", "Oi, Mary.")
            tg._send_line(_rows(), state, 123, "fake-model", "Até logo.")
        self.assertEqual(state["status"], "finished")
        self.assertEqual(state["worksheet_name"], "MARY_CELULAR_RECEBIDO")

    def test_incoming_message_activates_received_tab(self):
        self.message_id = 60
        session = {}
        event = {"update_id": 121, "message": {
            "message_id": 35, "chat": {"id": 123}, "text": "Oi, Mary"
        }}
        with patch.object(tg.st, "session_state", session), \
             patch.object(tg, "_rows", return_value=_rows()) as loader, \
             patch.object(tg, "_allowed_chat", return_value=123), \
             patch.object(tg, "_generate", return_value="Oi, sumido!"), \
             patch.object(tg, "_telegram", side_effect=self._send_stub), \
             patch.object(tg, "_send_emotional_reply", return_value=False):
            tg._start_received(event, "fake-model")
        state = session["_mary_telegram_pilot"]
        self.assertTrue(state["incoming"])
        self.assertEqual(state["status"], "active")
        self.assertEqual(state["offset"], 122)
        loader.assert_called_with("Recebido1", "MARY_CELULAR_RECEBIDO")

    def test_emotional_loop_uses_authorial_row_and_does_not_advance(self):
        row = _rows()[0]
        row.update({
            "negative_prompt": "Não humilhar Mary.",
            "hurt_style": "Mary exige respeito.",
            "_emotional_loop_row": {
                "order": 0,
                "line_id": "loop_orgulho_ferido",
                "speech_guide": (
                    "Mary fala com calma na primeira tentativa. "
                    "Mary impõe limites na segunda tentativa. "
                    "Mary encerra na terceira tentativa."
                ),
            },
        })
        state = _state(incoming=True)
        with patch.object(tg, "_emotional_assessment",
                          return_value={"violation": True}):
            active, loop, exhausted = tg._prepare_emotional_row(
                row, state, "Você não vale nada.", "fake-model"
            )
        self.assertTrue(loop["active"])
        self.assertEqual(loop["attempts"], 1)
        self.assertFalse(exhausted)
        self.assertEqual(active["line_id"], "loop_orgulho_ferido")
        self.assertIn("primeira tentativa", active["speech_guide"])

    def test_first_received_line_preserves_incoming_user_speech(self):
        row = _rows()[0]
        with patch.object(tg, "analyze_user_understanding", return_value={}), \
             patch.object(tg, "build_direct_writer_prompt", return_value="Prompt") as writer, \
             patch.object(tg, "chat", return_value="[FALA] Oi, Doni!"), \
             patch.object(tg, "parse_mary_components", return_value={
                 "speech": "Oi, Doni!", "thought": "", "action": ""
             }), \
             patch.object(tg, "sanitize_mary_output", return_value="Oi, Doni!"), \
             patch.object(tg, "looks_like_action_narration", return_value=False), \
             patch.object(tg, "validate_direct_semantic_turn",
                          return_value={"fulfilled": True}):
            result = tg._generate(row, _rows(), [], "Oi, Mary!", "fake-model", incoming=True)
        self.assertEqual(result, "Oi, Doni!")
        self.assertEqual(writer.call_args.kwargs["row"]["interaction_mode"], "")
        self.assertEqual(writer.call_args.kwargs["user_text"], "Oi, Mary!")

    def test_recheck_rejected_encounter_releases_existing_call(self):
        state = _state()
        state.update({
            "status": "rejected", "outcome": "RECUO",
            "direct_script": {"completed": True},
            "history": [
                {"role": "assistant", "content": "Você vem ao deck?"},
                {"role": "user", "content": "Sim, eu vou às oito."},
                {"role": "assistant", "content": "Combinado, às oito."},
                {"role": "user", "content": "Tá bom, tchau."},
                {"role": "assistant", "content": "Até logo!"},
            ],
        })
        session = {"_mary_telegram_pilot": state}
        with patch.object(tg.st, "session_state", session), \
             patch.object(tg, "_classify_final_reply", return_value="ACEITE") as classify, \
             patch.object(tg, "_telegram") as telegram:
            outcome = tg.recheck_rejected_encounter("fake-model")
        self.assertEqual(outcome, "ACEITE")
        self.assertEqual(state["status"], "approved")
        classify.assert_called_once()
        telegram.assert_not_called()

    def test_final_classification_keeps_previous_yes_after_goodbye(self):
        history = [
            {"role": "assistant", "content": "Você aceita vir ao deck?"},
            {"role": "user", "content": "Poderia ser na suíte?"},
            {"role": "assistant", "content": "Prefiro no deck."},
            {"role": "user", "content": "Espera... tudo bem, sim, eu vou no deck. Que horas?"},
            {"role": "assistant", "content": "Vamos às oito, no deck onde a gente se conheceu."},
        ]
        with patch.object(tg, "chat", return_value="ACEITE") as request:
            outcome = tg._classify_final_reply(
                "Tá bom... tchau.", history, "fake-model"
            )
        self.assertEqual(outcome, "ACEITE")
        prompt = request.call_args.kwargs["messages"]
        self.assertIn("sim, eu vou no deck", prompt[1]["content"])
        self.assertIn("Tá bom... tchau.", prompt[1]["content"])
        self.assertIn("NÃO cancela", prompt[0]["content"])

    def test_final_classification_respects_explicit_later_retraction(self):
        history = [
            {"role": "assistant", "content": "Você aceita me encontrar no deck?"},
            {"role": "user", "content": "Sim, vou."},
            {"role": "assistant", "content": "Combinado, às oito."},
        ]
        with patch.object(tg, "chat", return_value="RECUO") as request:
            result = tg._classify_final_reply(
                "Mudei de ideia. Não vou mais ao deck.", history, "fake-model"
            )
        self.assertEqual(result, "RECUO")
        prompt = request.call_args.kwargs["messages"]
        self.assertIn("REVOGOU", prompt[0]["content"])
        self.assertIn("Não vou mais", prompt[1]["content"])

    def test_late_message_after_farewell_does_not_restart(self):
        state = _state(incoming=True)
        state.update({"status": "finished", "initialized": True, "offset": 80})
        session = {"_mary_telegram_pilot": state}
        event = {"update_id": 81, "message": {
            "message_id": 42, "chat": {"id": 123},
            "text": "Tá bom, eu aceito seus termos."
        }}
        with patch.object(tg.st, "session_state", session), \
             patch.object(tg, "_allowed_chat", return_value=123), \
             patch.object(tg, "_telegram",
                          return_value={"ok": True, "result": [event]}), \
             patch.object(tg, "_start_received") as starter:
            result = tg._check_reply("fake-model")
        starter.assert_not_called()
        self.assertIn("encerrado", result)
        self.assertEqual(state["status"], "finished")
        self.assertEqual(state["offset"], 82)

    def test_explicit_mary_command_restarts_after_farewell(self):
        state = _state(incoming=True)
        state.update({"status": "finished", "initialized": True, "offset": 80})
        session = {"_mary_telegram_pilot": state}
        event = {"update_id": 81, "message": {
            "message_id": 42, "chat": {"id": 123}, "text": "/mary"
        }}
        with patch.object(tg.st, "session_state", session), \
             patch.object(tg, "_allowed_chat", return_value=123), \
             patch.object(tg, "_telegram",
                          return_value={"ok": True, "result": [event]}), \
             patch.object(tg, "_start_received") as starter:
            tg._check_reply("fake-model")
        starter.assert_called_once_with(event, "fake-model")

    def test_call_release_allows_new_received_calls(self):
        state = _state()
        state["status"] = "approved"
        session = {"_mary_telegram_pilot": state}
        with patch.object(tg.st, "session_state", session):
            tg.release_telegram_call("test")
        self.assertEqual(session["_mary_telegram_pilot"]["status"], "finished")


if __name__ == "__main__":
    unittest.main()
