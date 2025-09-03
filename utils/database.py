import psycopg2
from config import config

def get_db_connection(db_name):
    """Get database connection for specified database"""
    return psycopg2.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=db_name
    )