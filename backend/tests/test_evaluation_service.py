"""
Unit tests for EvaluationService functions and recommendation logic.
Verifies correctness gating, alternating probe benchmarking, deterministic recommendations,
and error handling.
"""

import pytest
from unittest.mock import MagicMock, patch

from app.schemas.evaluation import EvaluationRequest
from app.services.evaluation_service import determine_recommendation, run_evaluation
from app.schemas.equivalence import CompareResultsResponse


def test_recommendation_when_correctness_different():
    perf, rec, rat = determine_recommendation(
        correctness_status="different",
        is_complete_comparison=True,
        original_median_ms=10.0,
        candidate_median_ms=5.0,
        percentage_improvement=50.0,
        mismatch_reason="Row 0 differs in values: id (1 != 2)",
    )
    assert rec == "do_not_recommend"
    assert perf == "inconclusive"
    assert "different" in rat.lower()


def test_recommendation_when_correctness_rejected():
    perf, rec, rat = determine_recommendation(
        correctness_status="rejected",
        is_complete_comparison=False,
        original_median_ms=10.0,
        candidate_median_ms=5.0,
        percentage_improvement=50.0,
        error_message="Prohibited statement",
    )
    assert rec == "do_not_recommend"
    assert perf == "inconclusive"
    assert "safety" in rat.lower() or "rejected" in rat.lower()


def test_recommendation_when_correctness_inconclusive():
    perf, rec, rat = determine_recommendation(
        correctness_status="inconclusive",
        is_complete_comparison=False,
        original_median_ms=10.0,
        candidate_median_ms=5.0,
        percentage_improvement=50.0,
        mismatch_reason="Row limit reached",
    )
    assert rec == "insufficient_evidence"
    assert perf == "inconclusive"
    assert "not be completely established" in rat.lower() or "inconclusive" in rat.lower()


def test_recommendation_when_no_benchmark_successes():
    perf, rec, rat = determine_recommendation(
        correctness_status="validated",
        is_complete_comparison=True,
        original_median_ms=None,
        candidate_median_ms=None,
        percentage_improvement=None,
    )
    assert rec == "insufficient_evidence"
    assert perf == "inconclusive"
    assert "insufficient" in rat.lower()


def test_recommendation_when_candidate_faster():
    perf, rec, rat = determine_recommendation(
        correctness_status="validated",
        is_complete_comparison=True,
        original_median_ms=100.0,
        candidate_median_ms=50.0,
        percentage_improvement=50.0,
    )
    assert rec == "recommend_candidate"
    assert perf == "faster"
    assert "improvement" in rat.lower() or "faster" in rat.lower()


def test_recommendation_when_candidate_faster_sub_millisecond():
    perf, rec, rat = determine_recommendation(
        correctness_status="validated",
        is_complete_comparison=True,
        original_median_ms=0.8,
        candidate_median_ms=0.4,
        percentage_improvement=50.0,
    )
    assert rec == "recommend_candidate"
    assert perf == "faster"
    assert "under 1ms" in rat.lower() or "modest" in rat.lower()


def test_recommendation_when_candidate_slower():
    perf, rec, rat = determine_recommendation(
        correctness_status="validated",
        is_complete_comparison=True,
        original_median_ms=50.0,
        candidate_median_ms=75.0,
        percentage_improvement=-50.0,
    )
    assert rec == "keep_original"
    assert perf == "slower"
    assert "slower" in rat.lower()


def test_recommendation_when_candidate_similar():
    perf, rec, rat = determine_recommendation(
        correctness_status="validated",
        is_complete_comparison=True,
        original_median_ms=50.0,
        candidate_median_ms=51.0,
        percentage_improvement=-2.0,
    )
    assert rec == "insufficient_evidence"
    assert perf == "similar"
    assert "within" in rat.lower() or "tolerance" in rat.lower()


def test_run_evaluation_halts_on_different_results():
    """Verify that if equivalence validation returns different results, benchmarking is never performed."""
    mock_db = MagicMock()

    diff_equiv = CompareResultsResponse(
        status="different",
        matched=False,
        original_row_count=1,
        candidate_row_count=1,
        is_complete_comparison=True,
        row_limit_applied=1000,
        order_deterministic=True,
        ordering_mode="ordered",
        mismatch_reason="Row 0 differs in values: id (1 != 2)",
    )

    with patch("app.services.evaluation_service.compare_query_results", return_value=diff_equiv) as mock_compare, \
         patch("app.services.evaluation_service.execute_single_run") as mock_exec:
        
        resp = run_evaluation(
            db=mock_db,
            original_sql="SELECT id, first_name FROM users WHERE id = 1;",
            candidate_sql="SELECT id, first_name FROM users WHERE id = 2;",
            confirmed=True,
            repetitions=3,
        )
        
        mock_compare.assert_called_once()
        mock_exec.assert_not_called()
        assert resp.correctness_status == "different"
        assert resp.recommendation == "do_not_recommend"
        assert resp.performance_assessment == "inconclusive"
        assert len(resp.original_runs) == 0
        assert len(resp.candidate_runs) == 0


def test_run_evaluation_halts_on_inconclusive_results():
    """Verify that if equivalence validation is inconclusive (e.g. row limit reached), benchmarking is skipped."""
    mock_db = MagicMock()

    inconclusive_equiv = CompareResultsResponse(
        status="inconclusive",
        matched=False,
        original_row_count=1000,
        candidate_row_count=1000,
        is_complete_comparison=False,
        row_limit_applied=1000,
        order_deterministic=True,
        ordering_mode="ordered",
        mismatch_reason="Bounded row limit of 1000 rows was reached. Formal equivalence cannot be verified beyond this limit.",
    )

    with patch("app.services.evaluation_service.compare_query_results", return_value=inconclusive_equiv), \
         patch("app.services.evaluation_service.execute_single_run") as mock_exec:
        
        resp = run_evaluation(
            db=mock_db,
            original_sql="SELECT id FROM users;",
            candidate_sql="SELECT id FROM users;",
            confirmed=True,
            repetitions=3,
        )
        
        mock_exec.assert_not_called()
        assert resp.correctness_status == "inconclusive"
        assert resp.recommendation == "insufficient_evidence"
        assert resp.performance_assessment == "inconclusive"
