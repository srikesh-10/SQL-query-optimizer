from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    String,
    Integer,
    Numeric,
    DateTime,
    ForeignKey,
    CheckConstraint,
    Index,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    """
    Represents customer accounts.
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationship to orders
    orders: Mapped[List["Order"]] = relationship(
        "Order", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email='{self.email}'>"


class Product(Base):
    """
    Represents catalog products available for purchase.
    """
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    inventory_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint("price >= 0", name="check_product_price_non_negative"),
        CheckConstraint("inventory_count >= 0", name="check_inventory_non_negative"),
    )

    # Relationship to order items
    order_items: Mapped[List["OrderItem"]] = relationship("OrderItem", back_populates="product")

    def __repr__(self) -> str:
        return f"<Product id={self.id} sku='{self.sku}' name='{self.name}'>"


class Order(Base):
    """
    Represents customer purchase transactions.
    """
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending", index=True
    )  # e.g., 'pending', 'processing', 'completed', 'cancelled'
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)

    __table_args__ = (
        CheckConstraint("total_amount >= 0", name="check_order_total_non_negative"),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="orders")
    items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Order id={self.id} user_id={self.user_id} status='{self.status}' total={self.total_amount}>"


class OrderItem(Base):
    """
    Represents line items inside an order.
    """
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    __table_args__ = (
        CheckConstraint("quantity > 0", name="check_order_item_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="check_order_item_unit_price_non_negative"),
        Index("idx_order_items_order_product", "order_id", "product_id"),
    )

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="items")
    product: Mapped["Product"] = relationship("Product", back_populates="order_items")

    def __repr__(self) -> str:
        return f"<OrderItem id={self.id} order_id={self.order_id} product_id={self.product_id} qty={self.quantity}>"
