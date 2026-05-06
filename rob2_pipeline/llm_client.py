import time
from collections import deque

import httpx
from dotenv import load_dotenv
from langchain_openrouter import ChatOpenRouter
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


class RateLimiter:
    """Proactive rate limiter: 20 req/min, 200 req/day."""

    def __init__(self, rpm: int = 18, rpd: int = 190):
        self.rpm = rpm
        self.rpd = rpd
        self.minute_calls: deque[float] = deque()
        self.day_calls: deque[float] = deque()

    def wait_if_needed(self):
        now = time.time()
        self.minute_calls = deque(t for t in self.minute_calls if now - t < 60)
        self.day_calls = deque(t for t in self.day_calls if now - t < 86400)

        if len(self.day_calls) >= self.rpd:
            sleep_time = 86400 - (now - self.day_calls[0]) + 1
            print(f"Daily limit approached. Sleeping {sleep_time:.0f}s")
            time.sleep(sleep_time)

        if len(self.minute_calls) >= self.rpm:
            sleep_time = 60 - (now - self.minute_calls[0]) + 1
            time.sleep(sleep_time)

        self.minute_calls.append(time.time())
        self.day_calls.append(time.time())


_rate_limiter = RateLimiter()


def get_llm(model: str = "openai/gpt-oss-120b:free") -> ChatOpenRouter:
    load_dotenv()
    return ChatOpenRouter(
        model=model,
        temperature=0,
        max_tokens=2000,
    )


@retry(
    wait=wait_exponential(multiplier=2, min=5, max=120),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type((httpx.HTTPStatusError, Exception)),
)
def call_llm(llm: ChatOpenRouter, messages: list, node_name: str = "") -> str:
    _rate_limiter.wait_if_needed()
    response = llm.invoke(messages)
    return response.content
