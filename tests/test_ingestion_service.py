import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, IngestionStatus, Problem
from app.interfaces.embedding import EmbeddingProvider
from app.interfaces.llm import LLMProvider
from app.interfaces.vector_store import VectorRecord, VectorStore
from app.services.ingestion_service import IngestionService


class FakeLLM(LLMProvider):
    async def generate_summary(self, problem_text, constraints=""):
        return "Summary of " + problem_text


class FailingLLM(LLMProvider):
    async def generate_summary(self, problem_text, constraints=""):
        raise RuntimeError("LLM unavailable")


class FakeEmbedder(EmbeddingProvider):
    async def embed_text(self, text):
        return [0.1, 0.2, 0.3]

    async def embed_batch(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]


class FakeVectorStore(VectorStore):
    def __init__(self):
        self.records = []

    async def upsert(self, records):
        self.records.extend(records)

    async def search(self, query_vector, top_k=10):
        return []


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    yield db
    db.close()


def add_problem(db, statement="Some statement", constraints="N <= 100"):
    problem = Problem(
        platform="cses",
        problem_id="two-sum",
        title="Two Sum",
        url="https://example.com/two-sum",
        statement=statement,
        constraints=constraints,
    )
    db.add(problem)
    db.commit()
    return problem


@pytest.mark.asyncio
async def test_run_batch_marks_completed_and_upserts(db_session):
    problem = add_problem(db_session)
    store = FakeVectorStore()
    service = IngestionService(
        llm=FakeLLM(), embedder=FakeEmbedder(), vector_store=store
    )

    processed = await service.run_batch(db_session, limit=10)

    assert processed == 1
    db_session.refresh(problem)
    assert problem.status == IngestionStatus.COMPLETED
    assert problem.summary == "Summary of Some statement"
    assert len(store.records) == 1
    record = store.records[0]
    assert record.id == str(problem.id)
    assert record.document == problem.summary
    assert record.metadata["title"] == "Two Sum"


@pytest.mark.asyncio
async def test_run_batch_marks_failed_on_error(db_session):
    problem = add_problem(db_session)
    store = FakeVectorStore()
    service = IngestionService(
        llm=FailingLLM(), embedder=FakeEmbedder(), vector_store=store
    )

    processed = await service.run_batch(db_session, limit=10)

    assert processed == 0
    db_session.refresh(problem)
    assert problem.status == IngestionStatus.FAILED
    assert problem.error_message == "LLM unavailable"
    assert store.records == []


@pytest.mark.asyncio
async def test_run_batch_skips_completed_problems(db_session):
    add_problem(db_session)  # pending
    done = Problem(
        platform="cses",
        problem_id="done",
        title="Done",
        url="https://example.com/done",
        statement="Already ingested.",
        status=IngestionStatus.COMPLETED,
    )
    db_session.add(done)
    db_session.commit()

    store = FakeVectorStore()
    service = IngestionService(
        llm=FakeLLM(), embedder=FakeEmbedder(), vector_store=store
    )

    processed = await service.run_batch(db_session, limit=10)

    assert processed == 1
    assert len(store.records) == 1