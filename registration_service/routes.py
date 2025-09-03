from flask import Blueprint, request, jsonify, render_template
import uuid
import os
from werkzeug.utils import secure_filename
from datetime import datetime
from models import check_nic_exists, register_voter
from utils import allowed_file

registration_bp = Blueprint('registration', __name__)

# Configuration
UPLOAD_FOLDER = 'static/images/uploads'
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@registration_bp.route('/')
def index():
    return render_template('registration.html')


@registration_bp.route('/register', methods=['POST'])
def register():
    try:
        # Get form data
        nic = request.form.get('nic')
        full_name = request.form.get('full_name')
        address = request.form.get('address')
        electoral_division = request.form.get('electoral_division')

        # Check if all required fields are present
        if not all([nic, full_name, address, electoral_division]):
            return jsonify({'success': False, 'error': 'All fields are required'}), 400

        # Check if files are present
        if 'face_image' not in request.files or 'fingerprint' not in request.files:
            return jsonify({'success': False, 'error': 'Missing image files'}), 400

        face_image = request.files['face_image']
        fingerprint = request.files['fingerprint']

        if face_image.filename == '' or fingerprint.filename == '':
            return jsonify({'success': False, 'error': 'No selected file'}), 400

        if face_image and allowed_file(face_image.filename) and fingerprint and allowed_file(fingerprint.filename):
            # Check if NIC already exists
            if check_nic_exists(nic):
                return jsonify({'success': False, 'error': 'NIC already registered'}), 400

            # Generate unique ID
            unique_id = str(uuid.uuid4())

            # Create secure filenames with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            face_filename = secure_filename(f"{unique_id}_{timestamp}_face.jpg")
            fingerprint_filename = secure_filename(f"{unique_id}_{timestamp}_fingerprint.jpg")

            # Save files
            face_path = os.path.join(UPLOAD_FOLDER, face_filename)
            fingerprint_path = os.path.join(UPLOAD_FOLDER, fingerprint_filename)

            face_image.save(face_path)
            fingerprint.save(fingerprint_path)

            # Register voter
            if register_voter(unique_id, nic, full_name, address, electoral_division, face_filename,
                              fingerprint_filename):
                return jsonify({
                    'success': True,
                    'unique_id': unique_id,
                    'message': 'Registration successful'
                })
            else:
                return jsonify({'success': False, 'error': 'Registration failed'}), 500

        return jsonify({'success': False, 'error': 'Invalid file type'}), 400

    except Exception as e:
        print(f"Error during registration: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500