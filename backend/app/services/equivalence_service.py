"""
SQL Rewrite Correctness & Result Equivalence Validation Service.
Safely executes original and candidate rewritten queries within a read-only,
repeatable-read transaction snapshot, validates column compatibility,
enforces strict row limits, and performs multiset or deterministic ordered comparisons.
"""

from collections import Counter
from datetime import date, datetime, time
from decimal import Decimal
import math
from typing import Any, Dict, List, Optional, Tuple

import sqlglot
from sqlglot import exp
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, OperationalError

from app.db.session import engine
from app.schemas.equivalence import (
    ColumnCompatibility,
    CompareResultsResponse,
)
from app.services.benchmark_service import (
    ALLOWED_BENCHMARK_TABLES,
    FORBIDDEN_BENCHMARK_FUNCTIONS,
)
from app.services.sql_validator import SQLValidationError, validate_read_only_sql


class EquivalenceValidationError(Exception):
    """Raised when an equivalence query fails safety or table-scope checks."""
    def __init__(self, message: str, detail: str = ""):
        super().__init__(message)
        self.message = message
        self.detail = detail


def validate_for_equivalence(raw_sql: str) -> Tuple[str, exp.Expression]:
    """
    Validates that a SQL query is a single-statement read-only SELECT,
    does not access system catalogs or dangerous functions, and queries
    only allowed sample-database tables.
    """
    normalized_sql, parsed_ast = validate_read_only_sql(raw_sql)

    # 1. Reject forbidden functions
    for func_node in parsed_ast.find_all((exp.Anonymous, exp.Func)):
        func_name = func_node.name.lower() if func_node.name else ""
        if func_name in FORBIDDEN_BENCHMARK_FUNCTIONS:
            raise EquivalenceValidationError(
                f"Prohibited function detected: '{func_name}'.",
                "Queries submitted for result equivalence validation cannot call sleep, administrative, or out-of-band functions."
            )

    # 2. Reject system catalogs & non-sample tables
    for table_node in parsed_ast.find_all(exp.Table):
        t_name = table_node.name.lower() if table_node.name else ""
        t_db = table_node.db.lower() if table_node.db else ""
        if t_name.startswith("pg_") or t_db.startswith("pg_") or t_db == "information_schema":
            raise EquivalenceValidationError(
                f"System catalog access prohibited: '{table_node.sql()}'.",
                "Validation queries are restricted to application sample tables (users, products, orders, order_items)."
            )
        if t_name and t_name not in ALLOWED_BENCHMARK_TABLES:
            raise EquivalenceValidationError(
                f"Unsupported table: '{t_name}'.",
                f"Validation queries must operate solely on sample tables: {', '.join(sorted(ALLOWED_BENCHMARK_TABLES))}."
            )

    return normalized_sql, parsed_ast


def analyze_query_ordering(ast: exp.Expression) -> Tuple[bool, bool, List[str]]:
    """
    Inspects AST for ORDER BY clause and determines whether sort is deterministically unique.
    Returns: (has_order_by, is_deterministic, order_column_expressions)

    Hardened to:
    - Preserve order direction (asc/desc) and nulls ordering so queries with different
      order clauses are not mistakenly considered equivalent in sequence.
    - Treat multi-table joins and aggregations conservatively: ordering by a parent primary key
      in a 1:N join does not establish unique row ordering for the joined result set.
    """
    order_node = ast.find(exp.Order)
    if not order_node:
        return False, False, []

    order_clauses = []
    order_column_names = []
    for expr in order_node.expressions:
        if isinstance(expr, exp.Ordered):
            col_name = expr.this.sql().lower()
            is_desc = bool(expr.args.get("desc"))
            direction = "desc" if is_desc else "asc"
            full_clause = f"{col_name} {direction}"
        else:
            col_name = expr.sql().lower()
            full_clause = f"{col_name} asc"
        order_clauses.append(full_clause)
        order_column_names.append(col_name)

    # Conservative determinism check:
    # 1. Joins: In multi-table joins (e.g. orders JOIN order_items), ordering by parent.id alone
    # does NOT guarantee deterministic unique sorting because 1:N relations create multiple rows
    # with the same parent ID. If any joins exist, ordering is treated conservatively as non-deterministic.
    has_joins = bool(ast.find(exp.Join))

    # 2. Aggregations: If GROUP BY is present, grouping can change row cardinality and uniqueness.
    has_group = bool(ast.find(exp.Group))

    # In our single-table sample queries, ordering is deterministically unique if primary key 'id'
    # is among the order columns without multi-table row multiplication or grouping.
    is_deterministic = (
        not has_joins
        and not has_group
        and any(col == "id" or col.endswith(".id") for col in order_column_names)
    )

    return True, is_deterministic, order_clauses


def make_hashable(val: Any) -> Any:
    """
    Recursively normalizes SQL values into deterministic, hashable representations.
    
    Hardened protections:
    - Avoids lossy Decimal-to-float conversions, preserving arbitrary precision.
    - Tags booleans with a distinct marker so that Python's True == 1 / False == 0
      coercion does not produce false positives between boolean and integer columns.
    - Tags dates, datetimes, and times so they do not collide with raw ISO strings.
    - Handles IEEE-754 NaN floats deterministically.
    """
    if val is None:
        return None
    # Booleans are a subclass of int in Python (True == 1, False == 0).
    # We must check and tag boolean before int to prevent cross-type collisions.
    if isinstance(val, bool):
        return ("__bool__", val)
    if isinstance(val, int):
        return val
    if isinstance(val, str):
        return val
    if isinstance(val, Decimal):
        # Keep exact Decimal value. Decimal('10.00') == Decimal('10.0') evaluates to True
        # in Python and hashes identically without precision-losing conversion to float.
        return val
    if isinstance(val, float):
        if math.isnan(val):
            return ("__float_nan__",)
        return val
    # Note: datetime is a subclass of date in Python. Check datetime first.
    if isinstance(val, datetime):
        return ("__datetime__", val.isoformat())
    if isinstance(val, date):
        return ("__date__", val.isoformat())
    if isinstance(val, time):
        return ("__time__", val.isoformat())
    if isinstance(val, (bytes, bytearray, memoryview)):
        return ("__bytes__", bytes(val).hex())
    if isinstance(val, (list, tuple)):
        return tuple(make_hashable(x) for x in val)
    if isinstance(val, dict):
        return tuple(sorted((k, make_hashable(v)) for k, v in val.items()))
    return ("__str__", str(val))


def normalize_row(row: Any) -> Tuple[Any, ...]:
    """Converts a database row into a tuple of hashable values."""
    if isinstance(row, (tuple, list)):
        items = row
    else:
        items = tuple(row)
    return tuple(make_hashable(v) for v in items)


def evaluate_result_sets(
    orig_cols: List[str],
    cand_cols: List[str],
    orig_raw_rows: List[Any],
    cand_raw_rows: List[Any],
    row_limit: int,
    orig_ast: exp.Expression,
    cand_ast: exp.Expression,
) -> CompareResultsResponse:
    """
    Compares two result sets according to column compatibility, row truncation limits,
    ordering determinism, and multiset/ordered value equality.
    """
    # 1. Column Compatibility Check
    orig_col_count = len(orig_cols)
    cand_col_count = len(cand_cols)
    counts_match = orig_col_count == cand_col_count

    # Compare column names case-insensitively in positional order
    names_match = (
        counts_match
        and [c.lower() for c in orig_cols] == [c.lower() for c in cand_cols]
    )
    compatible = counts_match

    col_details = None
    if not counts_match:
        col_details = (
            f"Column count mismatch: original query returns {orig_col_count} columns "
            f"({', '.join(orig_cols)}), candidate query returns {cand_col_count} columns "
            f"({', '.join(cand_cols)})."
        )
    elif not names_match:
        col_details = (
            f"Column name/order difference: original columns are [{', '.join(orig_cols)}], "
            f"candidate columns are [{', '.join(cand_cols)}]."
        )

    col_compat = ColumnCompatibility(
        original_columns=orig_cols,
        candidate_columns=cand_cols,
        counts_match=counts_match,
        names_match=names_match,
        compatible=compatible,
        details=col_details,
    )

    if not counts_match:
        return CompareResultsResponse(
            status="different",
            matched=False,
            original_row_count=min(len(orig_raw_rows), row_limit),
            candidate_row_count=min(len(cand_raw_rows), row_limit),
            is_complete_comparison=False,
            row_limit_applied=row_limit,
            column_compatibility=col_compat,
            order_deterministic=False,
            ordering_mode="none",
            mismatch_reason=col_details,
            metadata={"comparison_phase": "column_schema_check"},
        )

    # 2. Check Truncation against row_limit
    orig_truncated = len(orig_raw_rows) > row_limit
    cand_truncated = len(cand_raw_rows) > row_limit
    is_complete_comparison = not (orig_truncated or cand_truncated)

    orig_rows = [normalize_row(r) for r in orig_raw_rows[:row_limit]]
    cand_rows = [normalize_row(r) for r in cand_raw_rows[:row_limit]]

    orig_count = len(orig_rows)
    cand_count = len(cand_rows)

    # 3. Analyze Ordering Determinism
    orig_has_order, orig_det, orig_order_cols = analyze_query_ordering(orig_ast)
    cand_has_order, cand_det, cand_order_cols = analyze_query_ordering(cand_ast)

    # Both must be deterministically ordered with matching order key
    both_deterministic = orig_det and cand_det and (orig_order_cols == cand_order_cols)

    if both_deterministic:
        order_deterministic = True
        ordering_mode = "ordered"
    else:
        order_deterministic = False
        ordering_mode = "multiset"

    # 4. Compare Row Counts
    if not is_complete_comparison:
        # One or both hit the limit
        if orig_truncated and not cand_truncated:
            return CompareResultsResponse(
                status="different",
                matched=False,
                original_row_count=orig_count,
                candidate_row_count=cand_count,
                is_complete_comparison=False,
                row_limit_applied=row_limit,
                column_compatibility=col_compat,
                order_deterministic=order_deterministic,
                ordering_mode=ordering_mode,
                mismatch_reason=(
                    f"Row count mismatch: original query exceeded the {row_limit} row limit, "
                    f"while candidate query returned only {cand_count} row(s)."
                ),
            )
        if cand_truncated and not orig_truncated:
            return CompareResultsResponse(
                status="different",
                matched=False,
                original_row_count=orig_count,
                candidate_row_count=cand_count,
                is_complete_comparison=False,
                row_limit_applied=row_limit,
                column_compatibility=col_compat,
                order_deterministic=order_deterministic,
                ordering_mode=ordering_mode,
                mismatch_reason=(
                    f"Row count mismatch: candidate query exceeded the {row_limit} row limit, "
                    f"while original query returned only {orig_count} row(s)."
                ),
            )
    else:
        # Complete comparison: exact count equality required
        if orig_count != cand_count:
            return CompareResultsResponse(
                status="different",
                matched=False,
                original_row_count=orig_count,
                candidate_row_count=cand_count,
                is_complete_comparison=True,
                row_limit_applied=row_limit,
                column_compatibility=col_compat,
                order_deterministic=order_deterministic,
                ordering_mode=ordering_mode,
                mismatch_reason=(
                    f"Row count mismatch: original query returned {orig_count} row(s), "
                    f"candidate query returned {cand_count} row(s)."
                ),
            )

    # 5. Row Values Comparison
    has_mismatch = False
    mismatch_detail: Optional[str] = None

    if both_deterministic:
        # Deterministic Ordered Comparison
        for idx, (o_row, c_row) in enumerate(zip(orig_rows, cand_rows)):
            if o_row != c_row:
                has_mismatch = True
                mismatch_detail = (
                    f"Row value or ordering mismatch at row index {idx} "
                    f"(ordered by {', '.join(orig_order_cols)})."
                )
                break
    else:
        # Multiset Comparison (Counter accounts for duplicate rows!)
        orig_counter = Counter(orig_rows)
        cand_counter = Counter(cand_rows)

        if orig_counter != cand_counter:
            has_mismatch = True
            diff_orig = orig_counter - cand_counter
            diff_cand = cand_counter - orig_counter
            missing_in_cand = sum(diff_orig.values())
            extra_in_cand = sum(diff_cand.values())
            mismatch_detail = (
                f"Row multiset mismatch: {missing_in_cand} row(s) in original not matched in candidate; "
                f"{extra_in_cand} row(s) in candidate not matched in original."
            )

    # 6. Resolve Final Status (Handling Truncation)
    if has_mismatch:
        return CompareResultsResponse(
            status="different",
            matched=False,
            original_row_count=orig_count,
            candidate_row_count=cand_count,
            is_complete_comparison=is_complete_comparison,
            row_limit_applied=row_limit,
            column_compatibility=col_compat,
            order_deterministic=order_deterministic,
            ordering_mode=ordering_mode,
            mismatch_reason=mismatch_detail,
        )

    # If rows matched so far, but results were truncated, status MUST be inconclusive!
    if not is_complete_comparison:
        return CompareResultsResponse(
            status="inconclusive",
            matched=None,
            original_row_count=orig_count,
            candidate_row_count=cand_count,
            is_complete_comparison=False,
            row_limit_applied=row_limit,
            column_compatibility=col_compat,
            order_deterministic=order_deterministic,
            ordering_mode=ordering_mode,
            mismatch_reason=(
                f"Comparison reached the maximum row limit of {row_limit} rows without divergence. "
                "Complete semantic equivalence cannot be guaranteed for truncated result sets."
            ),
        )

    # If complete and all rows matched: Equivalent!
    ordering_note = None
    if not both_deterministic:
        if orig_has_order or cand_has_order:
            ordering_note = "Results matched as multisets. ORDER BY is present but not deterministically unique across tied rows."
        else:
            ordering_note = "Results matched as multisets (neither query specifies ORDER BY)."

    return CompareResultsResponse(
        status="equivalent",
        matched=True,
        original_row_count=orig_count,
        candidate_row_count=cand_count,
        is_complete_comparison=True,
        row_limit_applied=row_limit,
        column_compatibility=col_compat,
        order_deterministic=order_deterministic,
        ordering_mode=ordering_mode,
        mismatch_reason=ordering_note,
    )


def compare_query_results(
    original_sql: str,
    candidate_sql: str,
    confirmed: bool,
    row_limit: int = 1000,
    statement_timeout_ms: int = 3000,
    lock_timeout_ms: int = 1000,
    conn: Optional[Any] = None,
) -> CompareResultsResponse:
    """
    Main entry point: Validates both queries, sets up a repeatable-read snapshot,
    executes both queries, and evaluates their returned results.
    """
    # 0. Confirmation check
    if not confirmed:
        return CompareResultsResponse(
            status="rejected",
            matched=False,
            is_complete_comparison=False,
            row_limit_applied=row_limit,
            order_deterministic=False,
            ordering_mode="none",
            mismatch_reason="Result comparison requires explicit user confirmation before queries can be executed.",
            error_message="User confirmation not provided.",
        )

    # 1. Safety Validation for Original SQL
    try:
        clean_orig_sql, orig_ast = validate_for_equivalence(original_sql)
    except (SQLValidationError, EquivalenceValidationError) as err:
        return CompareResultsResponse(
            status="rejected",
            matched=False,
            is_complete_comparison=False,
            row_limit_applied=row_limit,
            order_deterministic=False,
            ordering_mode="none",
            mismatch_reason=f"Original SQL validation rejected: {err.message if hasattr(err, 'message') else str(err)}",
            error_message=str(err),
        )
    except Exception as err:
        return CompareResultsResponse(
            status="rejected",
            matched=False,
            is_complete_comparison=False,
            row_limit_applied=row_limit,
            order_deterministic=False,
            ordering_mode="none",
            mismatch_reason=f"Original SQL validation failed: {str(err)}",
            error_message=str(err),
        )

    # 2. Safety Validation for Candidate SQL
    try:
        clean_cand_sql, cand_ast = validate_for_equivalence(candidate_sql)
    except (SQLValidationError, EquivalenceValidationError) as err:
        return CompareResultsResponse(
            status="rejected",
            matched=False,
            is_complete_comparison=False,
            row_limit_applied=row_limit,
            order_deterministic=False,
            ordering_mode="none",
            mismatch_reason=f"Candidate SQL validation rejected: {err.message if hasattr(err, 'message') else str(err)}",
            error_message=str(err),
        )
    except Exception as err:
        return CompareResultsResponse(
            status="rejected",
            matched=False,
            is_complete_comparison=False,
            row_limit_applied=row_limit,
            order_deterministic=False,
            ordering_mode="none",
            mismatch_reason=f"Candidate SQL validation failed: {str(err)}",
            error_message=str(err),
        )

    # 3. Database Execution within Transaction Snapshot
    def _execute(connection):
        # Configure PostgreSQL read-only repeatable read snapshot & timeouts
        if connection.dialect.name == "postgresql":
            connection.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
            connection.execute(text(f"SET LOCAL statement_timeout = {int(statement_timeout_ms)}"))
            connection.execute(text(f"SET LOCAL lock_timeout = {int(lock_timeout_ms)}"))

        # Fetch up to row_limit + 1 to detect truncation
        orig_res = connection.execute(text(clean_orig_sql))
        orig_cols = list(orig_res.keys())
        orig_raw_rows = orig_res.fetchmany(row_limit + 1)

        cand_res = connection.execute(text(clean_cand_sql))
        cand_cols = list(cand_res.keys())
        cand_raw_rows = cand_res.fetchmany(row_limit + 1)

        connection.rollback()
        return orig_cols, cand_cols, orig_raw_rows, cand_raw_rows

    try:
        if conn is not None:
            orig_cols, cand_cols, orig_raw_rows, cand_raw_rows = _execute(conn)
        else:
            with engine.connect() as connection:
                orig_cols, cand_cols, orig_raw_rows, cand_raw_rows = _execute(connection)

    except OperationalError as err:
        err_str = str(err).lower()
        if "timeout" in err_str or "canceling statement due to statement timeout" in err_str:
            return CompareResultsResponse(
                status="inconclusive",
                matched=None,
                is_complete_comparison=False,
                row_limit_applied=row_limit,
                order_deterministic=False,
                ordering_mode="none",
                mismatch_reason=f"Query execution timed out after {statement_timeout_ms}ms. Comparison could not complete.",
                error_message="Statement timeout exceeded.",
            )
        return CompareResultsResponse(
            status="rejected",
            matched=False,
            is_complete_comparison=False,
            row_limit_applied=row_limit,
            order_deterministic=False,
            ordering_mode="none",
            mismatch_reason="Database operational error occurred during query execution.",
            error_message="Operational error executing comparison queries.",
        )
    except DBAPIError as err:
        clean_err = str(getattr(err, "orig", str(err))).split("\n")[0]
        return CompareResultsResponse(
            status="rejected",
            matched=False,
            is_complete_comparison=False,
            row_limit_applied=row_limit,
            order_deterministic=False,
            ordering_mode="none",
            mismatch_reason=f"PostgreSQL execution error: {clean_err}",
            error_message=clean_err,
        )
    except Exception as err:
        return CompareResultsResponse(
            status="rejected",
            matched=False,
            is_complete_comparison=False,
            row_limit_applied=row_limit,
            order_deterministic=False,
            ordering_mode="none",
            mismatch_reason=f"Unexpected error executing comparison queries: {str(err)}",
            error_message=str(err),
        )

    # 4. Evaluate Results
    response = evaluate_result_sets(
        orig_cols=orig_cols,
        cand_cols=cand_cols,
        orig_raw_rows=orig_raw_rows,
        cand_raw_rows=cand_raw_rows,
        row_limit=row_limit,
        orig_ast=orig_ast,
        cand_ast=cand_ast,
    )
    response.metadata = {
        "engine": "PostgreSQL",
        "isolation_level": "REPEATABLE READ READ ONLY",
        "statement_timeout_ms": statement_timeout_ms,
        "lock_timeout_ms": lock_timeout_ms,
        "original_sql": clean_orig_sql,
        "candidate_sql": clean_cand_sql,
    }
    return response
