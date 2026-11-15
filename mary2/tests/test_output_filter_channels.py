"""Regressões da separação dos canais da Mary Core 2 (sem chamadas LLM)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from output_filter import parse_mary_components, sanitize_mary_output


class StructuredOutputSpeechTests(unittest.TestCase):
    def test_deepseek_instruction_before_channels_is_not_speech(self):
        raw = (
            "Use a memória física apenas quando necessário.\n\n"
            "[PENSAMENTO] Estou com saudade.\n"
            "[AÇÃO] Mary pega o celular.\n"
            "[FALA] Mary: Oi, Silvia!"
        )
        parts = parse_mary_components(raw)
        self.assertEqual(parts["speech"], "Mary: Oi, Silvia!")
        self.assertEqual(parts["thought"], "Estou com saudade.")
        self.assertEqual(parts["action"], "Mary pega o celular.")

    def test_protocol_echo_and_previous_dialogue_are_not_published(self):
        raw = (
            "Não falha de continuidade: não se desculpe por erros do modelo.\n"
            "---\nSilvia: Você viu a programação?\n\n"
            "[PENSAMENTO] Vou acordar Donisete.\n"
            "[AÇÃO] Mary se aproxima da cama.\n"
            "[FALA] Mary: Bom dia, meu amor."
        )
        self.assertEqual(
            parse_mary_components(raw)["speech"], "Mary: Bom dia, meu amor."
        )

    def test_same_rule_applies_to_gemini_style_output(self):
        raw = "Uma instrução inesperada.\n[AÇÃO] Mary levanta.\n[FALA] Mary: Vamos?"
        self.assertEqual(parse_mary_components(raw)["speech"], "Mary: Vamos?")

    def test_legacy_response_without_any_markers_is_preserved(self):
        raw = "Mary: Bom dia, Donisete!\nSilvia: Bom dia!"
        self.assertEqual(parse_mary_components(raw)["speech"], raw)

    def test_repeated_speech_blocks_and_actions_remain_separate(self):
        raw = (
            "[FALA] Mary: Bom dia.\n"
            "[AÇÃO] Mary abre a janela.\n"
            "[FALA] Silvia: Olha o mar!\n"
            "[PENSAMENTO] Que manhã linda."
        )
        parts = parse_mary_components(raw)
        self.assertEqual(parts["speech"], "Mary: Bom dia.\nSilvia: Olha o mar!")
        self.assertEqual(parts["action"], "Mary abre a janela.")
        self.assertEqual(parts["thought"], "Que manhã linda.")

    def test_speaker_inside_action_is_still_recovered(self):
        raw = "[AÇÃO] Mary abre a porta.\nMary: Entre!"
        parts = parse_mary_components(raw)
        self.assertEqual(parts["action"], "Mary abre a porta.")
        self.assertEqual(parts["speech"], "Mary: Entre!")

    def test_only_action_does_not_create_fake_speech(self):
        parts = parse_mary_components("Explicação técnica.\n[AÇÃO] Mary sai da suíte.")
        self.assertEqual(parts["speech"], "")
        self.assertEqual(parts["action"], "Mary sai da suíte.")

    def test_authorial_sound_marker_and_existing_sanitizer(self):
        raw = "[FALA] Mary: §SMACK!!§ Você chegou!"
        parts = parse_mary_components(raw)
        self.assertEqual(sanitize_mary_output(parts["speech"]),
                         "Mary: SMACK!! Você chegou!")


if __name__ == "__main__":
    unittest.main()
