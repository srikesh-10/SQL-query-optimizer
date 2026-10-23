"""
Unit tests for query plan parsing, metrics extraction, and rule-based findings using JSON fixtures.
Does not require an active PostgreSQL connection.
"""

import pytest
from app.services.plan_analyzer import analyze_plan


SAMPLE_SEQ_SCAN_PLAN = {
    "Plan": {
        "Node Type": "Seq Scan",
        "Parallel Aware": False,
        "Async Capable": False,
        "Relation Name": "orders",
        "Alias": "orders",
        "Startup Cost": 0.00,
        "Total Cost": 1250.00,
        "Plan Rows": 50000,
        "Plan Width": 36,
        "Filter": "(status = 'completed'::text)"
    },
    "Planning Time": 0.124
}

SAMPLE_INDEX_SCAN_PLAN = {
    "Plan": {
        "Node Type": "Index Scan",
        "Parallel Aware": False,
        "Async Capable": False,
        "Scan Direction": "Forward",
        "Index Name": "ix_users_email",
        "Relation Name": "users",
        "Alias": "u",
        "Startup Cost": 0.29,
        "Total Cost": 8.30,
        "Plan Rows": 1,
        "Plan Width": 68,
        "Index Cond": "(email = 'karen.harris.7505@example.com'::text)"
    },
    "Planning Time": 0.088
}

SAMPLE_HASH_JOIN_PLAN = {
    "Plan": {
        "Node Type": "Hash Join",
        "Parallel Aware": False,
        "Join Type": "Inner",
        "Startup Cost": 25.00,
        "Total Cost": 6200.50,
        "Plan Rows": 15000,
        "Plan Width": 104,
        "Hash Cond": "(o.user_id = u.id)",
        "Plans": [
            {
                "Node Type": "Seq Scan",
                "Relation Name": "orders",
                "Alias": "o",
                "Startup Cost": 0.00,
                "Total Cost": 1200.00,
                "Plan Rows": 50000,
                "Plan Width": 36
            },
            {
                "Node Type": "Hash",
                "Startup Cost": 15.00,
                "Total Cost": 15.00,
                "Plan Rows": 1000,
                "Plan Width": 68,
                "Plans": [
                    {
                        "Node Type": "Seq Scan",
                        "Relation Name": "users",
                        "Alias": "u",
                        "Startup Cost": 0.00,
                        "Total Cost": 15.00,
                        "Plan Rows": 1000,
                        "Plan Width": 68
                    }
                ]
            }
        ]
    },
    "Planning Time": 0.352
}


def test_seq_scan_plan_analysis():
    sql = "SELECT * FROM orders WHERE status = 'completed';"
    res = analyze_plan(SAMPLE_SEQ_SCAN_PLAN, sql)

    assert res.status == "success"
    assert res.plan_summary.root_node_type == "Seq Scan"
    assert res.plan_summary.total_cost == 1250.00
    assert res.plan_summary.plan_rows == 50000
    assert res.plan_summary.planning_time_ms == 0.124
    assert len(res.scan_nodes) == 1
    assert res.scan_nodes[0].relation_name == "orders"

    # Should detect large sequential scan warning
    finding_codes = [f.code for f in res.findings]
    assert "PERF_SEQ_SCAN_LARGE_TABLE" in finding_codes


def test_index_scan_plan_analysis():
    sql = "SELECT * FROM users WHERE email = 'karen.harris.7505@example.com';"
    res = analyze_plan(SAMPLE_INDEX_SCAN_PLAN, sql)

    assert res.plan_summary.root_node_type == "Index Scan"
    assert res.plan_summary.total_cost == 8.30
    assert len(res.scan_nodes) == 1
    assert res.scan_nodes[0].index_name == "ix_users_email"

    finding_codes = [f.code for f in res.findings]
    assert "PERF_INDEX_SCAN_USED" in finding_codes


def test_hash_join_plan_analysis():
    sql = "SELECT * FROM orders o JOIN users u ON o.user_id = u.id;"
    res = analyze_plan(SAMPLE_HASH_JOIN_PLAN, sql)

    assert res.plan_summary.root_node_type == "Hash Join"
    assert len(res.join_nodes) == 1
    assert res.join_nodes[0].node_type == "Hash Join"
    assert res.join_nodes[0].hash_condition == "(o.user_id = u.id)"
    # Nested nodes: 1 root join + 1 seq scan + 1 hash + 1 seq scan = 4 nodes
    assert res.plan_summary.node_count == 4
    assert len(res.scan_nodes) == 2

    finding_codes = [f.code for f in res.findings]
    assert "PERF_HASH_JOIN_USED" in finding_codes
    assert "PERF_HIGH_ESTIMATED_COST" in finding_codes


def test_plan_with_missing_optional_fields():
    minimal_plan = {
        "Plan": {
            "Node Type": "Result",
            "Total Cost": 0.01,
            "Plan Rows": 1,
            "Plan Width": 4
        }
    }
    res = analyze_plan(minimal_plan, "SELECT 1;")
    assert res.plan_summary.root_node_type == "Result"
    assert res.plan_summary.planning_time_ms is None
    assert len(res.scan_nodes) == 0
    assert len(res.join_nodes) == 0
    assert res.plan_summary.node_count == 1
