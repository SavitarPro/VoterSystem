import base64
import cv2
import requests
from flask import Blueprint, render_template, jsonify, session, request, redirect
import json
import time
from datetime import datetime

FRAUD_SERVICE_URL = "http://localhost:5004"
FRAUD_SERVICE_ENABLED = True

try:
    from utils import camera_manager, db_manager
    from config import fraud_config
except ImportError:
    import sys
    import os

    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from utils import camera_manager, db_manager
    from config import fraud_config

# Create admin blueprint
fraud_bp = Blueprint('fraud', __name__)

# Store active monitoring sessions
active_sessions = {}
fraud_cases = {}


def notify_fraud_service(voter_nic, action):
    """Notify fraud service to start/stop monitoring"""
    if not FRAUD_SERVICE_ENABLED:
        return True

    try:
        if action == "start_monitoring":
            response = requests.post(
                f"{FRAUD_SERVICE_URL}/api/start_monitoring",
                json={"voter_nic": voter_nic},
                timeout=2
            )
            return response.status_code == 200
        elif action == "stop_monitoring":
            response = requests.post(
                f"{FRAUD_SERVICE_URL}/api/stop_monitoring",
                json={"voter_nic": voter_nic},
                timeout=2
            )
            return response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"Fraud service notification failed: {e}")
        return False


@fraud_bp.route('/')
def fraud_dashboard():
    """Main fraud dashboard"""
    if not session.get('fraud_officer_logged_in'):
        return render_template('fraud_login.html')

    return render_template('fraud_dashboard_v2.html')


@fraud_bp.route('/dashboard_v2')
def fraud_dashboard_v2():
    """New fraud dashboard with real-time monitoring"""
    if not session.get('fraud_officer_logged_in'):
        return render_template('fraud_login.html')

    return render_template('fraud_dashboard_v2.html')


@fraud_bp.route('/monitor/<voter_nic>')
def monitor_voter(voter_nic):
    """Monitor specific voter"""
    if not session.get('fraud_officer_logged_in'):
        return redirect('/')

    return render_template('fraud_monitor.html', voter_nic=voter_nic)


@fraud_bp.route('/api/check_auth')
def api_check_auth():
    """Check if officer is authenticated"""
    if not session.get('fraud_officer_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    return jsonify({'success': True})


@fraud_bp.route('/api/login', methods=['POST'])
def api_login():
    """Officer login"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if (username == fraud_config.FRAUD_OFFICER_USERNAME and
            password == fraud_config.FRAUD_OFFICER_PASSWORD):
        session['fraud_officer_logged_in'] = True
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Invalid credentials'})


@fraud_bp.route('/api/logout')
def api_logout():
    """Officer logout"""
    session.pop('fraud_officer_logged_in', None)
    return jsonify({'success': True})


@fraud_bp.route('/api/detect_fraud', methods=['POST'])
def api_detect_fraud():
    """Detect fraud from voter camera feed with visual feedback"""
    try:
        data = request.get_json()
        voter_nic = data.get('voter_nic')
        image_data = data.get('image_data')

        if not voter_nic or not image_data:
            return jsonify({'error': 'Missing parameters'}), 400

        # Extract base64 data if needed
        if ',' in image_data:
            image_data = image_data.split(',')[1]

        # Detect persons with bounding boxes (using camera manager)
        camera_data = camera_manager.cameras.get(voter_nic, {})
        if camera_data and camera_data.get('cap'):
            ret, frame = camera_data['cap'].read()
            if ret:
                person_count, processed_frame = camera_manager.detect_persons(frame)
                # Convert to base64
                _, buffer = cv2.imencode('.jpg', processed_frame)
                image_with_boxes = base64.b64encode(buffer).decode('utf-8')

                # Log detection
                db_manager.log_fraud_attempt(voter_nic, person_count, image_data)

                # Check for fraud
                is_fraud = person_count >= fraud_config.FRAUD_PERSON_COUNT

                if is_fraud:
                    fraud_cases[voter_nic] = {
                        'person_count': person_count,
                        'image_data': image_data,
                        'image_with_boxes': image_with_boxes,
                        'status': 'pending'
                    }

                return jsonify({
                    'success': True,
                    'person_count': person_count,
                    'is_fraud': is_fraud,
                    'image_with_boxes': image_with_boxes,
                    'message': f'Detected {person_count} persons' if is_fraud else 'No fraud detected'
                })

        return jsonify({'success': False, 'error': 'Camera not available'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@fraud_bp.route('/api/fraud_cases')
def api_fraud_cases():
    """Get pending fraud cases"""
    if not session.get('fraud_officer_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    cases = db_manager.get_pending_fraud_cases()
    return jsonify([{
        'id': case[0],
        'voter_nic': case[1],
        'person_count': case[2],
        'detected_at': case[3].isoformat() if case[3] else None,
        'start_time': case[4].isoformat() if case[4] else None,
        'status': case[5]
    } for case in cases])


@fraud_bp.route('/api/resolve_fraud', methods=['POST'])
def api_resolve_fraud():
    """Resolve fraud case"""
    if not session.get('fraud_officer_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        data = request.get_json()
        voter_nic = data.get('voter_nic')
        action = data.get('action')  # 'approve' or 'reject'

        # Update fraud attempt record
        db_manager.log_fraud_attempt(voter_nic, None, None, action)

        # Stop monitoring this voter
        if voter_nic in active_sessions:
            camera_manager.stop_camera(voter_nic)
            del active_sessions[voter_nic]

        return jsonify({'success': True, 'action': action})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@fraud_bp.route('/api/active_sessions')
def api_active_sessions():
    """Get active monitoring sessions"""
    if not session.get('fraud_officer_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    sessions_data = {}
    for voter_nic, session_data in active_sessions.items():
        camera_data = camera_manager.cameras.get(voter_nic, {})
        detection = camera_data.get('last_detection', {})

        sessions_data[voter_nic] = {
            'start_time': session_data['start_time'],
            'person_count': detection.get('person_count', 0),
            'status': session_data['status']
        }

    return jsonify(sessions_data)


@fraud_bp.route('/api/start_monitoring', methods=['POST'])
def api_start_monitoring():
    """Start monitoring a voter with local camera"""
    try:
        data = request.get_json()
        voter_nic = data.get('voter_nic')

        if not voter_nic:
            return jsonify({'error': 'Voter NIC required'}), 400

        # Start local camera
        camera_started = camera_manager.start_camera(voter_nic)

        if not camera_started:
            return jsonify({'error': 'Failed to start camera'}), 500

        # Add to active sessions
        active_sessions[voter_nic] = {
            'start_time': time.time(),
            'status': 'active',
            'camera_index': 0
        }

        print(f"Started camera monitoring for voter: {voter_nic}")
        return jsonify({'success': True, 'voter_nic': voter_nic})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@fraud_bp.route('/api/stop_monitoring', methods=['POST'])
def api_stop_monitoring():
    """Stop monitoring a voter"""
    try:
        data = request.get_json()
        voter_nic = data.get('voter_nic')

        if voter_nic in active_sessions:
            # Stop camera
            camera_manager.stop_camera(voter_nic)
            del active_sessions[voter_nic]
            print(f"Stopped monitoring voter: {voter_nic}")

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@fraud_bp.route('/api/process_frame', methods=['POST'])
def api_process_frame():
    """Process video frame from vote service"""
    try:
        data = request.get_json()
        voter_nic = data.get('voter_nic')
        image_data = data.get('image_data')

        if not voter_nic or not image_data:
            return jsonify({'error': 'Missing parameters'}), 400

        # Extract base64 data if needed
        if ',' in image_data:
            image_data = image_data.split(',')[1]

        # Use camera manager for detection instead of fraud_detector
        camera_data = camera_manager.cameras.get(voter_nic, {})
        if camera_data and camera_data.get('cap'):
            ret, frame = camera_data['cap'].read()
            if ret:
                person_count, processed_frame = camera_manager.detect_persons(frame)
                # Convert to base64
                _, buffer = cv2.imencode('.jpg', processed_frame)
                image_with_boxes = base64.b64encode(buffer).decode('utf-8')

                # Update active session
                if voter_nic in active_sessions:
                    active_sessions[voter_nic]['last_frame'] = image_with_boxes
                    active_sessions[voter_nic]['last_detection'] = {
                        'person_count': person_count,
                        'timestamp': time.time()
                    }

                # Check for fraud
                is_fraud = person_count >= fraud_config.FRAUD_PERSON_COUNT

                if is_fraud:
                    # Log fraud attempt
                    db_manager.log_fraud_attempt(voter_nic, person_count, image_data)

                    # Update fraud case
                    fraud_cases[voter_nic] = {
                        'person_count': person_count,
                        'image_data': image_data,
                        'image_with_boxes': image_with_boxes,
                        'status': 'pending',
                        'timestamp': time.time()
                    }

                return jsonify({
                    'success': True,
                    'person_count': person_count,
                    'is_fraud': is_fraud,
                    'image_with_boxes': image_with_boxes,
                    'message': f'Detected {person_count} persons' if is_fraud else 'No fraud detected'
                })

        return jsonify({'success': False, 'error': 'Camera not available'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@fraud_bp.route('/api/active_monitoring')
def api_active_monitoring():
    """Get active monitoring data for dashboard"""
    if not session.get('fraud_officer_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        current_voter = None
        stats = {
            'total_detections': len(active_sessions),
            'fraud_cases': 0
        }

        # Get the first active voter
        if active_sessions:
            voter_nic = list(active_sessions.keys())[0]
            voter_details = db_manager.get_voter_details(voter_nic)

            # Get camera data
            camera_data = camera_manager.cameras.get(voter_nic, {})

            current_voter = {
                'nic': voter_nic,
                'full_name': voter_details.get('full_name', 'Unknown') if voter_details else 'Unknown',
                'electoral_division': voter_details.get('electoral_division',
                                                        'Unknown') if voter_details else 'Unknown',
                'status': voter_details.get('status', 'Unknown') if voter_details else 'Unknown',
                'last_frame': camera_data.get('last_frame'),
                'last_detection': camera_data.get('last_detection')
            }

            # Count fraud cases
            detection = camera_data.get('last_detection', {})
            if detection.get('person_count', 0) >= 2:
                stats['fraud_cases'] += 1

        return jsonify({
            'current_voter': current_voter,
            'stats': stats
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@fraud_bp.route('/api/focus_voter', methods=['POST'])
def api_focus_voter():
    """Focus on a specific voter for monitoring"""
    if not session.get('fraud_officer_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        data = request.get_json()
        voter_nic = data.get('voter_nic')

        if voter_nic not in active_sessions:
            return jsonify({'error': 'Voter not found'}), 404

        # Move to front of sessions (simulate focusing)
        session_data = active_sessions.pop(voter_nic)
        active_sessions[voter_nic] = session_data

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})