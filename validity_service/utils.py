from flask import current_app
import psycopg2
from config import config

def init_app(app):
    """Initialize the application"""
    pass

def get_db_connection():
    """Get database connection for validity service"""
    return psycopg2.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.VALIDITY_DB
    )