from database import get_db_connection


def init_db():
    connection = get_db_connection()
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

    print("PostgreSQL database initialized successfully.")


if __name__ == "__main__":
    init_db()