from flask import Blueprint, request, jsonify, render_template
from models import get_voter_by_id

validity_bp = Blueprint('validity', __name__)


@validity_bp.route('/')
def index():
    return render_template('validity_check.html')


@validity_bp.route('/check', methods=['POST'])
def check_validity():
    unique_id = request.form['unique_id']

    voter = get_voter_by_id(unique_id)

    if voter:
        return jsonify({
            'valid': True,
            'full_name': voter['full_name'],
            'nic': voter['nic']
        })
    else:
        return jsonify({'valid': False})