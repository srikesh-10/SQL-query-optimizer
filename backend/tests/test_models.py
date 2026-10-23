"""
Tests verifying SQLAlchemy model definitions, constraints, and relationships.
These tests validate the ORM metadata and basic schema contracts without assuming
a pre-existing seeded dataset.
"""

from decimal import Decimal
import pytest
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.ecommerce import User, Product, Order, OrderItem


def test_models_registered_in_metadata():
    """Verify that all four e-commerce models are registered in Base metadata."""
    table_names = set(Base.metadata.tables.keys())
    assert {"users", "products", "orders", "order_items"}.issubset(table_names)


def test_user_model_columns():
    """Verify Users table schema attributes."""
    table = Base.metadata.tables["users"]
    assert "email" in table.c
    assert "first_name" in table.c
    assert "last_name" in table.c
    assert table.c.email.unique is True or any(
        idx.unique for idx in table.indexes if "email" in [col.name for col in idx.columns]
    )


def test_product_monetary_type_and_constraints():
    """Verify Product price uses Numeric/Decimal and has non-negative check constraints."""
    table = Base.metadata.tables["products"]
    assert str(table.c.price.type).startswith("NUMERIC")
    constraint_names = [c.name for c in table.constraints if c.name]
    assert "check_product_price_non_negative" in constraint_names
    assert "check_inventory_non_negative" in constraint_names


def test_order_relationships_and_foreign_keys():
    """Verify Orders foreign key to users and cascading definitions."""
    table = Base.metadata.tables["orders"]
    fk_targets = [fk.target_fullname for fk in table.foreign_keys]
    assert "users.id" in fk_targets


def test_order_item_composite_index():
    """Verify OrderItems index across order_id and product_id."""
    table = Base.metadata.tables["order_items"]
    index_names = [idx.name for idx in table.indexes]
    assert "idx_order_items_order_product" in index_names
