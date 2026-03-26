"""Minimal client for DashScope/Qwen API using native SDK."""

import os
import time
from typing import Optional

from dotenv import load_dotenv
import dashscope
from dashscope import Generation

load_dotenv()

dashscope.base_http_api_url = "https://dashscope.aliyuncs.com/api/v1"


class QwenClient:
    """DashScope/Qwen API client with retry and rate limiting."""

    DEFAULT_MODEL = "qwen3-235b-a22b-instruct-2507"
    MAX_RETRIES = 3
    RETRY_DELAY = 5  # seconds
    MIN_INTERVAL = 2  # seconds between calls

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "DASHSCOPE_API_KEY not set. "
                "Set it in .env or as environment variable."
            )
        self.model = model or os.getenv("QWEN_MODEL", self.DEFAULT_MODEL)
        self._last_call_time = 0.0

    def _rate_limit(self):
        """Enforce minimum interval between API calls."""
        elapsed = time.time() - self._last_call_time
        if elapsed < self.MIN_INTERVAL:
            time.sleep(self.MIN_INTERVAL - elapsed)

    def chat(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        """Send chat request with retry logic."""
        self._rate_limit()

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                self._last_call_time = time.time()
                response = Generation.call(
                    api_key=self.api_key,
                    model=self.model,
                    messages=messages,
                    result_format="message",
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                # Extract text from response
                text = response.output.choices[0].message.content
                # Strip <think>...</think> blocks if present (Qwen reasoning)
                import re
                text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
                return text
            except Exception as e:
                last_error = e
                if attempt < self.MAX_RETRIES - 1:
                    wait = self.RETRY_DELAY * (attempt + 1)
                    print(f"  [retry {attempt + 1}/{self.MAX_RETRIES}] {e}, waiting {wait}s...")
                    time.sleep(wait)

        raise RuntimeError(f"API call failed after {self.MAX_RETRIES} retries: {last_error}")
