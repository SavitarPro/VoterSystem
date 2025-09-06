import psycopg2
from psycopg2 import sql
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config

def create_database(db_name):
    try:
        conn = psycopg2.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database='postgres'
        )
        conn.autocommit = True
        cur = conn.cursor()

        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        exists = cur.fetchone()

        if not exists:
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name)))
            print(f"Database {db_name} created successfully")
        else:
            print(f"Database {db_name} already exists")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"Error creating database {db_name}: {e}")


def init_central_database():
    try:
        conn = psycopg2.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.CENTRAL_DB
        )
        cur = conn.cursor()

        cur.execute('''
                    CREATE TABLE IF NOT EXISTS central_voter_registry
                    (
                        id
                        SERIAL
                        PRIMARY
                        KEY,
                        nic
                        VARCHAR
                    (
                        20
                    ) UNIQUE NOT NULL,
                        electoral_division VARCHAR
                    (
                        100
                    ) NOT NULL,
                        registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')

        conn.commit()
        print("Central database initialized successfully")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"Error initializing central database: {e}")


def init_registration_database():
    try:
        conn = psycopg2.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.REGISTRATION_DB
        )
        cur = conn.cursor()

        cur.execute('''
                    CREATE TABLE IF NOT EXISTS voters
                    (
                        id
                        SERIAL
                        PRIMARY
                        KEY,
                        unique_id
                        VARCHAR
                    (
                        50
                    ) UNIQUE NOT NULL,
                        nic VARCHAR
                    (
                        20
                    ) NOT NULL,
                        full_name VARCHAR
                    (
                        100
                    ) NOT NULL,
                        address TEXT NOT NULL,
                        electoral_division VARCHAR
                    (
                        100
                    ) NOT NULL,
                        face_image_path VARCHAR
                    (
                        255
                    ) NOT NULL,
                        fingerprint_path VARCHAR
                    (
                        255
                    ) NOT NULL,
                        registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')

        conn.commit()
        print("Registration database initialized successfully")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"Error initializing registration database: {e}")


def init_validity_database():
    try:
        conn = psycopg2.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.VALIDITY_DB
        )
        cur = conn.cursor()

        cur.execute('''
                    CREATE TABLE IF NOT EXISTS voters
                    (
                        id
                        SERIAL
                        PRIMARY
                        KEY,
                        unique_id
                        VARCHAR
                    (
                        50
                    ) UNIQUE NOT NULL,
                        nic VARCHAR
                    (
                        20
                    ) NOT NULL,
                        full_name VARCHAR
                    (
                        100
                    ) NOT NULL,
                        electoral_division VARCHAR
                    (
                        100
                    ) NOT NULL
                        )
                    ''')

        conn.commit()
        print("Validity database initialized successfully")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"Error initializing validity database: {e}")


def init_auth_database():
    try:
        conn = psycopg2.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.AUTH_DB
        )
        cur = conn.cursor()

        cur.execute('''
                    CREATE TABLE IF NOT EXISTS voters
                    (
                        id
                        SERIAL
                        PRIMARY
                        KEY,
                        unique_id
                        VARCHAR
                    (
                        50
                    ) UNIQUE NOT NULL,
                        nic VARCHAR
                    (
                        20
                    ) NOT NULL,
                        full_name VARCHAR
                    (
                        100
                    ) NOT NULL,
                        face_image_path VARCHAR
                    (
                        255
                    ) NOT NULL,
                        fingerprint_path VARCHAR
                    (
                        255
                    ) NOT NULL
                        )
                    ''')

        conn.commit()
        print("Authentication database initialized successfully")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"Error initializing authentication database: {e}")


def init_vote_database():
    try:
        conn = psycopg2.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.VOTE_DB
        )
        cur = conn.cursor()

        cur.execute('''
                    CREATE TABLE IF NOT EXISTS votes
                    (
                        id
                        SERIAL
                        PRIMARY
                        KEY,
                        vote_data
                        JSONB
                        NOT
                        NULL,
                        block_hash
                        VARCHAR
                    (
                        255
                    ) NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')

        cur.execute('''
                    CREATE TABLE IF NOT EXISTS election_parties
                    (
                        id
                        SERIAL
                        PRIMARY
                        KEY,
                        name
                        VARCHAR
                    (
                        100
                    ) NOT NULL,
                        logo_path VARCHAR
                    (
                        255
                    ),
                        symbol VARCHAR
                    (
                        10
                    )
                        )
                    ''')

        cur.execute('''
                    INSERT INTO election_parties (name, logo_path, symbol)
                    VALUES ('United National Party', 'unp.png', 'Elephant'),
                           ('Sri Lanka Freedom Party', 'slfp.png', 'Hand'),
                           ('Janatha Vimukthi Peramuna', 'jvp.png', 'Bell'),
                           ('Illankai Tamil Arasu Kachchi', 'itak.png', 'House') ON CONFLICT DO NOTHING
                    ''')

        conn.commit()
        print("Vote database initialized successfully")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"Error initializing vote database: {e}")


def init_admin_database():
    try:
        conn = psycopg2.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.ADMIN_DB
        )
        cur = conn.cursor()

        cur.execute('''
                    CREATE TABLE IF NOT EXISTS activity_log
                    (
                        id
                        SERIAL
                        PRIMARY
                        KEY,
                        timestamp
                        TIMESTAMP
                        DEFAULT
                        CURRENT_TIMESTAMP,
                        voter_id
                        VARCHAR
                    (
                        50
                    ),
                        action VARCHAR
                    (
                        100
                    ),
                        status VARCHAR
                    (
                        20
                    )
                        )
                    ''')

        cur.execute('''
                    CREATE TABLE IF NOT EXISTS voting_status
                    (
                        id
                        SERIAL
                        PRIMARY
                        KEY,
                        is_active
                        BOOLEAN
                        DEFAULT
                        FALSE,
                        start_time
                        TIMESTAMP,
                        end_time
                        TIMESTAMP
                    )
                    ''')

        cur.execute('''
                    INSERT INTO voting_status (is_active)
                    VALUES (FALSE) ON CONFLICT DO NOTHING
                    ''')

        conn.commit()
        print("Admin database initialized successfully")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"Error initializing admin database: {e}")


def main():
    print("Initializing databases...")

    create_database(config.CENTRAL_DB)
    create_database(config.REGISTRATION_DB)
    create_database(config.VALIDITY_DB)
    create_database(config.AUTH_DB)
    create_database(config.VOTE_DB)
    create_database(config.ADMIN_DB)

    init_central_database()
    init_registration_database()
    init_validity_database()
    init_auth_database()
    init_vote_database()
    init_admin_database()

    print("All databases initialized successfully")


if __name__ == "__main__":
    main()