import psycopg2
from utils import get_db_connection


def get_voter_by_id(unique_id):
    """Get voter details by unique ID"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT unique_id, nic, full_name FROM voters WHERE unique_id = %s', (unique_id,))
        voter = cur.fetchone()

        if voter:
            return {
                'unique_id': voter[0],
                'nic': voter[1],
                'full_name': voter[2]
            }
        return None
    except Exception as e:
        print(f"Error getting voter: {e}")
        return None
    finally:
        if conn:
            cur.close()
            conn.close()