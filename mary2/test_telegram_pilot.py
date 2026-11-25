"""Regressões do adaptador Telegram; não fazem requests nem chamadas LLM reais."""
from __future__ import annotations

import unittest
from unittest.mock import patch

import telegram_pilot as tg


def _rows(script="Celular1", conditional=True):
    return [
        {"order": 1, "line_id": "linha_1", "script_name": script,
         "interaction_mode": "bloqueado",
         "speech_guide": "Mary inicia ou atende."},
        {"order": 2, "line_id": "linha_2", "script_name": script,
         "interaction_mode": "",
         "speech_guide": (
             "ACEITE: Mary confirma e se despede.\n"
             "RECUO: Mary encerra sem confirmar."
             if conditional else "Mary termina a conversa e se despede."
         )},
    ]


def _state(incoming=False, script=None):
    return {
        "index": 0, "history": [], "offset": 0, "last_message_id": 0,
        "status": "active",
        "script_name": script or ("Recebido1" if incoming else "Celular1"),
        "worksheet_name": (
            "MARY_CELULAR_RECEBIDO" if incoming else "MARY_CELULAR"
        ),
        "trigger_id": "chapter:10", "incoming": incoming, "marker": (
            "celular_rec1" if incoming else "Celular1"
        ), "interlocutor": "Janio",
        "loop": {"active": False, "attempts": 0},
    }


def _event(text, update=81, message_id=51):
    return {"update_id": update, "message": {
        "message_id": message_id, "chat": {"id": 123}, "text": text
    }}


class TelegramNarrativeContractTest(unittest.TestCase):
    def _send_stub(self, method, payload):
        self.assertEqual(method, "sendMessage")
        self.assertEqual(payload["chat_id"], 123)
        return {"ok": True, "result": {"message_id": 70}}

    def test_shared_scene_context_is_scoped_to_selected_script(self):
        headers = ["Ordem", "Roteiro", "Fala-guia", "DESCRIÇÃO INICIAL-CENA",
                   "MEMÓRIA PERMANENTE-GLOBAL", "MEMÓRIA FÍSICA-GLOBAL",
                   "MEMÓRIA INSTANTÂNEA-LOCAL"]
        for worksheet_name, script_name in (
            ("MINHA_SUGESTAO", "Principal"),
            ("MARY_CELULAR", "Celular2"),
            ("MARY_CELULAR_RECEBIDO", "Recebido1"),
        ):
            with self.subTest(worksheet=worksheet_name):
                worksheet = unittest.mock.Mock()
                worksheet.get_all_values.return_value = [
                    headers,
                    ["1", "Outro", "Outra missão", "Contexto alheio", "Outra memória", "", ""],
                    ["1", script_name, "Iniciar", "Janio é amigo de Rodrigo.", "Amigas", "Adultas", "Sacada"],
                    ["2", script_name, "Continuar", "", "", "", "Conversa"],
                    ["3", script_name, "Responder", "Contexto específico", "", "", ""],
                    ["4", script_name, "Responder", "", "", "", ""],
                ]
                client = unittest.mock.Mock()
                client.open_by_key.return_value.worksheet.return_value = worksheet
                with patch.object(tg.gspread, "service_account_from_dict", return_value=client):
                    rows = tg.load_direct_script_rows(
                        service_account_info={"test": True}, spreadsheet_id="test",
                        worksheet_name=worksheet_name, script_name=script_name,
                    )
                self.assertEqual(len(rows), 4)
                self.assertEqual([row["initial_description"] for row in rows], [
                    "Janio é amigo de Rodrigo.", "Janio é amigo de Rodrigo.",
                    "Contexto específico", "Janio é amigo de Rodrigo.",
                ])
                self.assertEqual(rows[3]["permanent_memory"], "Amigas")
                self.assertEqual(rows[3]["physical_memory"], "Adultas")
                self.assertEqual(rows[3]["instant_memory"], "")
                prompt = tg.build_direct_writer_prompt(
                    row=rows[3], all_rows=rows, recent_messages=[],
                    user_text="Quem é o amigo de Rodrigo?", active_interlocutor="Silvia",
                )
                self.assertIn("Janio é amigo de Rodrigo.", prompt)
                self.assertNotIn("Contexto alheio", prompt)
                self.assertNotIn("Outra memória", prompt)

    def test_audit_contains_metadata_not_private_message(self):
        state = _state(incoming=True)
        state.update({
            "parent_order": "20", "marker": "celular_rec1",
            "script_name": "Recebido1", "interlocutor": "Janio",
        })
        worksheet = unittest.mock.Mock()
        book = unittest.mock.Mock()
        book.worksheet.return_value = worksheet
        client = unittest.mock.Mock()
        client.open_by_key.return_value = book
        session = {"run_id": "mary_test", "story_state": {"narrative": {
            "chapter_id": "sheet:Cruzeiro Caribe4",
            "chapter_instance_id": "scene_1",
        }}}
        with patch.object(tg.st, "session_state", session), \
             patch.object(tg, "_credentials", return_value=({"type":"service_account"}, "sheet")), \
             patch.object(tg.gspread, "service_account_from_dict", return_value=client):
            tg._audit_event(
                state, "incoming_processed", before="waiting", after="active",
                order=2, update_id=123,
            )
        worksheet.append_row.assert_called_once()
        logged = worksheet.append_row.call_args.args[0]
        record = dict(zip(tg._AUDIT_HEADERS, logged))
        self.assertEqual(record["run_id"], "mary_test")
        self.assertEqual(record["parent_order"], "20")
        self.assertEqual(record["subscript"], "Recebido1")
        self.assertEqual(record["interlocutor"], "Janio")
        self.assertEqual(record["telegram_update_id"], "123")
        self.assertNotIn("text", tg._AUDIT_HEADERS)
        self.assertNotIn("token", " ".join(tg._AUDIT_HEADERS))
        book.worksheet.assert_called_once_with("TELEGRAM_AUDIT")

    def test_audit_failure_does_not_interrupt_calls(self):
        state = _state()
        with patch.object(tg, "_credentials", side_effect=RuntimeError("offline")):
            tg._audit_event(state, "line_sent", order=1)
        # Silencioso para o usuário; nenhum reenvio ou LLM causado pelo log.

    def test_dynamic_script_mapping(self):
        self.assertEqual(
            tg.resolve_telegram_script("celular_rec2"),
            ("MARY_CELULAR_RECEBIDO", "Recebido2", True),
        )
        self.assertEqual(
            tg.resolve_telegram_script("Celular12"),
            ("MARY_CELULAR", "Celular12", False),
        )
        self.assertEqual(
            tg.resolve_telegram_script("CELULAR_REC1"),
            ("MARY_CELULAR_RECEBIDO", "Recebido1", True),
        )
        with self.assertRaises(ValueError):
            tg.resolve_telegram_script("Recebido1")

    def test_normal_parent_line_20_arms_received_call(self):
        row = {
            "order": 20, "telegram_script": "celular_rec1",
            "thought_guide": "Meu celular...droga..Janio? Meu Deus..",
            "speech_guide": (
                "Mary pede para Donisete esperar, mentindo que é Silvia."
            ),
            "action_guide": "Mary se afasta até o banheiro.",
            "interaction_mode": "",
        }
        state = {"awaiting_reply_order": 20, "automatic_emitted_order": 0}
        self.assertTrue(tg.telegram_parent_line_emitted(row, state))
        self.assertEqual(tg.extract_call_interlocutor(row), "Janio")
        self.assertFalse(tg.telegram_parent_line_emitted(
            row, {"awaiting_reply_order": 0, "automatic_emitted_order": 0}
        ))
        self.assertFalse(tg.telegram_parent_line_emitted(row, state, True))

    def test_blocked_and_automatic_parent_lines_still_arm(self):
        row = {"order": 2, "telegram_script": "Celular1"}
        self.assertTrue(tg.telegram_parent_line_emitted(
            row, {"automatic_emitted_order": 2}
        ))
        self.assertTrue(tg.telegram_parent_line_emitted(
            row, {"awaiting_reply_order": 2}
        ))
        self.assertFalse(tg.telegram_parent_line_emitted(
            {"order": 2, "telegram_script": ""}, {"awaiting_reply_order": 2}
        ))

    def test_parent_scene_identifies_interlocutor(self):
        self.assertEqual(tg.extract_call_interlocutor({
            "speech_guide": "Mary diz que vai tentar conversar com Donisete."
        }), "Donisete")
        self.assertEqual(tg.extract_call_interlocutor({
            "speech_guide": "Eita... Janio tá me ligando!"
        }), "Janio")
        self.assertEqual(tg.extract_call_interlocutor({
            "speech_guide": "Mary resolve ligar para Silvia."
        }), "Silvia")
        self.assertEqual(tg.extract_call_interlocutor({}), "")

    def test_waiting_requires_parent_trigger_and_emits_no_message(self):
        session = {}
        with patch.object(tg.st, "session_state", session), \
             patch.object(tg, "_rows", return_value=_rows("Recebido2")) as loader, \
             patch.object(tg, "_allowed_chat", return_value=123), \
             patch.object(tg, "_latest_offset", return_value=45), \
             patch.object(tg, "_telegram") as transport, \
             patch.object(tg, "_generate") as writer:
            status = tg.ensure_telegram_call(
                "chapter:10", "celular_rec2", "fake-model", "Silvia"
            )
        self.assertEqual(status, "waiting")
        self.assertEqual(session["_mary_telegram_pilot"]["script_name"], "Recebido2")
        self.assertEqual(session["_mary_telegram_pilot"]["interlocutor"], "Silvia")
        self.assertEqual(session["_mary_telegram_pilot"]["offset"], 45)
        loader.assert_called_once_with("Recebido2", "MARY_CELULAR_RECEBIDO")
        transport.assert_not_called()
        writer.assert_not_called()

    def test_waiting_rejects_missing_character_name(self):
        session = {}
        with patch.object(tg.st, "session_state", session):
            with self.assertRaisesRegex(RuntimeError, "identificar"):
                tg.ensure_telegram_call("chapter:10", "celular_rec2", "fake-model", "")

    def test_outgoing_n_calls_send_on_trigger(self):
        session = {}
        with patch.object(tg.st, "session_state", session), \
             patch.object(tg, "_rows", return_value=_rows("Celular2")) as loader, \
             patch.object(tg, "_allowed_chat", return_value=123), \
             patch.object(tg, "_latest_offset", return_value=45), \
             patch.object(tg, "_telegram", side_effect=self._send_stub) as transport, \
             patch.object(tg, "_generate", return_value="Oi, Silvia!"):
            result = tg.ensure_telegram_call("chapter:18", "Celular2",
                                             "fake-model", "Silvia")
            again = tg.ensure_telegram_call("chapter:18", "Celular2",
                                            "fake-model", "Silvia")
        self.assertEqual(result, "active")
        self.assertEqual(again, "active")
        self.assertEqual(transport.call_count, 1)
        loader.assert_called_once_with("Celular2", "MARY_CELULAR")
        self.assertEqual(session["_mary_telegram_pilot"]["interlocutor"], "Silvia")

    def test_received_call_activates_only_waiting_selected_script(self):
        session = {"_mary_telegram_pilot": {
            **_state(incoming=True, script="Recebido2"),
            "status": "waiting", "offset": 80,
        }}
        with patch.object(tg.st, "session_state", session), \
             patch.object(tg, "_rows", return_value=_rows("Recebido2")) as loader, \
             patch.object(tg, "_allowed_chat", return_value=123), \
             patch.object(tg, "_telegram",
                          side_effect=[{"ok": True, "result": [_event("Oi, Mary")]}] + [
                              {"ok": True, "result": {"message_id": 70}}
                          ]), \
             patch.object(tg, "_send_emotional_reply", return_value=False), \
             patch.object(tg, "_generate", return_value="Oi, Janio!"):
            notice = tg._check_reply("fake-model")
        state = session["_mary_telegram_pilot"]
        self.assertIn("Chamada recebida", notice)
        self.assertEqual(state["status"], "active")
        self.assertEqual(state["script_name"], "Recebido2")
        self.assertEqual(state["offset"], 82)
        self.assertEqual(state["history"][0]["content"], "Oi, Mary")
        loader.assert_called_with("Recebido2", "MARY_CELULAR_RECEBIDO")

    def test_idle_ignores_messages_without_parent_trigger(self):
        session = {"_mary_telegram_pilot": {**_state(), "status": "idle"}}
        with patch.object(tg.st, "session_state", session), \
             patch.object(tg, "_telegram") as transport:
            notice = tg._check_reply("fake-model")
        self.assertIn("Nenhuma chamada", notice)
        transport.assert_not_called()

    def test_late_message_after_finish_does_not_reopen(self):
        session = {"_mary_telegram_pilot": {**_state(), "status": "finished"}}
        with patch.object(tg.st, "session_state", session), \
             patch.object(tg, "_telegram") as transport:
            tg._check_reply("fake-model")
        transport.assert_not_called()

    def test_failed_processing_pauses_monitor_to_avoid_token_loop(self):
        state = {**_state(), "offset": 80}
        session = {"_mary_telegram_pilot": state}
        with patch.object(tg.st, "session_state", session), \
             patch.object(tg, "_allowed_chat", return_value=123), \
             patch.object(tg, "_telegram",
                          return_value={"ok": True, "result": [_event("Oi!")]}), \
             patch.object(tg, "_rows", side_effect=RuntimeError("Director indisponível")):
            with self.assertRaisesRegex(RuntimeError, "Director"):
                tg._check_reply("fake-model")
        self.assertEqual(state["status"], "reply_error")
        self.assertEqual(state["offset"], 80)
        with patch.object(tg.st, "session_state", session), \
             patch.object(tg, "_telegram") as transport:
            tg._check_reply("fake-model")
        transport.assert_not_called()

    def test_received_completion_releases_parent_without_meeting_gate(self):
        state = _state(incoming=True)
        with patch.object(tg, "_generate", return_value="Até mais!"), \
             patch.object(tg, "_telegram", side_effect=self._send_stub), \
             patch.object(tg, "_classify_final_reply", return_value="RECUO"):
            tg._send_line(_rows("Recebido1"), state, 123, "fake-model", "Oi!")
            tg._send_line(_rows("Recebido1"), state, 123, "fake-model", "Tchau!")
        self.assertEqual(state["status"], "approved")
        self.assertTrue(state["direct_script"]["completed"])
        # O retorno à cena mãe consumirá o status aprovado.

    def test_conditional_classification_uses_authored_mission_and_previous_yes(self):
        history = [
            {"role": "assistant", "content": "Você aceita encontrar Mary no deck?"},
            {"role": "user", "content": "Sim, eu vou ao deck às oito."},
            {"role": "assistant", "content": "Combinado, às oito."},
        ]
        guide = (
            "ACEITE: Mary confirma o encontro e se despede. "
            "RECUO: Mary respeita a recusa e se despede."
        )
        with patch.object(tg, "chat", return_value="ACEITE") as llm:
            outcome = tg._classify_final_reply(
                "Tá bom, tchau.", history, "fake-model", "Janio", guide
            )
        self.assertEqual(outcome, "ACEITE")
        messages = llm.call_args.kwargs["messages"]
        self.assertIn(guide, messages[1]["content"])
        self.assertIn("Sim, eu vou", messages[1]["content"])
        self.assertIn("NÃO cancela", messages[0]["content"])

    def test_outgoing_conditional_recuo_still_blocks(self):
        state = _state()
        with patch.object(tg, "_generate", return_value="Até mais!"), \
             patch.object(tg, "_telegram", side_effect=self._send_stub), \
             patch.object(tg, "_classify_final_reply", return_value="RECUO"):
            tg._send_line(_rows(), state, 123, "fake-model")
            tg._send_line(_rows(), state, 123, "fake-model", "Não.")
        self.assertEqual(state["status"], "rejected")

    def test_outgoing_without_conditional_branches_finishes_normally(self):
        state = _state(script="Celular3")
        with patch.object(tg, "_generate", return_value="Até mais!"), \
             patch.object(tg, "_telegram", side_effect=self._send_stub):
            tg._send_line(_rows("Celular3", conditional=False), state, 123, "fake-model")
            tg._send_line(_rows("Celular3", conditional=False), state, 123,
                          "fake-model", "Até logo.")
        self.assertEqual(state["status"], "approved")

    def test_writer_receives_selected_character_not_donisete(self):
        row = _rows("Recebido2")[0]
        with patch.object(tg, "analyze_user_understanding", return_value={}) as analysis, \
             patch.object(tg, "build_direct_writer_prompt", return_value="Prompt") as writer, \
             patch.object(tg, "chat", return_value="[FALA] Oi!"), \
             patch.object(tg, "parse_mary_components", return_value={
                 "speech": "Oi!", "thought": "", "action": ""
             }), \
             patch.object(tg, "sanitize_mary_output", return_value="Oi!"), \
             patch.object(tg, "looks_like_action_narration", return_value=False), \
             patch.object(tg, "validate_direct_semantic_turn",
                          return_value={"fulfilled": True}):
            tg._generate(row, _rows("Recebido2"), [], "Oi, Mary!",
                         "fake-model", incoming=True, interlocutor="Silvia")
        self.assertEqual(analysis.call_args.kwargs["active_interlocutor"], "Silvia")
        self.assertEqual(writer.call_args.kwargs["character_name"], "Silvia")
        self.assertEqual(writer.call_args.kwargs["row"]["interaction_mode"], "")

    def test_emotional_loop_preserves_parent_authorized_character(self):
        row = _rows()[0]
        row.update({
            "negative_prompt": "Não humilhar Mary.",
            "hurt_style": "Mary exige respeito.",
            "_emotional_loop_row": {
                "order": 0,
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
        self.assertFalse(exhausted)
        self.assertEqual(loop["attempts"], 1)
        self.assertIn("primeira tentativa", active["speech_guide"])

    def test_received_first_message_cannot_exhaust_three_turn_loop(self):
        row = _rows("Recebido1")[0]
        row.update({
            "negative_prompt": "Não ofender Mary.",
            "hurt_style": "Mary estabelece limites.",
            "_emotional_loop_row": {
                "order": 0, "speech_guide": (
                    "Mary educada no primeiro pedido de desculpas. "
                    "Mary firme na segunda tentativa. "
                    "Mary encerra na terceira tentativa."
                ),
            },
        })
        state = _state(incoming=True)
        with patch.object(tg, "_emotional_assessment",
                          return_value={"violation": True, "frustration": False}):
            _, first, exhausted = tg._prepare_emotional_row(
                row, state, "Mensagem ofensiva", "fake-model"
            )
        self.assertTrue(first["active"])
        self.assertEqual(first["attempts"], 1)
        self.assertFalse(exhausted)
        self.assertEqual(state["last_emotional_assessment"]["violation"], True)

    def test_no_offense_does_not_activate_loop(self):
        row = _rows("Recebido1")[0]
        row.update({
            "negative_prompt": "Não xingar Mary.",
            "hurt_style": "Mary protege seus limites.",
            "_emotional_loop_row": {"order": 0, "speech_guide": "Mary encerra após três tentativas."},
        })
        state = _state(incoming=True)
        with patch.object(tg, "_emotional_assessment",
                          return_value={"violation": False, "frustration": False,
                                        "rejected": False}):
            _, loop, exhausted = tg._prepare_emotional_row(
                row, state, "Oi, você pode falar?", "fake-model"
            )
        self.assertFalse(loop["active"])
        self.assertFalse(exhausted)

    def test_second_call_can_follow_first_after_parent_release(self):
        state = _state()
        state["status"] = "approved"
        session = {"_mary_telegram_pilot": state}
        with patch.object(tg.st, "session_state", session):
            tg.release_telegram_call("chapter:10")
        self.assertEqual(state["status"], "finished")
        with patch.object(tg.st, "session_state", session), \
             patch.object(tg, "_rows", return_value=_rows("Recebido2")), \
             patch.object(tg, "_allowed_chat", return_value=123), \
             patch.object(tg, "_latest_offset", return_value=99):
            new_status = tg.ensure_telegram_call(
                "chapter:20", "celular_rec2", "fake-model", "Janio"
            )
        self.assertEqual(new_status, "waiting")
        self.assertEqual(session["_mary_telegram_pilot"]["script_name"], "Recebido2")


if __name__ == "__main__":
    unittest.main()
