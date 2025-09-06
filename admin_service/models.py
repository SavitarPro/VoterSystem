from utils import get_db_connection


def get_voting_stats():
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute('SELECT COUNT(*) FROM voters')
        total_voters = cur.fetchone()[0]

        cur.execute('SELECT COUNT(*) FROM votes')
        votes_count = cur.fetchone()[0]

        cur.execute('''
                    SELECT ep.name, COUNT(v.id)
                    FROM election_parties ep
                             LEFT JOIN votes v ON v.vote_data ->>'party_id' = ep.id::text
                    GROUP BY ep.id, ep.name
                    ''')
        votes_by_party = cur.fetchall()

        cur.execute('SELECT COUNT(*) FROM activity_log WHERE status = %s', ('approved',))
        approved_count = cur.fetchone()[0]

        cur.execute('SELECT COUNT(*) FROM activity_log WHERE status = %s', ('rejected',))
        rejected_count = cur.fetchone()[0]

        return {
            'total_voters': total_voters,
            'votes_submitted': votes_count,
            'votes_approved': approved_count,
            'votes_rejected': rejected_count,
            'party_votes': [vote[1] for vote in votes_by_party],
            'party_names': [vote[0] for vote in votes_by_party]
        }
    except Exception as e:
        print(f"Error getting voting stats: {e}")
        return {}
    finally:
        if conn:
            cur.close()
            conn.close()


def get_activity_log():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
                    SELECT timestamp, voter_id, action, status
                    FROM activity_log
                    ORDER BY timestamp DESC
                        LIMIT 10
                    ''')
        activities = cur.fetchall()

        result = []
        for activity in activities:
            result.append({
                'timestamp': activity[0],
                'voter_id': activity[1],
                'action': activity[2],
                'status': activity[3]
            })
        return result
    except Exception as e:
        print(f"Error getting activity log: {e}")
        return []
    finally:
        if conn:
            cur.close()
            conn.close()


def add_activity_log(voter_id, action, status):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO activity_log (voter_id, action, status) VALUES (%s, %s, %s)',
            (voter_id, action, status)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Error adding activity log: {e}")
        return False
    finally:
        if conn:
            cur.close()
            conn.close()


def set_voting_status(is_active):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            'UPDATE voting_status SET is_active = %s',
            (is_active,)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Error setting voting status: {e}")
        return False
    finally:
        if conn:
            cur.close()
            conn.close()


def get_voting_status():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT is_active FROM voting_status')
        status = cur.fetchone()
        return status[0] if status else False
    except Exception as e:
        print(f"Error getting voting status: {e}")
        return False
    finally:
        if conn:
            cur.close()
            conn.close()