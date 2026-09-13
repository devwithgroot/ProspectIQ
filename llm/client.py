import os

import httpx
from dotenv import load_dotenv


load_dotenv()


class LLMClient:
    def __init__(self):
        self.base_url = os.getenv("MLX_BASE_URL")
        self.model = os.getenv("MLX_MODEL")

        if not self.base_url:
            raise ValueError("MLX_BASE_URL is not configured")

        if not self.model:
            raise ValueError("MLX_MODEL is not configured")

    def generate(
        self,
        prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 500,
    ) -> str:

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        response = httpx.post(
            f"{self.base_url}/v1/chat/completions",
            json=payload,
            timeout=120,
        )

        response.raise_for_status()

        data = response.json()

        return data["choices"][0]["message"]["content"]