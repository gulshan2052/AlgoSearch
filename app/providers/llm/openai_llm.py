from openai import AsyncOpenAI

from app.core.prompts import SYSTEM_PROMPT
from app.interfaces.llm import LLMProvider


class OpenAILLM(LLMProvider):

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: str | None = None,
    ):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    async def generate_summary(
        self, problem_text: str, constraints: str = ""
    ) -> str:
        user_content = f"[PROBLEM STATEMENT]\n{problem_text}\n\n[CONSTRAINTS]\n{constraints}"
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.1,
        )
        return response.choices[0].message.content.strip()
