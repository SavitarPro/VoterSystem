from flask import Blueprint, render_template, jsonify, session, request
import psycopg2
from datetime import datetime

# Import config directly (no relative import)
try:
    from config import admin_config
except ImportError:
    # Fallback for direct execution
    import sys
    import os

    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from config import admin_config

# Create admin blueprint
admin_bp = Blueprint('admin', __name__)


class AdminManager:
    def __init__(self):
        self.vote_pool = admin_config.vote_pool
        self.registration_pool = admin_config.registration_pool

    def get_election_results(self):
        """Get comprehensive election results from anonymous_votes table"""
        if not self.vote_pool:
            return None

        conn = self.vote_pool.getconn()
        try:
            with conn.cursor() as cursor:
                # Get total votes per party
                cursor.execute('''
                               SELECT party_code, COUNT(*) as vote_count
                               FROM anonymous_votes
                               GROUP BY party_code
                               ORDER BY vote_count DESC
                               ''')
                party_results = cursor.fetchall()

                # Get total votes
                cursor.execute('SELECT COUNT(*) FROM anonymous_votes')
                total_votes_result = cursor.fetchone()
                total_votes = total_votes_result[0] if total_votes_result else 0

                # Get voting timeline (votes per hour)
                cursor.execute('''
                               SELECT DATE_TRUNC('hour', vote_time) as hour, 
                           COUNT(*) as votes_per_hour
                               FROM anonymous_votes
                               GROUP BY hour
                               ORDER BY hour
                               ''')
                timeline_data = cursor.fetchall()

                return {
                    'party_results': party_results or [],
                    'total_votes': total_votes,
                    'timeline_data': timeline_data or []
                }

        except Exception as e:
            print(f"Error getting election results: {e}")
            return {
                'party_results': [],
                'total_votes': 0,
                'timeline_data': []
            }
        finally:
            self.vote_pool.putconn(conn)

    def get_voter_turnout(self):
        """Get voter turnout statistics"""
        if not self.registration_pool or not self.vote_pool:
            return None

        conn_reg = self.registration_pool.getconn()
        conn_vote = self.vote_pool.getconn()

        try:
            with conn_reg.cursor() as cursor:
                # Get total registered voters
                cursor.execute('SELECT COUNT(*) FROM voters')
                result = cursor.fetchone()
                total_registered = result[0] if result else 0

            with conn_vote.cursor() as cursor:
                # Get total votes cast (from vote_sessions)
                cursor.execute("SELECT COUNT(*) FROM vote_sessions WHERE status = 'completed'")
                result = cursor.fetchone()
                votes_cast = result[0] if result else 0

                turnout_percentage = (votes_cast / total_registered * 100) if total_registered > 0 else 0

                return {
                    'total_registered': total_registered,
                    'votes_cast': votes_cast,
                    'turnout_percentage': round(turnout_percentage, 2)
                }

        except Exception as e:
            print(f"Error getting voter turnout: {e}")
            return None
        finally:
            self.registration_pool.putconn(conn_reg)
            self.vote_pool.putconn(conn_vote)

    def get_recent_activity(self, limit=10):
        """Get recent voting activity"""
        if not self.vote_pool:
            return None

        conn = self.vote_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute('''
                               SELECT voter_nic, start_time, end_time, status
                               FROM vote_sessions
                               ORDER BY start_time DESC
                                   LIMIT %s
                               ''', (limit,))
                return cursor.fetchall()

        except Exception as e:
            print(f"Error getting recent activity: {e}")
            return None
        finally:
            self.vote_pool.putconn(conn)

    def get_system_stats(self):
        """Get system statistics"""
        if not self.vote_pool:
            return None

        conn = self.vote_pool.getconn()
        try:
            with conn.cursor() as cursor:
                # Get today's votes
                cursor.execute('''
                               SELECT COUNT(*)
                               FROM anonymous_votes
                               WHERE DATE (vote_time) = CURRENT_DATE
                               ''')
                result = cursor.fetchone()
                today_votes = result[0] if result else 0

                # Get active sessions
                cursor.execute("SELECT COUNT(*) FROM vote_sessions WHERE status = 'active'")
                result = cursor.fetchone()
                active_sessions = result[0] if result else 0

                return {
                    'today_votes': today_votes,
                    'active_sessions': active_sessions
                }

        except Exception as e:
            print(f"Error getting system stats: {e}")
            return None
        finally:
            self.vote_pool.putconn(conn)


# Initialize admin manager
admin_manager = AdminManager()


@admin_bp.route('/')
def admin_dashboard():
    """Admin dashboard main page"""
    if not session.get('admin_logged_in'):
        return render_template('admin_login.html')

    results = admin_manager.get_election_results() or {}
    turnout = admin_manager.get_voter_turnout() or {}
    recent_activity = admin_manager.get_recent_activity(15) or []
    system_stats = admin_manager.get_system_stats() or {}

    return render_template('admin_dashboard.html',
                           results=results,
                           turnout=turnout,
                           recent_activity=recent_activity,
                           system_stats=system_stats,
                           parties=admin_config.PARTIES)


@admin_bp.route('/login', methods=['POST'])
def admin_login():
    """Admin login endpoint"""
    username = request.form.get('username')
    password = request.form.get('password')

    # Authentication
    if username == admin_config.ADMIN_USERNAME and password == admin_config.ADMIN_PASSWORD:
        session['admin_logged_in'] = True
        return jsonify({'success': True, 'redirect': '/'})
    else:
        return jsonify({'success': False, 'error': 'Invalid credentials'})


@admin_bp.route('/logout')
def admin_logout():
    """Admin logout"""
    session.pop('admin_logged_in', None)
    return jsonify({'success': True, 'redirect': '/'})


@admin_bp.route('/api/results')
def api_results():
    """API endpoint for election results"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    results = admin_manager.get_election_results()
    if not results:
        return jsonify({'error': 'Failed to get results'}), 500

    party_results = []
    for party_code, vote_count in results.get('party_results', []):
        party_name = admin_config.PARTIES.get(party_code, {}).get('name', 'Unknown Party')
        percentage = (vote_count / results['total_votes'] * 100) if results.get('total_votes', 0) > 0 else 0
        party_results.append({
            'party_code': party_code,
            'party_name': party_name,
            'vote_count': vote_count,
            'percentage': round(percentage, 1)
        })

    return jsonify({
        'party_results': party_results,
        'total_votes': results.get('total_votes', 0)
    })


@admin_bp.route('/api/timeline')
def api_timeline():
    """API endpoint for voting timeline"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    results = admin_manager.get_election_results()
    if not results or not results.get('timeline_data'):
        return jsonify([])

    timeline = []
    for hour, votes_count in results['timeline_data']:
        timeline.append({
            'hour': hour.strftime('%Y-%m-%d %H:00'),
            'votes': votes_count
        })

    return jsonify(timeline)


@admin_bp.route('/api/activity')
def api_activity():
    """API endpoint for recent activity"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    activity = admin_manager.get_recent_activity(20)
    if not activity:
        return jsonify([])

    activity_list = []
    for nic, start_time, end_time, status in activity:
        activity_list.append({
            'voter_nic': nic,
            'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S') if start_time else 'N/A',
            'end_time': end_time.strftime('%Y-%m-%d %H:%M:%S') if end_time else 'N/A',
            'status': status
        })

    return jsonify(activity_list)


@admin_bp.route('/api/stats')
def api_stats():
    """API endpoint for system statistics"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    turnout = admin_manager.get_voter_turnout() or {}
    system_stats = admin_manager.get_system_stats() or {}

    return jsonify({
        'voter_turnout': turnout,
        'system_stats': system_stats
    })