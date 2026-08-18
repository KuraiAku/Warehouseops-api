from fastapi import APIRouter, HTTPException
from database import get_db_connection

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/orders-summary")
def get_orders_summary():
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
                COUNT(*) AS total_orders,
                COUNT(*) FILTER (WHERE status = 'pending') AS pending_orders,
                COUNT(*) FILTER (WHERE status = 'allocated') AS allocated_orders,
                COUNT(*) FILTER (WHERE status = 'picked') AS picked_orders,
                COUNT(*) FILTER (WHERE status = 'cancelled') AS cancelled_orders
            FROM orders
        """)

        summary = cursor.fetchone()
        return summary

    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))

    finally:
        cursor.close()
        connection.close()

@router.get("/inventory-status")
def get_inventory_status():
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
                COUNT(*) AS total_products,
                COALESCE(SUM(quantity), 0) AS total_quantity_on_hand,
                COALESCE(SUM(allocated_quantity), 0) AS total_allocated,
                COALESCE(SUM(quantity - allocated_quantity), 0) AS total_available,
                COUNT(*) FILTER (
                    WHERE (quantity - allocated_quantity) <= reorder_level
                ) AS low_stock_products
            FROM products
        """)

        summary = cursor.fetchone()
        return summary

    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))

    finally:
        cursor.close()
        connection.close()