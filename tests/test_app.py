import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import main


class CodeMentorAPITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(main.app)

    def test_homepage_renders(self) -> None:
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("CodeMentor", response.text)

    def test_chat_endpoint_success(self) -> None:
        payload = {
            "message": "O que é uma variável?",
            "history": [
                {"role": "user", "content": "Oi!"},
                {"role": "assistant", "content": "Olá, como posso ajudar?"},
            ],
        }

        with patch("main._call_ollama", return_value="Uma variável armazena valores na memória."):
            response = self.client.post("/api/chat", json=payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["response"], "Uma variável armazena valores na memória.")

    def test_chat_endpoint_validation_error(self) -> None:
        response = self.client.post("/api/chat", json={"message": ""})
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
