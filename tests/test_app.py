import os
import unittest
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
import requests

# Använd en testkonfiguration och aldrig produktionswebhooks vid import.
os.environ["DISCORD_WEBHOOKS"] = '{"general":"https://example.invalid/general"}'
os.environ["DISCORD_DEFAULT_CHANNEL"] = "general"
os.environ["DISCORD_WEBHOOK_URL"] = "https://example.invalid/legacy"

import app as proxy  # noqa: E402


class ConfigTests(unittest.TestCase):
    def test_old_env_still_works(self):
        config = proxy.load_webhook_config({"DISCORD_WEBHOOK_URL": "https://example.invalid/legacy"})
        self.assertEqual(config.legacy_url, "https://example.invalid/legacy")
        self.assertEqual(config.webhooks, {})
        self.assertIsNone(config.default_channel)

    def test_named_webhooks_allow_discord_channel_names(self):
        config = proxy.load_webhook_config({
            "DISCORD_WEBHOOKS": '{"general":"https://example.invalid/general","tradera-watch":"https://example.invalid/tradera"}',
            "DISCORD_DEFAULT_CHANNEL": "general",
        })
        self.assertEqual(config.webhooks["tradera-watch"], "https://example.invalid/tradera")

    def test_invalid_json_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "giltig JSON"):
            proxy.load_webhook_config({"DISCORD_WEBHOOKS": "not-json"})

    def test_missing_default_rejected_without_legacy(self):
        with self.assertRaisesRegex(RuntimeError, "DISCORD_DEFAULT_CHANNEL krävs"):
            proxy.load_webhook_config({"DISCORD_WEBHOOKS": '{"general":"https://example.invalid/general"}'})

    def test_unknown_default_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "måste finnas"):
            proxy.load_webhook_config({
                "DISCORD_WEBHOOKS": '{"general":"https://example.invalid/general"}',
                "DISCORD_DEFAULT_CHANNEL": "annat",
            })


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(proxy.app)
        self.config = proxy.load_webhook_config({
            "DISCORD_WEBHOOKS": '{"general":"https://example.invalid/general","tradera-watch":"https://example.invalid/tradera"}',
            "DISCORD_DEFAULT_CHANNEL": "general",
            "DISCORD_WEBHOOK_URL": "https://example.invalid/legacy",
        })
        self.config_patcher = patch.object(proxy, "CONFIG", self.config)
        self.config_patcher.start()
        self.addCleanup(self.config_patcher.stop)

    @patch.object(proxy.requests, "post", return_value=Mock(status_code=204))
    def test_default_channel_when_omitted(self, post):
        result = self.client.post("/send", json={"text": "Hej"})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json(), {"status": "skickat"})
        post.assert_called_once_with("https://example.invalid/general", json={"content": "Hej"}, timeout=10)

    @patch.object(proxy.requests, "post", return_value=Mock(status_code=200))
    def test_explicit_named_channel(self, post):
        result = self.client.post("/send", json={"text": "Ny annons", "kanal": "tradera-watch"})
        self.assertEqual(result.status_code, 200)
        post.assert_called_once_with("https://example.invalid/tradera", json={"content": "Ny annons"}, timeout=10)

    @patch.object(proxy.requests, "post")
    def test_unknown_channel_is_rejected_without_sending(self, post):
        result = self.client.post("/send", json={"text": "Hej", "kanal": "saknas"})
        self.assertEqual(result.status_code, 400)
        post.assert_not_called()

    @patch.object(proxy.requests, "post", return_value=Mock(status_code=429))
    def test_discord_failure(self, post):
        result = self.client.post("/send", json={"text": "Hej"})
        self.assertEqual(result.status_code, 502)

    @patch.object(proxy.requests, "post", side_effect=requests.Timeout("timeout"))
    def test_timeout(self, post):
        result = self.client.post("/send", json={"text": "Hej"})
        self.assertEqual(result.status_code, 502)

    @patch.object(proxy.requests, "post", return_value=Mock(status_code=204))
    def test_legacy_only_fallback(self, post):
        with patch.object(proxy, "CONFIG", proxy.load_webhook_config({"DISCORD_WEBHOOK_URL": "https://example.invalid/legacy"})):
            result = self.client.post("/send", json={"text": "Gammalt anrop"})
        self.assertEqual(result.status_code, 200)
        post.assert_called_once_with("https://example.invalid/legacy", json={"content": "Gammalt anrop"}, timeout=10)

    def test_openapi_kanal_is_optional(self):
        schema = self.client.get("/openapi.json").json()
        message = schema["components"]["schemas"]["Message"]
        self.assertEqual(message["required"], ["text"])
        self.assertIn("kanal", message["properties"])


if __name__ == "__main__":
    unittest.main()
