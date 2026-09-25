import os
import time

import httpx
from dotenv import load_dotenv

from config.research_log import get_logger


load_dotenv()

log = get_logger("llm")


class LLMClient:
    def __init__(self):
        self.base_url = os.getenv("MLX_BASE_URL")
        self.model = os.getenv("MLX_MODEL")
        self.timeout = float(os.getenv("MLX_TIMEOUT", "180"))

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

        url = f"{self.base_url}/v1/chat/completions"
        log.info(
            "MLX start model=%s tokens=%s prompt_chars=%s timeout=%.0fs",
            self.model,
            max_tokens,
            len(prompt),
            self.timeout,
        )
        log.debug("MLX prompt: %s", prompt[:800])
        started = time.perf_counter()
        try:
            response = httpx.post(
                url,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
        except Exception:
            log.exception(
                "MLX failed model=%s url=%s elapsed=%.1fs",
                self.model,
                url,
                time.perf_counter() - started,
            )
            raise

        elapsed = time.perf_counter() - started
        log.info(
            "MLX ok elapsed=%.1fs reply_chars=%s",
            elapsed,
            len(content or ""),
        )
        log.debug("MLX reply: %s", (content or "")[:800])
        return content