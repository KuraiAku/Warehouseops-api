from fastapi import APIRouter, HTTPException
from database import get_db_connection
import sqlite3
from datetime import datetime
from models import (
ProductCreate,
ProductUpdate, 
QuantityUpdate, 
QuantityAdjustment,
)

router = APIRouter()

@router.get("/products")
def get_products():
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM products")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        if connection:
            connection.close()


@router.get('/products/low-stock')
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



@router.get("/products/search")
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


@router.get("/products/{product_id}")
def get_product_by_id(product_id: int):
    product = find_product_by_id(product_id)
    
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return product


@router.post("/products", status_code=201)
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

@router.put("/products/{product_id}")
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


@router.delete("/products/{product_id}")
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


def find_product_by_id(product_id: int):
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    row = cursor.fetchone()
    connection.close()

    if row is None:
        return None
    
    return dict(row)