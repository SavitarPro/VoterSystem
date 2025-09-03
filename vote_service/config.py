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
    VOTE_DB = 'vote_db'
    VOTER_AUTH_DB = 'voter_auth_db'  # New database for authentication status

    # AI Model paths
    FINGERPRINT_MODEL_PATH = 'models/fingerprint_model.pkl'

    # File paths
    BLOCKCHAIN_FILE = 'blockchain/vote_chain.json'
    UPLOAD_FOLDER = 'static/images/uploads'

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

    # Parties configuration (needed for party selection page)
    PARTIES = {
        '1': {'name': 'National Unity Party', 'logo': 'party1.png', 'color': '#007bff'},
        '2': {'name': 'People\'s Alliance', 'logo': 'party2.png', 'color': '#dc3545'},
        '3': {'name': 'Green Progress Party', 'logo': 'party3.png', 'color': '#28a745'},
        '4': {'name': 'Democratic Front', 'logo': 'party4.png', 'color': '#ffc107'},
        '5': {'name': 'Independent Coalition', 'logo': 'party5.png', 'color': '#6f42c1'}
    }

    # Authorized officer IDs for override functionality
    AUTHORIZED_OFFICER_IDS = ['OFFICER_001', 'OFFICER_002', 'OFFICER_003', 'ADMIN_001']

    VOTE_PORT = 5004

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

        vote_pool = pool.SimpleConnectionPool(
            1, 10,
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=VOTE_DB
        )

        # New connection pool for voter authentication database
        voter_auth_pool = pool.SimpleConnectionPool(
            1, 10,
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=VOTER_AUTH_DB
        )
    except Exception as e:
        print(f"Database connection error: {e}")
        registration_pool = None
        vote_pool = None
        voter_auth_pool = None


config = Config()