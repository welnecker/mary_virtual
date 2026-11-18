"""Offline tests: no OpenRouter calls or API credits required."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import openrouter_client as client


def response(content, *, output=10, reasoning=0, finish="stop", status=200):
    result = Mock()
    result.status_code = status
    result.raise_for_status.return_value = None
    result.json.return_value = {
        "choices": [{"message": {"content": content}, "finish_reason": finish}],
        "usage": {
            "completion_tokens": output,
            "completion_tokens_details": {"reasoning_tokens": reasoning},
        },
    }
    return result


class OpenRouterModelCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.messages = [{"role": "user", "content": "teste"}]

    @patch.object(client, "record")
    @patch.object(client.requests, "post")
    def test_mimo_first_attempt_disables_reasoning(self, post, record):
        post.return_value = response("Mary: Oi!")
        self.assertEqual(client.chat(api_key="test", model="xiaomi/mimo-v2.6-pro",
                                     messages=self.messages, call_type="REDACTOR"), "Mary: Oi!")
        config = post.call_args.kwargs["json"]
        self.assertEqual(config["reasoning"], {"enabled": False})
        self.assertEqual(config["max_tokens"], 3000)

    @patch.object(client, "record")
    @patch.object(client.requests, "post")
    def test_mimo_length_empty_recovers_without_reasoning_usage(self, post, record):
        post.side_effect = [response("", output=3000, reasoning=0, finish="length"),
                            response("Resposta recuperada")]
        self.assertEqual(client.chat(api_key="test", model="xiaomi/mimo-v2.6-pro",
                                     messages=self.messages, call_type="REDACTOR"),
                         "Resposta recuperada")
        self.assertEqual(post.call_count, 2)
        first, second = [call.kwargs["json"] for call in post.call_args_list]
        self.assertEqual(first["reasoning"], {"enabled": False})
        self.assertEqual(second["reasoning"], {"max_tokens": 768})
        self.assertEqual(second["max_tokens"], 3500)

    @patch.object(client, "record")
    @patch.object(client.requests, "post")
    def test_mimo_keeps_director_and_explicit_budgets(self, post, record):
        post.return_value = response("JSON pronto")
        client.chat(api_key="test", model="xiaomi/mimo-v2.6-pro",
                    messages=self.messages, call_type="SEMANTIC_DIRECTOR", max_tokens=7425)
        self.assertEqual(post.call_args.kwargs["json"]["max_tokens"], 7425)

    @patch.object(client, "record")
    @patch.object(client.requests, "post")
    def test_gemini_baseline_unchanged(self, post, record):
        post.return_value = response("Olá")
        value = client.chat(api_key="test", model="google/gemini-3-flash-preview",
                            messages=self.messages, call_type="REDACTOR")
        self.assertEqual(value, "Olá")
        self.assertEqual(post.call_args.kwargs["json"]["max_tokens"], 700)
        self.assertNotIn("reasoning", post.call_args.kwargs["json"])
        self.assertEqual(post.call_count, 1)

    @patch.object(client, "record")
    @patch.object(client.requests, "post")
    def test_reasoning_budget_recovery(self, post, record):
        post.side_effect = [
            response("", output=4500, reasoning=4500, finish="length"),
            response("JSON pronto", output=270, reasoning=50),
        ]
        value = client.chat(api_key="test", model="deepseek/deepseek-v4.1-flash-1017",
                            messages=self.messages, max_tokens=2600,
                            call_type="SEMANTIC_DIRECTOR")
        self.assertEqual(value, "JSON pronto")
        first, second = (x.kwargs["json"] for x in post.call_args_list)
        self.assertEqual(first["max_tokens"], 4500)
        self.assertEqual(first["reasoning"], {"enabled": False})
        self.assertEqual(second["max_tokens"], first["max_tokens"])
        self.assertEqual(second["reasoning"], {"max_tokens": 768})
        self.assertEqual(post.call_count, 2)

    @patch.object(client, "record")
    @patch.object(client.requests, "post")
    def test_deepseek_disabled_thinking_succeeds_without_retry(self, post, record):
        post.return_value = response("Mary: Oi!", output=140, reasoning=0)
        self.assertEqual(
            client.chat(api_key="test", model="deepseek/deepseek-v4.1-flash-1017",
                        messages=self.messages, call_type="REDACTOR"), "Mary: Oi!"
        )
        self.assertEqual(post.call_count, 1)
        self.assertEqual(post.call_args.kwargs["json"]["reasoning"], {"enabled": False})

    @patch.object(client, "record")
    @patch.object(client.requests, "post")
    def test_deepseek_disabled_rejected_uses_capped_reasoning(self, post, record):
        bad = Mock()
        bad.status_code = 400
        bad.json.return_value = {"error": {"message": "unsupported reasoning setting"}}
        bad.raise_for_status.side_effect = client.requests.HTTPError(response=bad)
        post.side_effect = [bad, response("Resposta útil", output=330, reasoning=180)]
        self.assertEqual(
            client.chat(api_key="test", model="deepseek/deepseek-v4.1-flash-1017",
                        messages=self.messages, call_type="REDACTOR"), "Resposta útil"
        )
        self.assertEqual(post.call_args_list[0].kwargs["json"]["reasoning"], {"enabled": False})
        self.assertEqual(post.call_args_list[1].kwargs["json"]["reasoning"], {"max_tokens": 768})

    @patch.object(client, "record")
    @patch.object(client.requests, "post")
    def test_unsupported_reasoning_option_retry_without_hint(self, post, record):
        bad = Mock()
        bad.status_code = 400
        bad.json.return_value = {"error": {"message": "unknown reasoning parameter"}}
        bad.raise_for_status.side_effect = client.requests.HTTPError(response=bad)
        post.side_effect = [bad, response("Funcionou")]
        self.assertEqual(
            client.chat(api_key="test", model="z-ai/glm-5.3-flash",
                        messages=self.messages, call_type="REDACTOR"),
            "Funcionou",
        )
        self.assertIn("reasoning", post.call_args_list[0].kwargs["json"])
        self.assertNotIn("reasoning", post.call_args_list[1].kwargs["json"])

    @patch.object(client, "record")
    @patch.object(client.requests, "post")
    def test_multipart_text_response(self, post, record):
        post.return_value = response([{"type": "text", "text": "Oi, "},
                                      {"type": "text", "text": "Mary"}])
        self.assertEqual(
            client.chat(api_key="test", model="google/gemma-4-31b-it",
                        messages=self.messages), "Oi, Mary"
        )

    @patch.object(client, "record")
    @patch.object(client.requests, "post")
    def test_fallback_after_two_empty_responses(self, post, record):
        post.side_effect = [
            response("", output=2000, reasoning=2000, finish="length"),
            response("", output=3300, reasoning=3300, finish="length"),
            response("Fallback válido"),
        ]
        self.assertEqual(
            client.chat(api_key="test", model="deepseek/deepseek-v4-flash",
                        fallback_model="google/gemini-3-flash-preview",
                        messages=self.messages, call_type="REDACTOR"),
            "Fallback válido",
        )
        self.assertEqual(post.call_count, 3)
        self.assertEqual(post.call_args_list[-1].kwargs["json"]["max_tokens"], 700)

    @patch.object(client, "record")
    @patch.object(client.requests, "post")
    def test_nonreasoning_empty_never_increases_budget(self, post, record):
        post.side_effect = [response("", finish="stop"), response("OK")]
        self.assertEqual(
            client.chat(api_key="test", model="google/gemma-4-31b-it",
                        messages=self.messages, call_type="REDACTOR"), "OK"
        )
        self.assertEqual(
            post.call_args_list[0].kwargs["json"]["max_tokens"],
            post.call_args_list[1].kwargs["json"]["max_tokens"]
        )


if __name__ == "__main__":
    unittest.main()
