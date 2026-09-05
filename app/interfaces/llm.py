from abc import ABC, abstractmethod


class LLMProvider(ABC):

    @abstractmethod
    async def generate_summary(
        self, problem_text: str, constraints: str = ""
    ) -> str:
        """Extracts the underlying algorithmic essence and removes all lore/story elements."""
        pass
