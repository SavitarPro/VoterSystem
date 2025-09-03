import psycopg2
from utils import get_db_connection
from blockchain import blockchain


def get_election_parties():
    """Get all election parties"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT id, name, logo_path, symbol FROM election_parties')
        parties = cur.fetchall()

        result = []
        for party in parties:
            result.append({
                'id': party[0],
                'name': party[1],
                'logo_path': party[2],
                'symbol': party[3]
            })
        return result
    except Exception as e:
        print(f"Error getting election parties: {e}")
        return []
    finally:
        if conn:
            cur.close()
            conn.close()


def submit_vote(unique_id, party_id):
    """Submit a vote"""
    try:
        # Create vote data (without voter identification for privacy)
        vote_data = {
            'party_id': party_id,
            'timestamp': time.time()
        }

        # Add to blockchain
        new_block = blockchain.add_vote(vote_data)

        # Also store in database for easy querying
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO votes (vote_data, block_hash) VALUES (%s, %s)',
            (json.dumps(vote_data), new_block['hash'])
        )
        conn.commit()

        return new_block['hash']
    except Exception as e:
        print(f"Error submitting vote: {e}")
        return None
    finally:
        if conn:
            cur.close()
            conn.close()