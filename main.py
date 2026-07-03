from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from database import get_db_connection
from datetime import datetime
import sqlite3
from routes.products import router as products_router

from models import (
    ProductCreate,
    ProductUpdate,
    QuantityUpdate,
    QuantityAdjustment,
    InventoryAction,
    OrderItemCreate,
    OrderCreate,
)



app = FastAPI()
app.include_router(products_router)

@app.get("/")
def home():
    return {"message": "Warehouseops API is running!"}

@app.get('/products/low-stock')
def get_low_stock_products():
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM products WHERE quantity < reorder_level")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        if connection:
            connection.close()



@app.get("/products/search")
def search_products(category: str = None, location: str = None):
    if category is None and location is None:
        raise HTTPException(status_code=400, detail="Category or location is required")
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        if category is not None and location is not None:
            cursor.execute(
            "SELECT * FROM products WHERE category = ? AND location = ?",
            (category, location)
        )
        elif category is not None:
            cursor.execute(
                "SELECT * FROM products WHERE category = ?", (category,)
            )
        else:
            cursor.execute(
                "SELECT * FROM products WHERE location = ?", (location,)
                )
        rows = cursor.fetchall()

        if not rows:
            raise HTTPException(status_code=404, detail="Product not found")
        return [dict(row) for row in rows]
    
    finally:
        if connection:
            connection.close()

@app.get("/movements")
def get_all_movements():
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("""
        SELECT 
            inventory_movements.id AS movement_id,  
            inventory_movements.product_id, 
            products.sku, 
            products.name,  
            products.category,
            products.location, 
            inventory_movements.change, 
            inventory_movements.reason, 
            inventory_movements.created_at
        FROM inventory_movements 
        JOIN products 
        ON inventory_movements.product_id = products.id  
        ORDER BY inventory_movements.created_at DESC
        """)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    finally:
        if connection:
            connection.close()

@app.get("/products/{product_id}")
def get_product_by_id(product_id: int):
    product = find_product_by_id(product_id)
    
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return product


@app.post("/products", status_code=201)
def add_product(product: ProductCreate):
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(""" 
        INSERT INTO products (sku, name, category, quantity, location, reorder_level, allocated_quantity) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            product.sku, 
            product.name, 
            product.category, 
            product.quantity, 
            product.location, 
            product.reorder_level,
            0
        ))

        connection.commit()
        new_product_id = cursor.lastrowid

        return {"message": "Product added successfully",
             "product_id": new_product_id
            }

    except sqlite3.IntegrityError:
        if connection:
            connection.rollback()
        raise HTTPException(status_code=409, detail="Product already exists or violates a database constraint")
    except Exception as e:
        if connection:
            connection.rollback()
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        if connection:
            connection.close()

@app.post("/orders/{order_id}/allocate")
def allocate_order(order_id: int):
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        order_row = cursor.fetchone()

        if order_row is None:
            raise HTTPException(status_code=404, detail="Order not found")
        if order_row["status"] != "pending":
            raise HTTPException(status_code=400, detail="Only pending orders can be allocated")
        
             
        
        cursor.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,))
        order_items = cursor.fetchall()

        if not order_items:
            raise HTTPException(status_code=400, detail="Order has no items")
        
        order_items_quantities = {}
    
        for item in order_items:
            if item["quantity"] <= 0:
                raise HTTPException(status_code=400, detail="Order item quantity must be positive")
            
            product_id = item["product_id"]
            item_quantity = item["quantity"]

            if product_id not in order_items_quantities:
                order_items_quantities[product_id] = item_quantity

            else:
                order_items_quantities[product_id] += item_quantity

        for product_id, total_requested_quantity in order_items_quantities.items():

            cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
            product = cursor.fetchone()

            if product is None:
                raise HTTPException(status_code=404, detail="No Product found in orders")
            
            quantity_on_hand = product["quantity"]
            allocated_quantity = product["allocated_quantity"]
            available_quantity = quantity_on_hand - allocated_quantity

            if total_requested_quantity > available_quantity:
                raise HTTPException(status_code=400, detail="Not enough inventory to allocate order")
            
           
        
        for product_id, total_requested_quantity in order_items_quantities.items():
            
        
            cursor.execute("UPDATE products SET allocated_quantity = allocated_quantity + ? WHERE id = ?", (total_requested_quantity, product_id))
        
        cursor.execute("UPDATE order_items SET status = ? WHERE order_id = ?", ("allocated", order_id))
        cursor.execute("UPDATE orders SET status = ? WHERE id = ?", ("allocated", order_id))
        connection.commit()

        return {
            "message": "Order allocated successfully",
            "allocated_items": order_items_quantities,
            "order_id": order_id,
            "status": "allocated"
        }
    except HTTPException:
        if connection:
            connection.rollback()
        raise

    except Exception as e:
        if connection:
            connection.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    finally:
        if connection:
            connection.close()


@app.post("/orders/{order_id}/pick")
def pick_order(order_id: int):
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        order_row = cursor.fetchone()

        if order_row is None:
            raise HTTPException(status_code=404, detail="Order does not exist")
        
        if order_row["status"] != "allocated":
            raise HTTPException(status_code=400, detail=("Only orders with allocated status can be picked"))
        
        cursor.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,))
        item_in_orders = cursor.fetchall()

        if not item_in_orders:
            raise HTTPException(status_code=404, detail="No orders available to pick")
        
        for item in item_in_orders:
            cursor.execute("SELECT * FROM products WHERE id = ?", (item["product_id"],))
            product = cursor.fetchone()

            if product is None:
                raise HTTPException(status_code=404, detail="Product does not exist")
            
            new_quantity = product["quantity"] - item["quantity"]
            new_allocated = product["allocated_quantity"] - item["quantity"]

            if new_quantity < 0:
                raise HTTPException(status_code=400, detail="Quantity can not be less than zero")
            if new_allocated < 0:
                raise HTTPException(status_code=400, detail="Cannot pick more than allocated quantity")
            
            created_at = datetime.now().isoformat()

            cursor.execute("INSERT INTO inventory_movements (product_id, change, reason, created_at) VALUES (?,?,?,?)",
                            (item["product_id"], -item["quantity"], "Item picked", created_at))
            
            cursor.execute("UPDATE products SET quantity = ?, allocated_quantity = ? WHERE id = ?",
                            (new_quantity, new_allocated, item["product_id"]))

        cursor.execute("UPDATE order_items SET status = ? WHERE order_id = ?", ("picked", order_id))
        cursor.execute("UPDATE orders SET status = ? WHERE id = ?", ("picked", order_id))
        connection.commit()
        return {"message": "Order picked successfully", "order_id": order_id}

    except HTTPException:
        if connection: 
            connection.rollback()
        raise

    except Exception:
        if connection:
            connection.rollback()
        raise HTTPException(status_code=500, detail="Database error")
    
    finally:
        if connection:
            connection.close() 

@app.post("/orders/{order_id}/cancel")
def cancel_order(order_id: int):
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))

        order_row = cursor.fetchone()
        if order_row is None:
            raise HTTPException(status_code=404, detail="No order found")

        if order_row["status"] == "picked":
            raise HTTPException(status_code=400, detail="Picked orders can not be cancelled")
        
        elif order_row["status"] == "cancelled":
            raise HTTPException(status_code=400, detail="Order is already cancelled")

        cursor.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,))
        order_items = cursor.fetchall()

        if not order_items:
            raise HTTPException(status_code=404, detail="No orders to be cancelled")
        
        for item in order_items:
            cursor.execute("SELECT * FROM products WHERE id = ?", (item["product_id"],)) 
            product = cursor.fetchone()

            if product is None:
                raise HTTPException(status_code=404, detail="Product does not exist")
                
            if item["status"] == "allocated":
                new_allocated = product["allocated_quantity"] - item["quantity"]

                if new_allocated < 0:
                    raise HTTPException(status_code=400, detail="Allocated quantity can not be less than zero")
                cursor.execute("UPDATE products SET allocated_quantity = ? WHERE id = ?", (new_allocated, item["product_id"]))                           
            
            
        cursor.execute("UPDATE orders SET status = ? WHERE id = ?", ("cancelled", order_id))
        cursor.execute("UPDATE order_items SET status = ? WHERE order_id = ?", ("cancelled", order_id))
        connection.commit()
        return {"message": "Order cancelled successfully", "order_id": order_id}

    except HTTPException:
        if connection:
            connection.rollback()
        raise

    except Exception:
        if connection:
            connection.rollback()
        raise HTTPException(status_code=500, detail="Database error")
    
    finally:
        if connection:
            connection.close()
    


@app.post("/products/unallocate")
def unallocate_order(order: InventoryAction):
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM products WHERE id = ?", (order.product_id,)) 
        row = cursor.fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail=("Product does not exist"))
        
        if order.quantity <= 0:
            raise HTTPException(status_code=400, detail="Quantity must be positive")
        
        quantity = row["quantity"]
        allocated_quantity = row["allocated_quantity"]
        unallocated_quantity = order.quantity
        if unallocated_quantity > allocated_quantity:
            raise HTTPException(status_code=400, detail="Cannot unallocate more than allocated quantity")
        
        new_allocated = allocated_quantity - unallocated_quantity
        available_quantity = quantity - new_allocated


        cursor.execute("UPDATE products SET allocated_quantity = ? WHERE id = ?", (new_allocated, order.product_id))
        connection.commit()
       

        return {
            "message": "Inventory unallocated successfully",
            "product_id": order.product_id,
            "quantity_on_hand": quantity,
            "old_allocated": allocated_quantity,
            "new_allocated": new_allocated,
            "available": available_quantity
            }

    except HTTPException:
        if connection:
            connection.rollback()
        raise

    except Exception:
        if connection:
            connection.rollback()
        raise HTTPException(status_code=500, detail="Database error")
        
    finally:
        if connection:
            connection.close()


@app.post("/orders")
def create_order(order: OrderCreate):
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        created_at = datetime.now().isoformat()

        if not order.items:
            raise HTTPException(status_code=400, detail="Order must have at least one item")

       
        for item in order.items:
            if item.quantity <= 0:
                raise HTTPException(status_code=400, detail="Item quantity must be positive")

            cursor.execute("SELECT * FROM products WHERE id = ?", (item.product_id,))
            product = cursor.fetchone()

            if product is None:
                raise HTTPException(status_code=404, detail="Product not found")

        
        cursor.execute(
            "INSERT INTO orders (status, created_at) VALUES (?, ?)",
            ("pending", created_at)
        )

        new_order_id = cursor.lastrowid

        
        for item in order.items:
            cursor.execute(
                "INSERT INTO order_items (order_id, product_id, quantity, status) VALUES (?, ?, ?, ?)",
                (new_order_id, item.product_id, item.quantity, "pending")
            )

        connection.commit()

        return {
            "items": [
                {
                    "product_id": item.product_id,
                    "quantity": item.quantity,
                    "status": "pending"
                }
                for item in order.items
            ]
        }

    except HTTPException:
        if connection:
            connection.rollback()
        raise

    except Exception as e:
        if connection:
            connection.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if connection:
            connection.close()

@app.delete("/products/{product_id}")
def delete_product(product_id: int):
    connection = None

    try:    
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        row = cursor.fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail="Product not found")
        cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
        connection.commit()

        return {"message": "Product has been successfully deleted", "deleted_product": dict(row)}
    
    except HTTPException:
        if connection:
            connection.rollback()
        raise

    except Exception:
        if connection:
            connection.rollback()
        raise HTTPException(status_code=500, detail="Database error")
        
    finally:
        if connection:
            connection.close()

@app.put("/products/{product_id}")
def update_product(product_id: int, product: ProductUpdate):
    connection  = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        row = cursor.fetchone()   

        if row is None:
            raise HTTPException(status_code=404, detail = "Product not found")
        
        cursor.execute(
            "UPDATE products SET sku = ?, name = ?, category = ?, quantity = ?, location = ?, reorder_level = ?  WHERE id = ?", 
            (product.sku, product.name, product.category, product.quantity, product.location, product.reorder_level, product_id)
            
            )
        connection.commit()
        return {"message" : "Product has been updated successfully"}
    except HTTPException:
        if connection:
            connection.rollback()
        raise

    except Exception:
        if connection:
            connection.rollback()
        raise HTTPException(status_code=500, detail="Database error")
        
    finally:
        if connection:
            connection.close()


@app.get("/products/{product_id}/movements")
def get_product_movements(product_id: int):
    product = find_product_by_id(product_id)

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("""
        SELECT
        inventory_movements.id AS movement_id,
        inventory_movements.product_id,
        inventory_movements.reason,
        products.sku,
        products.name,
        inventory_movements.change,
        inventory_movements.created_at
        FROM inventory_movements
        JOIN products
        ON inventory_movements.product_id = products.id
        WHERE inventory_movements.product_id = ?  
        ORDER BY inventory_movements.created_at DESC""", (product_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    except Exception:
        raise HTTPException(status_code=500, detail="Database error")
    
    finally:
        if connection:
            connection.close()

@app.get("/products/{product_id}/inventory-summary")
def inventory_summary(product_id: int):
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,) )
        row = cursor.fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail="Product not found")
        
        quantity_on_hand = row["quantity"]
        allocated_quantity = row["allocated_quantity"]
        available_quantity = quantity_on_hand - allocated_quantity
        reorder_level = row["reorder_level"]

        if quantity_on_hand <= reorder_level:
            stock_status = "low_stock"
        else:
            stock_status = "in_stock"

        return {
        "product_id": product_id,
        "sku": row["sku"],
        "name": row["name"],
        "quantity_on_hand": quantity_on_hand,
        "allocated_quantity": allocated_quantity,
        "available_quantity": available_quantity,
        "reorder_level": reorder_level,
        "stock_status": stock_status
    }
    except HTTPException:
        raise
    
    except Exception:
        raise HTTPException(status_code=500, detail="Database error")
    
    finally:
        if connection:
            connection.close()


@app.get("/orders/{order_id}")
def get_order(order_id: int):
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        order_row = cursor.fetchone()
    

        if order_row is None:
            raise HTTPException(status_code=404, detail="Order not found")
        
        order_id_db = order_row["id"]
        status = order_row["status"]
        created_time = order_row["created_at"]

        cursor.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,))
        item_rows = cursor.fetchall()
        item_list = [dict(item) for item in item_rows]
        return {
        "order_id": order_id_db,
        "status": status,
        "created_at": created_time,
        "items_list": item_list
    }
    except HTTPException:
        raise

    except Exception:
        raise HTTPException(status_code=500, detail="Database error")
    
    finally:
        if connection:
            connection.close()


@app.patch("/products/{product_id}/quantity")
def update_product_quantity(product_id: int, update: QuantityUpdate):
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "SELECT * FROM products WHERE id = ?",
            (product_id,)
        )
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Product not found")
        
        if update.quantity < 0:
            raise HTTPException(status_code=400, detail="Quantity cannot be negative")
        
        current_quantity = row["quantity"]
        change = update.quantity - current_quantity
        cursor.execute(
            "UPDATE products SET quantity = ? WHERE id = ?", 
            (update.quantity, product_id)
        )
        created_at = datetime.now().isoformat()
        cursor.execute("INSERT INTO inventory_movements (product_id, change, reason, created_at) VALUES (?,?,?,?)", 
                    (product_id, change, "Manual quantity correction", created_at))

        connection.commit()
        return {
            "message": "Product quantity has been updated successfully",
            "old_quantity": current_quantity,
            "new_quantity": update.quantity,
            "change": change
    }
    except HTTPException:
        if connection:
            connection.rollback()
        raise

    except Exception:
        if connection:
            connection.rollback()
        raise HTTPException(status_code=500, detail="Database error")

    finally:
        if connection:
            connection.close()

@app.patch("/products/{product_id}/adjust-quantity")
def adjust_product_quantity(product_id: int, update: QuantityAdjustment):
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "SELECT * FROM products WHERE id = ?", 
            (product_id,)
        )
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Product not found")
        current_quantity = row["quantity"]
        new_quantity = current_quantity + update.change
        if new_quantity < 0:
            raise HTTPException(status_code=400, detail="Quantity can not be negative")

        cursor.execute(
            "UPDATE products SET quantity = quantity + ? WHERE id = ?", 
            (update.change, product_id)
        )
        created_at = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO inventory_movements (product_id, change, reason, created_at) VALUES (?,?,?,?)", 
            (product_id, update.change, update.reason, created_at)
        
        )
        connection.commit()
        return {
            "message": "Product quantity has been adjusted successfully",
            "old_quantity": current_quantity,
            "new_quantity": new_quantity,
            "change": update.change,
            "reason": update.reason
    }
    except HTTPException:
        if connection:
            connection.rollback()
        raise
    except Exception:
        if connection:
            connection.rollback()
        raise HTTPException(status_code=500, detail="Database error")

    finally:
        if connection:
            connection.close()




def find_product_by_id(product_id: int):
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    row = cursor.fetchone()
    connection.close()

    if row is None:
        return None
    
    return dict(row)