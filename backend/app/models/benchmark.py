import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    String,
    Integer,
    Float,
    Text,
    DateTime,
    ForeignKey,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Benchmark(Base):
    """
    Stores metadata and summary metrics for an explicitly requested query benchmark.
    """
    __tablename__ = "benchmarks"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    sql: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending"
    )  # 'completed', 'partial_failure', 'failed'
    requested_repetitions: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    successful_runs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_runs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    median_execution_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    median_planning_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    estimated_total_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relationships
    runs: Mapped[List["BenchmarkRun"]] = relationship(
        "BenchmarkRun",
        back_populates="benchmark",
        cascade="all, delete-orphan",
        order_by="BenchmarkRun.run_order",
    )

    def __repr__(self) -> str:
        return f"<Benchmark id={self.id} status='{self.status}' median_time={self.median_execution_time_ms}ms>"


class BenchmarkRun(Base):
    """
    Stores metrics for an individual repetition within a benchmark execution.
    """
    __tablename__ = "benchmark_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    benchmark_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("benchmarks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_order: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="success"
    )  # 'success', 'failed', 'timeout'
    execution_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    planning_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    plan_rows: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    actual_rows: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    benchmark: Mapped["Benchmark"] = relationship("Benchmark", back_populates="runs")

    def __repr__(self) -> str:
        return (
            f"<BenchmarkRun benchmark_id={self.benchmark_id} order={self.run_order} "
            f"time={self.execution_time_ms}ms status='{self.status}'>"
        )
