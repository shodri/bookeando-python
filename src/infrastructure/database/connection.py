"""Database connection management."""

import mysql.connector
from mysql.connector import MySQLConnection
from typing import Any

from src.config.settings import settings
from src.domain.exceptions import DatabaseConnectionError


def get_db_connection() -> MySQLConnection:
    """Create a new database connection.

    Returns:
        MySQL connection object.

    Raises:
        DatabaseConnectionError: If connection fails.
    """
    try:
        return mysql.connector.connect(**settings.db_connection_params)
    except mysql.connector.Error as e:
        raise DatabaseConnectionError(f"Failed to connect to database: {e}") from e

