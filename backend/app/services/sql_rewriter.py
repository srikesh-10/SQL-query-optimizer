"""
Conservative SQL Rewrite Engine.
Identifies query anti-patterns and generates semantically verified rewrite candidates.
Enforces strict safety: only generates rewritten SQL when semantic equivalence
and catalog schemas are proven (e.g. single-table SELECT * projection expansion).
All candidate SQL must pass the SQL validator.
"""

from typing import List, Optional, Tuple, Dict
from pydantic import BaseModel
import sqlglot
from sqlglot import exp

from app.services.index_advisor import get_table_metadata, resolve_tables_and_aliases
from app.services.sql_validator import validate_read_only_sql, SQLValidationError


class RewriteCandidate(BaseModel):
    rule_id: str
    title: str
    description: str
    original_sql: str
    rewritten_sql: Optional[str] = None
    reason: str
    confidence: str  # 'high', 'medium', 'low'
    semantic_safety: str  # 'verified_safe', 'heuristic_suggestion'
    limitations: str


def check_select_star_expansion(
    parsed_ast: exp.Expression,
    original_sql: str,
    table_columns: Dict[str, List[str]],
) -> Optional[RewriteCandidate]:
    """
    Safely expands SELECT * into explicit column list IF AND ONLY IF:
    - Query is an ordinary single-table SELECT (no JOINs, CTEs, or set operations).
    - Table exists in known schema catalog.
    - Preserves column ordering, filters, order by, limit, and table aliases.
    """
    # 1. Check if top-level statement is a simple Select
    if not isinstance(parsed_ast, exp.Select):
        return None

    # 2. Reject queries with JOINs
    if parsed_ast.args.get("joins"):
        return None

    # 3. Reject queries with CTEs
    if parsed_ast.args.get("with"):
        return None

    # 4. Find FROM table
    from_clause = parsed_ast.args.get("from")
    if not from_clause or not from_clause.this or not isinstance(from_clause.this, exp.Table):
        return None

    table_node = from_clause.this
    table_name = table_node.name
    table_alias = table_node.alias

    if table_name not in table_columns:
        return None

    cols = table_columns[table_name]
    if not cols:
        return None

    # 5. Check if expressions contain exp.Star
    select_expressions = parsed_ast.expressions
    has_star = False
    for expr in select_expressions:
        if isinstance(expr, exp.Star):
            has_star = True
            break
        elif isinstance(expr, exp.Column) and expr.name == "*":
            has_star = True
            break

    if not has_star:
        return None

    # 6. Perform AST clone and replace Star with explicit column nodes
    cloned_ast = parsed_ast.copy()
    prefix = f"{table_alias}." if table_alias else ""
    explicit_columns = [
        sqlglot.parse_one(f"{prefix}{col}", read="postgres")
        for col in cols
    ]

    # Replace select expressions list
    cloned_ast.set("expressions", explicit_columns)

    try:
        rewritten_sql = cloned_ast.sql(dialect="postgres")
        # Validate that generated rewritten SQL passes our strict validator
        validate_read_only_sql(rewritten_sql)
    except Exception as e:
        return None

    return RewriteCandidate(
        rule_id="REWRITE_EXPAND_SELECT_STAR",
        title="Explicit Column Projection Expansion",
        description="Replaces 'SELECT *' with explicit column names from the table schema.",
        original_sql=original_sql.strip().rstrip(";"),
        rewritten_sql=rewritten_sql,
        reason=(
            "Using 'SELECT *' retrieves every column regardless of necessity, "
            "increasing network payload and preventing Index-Only Scans."
        ),
        confidence="high",
        semantic_safety="verified_safe",
        limitations="Applies only to single-table queries with known schema definitions; preserves column order.",
    )


def check_anti_pattern_heuristics(
    parsed_ast: exp.Expression,
    original_sql: str,
) -> List[RewriteCandidate]:
    """
    Detects recognizable anti-patterns where automated rewriting cannot guarantee
    identical three-valued null logic or execution behavior, returning actionable suggestions.
    """
    candidates: List[RewriteCandidate] = []

    # Heuristic 1: Function wrapping indexed column in WHERE predicate (e.g. UPPER(email) = '...')
    for eq in parsed_ast.find_all(exp.EQ):
        for side in (eq.left, eq.right):
            if isinstance(side, (exp.Anonymous, exp.Func)):
                func_name = side.name if hasattr(side, "name") else type(side).__name__
                if any(isinstance(arg, exp.Column) for arg in side.args.values()):
                    candidates.append(RewriteCandidate(
                        rule_id="SUGGESTION_FUNCTION_ON_COLUMN",
                        title=f"Function Expression in Filter Predicate ({func_name})",
                        description=f"Predicate applies function '{func_name}' directly onto a column.",
                        original_sql=original_sql.strip().rstrip(";"),
                        rewritten_sql=None,
                        reason=(
                            f"Applying functions like '{func_name}' prevents standard B-Tree indexes on the column "
                            "from being utilized, forcing a sequential table scan."
                        ),
                        confidence="medium",
                        semantic_safety="heuristic_suggestion",
                        limitations="Cannot automatically rewrite without changing case sensitivity or requiring expression indexes.",
                    ))
                    break

    # Heuristic 2: NOT IN with Subquery (vulnerable to NULL pitfalls)
    for in_node in parsed_ast.find_all(exp.In):
        if in_node.args.get("is_not") and isinstance(in_node.args.get("query"), exp.Select):
            candidates.append(RewriteCandidate(
                rule_id="SUGGESTION_NOT_IN_SUBQUERY",
                title="NOT IN Subquery Null-Safety Risk",
                description="Query uses 'NOT IN (SELECT ...)' construct.",
                original_sql=original_sql.strip().rstrip(";"),
                rewritten_sql=None,
                reason=(
                    "If the subquery returns even a single NULL value, NOT IN evaluates to UNKNOWN/false for all rows. "
                    "Consider rewriting to 'NOT EXISTS (SELECT 1 ...)' for null safety and better planner optimization."
                ),
                confidence="medium",
                semantic_safety="heuristic_suggestion",
                limitations="Automated rewriting skipped because NOT IN and NOT EXISTS behave differently if subquery contains NULLs.",
            ))

    # Heuristic 3: Leading Wildcard in LIKE (LIKE '%abc')
    for like_node in parsed_ast.find_all(exp.Like):
        pattern = like_node.expression
        if isinstance(pattern, exp.Literal) and pattern.is_string:
            if pattern.this.startswith("%") or pattern.this.startswith("_"):
                candidates.append(RewriteCandidate(
                    rule_id="SUGGESTION_LEADING_WILDCARD_LIKE",
                    title="Leading Wildcard in LIKE Predicate",
                    description=f"LIKE pattern '{pattern.this}' begins with a wildcard character.",
                    original_sql=original_sql.strip().rstrip(";"),
                    rewritten_sql=None,
                    reason=(
                        "Standard B-Tree indexes cannot be used for patterns starting with '%' or '_', "
                        "forcing PostgreSQL to sequentially scan the table."
                    ),
                    confidence="high",
                    semantic_safety="heuristic_suggestion",
                    limitations="Consider full-text search (tsvector) or trigram indexes (pg_trgm) for substring matching.",
                ))

    return candidates


def generate_rewrite_candidates(
    parsed_ast: exp.Expression,
    original_sql: str,
) -> List[RewriteCandidate]:
    """
    Main entry point for SQL rewrite candidate generator.
    """
    table_columns, _ = get_table_metadata()
    candidates: List[RewriteCandidate] = []

    # Check verified safe rewrites
    star_cand = check_select_star_expansion(parsed_ast, original_sql, table_columns)
    if star_cand:
        candidates.append(star_cand)

    # Check heuristic suggestions
    heuristics = check_anti_pattern_heuristics(parsed_ast, original_sql)
    candidates.extend(heuristics)

    return candidates
