from fastapi import FastAPI, HTTPException
from database import get_db_connection
from datetime import datetime
import sqlite3
from routes.products import router as products_router
from routes.orders import router as orders_router
from models import (
    InventoryAction,
    OrderCreate,
)



app = FastAPI()
app.include_router(products_router)
app.include_router(products_router)
app.include_router(orders_router)

@app.get("/")
def home():
    return {"message": "Warehouseops API is running!"}




    


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









 