from flask import Blueprint, render_template, request, jsonify
import cv2
import numpy as np
import base64
from utils import FaceRecognizer, DatabaseManager
from config import config

auth_bp = Blueprint('auth', __name__)


face_recognizer = FaceRecognizer(config.FACE_MODEL_PATH)
db_manager = DatabaseManager()


@auth_bp.route('/')
def index():
    return render_template('dashboard.html')


@auth_bp.route('/authentication')
def authentication():
    return render_template('authentication.html')


@auth_bp.route('/api/process_frame', methods=['POST'])
def process_frame():
    try:
        data = request.get_json()
        image_data = data['image'].split(',')[1]
        officer_id = data.get('officer_id', 'OFFICER_001')


        nparr = np.frombuffer(base64.b64decode(image_data), np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)


        nic, confidence = face_recognizer.recognize_face(frame)

        response = {
            'success': True,
            'detected': False,
            'confidence': float(confidence) if confidence else 0.0
        }

        if nic:

            voter_info = db_manager.get_voter_info(nic)
            if voter_info:
                response.update({
                    'detected': True,
                    'voter': voter_info,
                    'confidence': float(confidence)
                })

        return jsonify(response)

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@auth_bp.route('/api/confirm_auth', methods=['POST'])
def confirm_authentication():
    try:
        data = request.get_json()
        unique_id = data['unique_id']
        nic = data['nic']
        full_name = data['full_name']
        officer_id = data['officer_id']
        confidence = data['confidence']


        db_manager.log_authentication(unique_id, nic, full_name, officer_id, confidence, 'APPROVED')

        return jsonify({
            'success': True,
            'message': f'Authentication approved for {full_name}'
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@auth_bp.route('/api/auth_stats')
def auth_stats():
    stats = db_manager.get_auth_stats()
    return jsonify(stats)