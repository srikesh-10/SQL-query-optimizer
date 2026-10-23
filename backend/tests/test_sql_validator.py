"""
Unit tests for SQL parsing, validation, and security safeguards using SQLGlot.
"""

import pytest
from app.services.sql_validator import validate_read_only_sql, SQLValidationError


# -----------------------------------------------------------------------------
# Valid Queries (Must Pass)
# -----------------------------------------------------------------------------

def test_valid_simple_select():
    sql = "SELECT id, email FROM users;"
    normalized, ast = validate_read_only_sql(sql)
    assert "SELECT" in normalized
    assert "users" in normalized


def test_valid_select_with_where_order_limit():
    sql = """
    SELECT id, total_amount, status
    FROM orders
    WHERE status = 'completed' AND total_amount > 100.00
    ORDER BY order_date DESC
    LIMIT 20;
    """
    normalized, ast = validate_read_only_sql(sql)
    assert "SELECT" in normalized
    assert "LIMIT 20" in normalized


def test_valid_multitable_join():
    sql = """
    SELECT u.email, count(o.id) AS total_orders, sum(o.total_amount) AS revenue
    FROM users u
    JOIN orders o ON u.id = o.user_id
    GROUP BY u.email
    HAVING count(o.id) > 5;
    """
    normalized, ast = validate_read_only_sql(sql)
    assert "JOIN" in normalized
    assert "GROUP BY" in normalized


def test_valid_read_only_cte():
    sql = """
    WITH high_value_orders AS (
        SELECT id, user_id, total_amount
        FROM orders
        WHERE total_amount > 500
    )
    SELECT u.first_name, hvo.total_amount
    FROM high_value_orders hvo
    JOIN users u ON hvo.user_id = u.id;
    """
    normalized, ast = validate_read_only_sql(sql)
    assert "WITH high_value_orders AS" in normalized
    assert "SELECT" in normalized


def test_valid_union_query():
    sql = """
    SELECT id, name, 'product' as item_type FROM products
    UNION ALL
    SELECT id, email, 'user' as item_type FROM users;
    """
    normalized, ast = validate_read_only_sql(sql)
    assert "UNION ALL" in normalized


# -----------------------------------------------------------------------------
# Invalid / Dangerous Queries (Must Be Rejected)
# -----------------------------------------------------------------------------

def test_reject_empty_and_whitespace():
    with pytest.raises(SQLValidationError, match="cannot be empty"):
        validate_read_only_sql("")

    with pytest.raises(SQLValidationError, match="cannot be empty"):
        validate_read_only_sql("    \n\t   ")


def test_reject_malformed_sql():
    with pytest.raises(SQLValidationError, match="Malformed SQL"):
        validate_read_only_sql("SELECT FROM WHERE ;")


def test_reject_insert():
    with pytest.raises(SQLValidationError, match="Unsupported statement type|Data-modifying"):
        validate_read_only_sql("INSERT INTO users (email, first_name, last_name) VALUES ('a@b.com', 'A', 'B');")


def test_reject_update():
    with pytest.raises(SQLValidationError, match="Unsupported statement type|Data-modifying"):
        validate_read_only_sql("UPDATE orders SET status = 'cancelled' WHERE id = 1;")


def test_reject_delete():
    with pytest.raises(SQLValidationError, match="Unsupported statement type|Data-modifying"):
        validate_read_only_sql("DELETE FROM users WHERE id = 5;")


def test_reject_drop_and_alter():
    with pytest.raises(SQLValidationError, match="Unsupported statement type|Data-modifying"):
        validate_read_only_sql("DROP TABLE users;")

    with pytest.raises(SQLValidationError, match="Unsupported statement type|Data-modifying"):
        validate_read_only_sql("ALTER TABLE users ADD COLUMN phone VARCHAR(20);")


def test_reject_truncate():
    with pytest.raises(SQLValidationError, match="Unsupported statement type|Data-modifying"):
        validate_read_only_sql("TRUNCATE TABLE orders;")


def test_reject_multiple_statements():
    with pytest.raises(SQLValidationError, match="Multiple SQL statements"):
        validate_read_only_sql("SELECT 1; SELECT 2;")

    with pytest.raises(SQLValidationError, match="Multiple SQL statements"):
        validate_read_only_sql("SELECT * FROM users; DROP TABLE products;")


def test_reject_data_modifying_cte():
    sql = """
    WITH deleted_orders AS (
        DELETE FROM orders WHERE status = 'cancelled' RETURNING *
    )
    SELECT * FROM deleted_orders;
    """
    with pytest.raises(SQLValidationError, match="Data-modifying"):
        validate_read_only_sql(sql)


def test_reject_select_into():
    sql = "SELECT id, email INTO new_users FROM users;"
    with pytest.raises(SQLValidationError, match="SELECT INTO"):
        validate_read_only_sql(sql)


def test_reject_unsupported_statement_types():
    with pytest.raises(SQLValidationError, match="Unsupported statement type"):
        validate_read_only_sql("SET work_mem = '64MB';")

    with pytest.raises(SQLValidationError, match="Unsupported statement type"):
        validate_read_only_sql("EXPLAIN SELECT * FROM users;")
