import psycopg2
from utils import get_db_connection, get_central_db_connection, get_validity_db_connection


def check_nic_exists(nic):
    try:
        conn = get_central_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT * FROM central_voter_registry WHERE nic = %s', (nic,))
        return cur.fetchone() is not None
    except Exception as e:
        print(f"Error checking NIC: {e}")
        return False
    finally:
        if conn:
            cur.close()
            conn.close()


def register_voter(unique_id, nic, full_name, address, electoral_division, dob, face_image_path, fingerprint_path):
    conn = None
    central_conn = None
    validity_conn = None

    try:
        central_conn = get_central_db_connection()
        central_cur = central_conn.cursor()
        central_cur.execute(
            'INSERT INTO central_voter_registry (nic, electoral_division, date_of_birth) VALUES (%s, %s, %s)',
            (nic, electoral_division, dob)
        )
        central_conn.commit()
        central_cur.close()

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            '''INSERT INTO voters (unique_id, nic, full_name, address, electoral_division, date_of_birth, 
                                   face_image_path, fingerprint_path)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)''',
            (unique_id, nic, full_name, address, electoral_division, dob, face_image_path, fingerprint_path)
        )
        conn.commit()
        cur.close()

        validity_conn = get_validity_db_connection()
        validity_cur = validity_conn.cursor()
        validity_cur.execute(
            '''INSERT INTO voters (unique_id, nic, full_name, electoral_division, date_of_birth)
               VALUES (%s, %s, %s, %s, %s)''',
            (unique_id, nic, full_name, electoral_division, dob)
        )
        validity_conn.commit()
        validity_cur.close()

        return True

    except Exception as e:
        print(f"Error registering voter: {e}")
        try:
            if central_conn:
                central_cur = central_conn.cursor()
                central_cur.execute('DELETE FROM central_voter_registry WHERE nic = %s', (nic,))
                central_conn.commit()
                central_cur.close()
        except:
            pass

        try:
            if conn:
                cur = conn.cursor()
                cur.execute('DELETE FROM voters WHERE unique_id = %s', (unique_id,))
                conn.commit()
                cur.close()
        except:
            pass

        try:
            if validity_conn:
                validity_cur = validity_conn.cursor()
                validity_cur.execute('DELETE FROM voters WHERE unique_id = %s', (unique_id,))
                validity_conn.commit()
                validity_cur.close()
        except:
            pass

        return False

    finally:
        if conn:
            conn.close()
        if central_conn:
            central_conn.close()
        if validity_conn:
            validity_conn.close()