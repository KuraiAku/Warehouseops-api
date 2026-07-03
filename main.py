from fastapi import FastAPI, HTTPException
from database import get_db_connection
from datetime import datetime
import sqlite3
from routes.products import router as products_router

from models import (
    InventoryAction,
    OrderCreate,
)



app = FastAPI()
app.include_router(products_router)

@app.get("/")
def home():
    return {"message": "Warehouseops API is running!"}



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





 