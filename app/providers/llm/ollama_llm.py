import httpx

from app.core.prompts import build_problem_prompt
from app.interfaces.llm import LLMProvider


class OllamaLLM(LLMProvider):

    def __init__(
        self, base_url: str = "http://localhost:11434", model: str = "llama3"
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def generate_summary(
        self, problem_text: str, constraints: str = ""
    ) -> str:
        prompt = build_problem_prompt(problem_text, constraints)
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
            )
            response.raise_for_status()
            data = response.json()
            return data["response"].strip()
