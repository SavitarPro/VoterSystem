import pytest
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    with app.test_client() as client:
        with app.app_context():
            yield client

@patch('routes.vote_manager.blockchain.has_voted')
@patch('routes.vote_manager.check_voter_auth_status')
@patch('routes.notify_fraud_service')
def test_cast_vote_integration(mock_notify_fraud, mock_check_auth, mock_has_voted, client):
    mock_has_voted.return_value = False
    mock_check_auth.return_value = True
    mock_notify_fraud.return_value = True

    with client.session_transaction() as sess:
        sess['voter_nic'] = 'test_nic_123'

    data = {'party_code': '1'}
    response = client.post('/api/cast', json=data)

    assert response.status_code == 200
    assert response.json['success'] is True