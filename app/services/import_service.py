import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

# Columns copied from the scraped DB (excludes the autoincrement primary key `id`).
PROBLEM_COLUMNS = [
    "platform",
    "problem_id",
    "title",
    "url",
    "statement",
    "constraints",
    "input_format",
    "output_format",
    "status",
    "summary",
    "error_message",
    "created_at",
    "updated_at",
]

REQUIRED_FIELDS = ["platform", "problem_id", "title", "url", "statement"]


class ImportValidationError(Exception):
    """Raised when the uploaded source database is malformed or incompatible."""


class ImportReport(BaseModel):
    source_rows: int
    inserted: int
    skipped_duplicates: int
    skipped_invalid: int
    total_problems: int


class FileImportResult(BaseModel):
    filename: str
    report: ImportReport | None = None
    error: str | None = None


class CatalogImportService:
    """Merges rows from an externally scraped SQLite DB into the catalog's `problems.db`.

    The source is opened read-only. Rows are inserted into the target `problems`
    table keyed on the unique `url` column, so an already-present problem is never
    re-added and existing rows are never overwritten.
    """

    def __init__(self, engine: Engine):
        self.engine = engine

    def import_from_db(self, source_path: str) -> ImportReport:
        rows = self._read_source_rows(source_path)

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        valid_rows, skipped_invalid = self._validate_rows(rows, now)

        inserted, skipped_duplicates = self._insert_rows(valid_rows)

        total_problems = self._count_problems()

        return ImportReport(
            source_rows=len(rows),
            inserted=inserted,
            skipped_duplicates=skipped_duplicates,
            skipped_invalid=skipped_invalid,
            total_problems=total_problems,
        )

    def import_from_dir(
        self, source_dir: str, filename: str | None = None
    ) -> list[FileImportResult]:
        """Imports every ``*.db`` file in ``source_dir`` (or just ``filename``).

        Files are never deleted or modified; each one is processed independently,
        so an invalid file is reported in its own result without blocking the rest.
        """
        import_paths = self._find_source_files(source_dir, filename)
        results: list[FileImportResult] = []
        for path in import_paths:
            try:
                report = self.import_from_db(str(path))
                results.append(
                    FileImportResult(filename=path.name, report=report)
                )
            except Exception as exc:
                logger.warning("Skipped import of %s: %s", path.name, exc)
                results.append(
                    FileImportResult(filename=path.name, error=str(exc))
                )
        return results

    @staticmethod
    def _find_source_files(
        source_dir: str, filename: str | None = None
    ) -> list[Path]:
        directory = Path(source_dir)
        if filename:
            path = directory / filename
            if not path.is_file():
                raise ImportValidationError(
                    f"No such file in import directory: {filename}"
                )
            return [path]
        if not directory.is_dir():
            raise ImportValidationError(
                f"Import directory does not exist: {directory}"
            )
        files = sorted(directory.glob("*.db"))
        if not files:
            raise ImportValidationError(
                f"No '.db' files found in import directory: {directory}"
            )
        return files

    def _read_source_rows(self, source_path: str) -> list[tuple]:
        path = Path(source_path).resolve()
        src = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            table = src.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='problems'"
            ).fetchone()
            if table is None:
                raise ImportValidationError(
                    "The uploaded file is not a valid catalog database: the 'problems' table is missing."
                )

            cols = [row[1] for row in src.execute("PRAGMA table_info(problems)")]
            missing = [c for c in PROBLEM_COLUMNS if c not in cols]
            if missing:
                raise ImportValidationError(
                    "The uploaded 'problems' table is missing required columns: "
                    f"{', '.join(missing)}. Expected columns: {', '.join(PROBLEM_COLUMNS)}."
                )

            select = ", ".join(PROBLEM_COLUMNS)
            return src.execute(f"SELECT {select} FROM problems").fetchall()
        finally:
            src.close()

    @staticmethod
    def _validate_rows(
        rows: list[tuple], now: str
    ) -> tuple[list[tuple], int]:
        valid = []
        skipped_invalid = 0
        for row in rows:
            values = dict(zip(PROBLEM_COLUMNS, row))
            if any(
                not (values.get(field) or "").strip() for field in REQUIRED_FIELDS
            ):
                skipped_invalid += 1
                continue

            values["status"] = values.get("status") or "PENDING"
            for field in ("created_at", "updated_at"):
                if not values.get(field):
                    values[field] = now

            valid.append(tuple(values[col] for col in PROBLEM_COLUMNS))
        return valid, skipped_invalid

    def _insert_rows(self, rows: list[tuple]) -> tuple[int, int]:
        if not rows:
            return 0, 0

        cols = ", ".join(PROBLEM_COLUMNS)
        placeholders = ", ".join("?" for _ in PROBLEM_COLUMNS)
        sql = f"INSERT OR IGNORE INTO problems ({cols}) VALUES ({placeholders})"

        inserted = 0
        skipped_duplicates = 0
        raw = self.engine.raw_connection()
        try:
            cursor = raw.cursor()
            for row in rows:
                cursor.execute(sql, row)
                if cursor.rowcount == 1:
                    inserted += 1
                else:
                    skipped_duplicates += 1
            raw.commit()
            logger.info(
                "Merged %d rows from source DB (%d inserted, %d duplicate urls skipped)",
                len(rows), inserted, skipped_duplicates,
            )
        finally:
            raw.close()
        return inserted, skipped_duplicates

    def _count_problems(self) -> int:
        raw = self.engine.raw_connection()
        try:
            cursor = raw.cursor()
            return cursor.execute("SELECT COUNT(*) FROM problems").fetchone()[0]
        finally:
            raw.close()