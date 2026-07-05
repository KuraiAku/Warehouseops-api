import os
import sqlite3
import pytest
from fastapi.testclient import TestClient


TEST_DATABASE = "test_warehouse.db"


@pytest.fixture
def client():
    os.environ["DATABASE_NAME"] = TEST_DATABASE

    connection = sqlite3.connect(TEST_DATABASE)
    cursor = connection.cursor()

    cursor.execute("DROP TABLE IF EXISTS order_items")
    cursor.execute("DROP TABLE IF EXISTS orders")
    cursor.execute("DROP TABLE IF EXISTS inventory_movements")
    cursor.execute("DROP TABLE IF EXISTS products")

    cursor.execute("""
    CREATE TABLE products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sku TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        location TEXT NOT NULL,
        reorder_level INTEGER NOT NULL,
        allocated_quantity INTEGER NOT NULL DEFAULT 0
    )
    """)

    cursor.execute("""
    CREATE TABLE inventory_movements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        change INTEGER NOT NULL,
        reason TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (product_id) REFERENCES products(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        status TEXT NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(id),
        FOREIGN KEY (product_id) REFERENCES products(id)
    )
    """)

    connection.commit()
    connection.close()

    from main import app

    test_client = TestClient(app)

    yield test_client

    os.environ.pop("DATABASE_NAME", None)

    if os.path.exists(TEST_DATABASE):
        os.remove(TEST_DATABASE)