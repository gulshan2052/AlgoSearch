import httpx

from app.core.prompts import SYSTEM_PROMPT
from app.interfaces.llm import LLMProvider

GEMINI_API_BASE = "https://generativelanguage.googleapis.com"


class GeminiLLM(LLMProvider):

    def __init__(
        self, api_key: str, model: str = "gemini-2.5-flash"
    ):
        self.api_key = api_key
        self.model = model

    async def generate_summary(
        self, problem_text: str, constraints: str = ""
    ) -> str:
        user_content = (
            f"[PROBLEM STATEMENT]\n{problem_text}\n\n"
            f"[CONSTRAINTS]\n{constraints}"
        )
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{GEMINI_API_BASE}/v1beta/models/{self.model}:generateContent",
                headers={"x-goog-api-key": self.api_key},
                json={
                    "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                    "contents": [
                        {"role": "user", "parts": [{"text": user_content}]}
                    ],
                    "generationConfig": {"temperature": 0.1},
                },
            )
            response.raise_for_status()
            data = response.json()
            parts = data["candidates"][0]["content"]["parts"]
            return "".join(part["text"] for part in parts).strip()