"""
SQL Parsing and Validation Module using SQLGlot.
Enforces read-only SELECT queries and strictly rejects write operations,
data-modifying CTEs, multiple statements, SELECT INTO, and malformed SQL.
"""

from typing import Tuple
import sqlglot
from sqlglot import exp, errors


class SQLValidationError(Exception):
    """Exception raised when a SQL query violates validation rules."""
    def __init__(self, message: str, detail: str = ""):
        super().__init__(message)
        self.message = message
        self.detail = detail


def validate_read_only_sql(raw_sql: str) -> Tuple[str, exp.Expression]:
    """
    Parses and validates that a given SQL string is a single, valid, read-only SELECT query.

    Args:
        raw_sql: Raw SQL string submitted by the user.

    Returns:
        Tuple of (normalized_sql_str, parsed_ast_expression)

    Raises:
        SQLValidationError: When the SQL is empty, malformed, multiple statements,
                            or performs write/DDL operations.
    """
    if not raw_sql or not raw_sql.strip():
        raise SQLValidationError(
            "SQL query cannot be empty or whitespace.",
            "Empty query string provided."
        )

    clean_sql = raw_sql.strip()

    # Parse using postgres dialect
    try:
        parsed_statements = sqlglot.parse(clean_sql, read="postgres")
    except errors.ParseError as e:
        raise SQLValidationError(
            "Malformed SQL syntax.",
            f"Parsing error: {str(e)}"
        )
    except Exception as e:
        raise SQLValidationError(
            "Unable to parse SQL query.",
            f"Parser error: {str(e)}"
        )

    # Filter out empty statements (e.g., trailing semicolons)
    statements = [stmt for stmt in parsed_statements if stmt is not None]

    if not statements:
        raise SQLValidationError(
            "No executable SQL statements found.",
            "The input did not contain any valid SQL statement."
        )

    if len(statements) > 1:
        raise SQLValidationError(
            "Multiple SQL statements are not allowed.",
            f"Expected exactly 1 statement, but received {len(statements)}."
        )

    stmt = statements[0]

    # Reject dangerous top-level statements
    # exp.Select is standard SELECT. Union/Intersect/Except are also read-only queries.
    allowed_query_types = (exp.Select, exp.Union, exp.Intersect, exp.Except)

    if not isinstance(stmt, allowed_query_types):
        raise SQLValidationError(
            f"Unsupported statement type: '{type(stmt).__name__}'. Only read-only SELECT queries are supported.",
            "Statement must begin with SELECT or a read-only set operation."
        )

    # Explicitly check for data-modifying expressions anywhere in the AST
    forbidden_ast_types = (
        exp.Insert,
        exp.Update,
        exp.Delete,
        exp.Drop,
        exp.Create,
        exp.Alter,
        exp.TruncateTable,
        exp.Command,
    )

    for forbidden in forbidden_ast_types:
        if stmt.find(forbidden):
            raise SQLValidationError(
                f"Data-modifying or DDL operation detected ({forbidden.__name__}).",
                "Queries modifying data or schema are strictly forbidden."
            )

    # Check for SELECT INTO (which creates a new table)
    # In SQLGlot, SELECT ... INTO is represented by an exp.Into node inside exp.Select
    if stmt.find(exp.Into):
        raise SQLValidationError(
            "SELECT INTO statements are not allowed.",
            "Creating tables via SELECT INTO is not permitted."
        )

    # Check CTEs (Common Table Expressions) for data modification
    # e.g., WITH deleted AS (DELETE FROM orders RETURNING *) SELECT * FROM deleted;
    with_clause = stmt.args.get("with")
    if with_clause:
        for cte in with_clause.expressions:
            # The CTE's underlying query must be checked
            cte_query = cte.this
            if not isinstance(cte_query, allowed_query_types):
                raise SQLValidationError(
                    "Data-modifying CTEs are not allowed.",
                    f"CTE '{cte.alias_or_name}' contains a non-SELECT statement."
                )
            for forbidden in forbidden_ast_types:
                if cte.find(forbidden):
                    raise SQLValidationError(
                        "Data-modifying operation found inside CTE.",
                        f"CTE '{cte.alias_or_name}' contains forbidden operation: {forbidden.__name__}."
                    )

    # Generate normalized, sanitized PostgreSQL query string
    try:
        normalized_sql = stmt.sql(dialect="postgres")
    except Exception:
        normalized_sql = clean_sql.rstrip(";")

    return normalized_sql, stmt
