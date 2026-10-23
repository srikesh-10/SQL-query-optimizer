"""
Index Advisor Module.
Analyzes query predicates (equality, range, join, group/order), resolves aliases,
compares against existing PostgreSQL table indexes, and produces evidence-based,
safe index recommendations with confidence, tradeoffs, and suggested DDL.
Never executes DDL or alters the database schema.
"""

from typing import Dict, Any, List, Set, Tuple, Optional
from pydantic import BaseModel
import sqlglot
from sqlglot import exp
from sqlalchemy import inspect

from app.db.session import engine


class IndexRecommendation(BaseModel):
    recommendation_id: str
    table_name: str
    columns: List[str]
    index_type: str  # e.g., 'btree'
    reason: str
    supporting_evidence: str
    estimated_benefit: str  # 'high', 'medium', 'low'
    confidence: str        # 'high', 'medium', 'low'
    tradeoffs: str
    suggested_ddl: Optional[str] = None


def get_table_metadata() -> Tuple[Dict[str, List[str]], Dict[str, List[Dict[str, Any]]]]:
    """
    Inspects PostgreSQL metadata using SQLAlchemy Inspector.
    Falls back to Base.metadata if database connection is unavailable (e.g. isolated testing).
    Returns:
        table_columns: Dict[table_name, list of column names]
        table_indexes: Dict[table_name, list of index metadata dicts]
    """
    table_columns: Dict[str, List[str]] = {}
    table_indexes: Dict[str, List[Dict[str, Any]]] = {}

    try:
        inspector = inspect(engine)
        for table in inspector.get_table_names():
            cols = [c["name"] for c in inspector.get_columns(table)]
            table_columns[table] = cols
            
            indexes = inspector.get_indexes(table)
            pk = inspector.get_pk_constraint(table)
            if pk and pk.get("constrained_columns"):
                indexes.append({
                    "name": pk.get("name") or f"{table}_pkey",
                    "unique": True,
                    "column_names": pk["constrained_columns"],
                })
            table_indexes[table] = indexes
    except Exception:
        # Fallback to declared ORM Base metadata
        from app.db.base import Base
        for table_name, table in Base.metadata.tables.items():
            table_columns[table_name] = [c.name for c in table.columns]
            idx_list = []
            for idx in table.indexes:
                idx_list.append({
                    "name": idx.name,
                    "unique": idx.unique,
                    "column_names": [c.name for c in idx.columns],
                })
            table_indexes[table_name] = idx_list

    return table_columns, table_indexes


def resolve_tables_and_aliases(parsed_ast: exp.Expression) -> Tuple[Dict[str, str], Set[str]]:
    """
    Resolves aliases to real table names.
    Returns:
        alias_to_table: Dict mapping alias (or table name) to real table name
        tables_in_query: Set of real table names referenced in query
    """
    alias_to_table: Dict[str, str] = {}
    tables_in_query: Set[str] = set()

    for table_node in parsed_ast.find_all(exp.Table):
        real_table = table_node.name
        alias = table_node.alias or real_table
        if real_table:
            tables_in_query.add(real_table)
            alias_to_table[alias] = real_table
            alias_to_table[real_table] = real_table

    return alias_to_table, tables_in_query


def extract_column_predicates(
    parsed_ast: exp.Expression,
    alias_to_table: Dict[str, str],
    table_columns: Dict[str, List[str]],
) -> Dict[str, Dict[str, Set[str]]]:
    """
    Extracts columns used in predicates categorized by usage:
    - equality: column = value / column = column
    - range: <, <=, >, >=, BETWEEN
    - join: joined with other table columns
    - order_by: columns in ORDER BY
    - group_by: columns in GROUP BY

    Returns:
        predicates_by_table: Dict[table_name, Dict[predicate_type, Set[column_name]]]
    """
    predicates: Dict[str, Dict[str, Set[str]]] = {}

    def add_col(tbl: str, col: str, ptype: str):
        if not tbl or not col:
            return
        if tbl not in predicates:
            predicates[tbl] = {
                "equality": set(),
                "range": set(),
                "join": set(),
                "order_by": set(),
                "group_by": set(),
            }
        predicates[tbl][ptype].add(col)

    def resolve_col_table(col_expr: exp.Column) -> Optional[Tuple[str, str]]:
        col_name = col_expr.name
        table_qualifier = col_expr.table

        if table_qualifier:
            real_table = alias_to_table.get(table_qualifier)
            if real_table and col_name in table_columns.get(real_table, []):
                return real_table, col_name
        else:
            # Unqualified column: check which table in query possesses it
            possible_tables = [
                tbl for tbl in alias_to_table.values()
                if col_name in table_columns.get(tbl, [])
            ]
            # Avoid ambiguous columns
            if len(possible_tables) == 1:
                return possible_tables[0], col_name

        return None

    # 1. WHERE and JOIN condition predicates
    for eq_node in parsed_ast.find_all(exp.EQ):
        left, right = eq_node.left, eq_node.right
        left_res = resolve_col_table(left) if isinstance(left, exp.Column) else None
        right_res = resolve_col_table(right) if isinstance(right, exp.Column) else None

        if left_res and right_res:
            # Both are columns -> join condition
            t1, c1 = left_res
            t2, c2 = right_res
            if t1 != t2:
                add_col(t1, c1, "join")
                add_col(t2, c2, "join")
            else:
                add_col(t1, c1, "equality")
                add_col(t2, c2, "equality")
        elif left_res:
            add_col(left_res[0], left_res[1], "equality")
        elif right_res:
            add_col(right_res[0], right_res[1], "equality")

    # 2. Range predicates (<, <=, >, >=, Between)
    range_nodes = list(parsed_ast.find_all(exp.GT)) + \
                  list(parsed_ast.find_all(exp.GTE)) + \
                  list(parsed_ast.find_all(exp.LT)) + \
                  list(parsed_ast.find_all(exp.LTE))

    for r_node in range_nodes:
        left, right = r_node.left, r_node.right
        left_res = resolve_col_table(left) if isinstance(left, exp.Column) else None
        right_res = resolve_col_table(right) if isinstance(right, exp.Column) else None
        if left_res and not right_res:
            add_col(left_res[0], left_res[1], "range")
        elif right_res and not left_res:
            add_col(right_res[0], right_res[1], "range")

    for between_node in parsed_ast.find_all(exp.Between):
        this_col = between_node.this
        if isinstance(this_col, exp.Column):
            res = resolve_col_table(this_col)
            if res:
                add_col(res[0], res[1], "range")

    # 3. ORDER BY columns
    order_clause = parsed_ast.args.get("order")
    if order_clause:
        for ordered in order_clause.expressions:
            col_expr = ordered.this if isinstance(ordered, exp.Ordered) else ordered
            if isinstance(col_expr, exp.Column):
                res = resolve_col_table(col_expr)
                if res:
                    add_col(res[0], res[1], "order_by")

    # 4. GROUP BY columns
    group_clause = parsed_ast.args.get("group")
    if group_clause:
        for grouped in group_clause.expressions:
            if isinstance(grouped, exp.Column):
                res = resolve_col_table(grouped)
                if res:
                    add_col(res[0], res[1], "group_by")

    return predicates


def is_covered_by_existing_index(
    candidate_cols: List[str],
    existing_indexes: List[Dict[str, Any]],
) -> Tuple[bool, Optional[str]]:
    """
    Determines if candidate columns are already covered by an existing index.
    A composite index (A, B) covers candidate [A] or candidate [A, B], but NOT [B].
    """
    for idx in existing_indexes:
        idx_cols = idx.get("column_names") or []
        if not idx_cols:
            continue
        # Check if candidate_cols is a prefix of idx_cols
        if len(candidate_cols) <= len(idx_cols):
            if idx_cols[:len(candidate_cols)] == candidate_cols:
                return True, idx.get("name")
    return False, None


def advise_indexes(
    parsed_ast: exp.Expression,
    plan_dict: Optional[Dict[str, Any]] = None,
) -> List[IndexRecommendation]:
    """
    Main Index Advisor entry point.
    Examines AST predicates, correlates with execution plan scan nodes,
    and produces actionable, evidence-based recommendations.
    """
    table_columns, table_indexes = get_table_metadata()
    alias_to_table, tables_in_query = resolve_tables_and_aliases(parsed_ast)
    predicates = extract_column_predicates(parsed_ast, alias_to_table, table_columns)

    # Collect scan nodes from plan to check for sequential scans
    seq_scan_tables: Dict[str, Dict[str, Any]] = {}
    if plan_dict:
        def extract_seq_scans(node: Dict[str, Any]):
            if not isinstance(node, dict):
                return
            if node.get("Node Type") == "Seq Scan":
                rel = node.get("Relation Name")
                if rel:
                    seq_scan_tables[rel] = node
            for child in node.get("Plans", []):
                extract_seq_scans(child)
        extract_seq_scans(plan_dict.get("Plan", {}))

    recommendations: List[IndexRecommendation] = []
    rec_counter = 1

    for table_name, usage in predicates.items():
        existing = table_indexes.get(table_name, [])
        eq_cols = sorted(list(usage["equality"]))
        range_cols = sorted(list(usage["range"]))
        join_cols = sorted(list(usage["join"]))
        order_cols = sorted(list(usage["order_by"]))

        has_seq_scan = table_name in seq_scan_tables
        seq_scan_node = seq_scan_tables.get(table_name)
        cost_info = f" (estimated cost: {seq_scan_node.get('Total Cost', 0):.1f})" if seq_scan_node else ""

        # Case 1: Composite Candidate (Equality + Range or Equality + Status/Date)
        # Optimal composite index order: Equality columns first, then Range/Order columns
        if eq_cols and range_cols:
            candidate = [eq_cols[0], range_cols[0]]
            covered, existing_name = is_covered_by_existing_index(candidate, existing)
            if not covered:
                rec_id = f"IDX_REC_{rec_counter:03d}"
                rec_counter += 1
                col_str = ", ".join(candidate)
                idx_name = f"idx_{table_name}_{'_'.join(candidate)}"
                ddl = f"CREATE INDEX {idx_name} ON {table_name} ({col_str});"

                recommendations.append(IndexRecommendation(
                    recommendation_id=rec_id,
                    table_name=table_name,
                    columns=candidate,
                    index_type="btree",
                    reason=f"Composite filtering detected on '{table_name}' with equality on '{eq_cols[0]}' and range on '{range_cols[0]}'.",
                    supporting_evidence=(
                        f"PostgreSQL planner used Sequential Scan{cost_info} on '{table_name}'"
                        if has_seq_scan else f"Query filters on '{table_name}' using combined predicates."
                    ),
                    estimated_benefit="high" if has_seq_scan else "medium",
                    confidence="high" if has_seq_scan else "medium",
                    tradeoffs=f"Accelerates combined filters on ({col_str}); incurs slight INSERT/UPDATE maintenance overhead on table '{table_name}'.",
                    suggested_ddl=ddl,
                ))

        # Case 2: Equality or Join filter on table undergoing sequential scan
        filter_candidates = eq_cols or join_cols or range_cols
        for col in filter_candidates:
            candidate = [col]
            covered, existing_name = is_covered_by_existing_index(candidate, existing)
            if not covered:
                # Avoid duplicate recommendations for the table
                if any(r.table_name == table_name and col in r.columns for r in recommendations):
                    continue

                rec_id = f"IDX_REC_{rec_counter:03d}"
                rec_counter += 1
                idx_name = f"idx_{table_name}_{col}"
                ddl = f"CREATE INDEX {idx_name} ON {table_name} ({col});"

                recommendations.append(IndexRecommendation(
                    recommendation_id=rec_id,
                    table_name=table_name,
                    columns=candidate,
                    index_type="btree",
                    reason=f"High-frequency filtering predicate on '{table_name}.{col}'.",
                    supporting_evidence=(
                        f"PostgreSQL performed a Sequential Scan{cost_info} across table '{table_name}'."
                        if has_seq_scan else f"Column '{col}' is used as a filter/join predicate without a dedicated B-Tree index."
                    ),
                    estimated_benefit="high" if has_seq_scan else "medium",
                    confidence="high" if has_seq_scan else "medium",
                    tradeoffs=f"B-Tree index speeds up lookups on '{col}'; consumes additional disk storage and memory buffers.",
                    suggested_ddl=ddl,
                ))

    return recommendations
