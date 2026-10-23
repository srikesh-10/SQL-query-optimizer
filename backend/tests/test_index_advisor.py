"""
Unit and integration tests for the Index Advisor service.
"""

import pytest
import sqlglot
from app.services.index_advisor import (
    advise_indexes,
    extract_column_predicates,
    is_covered_by_existing_index,
    resolve_tables_and_aliases,
)


def test_is_covered_by_existing_index():
    existing = [
        {"name": "idx_order_items_order_product", "column_names": ["order_id", "product_id"]},
        {"name": "ix_orders_status", "column_names": ["status"]},
    ]
    # Single column prefix covered
    covered, name = is_covered_by_existing_index(["order_id"], existing)
    assert covered is True
    assert name == "idx_order_items_order_product"

    # Full composite prefix covered
    covered, name = is_covered_by_existing_index(["order_id", "product_id"], existing)
    assert covered is True

    # Non-prefix column is NOT covered (product_id is 2nd in composite)
    covered, name = is_covered_by_existing_index(["product_id"], [{"name": "idx", "column_names": ["order_id", "product_id"]}])
    assert covered is False


def test_resolve_tables_and_aliases():
    ast = sqlglot.parse_one("SELECT u.email, o.total_amount FROM users AS u JOIN orders o ON u.id = o.user_id", read="postgres")
    alias_to_table, tables = resolve_tables_and_aliases(ast)
    assert alias_to_table["u"] == "users"
    assert alias_to_table["o"] == "orders"
    assert "users" in tables
    assert "orders" in tables


def test_advise_indexes_for_unindexed_filter_live():
    # first_name on users is NOT indexed in the schema (only email is indexed)
    ast = sqlglot.parse_one("SELECT * FROM users WHERE first_name = 'David';", read="postgres")
    recs = advise_indexes(ast)
    assert len(recs) >= 1
    rec = next((r for r in recs if r.table_name == "users" and "first_name" in r.columns), None)
    assert rec is not None
    assert rec.index_type == "btree"
    assert "CREATE INDEX" in rec.suggested_ddl
    assert rec.confidence in ["medium", "high"]


def test_advise_indexes_composite_filter():
    # orders has index on status and order_date separately, but NOT composite (status, total_amount)
    ast = sqlglot.parse_one("SELECT * FROM orders WHERE status = 'completed' AND total_amount > 100;", read="postgres")
    recs = advise_indexes(ast)
    rec = next((r for r in recs if r.table_name == "orders" and "status" in r.columns and "total_amount" in r.columns), None)
    assert rec is not None
    assert rec.index_type == "btree"
    assert "total_amount" in rec.columns
    assert "status" in rec.columns


def test_advise_indexes_avoids_duplicate_for_indexed_column():
    # email on users IS uniquely indexed
    ast = sqlglot.parse_one("SELECT * FROM users WHERE email = 'karen.harris.7505@example.com';", read="postgres")
    recs = advise_indexes(ast)
    # Should not suggest creating an index on email
    assert not any(r.table_name == "users" and r.columns == ["email"] for r in recs)
