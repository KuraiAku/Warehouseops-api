import sqlite3

connection = sqlite3.connect("warehouse.db")
cursor = connection.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS products (
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
CREATE TABLE IF NOT EXISTS inventory_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    change INTEGER NOT NULL,
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products(id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    status TEXT NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
)
""")

starter_products = [
    ("BOX-1001", "Shipping Boxes", "Packaging", 250, "Aisle 3 - Bin 12", 100, 0),
    ("PAL-2001", "Wood Pallets", "Warehouse Supplies", 45, "Dock Area", 50, 0),
    ("WRAP-3001", "Stretch Wrap", "Packaging", 20, "Aisle 1 - Bin 4", 25, 0)
]

cursor.executemany("""
INSERT OR IGNORE INTO products (
    sku, name, category, quantity, location, reorder_level, allocated_quantity
)
VALUES (?, ?, ?, ?, ?, ?, ?)
""", starter_products)

connection.commit()

cursor.execute("SELECT * FROM products")
rows = cursor.fetchall()
print(rows)

connection.close()