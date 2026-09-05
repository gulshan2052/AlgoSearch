import sqlite3

import pytest
from sqlalchemy import create_engine

from app.db.models import Base, IngestionStatus, Problem
from app.services.import_service import (
    CatalogImportService,
    ImportValidationError,
    PROBLEM_COLUMNS,
)
from sqlalchemy.orm import sessionmaker


def build_source_db(path, rows):
    con = sqlite3.connect(path)
    try:
        cols = ", ".join(f"{c} TEXT" for c in PROBLEM_COLUMNS)
        con.execute(f"CREATE TABLE problems (id INTEGER PRIMARY KEY, {cols})")
        placeholders = ", ".join("?" for _ in PROBLEM_COLUMNS)
        for row in rows:
            assert len(row) == len(PROBLEM_COLUMNS)
            con.execute(
                f"INSERT INTO problems (id, {', '.join(PROBLEM_COLUMNS)}) "
                f"VALUES (?, {placeholders})",
                (None, *row),
            )
        con.commit()
    finally:
        con.close()


def make_row(url, title="Title", platform="cses", status="PENDING", statement="Stmt"):
    return (
        platform,
        "two-sum",
        title,
        url,
        statement,
        None,
        None,
        None,
        status,
        None,
        None,
        "2026-09-05 10:00:00",
        "2026-09-05 10:00:00",
    )


@pytest.fixture
def target_engine(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'problems.db'}")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    existing = Problem(
        platform="codeforces",
        problem_id="158A",
        title="Next Round",
        url="https://codeforces.com/problemset/problem/158/A",
        statement="Original statement.",
        status=IngestionStatus.COMPLETED,
        summary="Existing summary.",
    )
    db.add(existing)
    db.commit()
    existing_id = existing.id
    db.close()
    return engine, existing_id


def test_import_inserts_new_rows_and_skips_duplicates(tmp_path, target_engine):
    engine, existing_id = target_engine
    source = tmp_path / "new_problems.db"
    build_source_db(
        source,
        [
            make_row("https://example.com/new"),
            make_row("https://codeforces.com/problemset/problem/158/A", title="Changed"),
        ],
    )

    report = CatalogImportService(engine).import_from_db(str(source))

    assert report.source_rows == 2
    assert report.inserted == 1
    assert report.skipped_duplicates == 1
    assert report.skipped_invalid == 0
    assert report.total_problems == 2

    Session = sessionmaker(bind=engine)
    db = Session()
    existing = db.query(Problem).filter_by(url="https://codeforces.com/problemset/problem/158/A").one()
    assert existing.status == IngestionStatus.COMPLETED
    assert existing.statement == "Original statement."
    assert existing.summary == "Existing summary."
    assert existing.id == existing_id

    new = db.query(Problem).filter_by(url="https://example.com/new").one()
    assert new.status == IngestionStatus.PENDING
    assert new.id > existing_id
    db.close()


def test_import_counts_invalid_rows_that_miss_required_fields(tmp_path, target_engine):
    engine, _ = target_engine
    source = tmp_path / "new_problems.db"
    bad = list(make_row("https://example.com/no-title"))
    bad[2] = ""  # title empty
    build_source_db(source, [bad])

    report = CatalogImportService(engine).import_from_db(str(source))

    assert report.source_rows == 1
    assert report.inserted == 0
    assert report.skipped_invalid == 1
    assert report.skipped_duplicates == 0
    assert report.total_problems == 1


def test_import_rejects_source_without_problems_table(tmp_path, target_engine):
    engine, _ = target_engine
    source = tmp_path / "empty.db"
    con = sqlite3.connect(source)
    con.execute("CREATE TABLE other (x TEXT)")
    con.commit()
    con.close()

    with pytest.raises(ImportValidationError):
        CatalogImportService(engine).import_from_db(str(source))


def test_import_tolerates_missing_optional_timestamps(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    source = tmp_path / "new_problems.db"
    row = list(make_row("https://example.com/no-ts"))
    row[11] = None
    row[12] = None
    build_source_db(source, [row])

    report = CatalogImportService(engine).import_from_db(str(source))

    assert report.inserted == 1
    assert report.skipped_invalid == 0


def test_import_from_dir_imports_all_db_files_ignoring_others(tmp_path, target_engine):
    engine, _ = target_engine
    src_dir = tmp_path / "imports"
    src_dir.mkdir()
    build_source_db(src_dir / "a.db", [make_row("https://example.com/a")])
    build_source_db(src_dir / "b.db", [make_row("https://example.com/b")])
    (src_dir / "notes.txt").write_text("not a db")

    results = CatalogImportService(engine).import_from_dir(str(src_dir))

    assert [r.filename for r in results] == ["a.db", "b.db"]
    assert all(r.error is None for r in results)
    assert [r.report.inserted for r in results] == [1, 1]
    assert (src_dir / "a.db").is_file()
    assert (src_dir / "b.db").is_file()


def test_import_from_dir_filename_filter(tmp_path, target_engine):
    engine, _ = target_engine
    src_dir = tmp_path / "imports"
    src_dir.mkdir()
    build_source_db(src_dir / "a.db", [make_row("https://example.com/a")])
    build_source_db(src_dir / "b.db", [make_row("https://example.com/b")])

    results = CatalogImportService(engine).import_from_dir(str(src_dir), filename="b.db")

    assert [r.filename for r in results] == ["b.db"]
    assert results[0].report.inserted == 1


def test_import_from_dir_invalid_file_does_not_block_others(tmp_path, target_engine):
    engine, _ = target_engine
    src_dir = tmp_path / "imports"
    src_dir.mkdir()
    build_source_db(src_dir / "good.db", [make_row("https://example.com/good")])
    bad = sqlite3.connect(src_dir / "bad.db")
    bad.execute("CREATE TABLE other (x TEXT)")
    bad.commit()
    bad.close()

    results = CatalogImportService(engine).import_from_dir(str(src_dir))

    by_name = {r.filename: r for r in results}
    assert by_name["good.db"].report is not None
    assert by_name["good.db"].report.inserted == 1
    assert by_name["bad.db"].report is None
    assert "problems" in by_name["bad.db"].error


def test_import_from_dir_missing_filename_raises(tmp_path, target_engine):
    engine, _ = target_engine
    src_dir = tmp_path / "imports"
    src_dir.mkdir()

    with pytest.raises(ImportValidationError, match="No such file"):
        CatalogImportService(engine).import_from_dir(str(src_dir), filename="nope.db")


def test_import_from_dir_empty_dir_raises(tmp_path, target_engine):
    engine, _ = target_engine
    src_dir = tmp_path / "imports"
    src_dir.mkdir()

    with pytest.raises(ImportValidationError, match="No '.db' files"):
        CatalogImportService(engine).import_from_dir(str(src_dir))


def test_import_from_dir_missing_dir_raises(tmp_path, target_engine):
    engine, _ = target_engine

    with pytest.raises(ImportValidationError, match="does not exist"):
        CatalogImportService(engine).import_from_dir(str(tmp_path / "gone"))