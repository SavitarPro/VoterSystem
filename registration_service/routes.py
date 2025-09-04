from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session
import uuid
import os
from werkzeug.utils import secure_filename
from functools import wraps
from datetime import datetime
from models import check_nic_exists, register_voter
from utils import allowed_file
from config import config

registration_bp = Blueprint('registration', __name__)


# Authentication decorator (using sessions)
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return jsonify({'success': False, 'error': 'Login required'}), 401
        return f(*args, **kwargs)

    return decorated


@registration_bp.route('/')
def index():
    # Check if user is logged in using session
    if not session.get('logged_in'):
        return redirect(url_for('registration.login_page'))

    return render_template('registration.html')


@registration_bp.route('/login')
def login_page():
    # If already logged in, redirect to main page
    if session.get('logged_in'):
        return redirect(url_for('registration.index'))

    return render_template('login.html')


@registration_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Invalid data'}), 400

        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'success': False, 'error': 'Username and password required'}), 400

        # Validate credentials
        valid_username = config.REGISTRATION_USER
        valid_password = config.REGISTRATION_PASSWORD

        if username == valid_username and password == valid_password:
            # Set session variables
            session['logged_in'] = True
            session['username'] = username
            session['login_time'] = datetime.now().isoformat()

            return jsonify({
                'success': True,
                'message': 'Login successful',
                'user': username
            })
        else:
            return jsonify({'success': False, 'error': 'Invalid credentials'}), 401

    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({'success': False, 'error': 'Login failed'}), 500


@registration_bp.route('/logout', methods=['POST'])
def logout():
    # Clear session
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'})


@registration_bp.route('/check-auth', methods=['GET'])
def check_auth():
    # Check if user is authenticated
    if session.get('logged_in'):
        return jsonify({
            'authenticated': True,
            'user': session.get('username'),
            'login_time': session.get('login_time')
        })
    else:
        return jsonify({'authenticated': False}), 401


@registration_bp.route('/register', methods=['POST'])
@login_required  # Protect the registration endpoint
def register():
    try:
        # Get the current user from session
        current_user = session.get('username', 'unknown')
        print(f"Registration attempt by user: {current_user}")

        # Get form data
        nic = request.form.get('nic')
        full_name = request.form.get('full_name')
        address = request.form.get('address')
        electoral_division = request.form.get('electoral_division')
        dob = request.form.get('dob')

        # Check if all required fields are present
        if not all([nic, full_name, address, electoral_division, dob]):
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
            face_path = os.path.join(config.UPLOAD_FOLDER, face_filename)
            fingerprint_path = os.path.join(config.UPLOAD_FOLDER, fingerprint_filename)

            face_image.save(face_path)
            fingerprint.save(fingerprint_path)

            # Register voter with DOB
            if register_voter(unique_id, nic, full_name, address, electoral_division, dob, face_filename,
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