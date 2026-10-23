"""
Safe PostgreSQL Execution-Plan Inspection Service.
Executes EXPLAIN (FORMAT JSON, COSTS TRUE, VERBOSE FALSE) inside a read-only transaction.
Never executes EXPLAIN ANALYZE or raw user write queries.
"""

from typing import Dict, Any, List
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, OperationalError, TimeoutError

from app.db.session import engine


class ExplainServiceError(Exception):
    """Exception raised during explain plan execution."""
    def __init__(self, message: str, status_code: int = 500, detail: str = ""):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.detail = detail


def get_execution_plan(validated_sql: str, statement_timeout_ms: int = 3000) -> Dict[str, Any]:
    """
    Executes EXPLAIN on the validated read-only SELECT query within a transaction-scoped,
    read-only PostgreSQL connection with strict timeout limits.

    Args:
        validated_sql: Normalized, safe SELECT SQL query string.
        statement_timeout_ms: Execution plan timeout limit in milliseconds.

    Returns:
        The raw JSON query plan dictionary returned by PostgreSQL.

    Raises:
        ExplainServiceError: If PostgreSQL fails, times out, or cannot produce a plan.
    """
    # Defensive check: ensure no leading semicolons or multiline injections
    clean_sql = validated_sql.strip().rstrip(";")

    explain_command = f"EXPLAIN (FORMAT JSON, COSTS TRUE, VERBOSE FALSE) {clean_sql}"

    try:
        with engine.connect() as conn:
            # Set read-only transaction and statement timeout for safety
            conn.execute(text("SET TRANSACTION READ ONLY"))
            conn.execute(text(f"SET LOCAL statement_timeout = {int(statement_timeout_ms)}"))

            result = conn.execute(text(explain_command))
            plan_rows = result.fetchall()

            # Cleanly rollback read-only transaction
            conn.rollback()

            if not plan_rows:
                raise ExplainServiceError(
                    "PostgreSQL returned an empty execution plan.",
                    status_code=500,
                    detail="No plan records returned by EXPLAIN command."
                )

            # In PostgreSQL FORMAT JSON, result is typically a list with a single dict
            raw_plan_data = plan_rows[0][0]
            if isinstance(raw_plan_data, list) and len(raw_plan_data) > 0:
                return raw_plan_data[0]
            elif isinstance(raw_plan_data, dict):
                return raw_plan_data
            else:
                raise ExplainServiceError(
                    "Unexpected plan format received from PostgreSQL.",
                    status_code=500,
                    detail=f"Received plan type: {type(raw_plan_data).__name__}"
                )

    except OperationalError as e:
        error_msg = str(e).lower()
        if "timeout" in error_msg or "canceling statement due to statement timeout" in error_msg:
            raise ExplainServiceError(
                "Execution plan inspection timed out.",
                status_code=504,
                detail="The query plan generation exceeded the configured timeout limit."
            )
        raise ExplainServiceError(
            "Database service is unreachable or operational error occurred.",
            status_code=503,
            detail="Could not establish connection to PostgreSQL engine."
        )

    except DBAPIError as e:
        # PostgreSQL returned a syntax/relation error without crashing engine
        pg_orig_msg = str(getattr(e, "orig", e))
        # Strip potential passwords/host strings defensively
        clean_detail = pg_orig_msg.split("\n")[0] if pg_orig_msg else "Database execution error"
        raise ExplainServiceError(
            "Failed to generate execution plan for query.",
            status_code=400,
            detail=clean_detail
        )

    except ExplainServiceError:
        raise

    except Exception as e:
        raise ExplainServiceError(
            "An unexpected error occurred while inspecting the query plan.",
            status_code=500,
            detail=str(e)
        )
