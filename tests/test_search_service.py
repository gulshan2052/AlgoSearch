import pytest

from app.interfaces.embedding import EmbeddingProvider
from app.interfaces.llm import LLMProvider
from app.interfaces.vector_store import SearchResult, VectorStore
from app.services.search_service import SearchService


class FakeLLM(LLMProvider):
    async def generate_summary(self, problem_text, constraints=""):
        return "Canonical summary for: " + problem_text[:20]


class FakeEmbedder(EmbeddingProvider):
    async def embed_text(self, text):
        return [0.1, 0.2, 0.3]

    async def embed_batch(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]


class FakeVectorStore(VectorStore):
    def __init__(self, results):
        self.results = results
        self.searched = None

    async def upsert(self, records):
        pass

    async def search(self, query_vector, top_k=10):
        self.searched = {"vector": query_vector, "top_k": top_k}
        return self.results


@pytest.mark.asyncio
async def test_find_similar_returns_formatted_matches():
    store = FakeVectorStore(
        [
            SearchResult(
                id="1",
                score=0.93,
                metadata={
                    "platform": "codeforces",
                    "problem_id": "158A",
                    "title": "Next Round",
                    "url": "https://example.com/158A",
                },
                document="Summary text",
            )
        ]
    )
    service = SearchService(
        llm=FakeLLM(), embedder=FakeEmbedder(), vector_store=store
    )

    matches = await service.find_similar(
        "Alice has some weird story input.", constraints="N <= 100", top_k=3
    )

    assert len(matches) == 1
    match = matches[0]
    assert match.title == "Next Round"
    assert match.url == "https://example.com/158A"
    assert match.platform == "codeforces"
    assert match.similarity_score == 0.93
    assert match.summary == "Summary text"


@pytest.mark.asyncio
async def test_find_similar_passes_embedding_and_top_k_to_store():
    store = FakeVectorStore([])
    service = SearchService(
        llm=FakeLLM(), embedder=FakeEmbedder(), vector_store=store
    )

    await service.find_similar("Query statement", top_k=7)

    assert store.searched == {
        "vector": [0.1, 0.2, 0.3],
        "top_k": 7,
    }