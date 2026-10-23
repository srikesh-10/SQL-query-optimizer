import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String,
    Integer,
    Float,
    Text,
    Boolean,
    DateTime,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Evaluation(Base):
    """
    Stores structured evaluations comparing an original SQL query with a proposed rewrite
    across correctness, performance, and deterministic recommendation.
    """
    __tablename__ = "evaluations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    original_sql: Mapped[str] = mapped_column(Text, nullable=False)
    candidate_sql: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # 1. Correctness Dimension
    correctness_status: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'validated', 'different', 'inconclusive', 'rejected'
    is_complete_comparison: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    original_row_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    candidate_row_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # 2. Performance Dimension
    original_median_execution_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    candidate_median_execution_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    runtime_difference_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    percentage_improvement: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    original_total_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    candidate_total_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    performance_assessment: Mapped[str] = mapped_column(
        String(50), nullable=False, default="inconclusive"
    )  # 'faster', 'similar', 'slower', 'inconclusive'

    # 3. Recommendation Dimension
    recommendation: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'recommend_candidate', 'keep_original', 'do_not_recommend', 'insufficient_evidence'
    recommendation_rationale: Mapped[str] = mapped_column(Text, nullable=False)

    # Benchmark reference IDs and repetition stats
    original_benchmark_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    candidate_benchmark_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    requested_repetitions: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    successful_runs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_runs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<Evaluation id={self.id} correctness={self.correctness_status} "
            f"recommendation={self.recommendation}>"
        )
