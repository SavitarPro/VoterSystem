import psycopg2
import sys
import os

# Add the parent directory to the path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config


def sync_voters():
    """Sync voter data from registration database to validity database"""
    try:
        # Connect to registration database
        reg_conn = psycopg2.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.REGISTRATION_DB
        )
        reg_cur = reg_conn.cursor()

        # Connect to validity database
        val_conn = psycopg2.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.VALIDITY_DB
        )
        val_cur = val_conn.cursor()

        # Get all voters from registration database
        reg_cur.execute('SELECT unique_id, nic, full_name, electoral_division FROM voters')
        voters = reg_cur.fetchall()

        # Insert or update voters in validity database
        for voter in voters:
            unique_id, nic, full_name, electoral_division = voter

            # Check if voter already exists in validity database
            val_cur.execute('SELECT * FROM voters WHERE unique_id = %s', (unique_id,))
            if val_cur.fetchone() is None:
                # Insert new voter
                val_cur.execute(
                    'INSERT INTO voters (unique_id, nic, full_name, electoral_division) VALUES (%s, %s, %s, %s)',
                    (unique_id, nic, full_name, electoral_division)
                )
                print(f"Added voter {unique_id} to validity database")
            else:
                # Update existing voter
                val_cur.execute(
                    'UPDATE voters SET nic = %s, full_name = %s, electoral_division = %s WHERE unique_id = %s',
                    (nic, full_name, electoral_division, unique_id)
                )
                print(f"Updated voter {unique_id} in validity database")

        val_conn.commit()
        print(f"Synced {len(voters)} voters to validity database")

    except Exception as e:
        print(f"Error syncing databases: {e}")

    finally:
        if reg_conn:
            reg_cur.close()
            reg_conn.close()
        if val_conn:
            val_cur.close()
            val_conn.close()


if __name__ == "__main__":
    sync_voters()