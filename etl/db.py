"""
etl/db.py
Centralised PostgreSQL connection helper.
Reads config from environment variables (injected by Docker Compose).
"""

import os
import psycopg2
import logging

logger = logging.getLogger(__name__)

DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "postgres"),
    "port":     int(os.getenv("DB_PORT", 5432)),
    "dbname":   os.getenv("DB_NAME", "ipo_db"),
    "user":     os.getenv("DB_USER", "ipo_user"),
    "password": os.getenv("DB_PASSWORD", "ipo_pass"),
}


def get_connection():
    """Return a live psycopg2 connection. Caller is responsible for closing it."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        logger.debug("DB connection established.")
        return conn
    except psycopg2.OperationalError as e:
        logger.error(f"DB connection failed: {e}")
        raise
