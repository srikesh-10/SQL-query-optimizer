"""
Unit tests for Equivalence Service (SQL Rewrite Correctness & Result Equivalence).
Covers column checks, multiset comparisons, duplicate rows, NULL handling,
ordering determinism, truncation handling, and safety rejections.
"""

from decimal import Decimal
import pytest
from unittest.mock import MagicMock, patch
from sqlglot import parse_one
from sqlalchemy.exc import OperationalError, DBAPIError

from app.services.equivalence_service import (
    validate_for_equivalence,
    analyze_query_ordering,
    make_hashable,
    normalize_row,
    evaluate_result_sets,
    compare_query_results,
    EquivalenceValidationError,
)
from app.services.sql_validator import SQLValidationError


def test_make_hashable_and_normalize_row():
    """Verify safe normalization of Decimals, Datetimes, NULLs, and complex types."""
    assert make_hashable(None) is None
    # Arbitrary precision preserved: Decimal is kept exact without float precision loss
    assert make_hashable(Decimal("19.99")) == Decimal("19.99")
    assert make_hashable(Decimal("100000000000000001")) != make_hashable(Decimal("100000000000000002"))
    assert make_hashable(10) == 10
    assert make_hashable("test") == "test"
    # Boolean is distinctly tagged to prevent collision with integers (True == 1, False == 0)
    assert make_hashable(True) == ("__bool__", True)
    assert make_hashable(True) != make_hashable(1)
    assert make_hashable(False) == ("__bool__", False)
    assert make_hashable(False) != make_hashable(0)

    # Test tuple normalization
    raw_row = (1, "Alice", Decimal("45.50"), None)
    norm = normalize_row(raw_row)
    assert norm == (1, "Alice", Decimal("45.50"), None)


def test_analyze_query_ordering():
    """Verify detection of ORDER BY, preservation of asc/desc direction, and joins conservatism."""
    # No ORDER BY
    ast_none = parse_one("SELECT * FROM users;")
    has_order, is_det, cols = analyze_query_ordering(ast_none)
    assert has_order is False
    assert is_det is False
    assert cols == []

    # Non-deterministic ORDER BY (ties can occur on first_name)
    ast_nondet = parse_one("SELECT * FROM users ORDER BY first_name ASC;")
    has_order, is_det, cols = analyze_query_ordering(ast_nondet)
    assert has_order is True
    assert is_det is False
    assert "first_name asc" in cols

    # Deterministic ORDER BY (primary key id is present on single table)
    ast_det = parse_one("SELECT * FROM users ORDER BY id;")
    has_order, is_det, cols = analyze_query_ordering(ast_det)
    assert has_order is True
    assert is_det is True
    assert "id asc" in cols

    # Direction preservation: ASC vs DESC produce distinct clauses
    ast_desc = parse_one("SELECT * FROM users ORDER BY id DESC;")
    _, _, cols_desc = analyze_query_ordering(ast_desc)
    assert cols_desc == ["id desc"]
    assert cols != cols_desc

    # Conservative ordering with Joins: ordering by parent id alone does NOT guarantee determinism
    ast_join = parse_one("SELECT * FROM orders o JOIN order_items oi ON o.id = oi.order_id ORDER BY o.id;")
    has_order_j, is_det_j, _ = analyze_query_ordering(ast_join)
    assert has_order_j is True
    assert is_det_j is False  # Correctly conservative: 1:N relations allow multiple rows per o.id



def test_evaluate_result_sets_identical_ordered():
    """Verify equivalent result for deterministically ordered identical queries."""
    orig_ast = parse_one("SELECT id, name FROM products ORDER BY id;")
    cand_ast = parse_one("SELECT id, name FROM products ORDER BY id;")

    orig_cols = ["id", "name"]
    cand_cols = ["id", "name"]
    rows = [(1, "Widget"), (2, "Gadget")]

    res = evaluate_result_sets(
        orig_cols=orig_cols,
        cand_cols=cand_cols,
        orig_raw_rows=rows,
        cand_raw_rows=rows,
        row_limit=1000,
        orig_ast=orig_ast,
        cand_ast=cand_ast,
    )
    assert res.status == "equivalent"
    assert res.matched is True
    assert res.is_complete_comparison is True
    assert res.order_deterministic is True
    assert res.ordering_mode == "ordered"
    assert res.original_row_count == 2
    assert res.candidate_row_count == 2


def test_evaluate_result_sets_unordered_multiset_with_duplicates():
    """Verify that multiset comparison accurately detects duplicate-row count differences."""
    orig_ast = parse_one("SELECT user_id FROM orders;")
    cand_ast = parse_one("SELECT user_id FROM orders;")

    orig_cols = ["user_id"]
    cand_cols = ["user_id"]

    # Query 1 has duplicate user_id 1 (two occurrences)
    orig_rows = [(1,), (1,), (2,)]
    # Query 2 only has one occurrence of user_id 1 (deduplicated or different)
    cand_rows = [(1,), (2,)]

    res = evaluate_result_sets(
        orig_cols=orig_cols,
        cand_cols=cand_cols,
        orig_raw_rows=orig_rows,
        cand_raw_rows=cand_rows,
        row_limit=1000,
        orig_ast=orig_ast,
        cand_ast=cand_ast,
    )
    # Multiset detects row count mismatch (3 vs 2)
    assert res.status == "different"
    assert res.matched is False
    assert "Row count mismatch" in res.mismatch_reason


def test_evaluate_result_sets_multiset_same_count_different_values():
    """Verify that multiset comparison detects different row contents even if counts match."""
    orig_ast = parse_one("SELECT status FROM orders;")
    cand_ast = parse_one("SELECT status FROM orders;")

    orig_cols = ["status"]
    cand_cols = ["status"]

    orig_rows = [("completed",), ("pending",)]
    cand_rows = [("completed",), ("cancelled",)]

    res = evaluate_result_sets(
        orig_cols=orig_cols,
        cand_cols=cand_cols,
        orig_raw_rows=orig_rows,
        cand_raw_rows=cand_rows,
        row_limit=1000,
        orig_ast=orig_ast,
        cand_ast=cand_ast,
    )
    assert res.status == "different"
    assert res.matched is False
    assert "Row multiset mismatch" in res.mismatch_reason


def test_evaluate_result_sets_column_mismatch():
    """Verify that column count or name mismatch returns different status."""
    orig_ast = parse_one("SELECT id, email, first_name FROM users;")
    cand_ast = parse_one("SELECT id, email FROM users;")

    orig_cols = ["id", "email", "first_name"]
    cand_cols = ["id", "email"]
    orig_rows = [(1, "test@example.com", "Test")]
    cand_rows = [(1, "test@example.com")]

    res = evaluate_result_sets(
        orig_cols=orig_cols,
        cand_cols=cand_cols,
        orig_raw_rows=orig_rows,
        cand_raw_rows=cand_rows,
        row_limit=1000,
        orig_ast=orig_ast,
        cand_ast=cand_ast,
    )
    assert res.status == "different"
    assert res.matched is False
    assert res.column_compatibility.counts_match is False
    assert "Column count mismatch" in res.mismatch_reason


def test_evaluate_result_sets_null_values():
    """Verify that NULL values match NULL, and do not falsely match empty strings or numbers."""
    orig_ast = parse_one("SELECT id, last_name FROM users;")
    cand_ast = parse_one("SELECT id, last_name FROM users;")

    orig_cols = ["id", "last_name"]
    cand_cols = ["id", "last_name"]

    # Both have NULL
    res_both_null = evaluate_result_sets(
        orig_cols=orig_cols,
        cand_cols=cand_cols,
        orig_raw_rows=[(1, None)],
        cand_raw_rows=[(1, None)],
        row_limit=1000,
        orig_ast=orig_ast,
        cand_ast=cand_ast,
    )
    assert res_both_null.status == "equivalent"
    assert res_both_null.matched is True

    # One NULL, one empty string
    res_null_vs_empty = evaluate_result_sets(
        orig_cols=orig_cols,
        cand_cols=cand_cols,
        orig_raw_rows=[(1, None)],
        cand_raw_rows=[(1, "")],
        row_limit=1000,
        orig_ast=orig_ast,
        cand_ast=cand_ast,
    )
    assert res_null_vs_empty.status == "different"
    assert res_null_vs_empty.matched is False


def test_evaluate_result_sets_truncation_returns_inconclusive():
    """Verify that when queries exceed the row limit, status is inconclusive (never equivalent)."""
    orig_ast = parse_one("SELECT id FROM users;")
    cand_ast = parse_one("SELECT id FROM users;")

    orig_cols = ["id"]
    cand_cols = ["id"]

    # 10 rows fetched, but row_limit is 5 (so row 6+ signals truncation)
    orig_rows = [(i,) for i in range(10)]
    cand_rows = [(i,) for i in range(10)]

    res = evaluate_result_sets(
        orig_cols=orig_cols,
        cand_cols=cand_cols,
        orig_raw_rows=orig_rows,
        cand_raw_rows=cand_rows,
        row_limit=5,
        orig_ast=orig_ast,
        cand_ast=cand_ast,
    )
    assert res.status == "inconclusive"
    assert res.matched is None
    assert res.is_complete_comparison is False
    assert "maximum row limit" in res.mismatch_reason.lower()


def test_safety_validation_rejects_dangerous_and_unsupported():
    """Verify that DDL, DML, multiple statements, dangerous functions, and foreign tables are rejected."""
    # Write statement
    with pytest.raises(SQLValidationError):
        validate_for_equivalence("UPDATE users SET is_active = false;")

    # Multiple statements
    with pytest.raises(SQLValidationError):
        validate_for_equivalence("SELECT * FROM users; DELETE FROM orders;")

    # Dangerous function
    with pytest.raises(EquivalenceValidationError) as exc:
        validate_for_equivalence("SELECT pg_sleep(5);")
    assert "pg_sleep" in str(exc.value)

    # System catalog access
    with pytest.raises(EquivalenceValidationError) as exc:
        validate_for_equivalence("SELECT * FROM pg_class;")
    assert "catalog" in str(exc.value).lower()

    # Unsupported table outside e-commerce scope
    with pytest.raises(EquivalenceValidationError) as exc:
        validate_for_equivalence("SELECT * FROM non_existent_secret_table;")
    assert "unsupported table" in str(exc.value).lower()


def test_compare_query_results_requires_confirmation():
    """Verify that unconfirmed comparison requests are safely rejected."""
    res = compare_query_results(
        original_sql="SELECT * FROM users;",
        candidate_sql="SELECT id FROM users;",
        confirmed=False,
    )
    assert res.status == "rejected"
    assert "confirmation" in res.mismatch_reason.lower()


def test_compare_query_results_timeout_simulation():
    """Verify that statement timeout returns inconclusive status."""
    mock_conn = MagicMock()
    mock_conn.dialect.name = "postgresql"
    mock_conn.execute.side_effect = OperationalError(
        "canceling statement due to statement timeout", None, None
    )

    res = compare_query_results(
        original_sql="SELECT * FROM users;",
        candidate_sql="SELECT * FROM users;",
        confirmed=True,
        conn=mock_conn,
    )
    assert res.status == "inconclusive"
    assert res.matched is None
    assert "timed out" in res.mismatch_reason.lower()


def test_make_hashable_prevents_decimal_float_precision_collision():
    """Verify that high-precision Decimals do not falsely match due to float conversion loss."""
    orig_ast = parse_one("SELECT total FROM orders;")
    cand_ast = parse_one("SELECT total FROM orders;")
    # These two Decimals have identical float(val) representation (1e+17) but different values
    d1 = Decimal("100000000000000001")
    d2 = Decimal("100000000000000002")

    res = evaluate_result_sets(
        orig_cols=["total"],
        cand_cols=["total"],
        orig_raw_rows=[(d1,)],
        cand_raw_rows=[(d2,)],
        row_limit=1000,
        orig_ast=orig_ast,
        cand_ast=cand_ast,
    )
    assert res.status == "different"
    assert res.matched is False


def test_make_hashable_prevents_boolean_integer_collision():
    """Verify that booleans and integers do not collide despite Python's True == 1."""
    orig_ast = parse_one("SELECT is_active FROM users;")
    cand_ast = parse_one("SELECT is_active FROM users;")

    res = evaluate_result_sets(
        orig_cols=["is_active"],
        cand_cols=["is_active"],
        orig_raw_rows=[(True,)],
        cand_raw_rows=[(1,)],
        row_limit=1000,
        orig_ast=orig_ast,
        cand_ast=cand_ast,
    )
    assert res.status == "different"
    assert res.matched is False


def test_make_hashable_prevents_date_string_collision():
    """Verify that dates and ISO strings do not collide."""
    from datetime import date
    orig_ast = parse_one("SELECT created_date FROM orders;")
    cand_ast = parse_one("SELECT created_date FROM orders;")

    res = evaluate_result_sets(
        orig_cols=["created_date"],
        cand_cols=["created_date"],
        orig_raw_rows=[(date(2026, 1, 1),)],
        cand_raw_rows=[("2026-01-01",)],
        row_limit=1000,
        orig_ast=orig_ast,
        cand_ast=cand_ast,
    )
    assert res.status == "different"
    assert res.matched is False


def test_ordering_direction_mismatch_prevents_deterministic_sequence_match():
    """Verify that ORDER BY ASC vs ORDER BY DESC is recognized as distinct ordering."""
    orig_ast = parse_one("SELECT id FROM users ORDER BY id ASC;")
    cand_ast = parse_one("SELECT id FROM users ORDER BY id DESC;")

    _, orig_det, orig_cols = analyze_query_ordering(orig_ast)
    _, cand_det, cand_cols = analyze_query_ordering(cand_ast)

    assert orig_det is True
    assert cand_det is True
    assert orig_cols != cand_cols  # ['id asc'] != ['id desc']

