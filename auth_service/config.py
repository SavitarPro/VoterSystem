import os
from psycopg2 import pool


class Config:

    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '5432')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '1480')


    REGISTRATION_DB = 'voter_registration_db'
    AUTH_DB = 'voter_auth_db'

    AUTH_PORT = 5003


    FACE_MODEL_PATH = 'models/face_model.h5'


    UPLOAD_FOLDER = 'static/images/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}


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