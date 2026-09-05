from app.db.models import Base, IngestionStatus, Problem
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def test_problem_model_defaults_to_pending():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    problem = Problem(
        platform="codeforces",
        problem_id="158A",
        title="Next Round",
        url="https://codeforces.com/problemset/problem/158/A",
        statement="Some statement text.",
    )
    db.add(problem)
    db.commit()

    fetched = db.query(Problem).first()
    assert fetched.status == IngestionStatus.PENDING
    assert fetched.summary is None
    assert fetched.error_message is None
    assert fetched.id is not None

    db.close()