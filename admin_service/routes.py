from flask import Blueprint, render_template, jsonify, session, request
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch
import io
from datetime import datetime

try:
    from config import config
except ImportError:
    import sys
    import os

    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from config import config

admin_bp = Blueprint('admin', __name__)


class AdminManager:
    def __init__(self):
        self.vote_pool = config.vote_pool
        self.registration_pool = config.registration_pool

    def get_election_results(self):
        if not self.vote_pool:
            return None

        conn = self.vote_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute('''
                               SELECT party_code, COUNT(*) as vote_count
                               FROM anonymous_votes
                               GROUP BY party_code
                               ORDER BY vote_count DESC
                               ''')
                party_results = cursor.fetchall()

                cursor.execute('SELECT COUNT(*) FROM anonymous_votes')
                total_votes_result = cursor.fetchone()
                total_votes = total_votes_result[0] if total_votes_result else 0

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
        if not self.registration_pool or not self.vote_pool:
            return None

        conn_reg = self.registration_pool.getconn()
        conn_vote = self.vote_pool.getconn()

        try:
            with conn_reg.cursor() as cursor:
                cursor.execute('SELECT COUNT(*) FROM voters')
                result = cursor.fetchone()
                total_registered = result[0] if result else 0

            with conn_vote.cursor() as cursor:
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
        if not self.vote_pool:
            return None

        conn = self.vote_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute('''
                               SELECT COUNT(*)
                               FROM anonymous_votes
                               WHERE DATE (vote_time) = CURRENT_DATE
                               ''')
                result = cursor.fetchone()
                today_votes = result[0] if result else 0

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



admin_manager = AdminManager()


@admin_bp.route('/')
def admin_dashboard():

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
                           parties=config.PARTIES)


@admin_bp.route('/login', methods=['POST'])
def admin_login():

    username = request.form.get('username')
    password = request.form.get('password')


    if username == config.ADMIN_USERNAME and password == config.ADMIN_PASSWORD:
        session['admin_logged_in'] = True
        return jsonify({'success': True, 'redirect': '/'})
    else:
        return jsonify({'success': False, 'error': 'Invalid credentials'})


@admin_bp.route('/logout')
def admin_logout():

    session.pop('admin_logged_in', None)
    return jsonify({'success': True, 'redirect': '/'})


@admin_bp.route('/api/results')
def api_results():

    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    results = admin_manager.get_election_results()
    if not results:
        return jsonify({'error': 'Failed to get results'}), 500

    party_results = []
    for party_code, vote_count in results.get('party_results', []):
        party_name = config.PARTIES.get(party_code, {}).get('name', 'Unknown Party')
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

    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    turnout = admin_manager.get_voter_turnout() or {}
    system_stats = admin_manager.get_system_stats() or {}

    return jsonify({
        'voter_turnout': turnout,
        'system_stats': system_stats
    })


@admin_bp.route('/generate_report')
def generate_report():

    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    try:

        results = admin_manager.get_election_results() or {}
        turnout = admin_manager.get_voter_turnout() or {}


        buffer = io.BytesIO()


        doc = SimpleDocTemplate(buffer, pagesize=letter)


        elements = []


        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=20,
            spaceAfter=30,
            alignment=1
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=12
        )


        elements.append(Paragraph("Election Results Report", title_style))
        elements.append(
            Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        elements.append(Spacer(1, 20))


        elements.append(Paragraph("Summary Statistics", heading_style))

        summary_data = [
            ['Total Registered Voters', f"{turnout.get('total_registered', 0):,}"],
            ['Total Votes Cast', f"{results.get('total_votes', 0):,}"],
            ['Voter Turnout', f"{turnout.get('turnout_percentage', 0)}%"],
            ['Did Not Participate', f"{(turnout.get('total_registered', 0) - results.get('total_votes', 0)):,}"],
            ['Non-Participation Rate',
             f"{((turnout.get('total_registered', 0) - results.get('total_votes', 0)) / turnout.get('total_registered', 0) * 100 if turnout.get('total_registered', 0) > 0 else 0):.2f}%"]
        ]

        summary_table = Table(summary_data, colWidths=[3 * inch, 2 * inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        elements.append(summary_table)
        elements.append(Spacer(1, 20))


        elements.append(Paragraph("Party-wise Results", heading_style))

        party_data = [['Party', 'Votes', 'Percentage']]

        if results and results.get('party_results'):
            for party_code, vote_count in results.get('party_results', []):
                party_name = config.PARTIES.get(party_code, {}).get('name', 'Unknown Party')
                percentage = (vote_count / results['total_votes'] * 100) if results.get('total_votes', 0) > 0 else 0
                party_data.append([party_name, f"{vote_count:,}", f"{percentage:.2f}%"])

        party_table = Table(party_data, colWidths=[3 * inch, 1.5 * inch, 1.5 * inch])
        party_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        elements.append(party_table)
        elements.append(Spacer(1, 20))


        doc.build(elements)


        buffer.seek(0)
        return buffer.getvalue(), 200, {
            'Content-Type': 'application/pdf',
            'Content-Disposition': 'attachment; filename=election_report.pdf'
        }

    except Exception as e:
        print(f"Error generating PDF report: {e}")
        return jsonify({'error': 'Failed to generate report'}), 500