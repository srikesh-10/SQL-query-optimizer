"""
Deterministic E-commerce Dataset Generator.
Populates:
- Users (default: 10,000)
- Products (default: 1,000)
- Orders (default: 50,000)
- Order Items (multiple items per order)

Requirements:
- Fixed random seed for complete reproducibility.
- Batched inserts using SQLAlchemy Core for high performance.
- Idempotent: checks for existing counts and does not duplicate records.
- Configurable counts via CLI arguments.
"""

import argparse
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import random
import sys
import time
from typing import List, Dict, Any

from sqlalchemy import select, func, insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import engine, SessionLocal
from app.models.ecommerce import User, Product, Order, OrderItem

# Categories and product adjectives for realistic names
CATEGORIES = [
    "Electronics", "Computers", "Home & Kitchen", "Books", 
    "Clothing", "Sports & Outdoors", "Health & Personal Care", "Automotive",
    "Toys & Games", "Office Products"
]

ADJECTIVES = [
    "Ultra", "Pro", "Eco", "Smart", "Classic", "Premium", "Compact", 
    "Wireless", "Heavy-Duty", "Portable", "Ergonomic", "Advanced"
]

NOUNS = [
    "Monitor", "Headphones", "Keyboard", "Mouse", "Laptop Stand", "Backpack",
    "Water Bottle", "Blender", "Coffee Maker", "Desk Lamp", "Power Bank", "Speaker"
]

FIRST_NAMES = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
    "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa",
    "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra", "Donald", "Ashley",
    "Steven", "Kimberly", "Paul", "Emily", "Andrew", "Donna", "Joshua", "Michelle"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker"
]

ORDER_STATUSES = ["completed", "processing", "pending", "cancelled"]
STATUS_WEIGHTS = [0.70, 0.15, 0.10, 0.05]


def seed_database(
    num_users: int = 10_000,
    num_products: int = 1_000,
    num_orders: int = 50_000,
    min_items_per_order: int = 1,
    max_items_per_order: int = 4,
    random_seed: int = 42,
    batch_size: int = 5_000,
) -> None:
    """
    Populates the database with realistic sample e-commerce data.
    """
    print("=" * 60)
    print("SQL Query Optimizer - Deterministic Dataset Generator")
    print("=" * 60)
    print(f"Target Configuration:")
    print(f"  - Users:        {num_users:,}")
    print(f"  - Products:     {num_products:,}")
    print(f"  - Orders:       {num_orders:,}")
    print(f"  - Seed:         {random_seed}")
    print(f"  - Batch Size:   {batch_size:,}")
    print("=" * 60)

    # Initialize deterministic pseudo-random number generator
    rng = random.Random(random_seed)

    start_total_time = time.perf_counter()

    with SessionLocal() as db:
        # Check existing records to prevent duplication
        existing_users = db.scalar(select(func.count(User.id))) or 0
        existing_products = db.scalar(select(func.count(Product.id))) or 0
        existing_orders = db.scalar(select(func.count(Order.id))) or 0
        existing_items = db.scalar(select(func.count(OrderItem.id))) or 0

        print(f"Current counts in database:")
        print(f"  Users: {existing_users:,} | Products: {existing_products:,} | Orders: {existing_orders:,} | Items: {existing_items:,}")

        if existing_users >= num_users and existing_products >= num_products and existing_orders >= num_orders:
            print("[INFO] Target counts already reached or exceeded. Skipping seeding.")
            return

        # ---------------------------------------------------------------------
        # 1. Seed Users
        # ---------------------------------------------------------------------
        users_to_create = max(0, num_users - existing_users)
        if users_to_create > 0:
            print(f"\n[1/4] Generating {users_to_create:,} users...")
            user_start = time.perf_counter()
            base_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            total_seconds_span = int((now - base_date).total_seconds())

            user_records: List[Dict[str, Any]] = []
            for i in range(1, users_to_create + 1):
                idx = existing_users + i
                first = rng.choice(FIRST_NAMES)
                last = rng.choice(LAST_NAMES)
                # Ensure guaranteed uniqueness of email via indexed sequence suffix
                email = f"{first.lower()}.{last.lower()}.{idx}@example.com"
                created_delta = timedelta(seconds=rng.randint(0, total_seconds_span))
                created_at = base_date + created_delta

                user_records.append({
                    "email": email,
                    "first_name": first,
                    "last_name": last,
                    "created_at": created_at,
                    "updated_at": created_at,
                })

                if len(user_records) >= batch_size:
                    db.execute(insert(User), user_records)
                    db.commit()
                    user_records.clear()

            if user_records:
                db.execute(insert(User), user_records)
                db.commit()
                user_records.clear()

            print(f"  Done in {time.perf_counter() - user_start:.2f}s")

        # Query all available user IDs for order generation
        user_ids: List[int] = db.scalars(select(User.id)).all()
        print(f"  Total Users available: {len(user_ids):,}")

        # ---------------------------------------------------------------------
        # 2. Seed Products
        # ---------------------------------------------------------------------
        products_to_create = max(0, num_products - existing_products)
        if products_to_create > 0:
            print(f"\n[2/4] Generating {products_to_create:,} products...")
            prod_start = time.perf_counter()
            prod_records: List[Dict[str, Any]] = []

            for i in range(1, products_to_create + 1):
                idx = existing_products + i
                category = rng.choice(CATEGORIES)
                adj = rng.choice(ADJECTIVES)
                noun = rng.choice(NOUNS)
                name = f"{adj} {noun} Model-{idx}"
                sku = f"SKU-{category[:3].upper()}-{idx:06d}"
                price = Decimal(f"{rng.uniform(5.99, 1299.99):.2f}")
                inventory = rng.randint(0, 500)

                prod_records.append({
                    "sku": sku,
                    "name": name,
                    "category": category,
                    "price": price,
                    "inventory_count": inventory,
                })

                if len(prod_records) >= batch_size:
                    db.execute(insert(Product), prod_records)
                    db.commit()
                    prod_records.clear()

            if prod_records:
                db.execute(insert(Product), prod_records)
                db.commit()
                prod_records.clear()

            print(f"  Done in {time.perf_counter() - prod_start:.2f}s")

        # Query product info for order item generation (id and price)
        products_data = db.execute(select(Product.id, Product.price)).all()
        product_pool = [(p[0], Decimal(str(p[1]))) for p in products_data]
        print(f"  Total Products available: {len(product_pool):,}")

        # ---------------------------------------------------------------------
        # 3. Seed Orders & Order Items
        # ---------------------------------------------------------------------
        orders_to_create = max(0, num_orders - existing_orders)
        if orders_to_create > 0:
            print(f"\n[3/4] Generating {orders_to_create:,} orders with multiple order items...")
            orders_start = time.perf_counter()

            order_date_base = datetime(2023, 6, 1, tzinfo=timezone.utc)
            order_date_now = datetime.now(timezone.utc)
            order_seconds_span = int((order_date_now - order_date_base).total_seconds())

            # We insert orders in batches to obtain generated IDs, then insert their items
            for batch_offset in range(0, orders_to_create, batch_size):
                current_batch_count = min(batch_size, orders_to_create - batch_offset)

                orders_batch: List[Dict[str, Any]] = []
                # Precompute order plans to calculate totals before inserting orders
                batch_plans = []

                for _ in range(current_batch_count):
                    u_id = rng.choice(user_ids)
                    status = rng.choices(ORDER_STATUSES, weights=STATUS_WEIGHTS)[0]
                    created_delta = timedelta(seconds=rng.randint(0, order_seconds_span))
                    order_date = order_date_base + created_delta

                    # Sample items
                    num_items = rng.randint(min_items_per_order, max_items_per_order)
                    chosen_products = rng.sample(product_pool, min(num_items, len(product_pool)))

                    total = Decimal("0.00")
                    item_plans = []
                    for p_id, unit_price in chosen_products:
                        qty = rng.randint(1, 5)
                        total += (unit_price * qty)
                        item_plans.append({
                            "product_id": p_id,
                            "quantity": qty,
                            "unit_price": unit_price,
                        })

                    batch_plans.append((item_plans, {
                        "user_id": u_id,
                        "order_date": order_date,
                        "status": status,
                        "total_amount": total,
                    }))

                # Bulk insert orders returning IDs
                order_insert_stmt = (
                    insert(Order)
                    .values([plan[1] for plan in batch_plans])
                    .returning(Order.id)
                )
                inserted_order_ids = db.scalars(order_insert_stmt).all()

                # Build items linking to the returned order IDs
                order_items_batch: List[Dict[str, Any]] = []
                for order_id, (item_plans, _) in zip(inserted_order_ids, batch_plans):
                    for item in item_plans:
                        order_items_batch.append({
                            "order_id": order_id,
                            "product_id": item["product_id"],
                            "quantity": item["quantity"],
                            "unit_price": item["unit_price"],
                        })

                # Bulk insert items
                if order_items_batch:
                    db.execute(insert(OrderItem), order_items_batch)

                db.commit()

                progress = min(batch_offset + current_batch_count, orders_to_create)
                print(f"    Inserted {progress:,} / {orders_to_create:,} orders...")

            print(f"  Done in {time.perf_counter() - orders_start:.2f}s")

    total_time = time.perf_counter() - start_total_time
    print("=" * 60)
    print(f"Dataset generation complete in {total_time:.2f}s!")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed PostgreSQL database with sample e-commerce dataset.")
    parser.add_argument("--users", type=int, default=10_000, help="Number of users to seed (default: 10,000)")
    parser.add_argument("--products", type=int, default=1_000, help="Number of products to seed (default: 1,000)")
    parser.add_argument("--orders", type=int, default=50_000, help="Number of orders to seed (default: 50,000)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility (default: 42)")
    parser.add_argument("--batch-size", type=int, default=5_000, help="Batch insert size (default: 5,000)")

    args = parser.parse_args()

    seed_database(
        num_users=args.users,
        num_products=args.products,
        num_orders=args.orders,
        random_seed=args.seed,
        batch_size=args.batch_size,
    )
