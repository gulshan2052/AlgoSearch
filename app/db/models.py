from datetime import datetime
from enum import Enum

from sqlalchemy import Column, DateTime, Enum as SQLEnum, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class IngestionStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Problem(Base):
    __tablename__ = "problems"

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(
        String(50), nullable=False, index=True
    )  # e.g., 'codeforces', 'leetcode', 'cses'
    problem_id = Column(
        String(100), nullable=False, index=True
    )  # e.g., '158A', 'two-sum'
    title = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False, unique=True)
    statement = Column(Text, nullable=False)  # Raw problem text
    constraints = Column(Text, nullable=True)  # Raw constraints
    input_format = Column(Text, nullable=True)
    output_format = Column(Text, nullable=True)

    # Ingestion metadata
    status = Column(
        SQLEnum(IngestionStatus),
        default=IngestionStatus.PENDING,
        nullable=False,
        index=True,
    )
    summary = Column(Text, nullable=True)  # LLM-extracted algorithmic gist
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
