import os
import psycopg2
from psycopg2 import pool


class Config:
    # Database configuration
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '5432')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '1480')

    # Database names
    REGISTRATION_DB = 'voter_registration_db'
    AUTH_DB = 'voter_auth_db'

    # AI Model paths
    FACE_MODEL_PATH = 'models/face_model.pkl'

    # File upload settings
    UPLOAD_FOLDER = 'static/images/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

    # Create database connection pool
    try:
        registration_pool = pool.SimpleConnectionPool(
            1, 10,
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=REGISTRATION_DB
        )

        auth_pool = pool.SimpleConnectionPool(
            1, 10,
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=AUTH_DB
        )
    except Exception as e:
        print(f"Database connection error: {e}")
        registration_pool = None
        auth_pool = None


config = Config()