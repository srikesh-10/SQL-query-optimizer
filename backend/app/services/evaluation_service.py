"""
Optimizer Evaluation & Performance Scoring Service.
Coordinates:
1. Correctness validation gate (bounded result equivalence).
2. Fair performance benchmarking with alternating run orders.
3. Transparent, deterministic recommendation engine.
4. History persistence.
"""

import statistics
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.benchmark import Benchmark, BenchmarkRun
from app.models.evaluation import Evaluation
from app.schemas.benchmark import BenchmarkRunResult
from app.schemas.evaluation import (
    EvaluationListResponse,
    EvaluationResponse,
    EvaluationSummary,
)
from app.services.benchmark_service import execute_single_run
from app.services.equivalence_service import compare_query_results

# Documented performance significance threshold (5%)
PERFORMANCE_TOLERANCE_PERCENT = 5.0


def determine_recommendation(
    correctness_status: str,
    is_complete_comparison: bool,
    original_median_ms: Optional[float],
    candidate_median_ms: Optional[float],
    percentage_improvement: Optional[float],
    mismatch_reason: Optional[str] = None,
    error_message: Optional[str] = None,
) -> Tuple[str, str, str]:
    """
    Deterministic recommendation engine:
    Returns (performance_assessment, recommendation, rationale).

    Possible recommendations:
    - 'recommend_candidate'
    - 'keep_original'
    - 'do_not_recommend'
    - 'insufficient_evidence'
    """
    # 1. Correctness Gate Failures
    if correctness_status == "different":
        return (
            "inconclusive",
            "do_not_recommend",
            (
                f"Candidate query produces different results from original query: "
                f"{mismatch_reason or 'Result set divergence detected'}. "
                "Performance benchmarking was aborted to prevent optimizing an incorrect query."
            ),
        )

    if correctness_status == "rejected":
        return (
            "inconclusive",
            "do_not_recommend",
            (
                f"Query rejected by safety validation: "
                f"{mismatch_reason or error_message or 'Unsafe SQL construct detected'}."
            ),
        )

    if correctness_status == "inconclusive" or not is_complete_comparison:
        return (
            "inconclusive",
            "insufficient_evidence",
            (
                f"Result equivalence could not be completely established: "
                f"{mismatch_reason or 'Result comparison was truncated or timed out'}. "
                "A rewrite cannot be recommended without verified semantic correctness."
            ),
        )

    # 2. Performance Assessment (only reached if correctness_status == "validated")
    if original_median_ms is None or candidate_median_ms is None or percentage_improvement is None:
        return (
            "inconclusive",
            "insufficient_evidence",
            "Timing measurements were incomplete or failed. Insufficient evidence to evaluate performance.",
        )

    pct = percentage_improvement
    orig_ms = original_median_ms
    cand_ms = candidate_median_ms

    if pct >= PERFORMANCE_TOLERANCE_PERCENT:
        perf_assessment = "faster"
        rec = "recommend_candidate"
        if orig_ms < 1.0 and cand_ms < 1.0:
            rationale = (
                f"Candidate query executed {pct:.1f}% faster ({orig_ms:.2f}ms vs {cand_ms:.2f}ms) "
                f"with verified result equivalence. Both queries execute under 1ms, so practical "
                "production latency gains may be modest."
            )
        else:
            rationale = (
                f"Candidate query demonstrated a {pct:.1f}% measured runtime improvement "
                f"({orig_ms:.2f}ms vs {cand_ms:.2f}ms) with verified result equivalence."
            )
        return perf_assessment, rec, rationale

    if pct <= -PERFORMANCE_TOLERANCE_PERCENT:
        perf_assessment = "slower"
        rec = "keep_original"
        rationale = (
            f"Candidate query was {abs(pct):.1f}% slower than original query "
            f"({cand_ms:.2f}ms vs {orig_ms:.2f}ms). Keep the original SQL."
        )
        return perf_assessment, rec, rationale

    # Difference is within tolerance (-5% to +5%)
    perf_assessment = "similar"
    rec = "insufficient_evidence"
    rationale = (
        f"Candidate query runtime ({cand_ms:.2f}ms) is within ±{PERFORMANCE_TOLERANCE_PERCENT:.0f}% "
        f"of original ({orig_ms:.2f}ms). There is no demonstrated performance improvement to justify "
        "adopting the rewrite."
    )
    return perf_assessment, rec, rationale


def run_evaluation(
    db: Session,
    original_sql: str,
    candidate_sql: str,
    confirmed: bool,
    repetitions: int = 3,
    row_limit: int = 1000,
) -> EvaluationResponse:
    """
    Executes unified evaluation workflow:
    1. Checks confirmation and validates inputs.
    2. Runs Phase 6 bounded result equivalence validation.
    3. If results diverge or fail safety, stops and marks do_not_recommend.
    4. If validated, runs alternating benchmark probes.
    5. Determines deterministic recommendation and persists evaluation.
    """
    # Bound repetitions
    clamped_reps = max(1, min(int(repetitions), 5))
    evaluation_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    # 1. Require explicit confirmation
    if not confirmed:
        eval_obj = Evaluation(
            id=evaluation_id,
            original_sql=original_sql,
            candidate_sql=candidate_sql,
            created_at=now,
            correctness_status="rejected",
            is_complete_comparison=False,
            performance_assessment="inconclusive",
            recommendation="do_not_recommend",
            recommendation_rationale="Evaluation requires explicit user confirmation before queries can be executed.",
            requested_repetitions=clamped_reps,
            successful_runs=0,
            failed_runs=0,
            error_message="User confirmation not provided.",
        )
        db.add(eval_obj)
        db.commit()
        return EvaluationResponse(
            id=evaluation_id,
            original_sql=original_sql,
            candidate_sql=candidate_sql,
            created_at=now,
            correctness_status="rejected",
            is_complete_comparison=False,
            performance_assessment="inconclusive",
            recommendation="do_not_recommend",
            recommendation_rationale=eval_obj.recommendation_rationale,
            requested_repetitions=clamped_reps,
            successful_runs=0,
            failed_runs=0,
            error_message="User confirmation not provided.",
        )

    # 2. Correctness Gate: Phase 6 Result Equivalence Validation
    equiv_res = compare_query_results(
        original_sql=original_sql,
        candidate_sql=candidate_sql,
        confirmed=True,
        row_limit=row_limit,
    )

    orig_row_count = equiv_res.original_row_count
    cand_row_count = equiv_res.candidate_row_count
    is_complete_comp = equiv_res.is_complete_comparison
    mismatch_detail = equiv_res.mismatch_reason

    # Translate equivalence status to correctness_status
    if equiv_res.status == "equivalent" and is_complete_comp:
        correctness_status = "validated"
    elif equiv_res.status == "different":
        correctness_status = "different"
    elif equiv_res.status == "rejected":
        correctness_status = "rejected"
    else:
        correctness_status = "inconclusive"

    # 3. If Correctness Gate Fails: Stop before benchmarking!
    if correctness_status != "validated":
        perf_assessment, rec, rationale = determine_recommendation(
            correctness_status=correctness_status,
            is_complete_comparison=is_complete_comp,
            original_median_ms=None,
            candidate_median_ms=None,
            percentage_improvement=None,
            mismatch_reason=mismatch_detail,
            error_message=equiv_res.error_message,
        )

        eval_obj = Evaluation(
            id=evaluation_id,
            original_sql=original_sql,
            candidate_sql=candidate_sql,
            created_at=now,
            correctness_status=correctness_status,
            is_complete_comparison=is_complete_comp,
            original_row_count=orig_row_count,
            candidate_row_count=cand_row_count,
            performance_assessment=perf_assessment,
            recommendation=rec,
            recommendation_rationale=rationale,
            requested_repetitions=clamped_reps,
            successful_runs=0,
            failed_runs=0,
            error_message=equiv_res.error_message,
        )
        db.add(eval_obj)
        db.commit()

        return EvaluationResponse(
            id=evaluation_id,
            original_sql=original_sql,
            candidate_sql=candidate_sql,
            created_at=now,
            correctness_status=correctness_status,
            is_complete_comparison=is_complete_comp,
            original_row_count=orig_row_count,
            candidate_row_count=cand_row_count,
            mismatch_reason=mismatch_detail,
            performance_assessment=perf_assessment,
            recommendation=rec,
            recommendation_rationale=rationale,
            requested_repetitions=clamped_reps,
            successful_runs=0,
            failed_runs=0,
            error_message=equiv_res.error_message,
        )

    # 4. Correctness Gate Passed: Proceed to Fair Alternating Benchmarking!
    orig_runs: List[BenchmarkRunResult] = []
    cand_runs: List[BenchmarkRunResult] = []

    for rep in range(1, clamped_reps + 1):
        # Alternate order to reduce cache/warmup bias
        if rep % 2 == 1:
            # Odd repetition: Original first, Candidate second
            run_orig = execute_single_run(original_sql, run_order=rep)
            run_cand = execute_single_run(candidate_sql, run_order=rep)
        else:
            # Even repetition: Candidate first, Original second
            run_cand = execute_single_run(candidate_sql, run_order=rep)
            run_orig = execute_single_run(original_sql, run_order=rep)

        orig_runs.append(run_orig)
        cand_runs.append(run_cand)

    # Compute successful/failed runs and medians
    orig_successful = [r for r in orig_runs if r.status == "success" and r.execution_time_ms is not None]
    cand_successful = [r for r in cand_runs if r.status == "success" and r.execution_time_ms is not None]

    successful_runs_count = min(len(orig_successful), len(cand_successful))
    failed_runs_count = (clamped_reps - len(orig_successful)) + (clamped_reps - len(cand_successful))

    orig_median_ms = (
        round(statistics.median([r.execution_time_ms for r in orig_successful]), 3)
        if orig_successful
        else None
    )
    cand_median_ms = (
        round(statistics.median([r.execution_time_ms for r in cand_successful]), 3)
        if cand_successful
        else None
    )

    # Extract planner costs
    orig_total_cost = next((r.total_cost for r in orig_runs if r.total_cost is not None), None)
    cand_total_cost = next((r.total_cost for r in cand_runs if r.total_cost is not None), None)

    # Calculate runtime difference and percentage improvement
    runtime_diff_ms = None
    percentage_improvement = None
    if orig_median_ms is not None and cand_median_ms is not None:
        runtime_diff_ms = round(orig_median_ms - cand_median_ms, 3)
        if orig_median_ms > 0:
            percentage_improvement = round(
                ((orig_median_ms - cand_median_ms) / orig_median_ms) * 100, 2
            )
        else:
            percentage_improvement = 0.0

    # 5. Recommendation Engine Decision
    perf_assessment, rec, rationale = determine_recommendation(
        correctness_status=correctness_status,
        is_complete_comparison=is_complete_comp,
        original_median_ms=orig_median_ms,
        candidate_median_ms=cand_median_ms,
        percentage_improvement=percentage_improvement,
        mismatch_reason=mismatch_detail,
    )

    # 6. Save Benchmark records for historical continuity
    orig_bench_id = str(uuid.uuid4())
    cand_bench_id = str(uuid.uuid4())

    orig_bench = Benchmark(
        id=orig_bench_id,
        sql=original_sql,
        status="completed" if len(orig_successful) == clamped_reps else "partial_failure",
        requested_repetitions=clamped_reps,
        successful_runs=len(orig_successful),
        failed_runs=clamped_reps - len(orig_successful),
        median_execution_time_ms=orig_median_ms,
        estimated_total_cost=orig_total_cost,
    )
    for r in orig_runs:
        orig_bench.runs.append(
            BenchmarkRun(
                run_order=r.run_order,
                status=r.status,
                execution_time_ms=r.execution_time_ms,
                planning_time_ms=r.planning_time_ms,
                total_cost=r.total_cost,
                plan_rows=r.plan_rows,
                actual_rows=r.actual_rows,
                error_message=r.error_message,
            )
        )
    db.add(orig_bench)

    cand_bench = Benchmark(
        id=cand_bench_id,
        sql=candidate_sql,
        status="completed" if len(cand_successful) == clamped_reps else "partial_failure",
        requested_repetitions=clamped_reps,
        successful_runs=len(cand_successful),
        failed_runs=clamped_reps - len(cand_successful),
        median_execution_time_ms=cand_median_ms,
        estimated_total_cost=cand_total_cost,
    )
    for r in cand_runs:
        cand_bench.runs.append(
            BenchmarkRun(
                run_order=r.run_order,
                status=r.status,
                execution_time_ms=r.execution_time_ms,
                planning_time_ms=r.planning_time_ms,
                total_cost=r.total_cost,
                plan_rows=r.plan_rows,
                actual_rows=r.actual_rows,
                error_message=r.error_message,
            )
        )
    db.add(cand_bench)

    # 7. Persist Evaluation Record
    eval_obj = Evaluation(
        id=evaluation_id,
        original_sql=original_sql,
        candidate_sql=candidate_sql,
        created_at=now,
        correctness_status=correctness_status,
        is_complete_comparison=is_complete_comp,
        original_row_count=orig_row_count,
        candidate_row_count=cand_row_count,
        original_median_execution_time_ms=orig_median_ms,
        candidate_median_execution_time_ms=cand_median_ms,
        runtime_difference_ms=runtime_diff_ms,
        percentage_improvement=percentage_improvement,
        original_total_cost=orig_total_cost,
        candidate_total_cost=cand_total_cost,
        performance_assessment=perf_assessment,
        recommendation=rec,
        recommendation_rationale=rationale,
        original_benchmark_id=orig_bench_id,
        candidate_benchmark_id=cand_bench_id,
        requested_repetitions=clamped_reps,
        successful_runs=successful_runs_count,
        failed_runs=failed_runs_count,
    )
    db.add(eval_obj)
    db.commit()

    return EvaluationResponse(
        id=evaluation_id,
        original_sql=original_sql,
        candidate_sql=candidate_sql,
        created_at=now,
        correctness_status=correctness_status,
        is_complete_comparison=is_complete_comp,
        original_row_count=orig_row_count,
        candidate_row_count=cand_row_count,
        mismatch_reason=mismatch_detail,
        original_median_execution_time_ms=orig_median_ms,
        candidate_median_execution_time_ms=cand_median_ms,
        runtime_difference_ms=runtime_diff_ms,
        percentage_improvement=percentage_improvement,
        original_total_cost=orig_total_cost,
        candidate_total_cost=cand_total_cost,
        performance_assessment=perf_assessment,
        recommendation=rec,
        recommendation_rationale=rationale,
        requested_repetitions=clamped_reps,
        successful_runs=successful_runs_count,
        failed_runs=failed_runs_count,
        original_runs=orig_runs,
        candidate_runs=cand_runs,
        original_benchmark_id=orig_bench_id,
        candidate_benchmark_id=cand_bench_id,
        metadata={
            "performance_tolerance_percent": PERFORMANCE_TOLERANCE_PERCENT,
            "comparison_mode": "alternating_runs",
        },
    )


def list_evaluations(
    db: Session,
    limit: int = 10,
    offset: int = 0,
) -> EvaluationListResponse:
    """Retrieves paginated list of evaluation summaries sorted by creation time descending."""
    clamped_limit = max(1, min(int(limit), 50))
    clamped_offset = max(0, int(offset))

    total = db.scalar(select(func.count(Evaluation.id))) or 0
    records = db.scalars(
        select(Evaluation)
        .order_by(desc(Evaluation.created_at))
        .limit(clamped_limit)
        .offset(clamped_offset)
    ).all()

    items = [
        EvaluationSummary(
            id=r.id,
            original_sql=r.original_sql,
            candidate_sql=r.candidate_sql,
            created_at=r.created_at,
            correctness_status=r.correctness_status,
            is_complete_comparison=r.is_complete_comparison,
            performance_assessment=r.performance_assessment,
            recommendation=r.recommendation,
            original_median_execution_time_ms=r.original_median_execution_time_ms,
            candidate_median_execution_time_ms=r.candidate_median_execution_time_ms,
            percentage_improvement=r.percentage_improvement,
            original_total_cost=r.original_total_cost,
            candidate_total_cost=r.candidate_total_cost,
            recommendation_rationale=r.recommendation_rationale,
        )
        for r in records
    ]

    return EvaluationListResponse(
        items=items,
        total=total,
        limit=clamped_limit,
        offset=clamped_offset,
    )


def get_evaluation_by_id(
    db: Session,
    evaluation_id: str,
) -> Optional[EvaluationResponse]:
    """Retrieves single evaluation by ID, reconstructing individual runs if benchmark records exist."""
    record = db.scalar(select(Evaluation).where(Evaluation.id == evaluation_id))
    if not record:
        return None

    # Retrieve associated benchmark runs if available
    original_runs: List[BenchmarkRunResult] = []
    if record.original_benchmark_id:
        bench_orig = db.scalar(select(Benchmark).where(Benchmark.id == record.original_benchmark_id))
        if bench_orig:
            original_runs = [
                BenchmarkRunResult(
                    run_order=r.run_order,
                    status=r.status,
                    execution_time_ms=r.execution_time_ms,
                    planning_time_ms=r.planning_time_ms,
                    total_cost=r.total_cost,
                    plan_rows=r.plan_rows,
                    actual_rows=r.actual_rows,
                    error_message=r.error_message,
                )
                for r in bench_orig.runs
            ]

    candidate_runs: List[BenchmarkRunResult] = []
    if record.candidate_benchmark_id:
        bench_cand = db.scalar(select(Benchmark).where(Benchmark.id == record.candidate_benchmark_id))
        if bench_cand:
            candidate_runs = [
                BenchmarkRunResult(
                    run_order=r.run_order,
                    status=r.status,
                    execution_time_ms=r.execution_time_ms,
                    planning_time_ms=r.planning_time_ms,
                    total_cost=r.total_cost,
                    plan_rows=r.plan_rows,
                    actual_rows=r.actual_rows,
                    error_message=r.error_message,
                )
                for r in bench_cand.runs
            ]

    return EvaluationResponse(
        id=record.id,
        original_sql=record.original_sql,
        candidate_sql=record.candidate_sql,
        created_at=record.created_at,
        correctness_status=record.correctness_status,
        is_complete_comparison=record.is_complete_comparison,
        original_row_count=record.original_row_count,
        candidate_row_count=record.candidate_row_count,
        original_median_execution_time_ms=record.original_median_execution_time_ms,
        candidate_median_execution_time_ms=record.candidate_median_execution_time_ms,
        runtime_difference_ms=record.runtime_difference_ms,
        percentage_improvement=record.percentage_improvement,
        original_total_cost=record.original_total_cost,
        candidate_total_cost=record.candidate_total_cost,
        performance_assessment=record.performance_assessment,
        recommendation=record.recommendation,
        recommendation_rationale=record.recommendation_rationale,
        requested_repetitions=record.requested_repetitions,
        successful_runs=record.successful_runs,
        failed_runs=record.failed_runs,
        original_runs=original_runs,
        candidate_runs=candidate_runs,
        original_benchmark_id=record.original_benchmark_id,
        candidate_benchmark_id=record.candidate_benchmark_id,
        error_message=record.error_message,
    )
