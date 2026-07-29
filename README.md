# WarehouseOps API

WarehouseOps API is a backend project I built to practice real warehouse inventory and order workflows.

It lets you manage products, create orders, allocate inventory, pick orders, cancel orders, and track inventory movement history.

The main goal of this project is to practice backend development fundamentals like API design, SQL, database state, transactions, and testing.

---

## Tech Used

- Python
- FastAPI
- PostgreSQL
- Raw SQL
- Pydantic
- Pytest
- Uvicorn

---

## What It Does

### Products

- Add new products
- View all products
- View one product by ID
- Update product information
- Delete products
- Search products by category or location
- View low-stock products

### Orders

- Create orders with one or more products
- Allocate inventory to an order
- Pick an allocated order
- Cancel orders when allowed

### Inventory

- Track quantity on hand
- Track allocated quantity
- Calculate available quantity
- Record inventory movements when stock changes

---

## Main Business Rules

- SKUs must be unique.
- Orders need at least one item.
- Item quantities must be positive.
- Only pending orders can be allocated.
- Orders cannot be allocated if there is not enough available inventory.
- Only allocated orders can be picked.
- Picking an order reduces the product quantity and allocated quantity.
- Picked orders cannot be cancelled.

---

## Order Flow

```text
pending → allocated → picked
pending → cancelled
allocated → cancelled
```

---

## Project Structure

```text
warehouse_ops_api/
│
├── main.py
├── database.py
├── models.py
├── init_postgres.py
├── requirements.txt
├── README.md
│
├── routes/
│   ├── products.py
│   ├── orders.py
│   └── inventory.py
│
└── tests/
    ├── conftest.py
    ├── test_basic.py
    ├── test_products.py
    ├── test_orders.py
    └── test_order_workflow.py
```

---

## Environment Variables

Create a `.env` file in the project root.

```env
DB_NAME=warehouse_ops
TEST_DB_NAME=warehouse_ops_test
DB_USER=postgres
DB_PASSWORD=your_password_here
DB_HOST=localhost
DB_PORT=5432
```

The `.env` file should not be committed to GitHub.

---

## Setup

Create and activate a virtual environment:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Create the PostgreSQL databases:

```sql
CREATE DATABASE warehouse_ops;
CREATE DATABASE warehouse_ops_test;
```

Initialize the main database:

```powershell
python init_postgres.py
```

Run the API:

```powershell
uvicorn main:app --reload
```

Open the docs:

```text
http://127.0.0.1:8000/docs
```

---


---

## Example API Flow

### 1. Create a product

```http
POST /products
```

```json
{
  "sku": "BOX-1001",
  "name": "Shipping Boxes",
  "category": "Packaging",
  "quantity": 100,
  "location": "Aisle 3 - Bin 12",
  "reorder_level": 20
}
```

### 2. Create an order

```http
POST /orders
```

```json
{
  "items": [
    {
      "product_id": 1,
      "quantity": 5
    }
  ]
}
```

### 3. Allocate the order

```http
POST /orders/1/allocate
```

Allocation reserves inventory for the order.

### 4. Pick the order

```http
POST /orders/1/pick
```

Picking removes the inventory from quantity on hand and reduces allocated quantity.


## Testing

The project uses pytest with a separate PostgreSQL test database.

The tests cover the main product, order, and inventory workflow rules.

Run tests:

```powershell
python -m pytest
```

Current tests include:

- Creating products
- Rejecting duplicate SKUs
- Creating orders
- Rejecting orders with invalid products
- Allocating orders
- Rejecting allocation when inventory is too low
- Picking orders
- Preventing picking before allocation
- Preventing cancellation after picking

---

## What I Practiced

While building this project, I practiced:

- FastAPI routes
- Pydantic request models
- Raw SQL queries
- PostgreSQL setup
- Database transactions
- Error handling with HTTP status codes
- Business rule validation
- Pytest integration tests
- Using a separate test database

---

## Future Improvements

Some things I may add later:

- SQLAlchemy
- User login and roles
- Pagination
- Docker
- Better logging
- Deployment setup
- Alembic migrations

---

## Project Status

This project is still being improved. Right now, the main backend workflow is working with PostgreSQL and pytest tests.