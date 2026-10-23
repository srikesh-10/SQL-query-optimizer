"""
Plan Comparison Service.
Compares PostgreSQL execution planner estimates between the original query
and an eligible rewritten candidate using safe EXPLAIN infrastructure.
Never executes queries, never claims runtime measurements, handles zero baselines cleanly.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel

from app.services.explain_service import get_execution_plan, ExplainServiceError
from app.services.plan_analyzer import analyze_plan, AnalysisResult


class PlanComparisonResult(BaseModel):
    original_sql: str
    candidate_sql: str
    original_total_cost: float
    candidate_total_cost: float
    original_plan_rows: int
    candidate_plan_rows: int
    original_root_node: str
    candidate_root_node: str
    cost_difference: float
    percentage_change: Optional[float] = None
    interpretation: str
    note: str


def compare_plans(
    original_sql: str,
    candidate_sql: str,
) -> PlanComparisonResult:
    """
    Computes and compares estimated execution plans for original vs rewritten candidate SQL.

    Formula:
        cost_difference = original_cost - candidate_cost
        percentage_change = (original_cost - candidate_cost) / original_cost * 100 (if original_cost > 0)
    """
    orig_raw_plan = get_execution_plan(original_sql)
    cand_raw_plan = get_execution_plan(candidate_sql)

    orig_summary = analyze_plan(orig_raw_plan, original_sql).plan_summary
    cand_summary = analyze_plan(cand_raw_plan, candidate_sql).plan_summary

    orig_cost = orig_summary.total_cost
    cand_cost = cand_summary.total_cost

    diff = orig_cost - cand_cost

    pct_change: Optional[float] = None
    if orig_cost > 0:
        pct_change = round((diff / orig_cost) * 100.0, 2)

    # Formulate evidence-based interpretation
    if diff > 0.01:
        interpretation = (
            f"Candidate plan reduces estimated cost by {diff:.2f} ({pct_change}%). "
            f"Planner selected '{cand_summary.root_node_type}' instead of '{orig_summary.root_node_type}'."
        )
    elif diff < -0.01:
        interpretation = (
            f"Candidate plan has higher estimated cost by {-diff:.2f} ({-pct_change}%). "
            "Original query plan is estimated to be more efficient by the planner."
        )
    else:
        interpretation = (
            "Planner estimated identical total cost between original and candidate queries. "
            "Execution strategy remains equivalent under current catalog statistics."
        )

    return PlanComparisonResult(
        original_sql=original_sql,
        candidate_sql=candidate_sql,
        original_total_cost=round(orig_cost, 2),
        candidate_total_cost=round(cand_cost, 2),
        original_plan_rows=orig_summary.plan_rows,
        candidate_plan_rows=cand_summary.plan_rows,
        original_root_node=orig_summary.root_node_type,
        candidate_root_node=cand_summary.root_node_type,
        cost_difference=round(diff, 2),
        percentage_change=pct_change,
        interpretation=interpretation,
        note="Values are PostgreSQL optimizer planner cost units, not runtime execution milliseconds.",
    )
