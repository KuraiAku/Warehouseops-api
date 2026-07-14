import os

import pytest
import psycopg2
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from psycopg2.extras import RealDictCursor


load_dotenv()


def get_test_connection():
    return psycopg2.connect(
        dbname=os.getenv("TEST_DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        cursor_factory=RealDictCursor
    )


@pytest.fixture
def client():
    os.environ["DB_NAME"] = os.getenv("TEST_DB_NAME")

    connection = get_test_connection()
    cursor = connection.cursor()

    cursor.execute("DROP TABLE IF EXISTS order_items")
    cursor.execute("DROP TABLE IF EXISTS orders")
    cursor.execute("DROP TABLE IF EXISTS inventory_movements")
    cursor.execute("DROP TABLE IF EXISTS products")

    cursor.execute("""
    CREATE TABLE products (
        id SERIAL PRIMARY KEY,
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
        id SERIAL PRIMARY KEY,
        product_id INTEGER NOT NULL REFERENCES products(id),
        change INTEGER NOT NULL,
        reason TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE orders (
        id SERIAL PRIMARY KEY,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE order_items (
        id SERIAL PRIMARY KEY,
        order_id INTEGER NOT NULL REFERENCES orders(id),
        product_id INTEGER NOT NULL REFERENCES products(id),
        quantity INTEGER NOT NULL,
        status TEXT NOT NULL
    )
    """)

    connection.commit()
    cursor.close()
    connection.close()

    from main import app

    test_client = TestClient(app)

    yield test_client

    connection = get_test_connection()
    cursor = connection.cursor()

    cursor.execute("DROP TABLE IF EXISTS order_items")
    cursor.execute("DROP TABLE IF EXISTS orders")
    cursor.execute("DROP TABLE IF EXISTS inventory_movements")
    cursor.execute("DROP TABLE IF EXISTS products")

    connection.commit()
    cursor.close()
    connection.close()

    os.environ["DB_NAME"] = "warehouse_ops"
    