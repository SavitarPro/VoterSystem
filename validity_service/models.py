import psycopg2
import re
import uuid
from utils import get_db_connection, log_activity


def validate_unique_id(unique_id):

    if not unique_id or not isinstance(unique_id, str):
        return False

    try:
        uuid_obj = uuid.UUID(unique_id, version=4)
        return str(uuid_obj) == unique_id
    except ValueError:
        return False


def get_voter_by_id(unique_id, ip_address):
    
    
    if not validate_unique_id(unique_id):
        log_activity('WARNING', f'Invalid unique ID format: {unique_id}', ip_address)
        return None

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT unique_id, nic, full_name FROM voters WHERE unique_id = %s', (unique_id,))
        voter = cur.fetchone()

        if voter:
            log_activity('INFO', f'Valid voter found: {unique_id}', ip_address)
            return {
                'unique_id': voter[0],
                'nic': voter[1],
                'full_name': voter[2]
            }

        log_activity('WARNING', f'No voter found with ID: {unique_id}', ip_address)
        return None
    except Exception as e:
        error_msg = f"Error getting voter: {e}"
        log_activity('ERROR', error_msg, ip_address)
        return None
    finally:
        if conn:
            cur.close()
            conn.close()