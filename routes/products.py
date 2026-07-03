from fastapi import APIRouter
from database import get_db_connection

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