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