import pytest
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.benchmark import Benchmark, BenchmarkRun
from app.schemas.benchmark import BenchmarkRunResult
from app.services.benchmark_service import run_benchmark, list_benchmarks, get_benchmark_by_id


@pytest.fixture
def in_memory_db():
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_benchmark_persistence_and_retrieval(in_memory_db):
    # Mock single execution run
    def mock_run(clean_sql, run_order, statement_timeout_ms=3000):
        return BenchmarkRunResult(
            run_order=run_order,
            status="success",
            execution_time_ms=1.23 * run_order,
            planning_time_ms=0.15,
            total_cost=180.0,
            plan_rows=50,
            actual_rows=50,
        )

    with patch("app.services.benchmark_service.execute_single_run", side_effect=mock_run):
        # 1. Run benchmark with 3 repetitions and persist
        created = run_benchmark(
            sql="SELECT * FROM users WHERE id = 1;",
            repetitions=3,
            db=in_memory_db,
        )

        assert created.status == "completed"
        assert created.requested_repetitions == 3
        assert created.successful_runs == 3
        assert created.failed_runs == 0
        assert created.median_execution_time_ms is not None
        assert created.id is not None

        # 2. Retrieve by ID
        fetched = get_benchmark_by_id(in_memory_db, created.id)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.sql == "SELECT * FROM users WHERE id = 1"
        assert len(fetched.runs) == 3
        assert fetched.runs[0].execution_time_ms == 1.23
        assert fetched.runs[1].execution_time_ms == 2.46
        assert fetched.runs[2].execution_time_ms == 3.69

        # 3. List benchmarks
        history = list_benchmarks(in_memory_db, limit=10, offset=0)
        assert history.total == 1
        assert len(history.items) == 1
        assert history.items[0].id == created.id
        assert history.items[0].median_execution_time_ms == created.median_execution_time_ms

        # 4. Non-existent ID returns None
        non_existent = get_benchmark_by_id(in_memory_db, "00000000-0000-0000-0000-000000000000")
        assert non_existent is None
