"""
Unit and integration tests for Plan Comparison Service.
"""

from unittest.mock import patch
import pytest
from app.services.plan_comparison import compare_plans, PlanComparisonResult


def test_compare_plans_live_postgres():
    orig_sql = "SELECT * FROM products WHERE price > 50;"
    cand_sql = "SELECT id, sku, name, category, price, inventory_count, created_at FROM products WHERE price > 50;"

    result = compare_plans(orig_sql, cand_sql)
    assert isinstance(result, PlanComparisonResult)
    assert result.original_total_cost > 0
    assert result.candidate_total_cost > 0
    assert result.original_plan_rows > 0
    assert result.cost_difference is not None
    assert result.interpretation is not None
    assert "planner cost units" in result.note


def test_compare_plans_zero_baseline_handling():
    # Synthetic test to verify zero division safety
    mock_orig = {
        "Plan": {
            "Node Type": "Result",
            "Total Cost": 0.0,
            "Startup Cost": 0.0,
            "Plan Rows": 1,
            "Plan Width": 4
        }
    }
    mock_cand = {
        "Plan": {
            "Node Type": "Result",
            "Total Cost": 0.0,
            "Startup Cost": 0.0,
            "Plan Rows": 1,
            "Plan Width": 4
        }
    }
    with patch("app.services.plan_comparison.get_execution_plan") as mock_get:
        mock_get.side_effect = [mock_orig, mock_cand]
        result = compare_plans("SELECT 1;", "SELECT 1;")
        assert result.original_total_cost == 0.0
        assert result.percentage_change is None  # Handled without ZeroDivisionError
        assert "identical total cost" in result.interpretation
