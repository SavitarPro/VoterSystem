from flask import Blueprint, request, jsonify, render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from models import get_voter_by_id
from utils import log_activity

validity_bp = Blueprint('validity', __name__)


limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100 per hour"]
)


def init_limiter(app):
    limiter.init_app(app)


@validity_bp.route('/')
@limiter.limit("50 per hour")  
def index():
    log_activity('INFO', 'Validity check page accessed', request.remote_addr)
    return render_template('validity_check.html')


@validity_bp.route('/check', methods=['POST'])
@limiter.limit("10 per minute")  
def check_validity():
    ip_address = request.remote_addr

    if 'unique_id' not in request.form:
        log_activity('WARNING', 'Missing unique_id parameter in request', ip_address)
        return jsonify({'error': 'Missing unique_id parameter'}), 400

    unique_id = request.form['unique_id'].strip()

    
    log_activity('INFO', f'Validity check attempted for ID: {unique_id}', ip_address)

    voter = get_voter_by_id(unique_id, ip_address)

    if voter:
        return jsonify({
            'valid': True,
            'full_name': voter['full_name'],
            'nic': voter['nic']
        })
    else:
        return jsonify({'valid': False})