from fastapi import APIRouter, HTTPException
from database import get_db_connection
from datetime import datetime
from models import InventoryAction, QuantityUpdate, QuantityAdjustment

router = APIRouter()

@router.get("/movements")
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

@router.get("/products/{product_id}/movements")
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

@router.get("/products/{product_id}/inventory-summary")
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

@router.patch("/products/{product_id}/quantity")
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

@router.patch("/products/{product_id}/adjust-quantity")
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


@router.post("/products/unallocate")
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

def find_product_by_id(product_id: int):
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    row = cursor.fetchone()
    connection.close()

    if row is None:
        return None
    
    return dict(row)
