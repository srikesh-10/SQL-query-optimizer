"""
Unit and integration tests for Conservative SQL Rewrite Engine.
"""

import pytest
import sqlglot
from app.services.sql_rewriter import generate_rewrite_candidates, check_select_star_expansion
from app.services.sql_validator import validate_read_only_sql


def test_select_star_expansion_single_table():
    sql = "SELECT * FROM users WHERE id = 1;"
    ast = sqlglot.parse_one(sql, read="postgres")
    candidates = generate_rewrite_candidates(ast, sql)
    
    star_cand = next((c for c in candidates if c.rule_id == "REWRITE_EXPAND_SELECT_STAR"), None)
    assert star_cand is not None
    assert star_cand.semantic_safety == "verified_safe"
    assert "email" in star_cand.rewritten_sql
    assert "first_name" in star_cand.rewritten_sql
    assert "WHERE id = 1" in star_cand.rewritten_sql
    
    # Must pass strict validator
    normalized, _ = validate_read_only_sql(star_cand.rewritten_sql)
    assert normalized is not None


def test_select_star_with_alias_and_order_limit():
    sql = "SELECT * FROM products p WHERE p.category = 'Electronics' ORDER BY p.price DESC LIMIT 5;"
    ast = sqlglot.parse_one(sql, read="postgres")
    candidates = generate_rewrite_candidates(ast, sql)
    
    star_cand = next((c for c in candidates if c.rule_id == "REWRITE_EXPAND_SELECT_STAR"), None)
    assert star_cand is not None
    assert "p.sku" in star_cand.rewritten_sql
    assert "p.price" in star_cand.rewritten_sql
    assert "LIMIT 5" in star_cand.rewritten_sql


def test_no_select_star_expansion_on_join():
    # Multi-table query with join must NOT expand SELECT * due to ambiguity
    sql = "SELECT * FROM users u JOIN orders o ON u.id = o.user_id;"
    ast = sqlglot.parse_one(sql, read="postgres")
    candidates = generate_rewrite_candidates(ast, sql)
    
    assert not any(c.rule_id == "REWRITE_EXPAND_SELECT_STAR" for c in candidates)


def test_heuristic_function_on_column():
    sql = "SELECT id FROM users WHERE UPPER(email) = 'TEST@EXAMPLE.COM';"
    ast = sqlglot.parse_one(sql, read="postgres")
    candidates = generate_rewrite_candidates(ast, sql)
    
    cand = next((c for c in candidates if c.rule_id == "SUGGESTION_FUNCTION_ON_COLUMN"), None)
    assert cand is not None
    assert cand.rewritten_sql is None  # Safe: returns suggestion only, no automated rewrite
    assert cand.semantic_safety == "heuristic_suggestion"


def test_heuristic_leading_wildcard_like():
    sql = "SELECT id FROM products WHERE name LIKE '%Pro%';"
    ast = sqlglot.parse_one(sql, read="postgres")
    candidates = generate_rewrite_candidates(ast, sql)
    
    cand = next((c for c in candidates if c.rule_id == "SUGGESTION_LEADING_WILDCARD_LIKE"), None)
    assert cand is not None
    assert cand.rewritten_sql is None
