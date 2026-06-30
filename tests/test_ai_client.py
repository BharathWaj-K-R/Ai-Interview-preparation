import unittest
from unittest.mock import Mock, patch

from interview_app.services.ai_client import AnthropicAIClient, extract_json_payload


class TestAIClient(unittest.TestCase):
    def test_extract_json_payload_from_markdown_block(self):
        payload = extract_json_payload('```json\n{"score": 88}\n```')
        self.assertEqual(payload["score"], 88)

    @patch("interview_app.services.ai_client.anthropic")
    def test_complete_text_calls_anthropic_messages_api(self, anthropic_mock):
        fake_block = Mock(text='[{"question": "Explain Flask.", "topic": "Flask", "difficulty": "medium"}]')
        fake_response = Mock(content=[fake_block])
        fake_client = Mock()
        fake_client.messages.create.return_value = fake_response
        anthropic_mock.Anthropic.return_value = fake_client

        client = AnthropicAIClient(api_key="test-key", model="claude-sonnet-4-6")
        result = client.complete_text("prompt", system="system")

        self.assertIn("Explain Flask", result)
        fake_client.messages.create.assert_called_once()
        call_kwargs = fake_client.messages.create.call_args.kwargs
        self.assertEqual(call_kwargs["model"], "claude-sonnet-4-6")
        self.assertEqual(call_kwargs["messages"][0]["role"], "user")


if __name__ == "__main__":
    unittest.main()
