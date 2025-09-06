from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
import cv2
import numpy as np
import base64
from utils import FingerprintRecognizer, VoteManager
from config import config
import requests


FRAUD_SERVICE_URL = "http://localhost:5006"
FRAUD_SERVICE_ENABLED = True

vote_bp = Blueprint('vote', __name__)


fingerprint_recognizer = FingerprintRecognizer(config.FINGERPRINT_MODEL_PATH)
vote_manager = VoteManager()


@vote_bp.route('/')
def vote_dashboard():
    stats = vote_manager.get_vote_stats()
    return render_template('vote_dashboard.html', stats=stats)


@vote_bp.route('/vote/auth')
def vote_authentication():

    return render_template('vote_authentication.html')


@vote_bp.route('/vote/parties')
def vote_party_selection():
    voter_nic = session.get('voter_nic')
    if not voter_nic:
        return jsonify({'error': 'Not authenticated'}), 401

    voter_info = vote_manager.get_voter_info(voter_nic)
    if not voter_info:
        return jsonify({'error': 'Voter not found'}), 404

    return render_template('vote_party_selection.html',
                           voter=voter_info,
                           parties=config.PARTIES)


@vote_bp.route('/api/officer_override', methods=['POST'])
def officer_override():
    try:
        data = request.get_json()
        officer_id = data.get('officer_id')
        voter_nic = data.get('voter_nic')


        if FRAUD_SERVICE_ENABLED and voter_nic and not vote_manager.blockchain.has_voted(voter_nic):
            notify_fraud_service(voter_nic, "start_monitoring")

        if not officer_id or not voter_nic:
            return jsonify({'success': False, 'error': 'Officer ID and Voter NIC required'})


        if not vote_manager.validate_officer_id(officer_id):
            return jsonify({'success': False, 'error': 'Unauthorized officer ID'})


        voter_info = vote_manager.get_voter_info(voter_nic)
        if not voter_info:
            return jsonify({'success': False, 'error': 'Voter not found'})


        auth_status = vote_manager.check_voter_auth_status(voter_nic)
        if not auth_status:
            return jsonify({'success': False, 'error': 'Voter not approved for voting'})


        if vote_manager.blockchain.has_voted(voter_nic):
            return jsonify({'success': False, 'error': 'Voter has already voted'})


        session['voter_nic'] = voter_nic

        return jsonify({
            'success': True,
            'message': 'Override successful',
            'voter': voter_info,
            'redirect': '/vote/parties'
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@vote_bp.route('/api/cast', methods=['POST'])
def cast_vote():
    try:
        data = request.get_json()
        voter_nic = session.get('voter_nic')
        party_code = data['party_code']

        if not voter_nic:
            return jsonify({'success': False, 'error': 'Not authenticated'})


        success, message = vote_manager.cast_vote(voter_nic, party_code)

        if success:


            return jsonify({
                'success': True,
                'message': 'Vote cast successfully!',
                'redirect': '/confirmation'
            })
        else:
            return jsonify({'success': False, 'error': message})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@vote_bp.route('/api/stats')
def vote_stats():
    stats = vote_manager.get_vote_stats()
    return jsonify(stats)


@vote_bp.route('/api/check_status')
def check_vote_status():
    voter_nic = session.get('voter_nic')
    if voter_nic:
        has_voted = vote_manager.blockchain.has_voted(voter_nic)
        return jsonify({'has_voted': has_voted, 'voter_nic': voter_nic})
    return jsonify({'has_voted': False})


@vote_bp.route('/confirmation')
def vote_confirmation():

    voter_nic = session.get('voter_nic')
    if not voter_nic:
        return redirect(url_for('vote.vote_dashboard'))


    blockchain = vote_manager.blockchain
    latest_vote = None


    for block in reversed(blockchain.chain):
        for vote in block['votes']:
            if vote['voter_nic'] == voter_nic:
                latest_vote = vote
                break
        if latest_vote:
            break

    if not latest_vote:
        return redirect(url_for('vote.vote_dashboard'))


    total_votes = vote_manager.get_vote_stats()['total_votes']
    vote_number = 0
    for block in blockchain.chain:
        for vote in block['votes']:
            vote_number += 1
            if vote['voter_nic'] == voter_nic:
                break
        if latest_vote:
            break
    session.pop('voter_nic', None)

    return render_template('vote_confirmation.html',
                           voter_nic=voter_nic,
                           timestamp=latest_vote['timestamp'],
                           transaction_hash=latest_vote.get('vote_id', 'N/A'),
                           total_votes=total_votes,
                           your_vote_number=vote_number)


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



@vote_bp.route('/api/process_fingerprint', methods=['POST'])
def process_fingerprint():
    try:
        data = request.get_json()
        image_data = data['image'].split(',')[1]


        nparr = np.frombuffer(base64.b64decode(image_data), np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)


        nic, confidence = fingerprint_recognizer.recognize_fingerprint(image)

        response = {
            'success': True,
            'authenticated': False,
            'confidence': float(confidence) if confidence else 0.0
        }

        if nic:

            voter_info = vote_manager.get_voter_info(nic)
            if voter_info:

                auth_status = vote_manager.check_voter_auth_status(nic)
                if not auth_status:
                    response.update({
                        'authenticated': False,
                        'message': 'Voter not approved for voting',
                        'voter_rejected': True
                    })
                    return jsonify(response)


                if vote_manager.blockchain.has_voted(nic):
                    response.update({
                        'authenticated': True,
                        'voter': voter_info,
                        'message': 'Already voted',
                        'already_voted': True
                    })

                if not vote_manager.blockchain.has_voted(nic):

                    if FRAUD_SERVICE_ENABLED:
                        try:
                            notify_fraud_service(nic, "start_monitoring")
                            print(f"Started fraud monitoring for voter: {nic}")
                        except Exception as e:
                            print(f"Failed to start fraud monitoring: {e}")

                    response.update({
                        'authenticated': True,
                        'voter': voter_info,
                        'message': 'Authentication successful',
                        'already_voted': False
                    })

        return jsonify(response)

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})



@vote_bp.route('/api/send_video_frame', methods=['POST'])
def send_video_frame():

    try:
        data = request.get_json()
        voter_nic = session.get('voter_nic')
        image_data = data.get('image_data')

        if not voter_nic or not image_data:
            return jsonify({'success': False, 'error': 'Missing parameters'})

        if FRAUD_SERVICE_ENABLED:

            response = requests.post(
                f"{FRAUD_SERVICE_URL}/api/process_frame",
                json={
                    'voter_nic': voter_nic,
                    'image_data': image_data
                },
                timeout=1
            )

            if response.status_code == 200:
                result = response.json()
                return jsonify(result)

        return jsonify({'success': True, 'monitoring': False})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
