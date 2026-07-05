import os
import sqlite3


def get_db_connection():
    database_name = os.getenv("DATABASE_NAME", "warehouse.db")

    connection = sqlite3.connect(database_name)
    connection.row_factory = sqlite3.Row
    return connection