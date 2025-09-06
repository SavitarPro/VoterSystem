import base64
import cv2
import numpy as np
import requests
from flask import Blueprint, render_template, jsonify, session, request, redirect
import json
import time
from datetime import datetime
from models.person_detector import person_detector
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


fraud_bp = Blueprint('fraud', __name__)


active_sessions = {}
fraud_cases = {}


def notify_fraud_service(voter_nic, action):
    
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
    
    if not session.get('fraud_officer_logged_in'):
        return render_template('fraud_login.html')

    return render_template('fraud_dashboard_v2.html')


@fraud_bp.route('/dashboard_v2')
def fraud_dashboard_v2():
    
    if not session.get('fraud_officer_logged_in'):
        return render_template('fraud_login.html')

    return render_template('fraud_dashboard_v2.html')


@fraud_bp.route('/monitor/<voter_nic>')
def monitor_voter(voter_nic):
    
    if not session.get('fraud_officer_logged_in'):
        return redirect('/')

    return render_template('fraud_monitor.html', voter_nic=voter_nic)


@fraud_bp.route('/api/check_auth')
def api_check_auth():
    
    if not session.get('fraud_officer_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    return jsonify({'success': True})


@fraud_bp.route('/api/login', methods=['POST'])
def api_login():
    
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
    
    session.pop('fraud_officer_logged_in', None)
    return jsonify({'success': True})


@fraud_bp.route('/api/detect_fraud', methods=['POST'])
def api_detect_fraud():
    
    try:
        data = request.get_json()
        voter_nic = data.get('voter_nic')

        if not voter_nic:
            return jsonify({'error': 'Missing parameters'}), 400

        
        camera_data = camera_manager.cameras.get(voter_nic, {})
        if camera_data and camera_data.get('cap'):
            ret, frame = camera_data['cap'].read()
            if ret:
                person_count, processed_frame = camera_manager.detect_persons(frame)
                
                _, buffer = cv2.imencode('.jpg', processed_frame)
                image_with_boxes = base64.b64encode(buffer).decode('utf-8')

                
                db_manager.log_fraud_attempt(voter_nic, person_count)

                
                is_fraud = person_count >= fraud_config.FRAUD_PERSON_COUNT

                if is_fraud:
                    fraud_cases[voter_nic] = {
                        'person_count': person_count,
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
    
    if not session.get('fraud_officer_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    cases = db_manager.get_pending_fraud_cases()
    return jsonify([{
        'id': case[0],
        'voter_nic': case[1],
        'person_count': case[2],
        'detected_at': case[3].isoformat() if case[3] else None,
        'officer_action': case[4],
        'full_name': case[5],
        'electoral_division': case[6]
    } for case in cases])


@fraud_bp.route('/api/resolve_fraud', methods=['POST'])
def api_resolve_fraud():
    
    if not session.get('fraud_officer_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        data = request.get_json()
        voter_nic = data.get('voter_nic')
        action = data.get('action')  
        person_count = data.get('person_count', 0)

        if not voter_nic or not action:
            return jsonify({'error': 'Missing parameters'}), 400

        
        db_manager.log_fraud_attempt(voter_nic, person_count, action)

        
        if voter_nic in active_sessions:
            camera_manager.stop_camera(voter_nic)
            del active_sessions[voter_nic]

        
        if voter_nic in fraud_cases:
            del fraud_cases[voter_nic]

        return jsonify({'success': True, 'action': action})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@fraud_bp.route('/api/active_sessions')
def api_active_sessions():
    
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
    
    try:
        data = request.get_json()
        voter_nic = data.get('voter_nic')

        if not voter_nic:
            return jsonify({'error': 'Voter NIC required'}), 400

        
        camera_started = camera_manager.start_camera(voter_nic)

        if not camera_started:
            return jsonify({'error': 'Failed to start camera'}), 500

        
        camera_manager.start_monitoring_voter(voter_nic)

        
        active_sessions[voter_nic] = {
            'start_time': time.time(),
            'status': 'active',
            'camera_index': camera_manager.cameras[voter_nic].get('camera_index', 0)
        }

        print(f"Started camera monitoring for voter: {voter_nic}")
        return jsonify({'success': True, 'voter_nic': voter_nic})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@fraud_bp.route('/api/stop_monitoring', methods=['POST'])
def api_stop_monitoring():
    
    try:
        data = request.get_json()
        voter_nic = data.get('voter_nic')

        
        camera_manager.stop_monitoring_voter(voter_nic)

        if voter_nic in active_sessions:
            del active_sessions[voter_nic]
            print(f"Stopped monitoring voter: {voter_nic}")

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@fraud_bp.route('/api/process_frame', methods=['POST'])
def api_process_frame():
    
    try:
        data = request.get_json()
        voter_nic = data.get('voter_nic')

        if not voter_nic:
            return jsonify({'error': 'Missing parameters'}), 400

        
        camera_data = camera_manager.cameras.get(voter_nic, {})
        if camera_data and camera_data.get('cap'):
            ret, frame = camera_data['cap'].read()
            if ret:
                person_count, processed_frame = camera_manager.detect_persons(frame)
                
                _, buffer = cv2.imencode('.jpg', processed_frame)
                image_with_boxes = base64.b64encode(buffer).decode('utf-8')

                
                if voter_nic in active_sessions:
                    active_sessions[voter_nic]['last_frame'] = image_with_boxes
                    active_sessions[voter_nic]['last_detection'] = {
                        'person_count': person_count,
                        'timestamp': time.time()
                    }

                
                is_fraud = person_count >= fraud_config.FRAUD_PERSON_COUNT

                if is_fraud:
                    
                    db_manager.log_fraud_attempt(voter_nic, person_count)

                    
                    fraud_cases[voter_nic] = {
                        'person_count': person_count,
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
    
    if not session.get('fraud_officer_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        current_voter = None
        stats = {
            'total_detections': len(active_sessions),
            'fraud_cases': 0
        }

        
        if active_sessions:
            voter_nic = list(active_sessions.keys())[0]
            voter_details = db_manager.get_voter_details(voter_nic)

            
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
    
    if not session.get('fraud_officer_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        data = request.get_json()
        voter_nic = data.get('voter_nic')

        if voter_nic not in active_sessions:
            return jsonify({'error': 'Voter not found'}), 404

        
        session_data = active_sessions.pop(voter_nic)
        active_sessions[voter_nic] = session_data

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@fraud_bp.route('/api/camera_info')
def api_camera_info():
    
    if not session.get('fraud_officer_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        camera_info = {}
        for voter_nic, camera_data in camera_manager.cameras.items():
            camera_info[voter_nic] = {
                'camera_index': camera_data.get('camera_index', -1),
                'camera_type': camera_data.get('camera_type', 'Unknown'),
                'is_obs_camera': camera_data.get('camera_index', -1) in [1, 2],
                'is_main_camera': camera_data.get('camera_index', -1) == 0
            }

        return jsonify(camera_info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@fraud_bp.route('/test/start_monitoring')
def test_start_monitoring():
    
    if not session.get('fraud_officer_logged_in'):
        return redirect('/')

    return render_template('test_monitor.html')


@fraud_bp.route('/api/test/start_monitoring', methods=['POST'])
def api_test_start_monitoring():
    
    if not session.get('fraud_officer_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        data = request.get_json()
        voter_nic = data.get('voter_nic', 'TEST123456789')
        camera_index = data.get('camera_index', 0)  

        
        if camera_manager.try_camera(voter_nic, camera_index):
            
            active_sessions[voter_nic] = {
                'start_time': time.time(),
                'status': 'active',
                'camera_index': camera_index,
                'is_test': True  
            }

            return jsonify({
                'success': True,
                'voter_nic': voter_nic,
                'camera_index': camera_index,
                'message': f'Started monitoring with camera {camera_index}'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to start camera'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@fraud_bp.route('/api/test/stop_monitoring', methods=['POST'])
def api_test_stop_monitoring():
    
    if not session.get('fraud_officer_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        data = request.get_json()
        voter_nic = data.get('voter_nic', 'TEST123456789')

        
        if voter_nic in active_sessions:
            camera_manager.stop_camera(voter_nic)
            del active_sessions[voter_nic]

        return jsonify({'success': True, 'message': 'Stopped monitoring'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@fraud_bp.route('/api/test/available_cameras')
def api_test_available_cameras():
    
    if not session.get('fraud_officer_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        available_cameras = []

        
        for camera_index in range(0, 6):
            cap = cv2.VideoCapture(camera_index)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    available_cameras.append({
                        'index': camera_index,
                        'name': f'Camera {camera_index}',
                        'resolution': f'{frame.shape[1]}x{frame.shape[0]}'
                    })
                cap.release()

        return jsonify({'cameras': available_cameras})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@fraud_bp.route('/api/get_last_frame')
def api_get_last_frame():
    
    if not session.get('fraud_officer_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        voter_nic = request.args.get('nic')
        if not voter_nic:
            return jsonify({'error': 'Missing NIC parameter'}), 400

        
        if voter_nic in active_sessions:
            
            camera_data = camera_manager.cameras.get(voter_nic, {})
            if camera_data and camera_data.get('last_frame'):
                return jsonify({
                    'success': True,
                    'image_data': camera_data['last_frame']
                })

        
        if voter_nic in fraud_cases:
            return jsonify({
                'success': True,
                'image_data': fraud_cases[voter_nic].get('image_with_boxes', '')
            })

        return jsonify({'success': False, 'error': 'No frame available'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})