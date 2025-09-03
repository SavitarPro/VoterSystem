import os
import psycopg2
from psycopg2 import pool

class AdminConfig:
    # Database configuration
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '5432')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '1480')

    # Database names
    VOTE_DB = 'vote_db'
    REGISTRATION_DB = 'voter_registration_db'
    VOTER_AUTH_DB = 'voter_auth_db'

    # Admin configuration
    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')
    SECRET_KEY = os.getenv('ADMIN_SECRET_KEY', 'admin-secret-key-here')

    # Parties configuration (same as voting service)
    PARTIES = {
        '1': {'name': 'National Unity Party', 'logo': 'party1.png', 'color': '#007bff'},
        '2': {'name': 'People\'s Alliance', 'logo': 'party2.png', 'color': '#dc3545'},
        '3': {'name': 'Green Progress Party', 'logo': 'party3.png', 'color': '#28a745'},
        '4': {'name': 'Democratic Front', 'logo': 'party4.png', 'color': '#ffc107'},
        '5': {'name': 'Independent Coalition', 'logo': 'party5.png', 'color': '#6f42c1'}
    }

    # Create database connection pools
    try:
        vote_pool = pool.SimpleConnectionPool(
            1, 10,
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=VOTE_DB
        )

        registration_pool = pool.SimpleConnectionPool(
            1, 10,
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=REGISTRATION_DB
        )

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
        vote_pool = None
        registration_pool = None
        voter_auth_pool = None

admin_config = AdminConfig()