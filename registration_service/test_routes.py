import pytest
import io
import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from config import config


@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.test_client() as client:
        with app.app_context():
            yield client


@patch('routes.check_nic_exists')
@patch('routes.register_voter')
def test_register_voter_integration(mock_register_voter, mock_check_nic_exists, client):
    mock_check_nic_exists.return_value = False
    mock_register_voter.return_value = True

    login_response = client.post('/login', json={
        'username': config.REGISTRATION_USER,
        'password': config.REGISTRATION_PASSWORD
    })
    assert login_response.status_code == 200

    data = {
        'nic': '199012345678',
        'full_name': 'Test Voter',
        'address': '123 Test St',
        'electoral_division': 'Test Division',
        'dob': '1990-01-01',
        'face_image': (io.BytesIO(b'fake image data'), 'face.jpg'),
        'fingerprint': (io.BytesIO(b'fake fingerprint data'), 'fingerprint.jpg')
    }

    response = client.post('/register', data=data, content_type='multipart/form-data')

    assert response.status_code == 200
    assert response.json['success'] == True
    assert 'unique_id' in response.json


def test_login_success(client):
    response = client.post('/login', json={
        'username': config.REGISTRATION_USER,
        'password': config.REGISTRATION_PASSWORD
    })
    assert response.status_code == 200
    assert response.json['success'] == True


def test_login_failure(client):
    response = client.post('/login', json={
        'username': 'wrong',
        'password': 'wrong'
    })
    assert response.status_code == 401
    assert response.json['success'] == False


def test_check_auth_authenticated(client):
    client.post('/login', json={
        'username': config.REGISTRATION_USER,
        'password': config.REGISTRATION_PASSWORD
    })

    response = client.get('/check-auth')
    assert response.status_code == 200
    assert response.json['authenticated'] == True


def test_check_auth_unauthenticated(client):
    response = client.get('/check-auth')
    assert response.status_code == 401
    assert response.json['authenticated'] == False


def test_register_missing_fields(client):
    client.post('/login', json={
        'username': config.REGISTRATION_USER,
        'password': config.REGISTRATION_PASSWORD
    })

    data = {
        'nic': '199012345678',
        'full_name': 'Test Voter',
        'face_image': (io.BytesIO(b'fake image data'), 'face.jpg'),
        'fingerprint': (io.BytesIO(b'fake fingerprint data'), 'fingerprint.jpg')
    }

    response = client.post('/register', data=data, content_type='multipart/form-data')
    assert response.status_code == 400
    assert response.json['success'] == False


def test_register_unauthorized(client):
    data = {
        'nic': '199012345678',
        'full_name': 'Test Voter',
        'address': '123 Test St',
        'electoral_division': 'Test Division',
        'dob': '1990-01-01',
        'face_image': (io.BytesIO(b'fake image data'), 'face.jpg'),
        'fingerprint': (io.BytesIO(b'fake fingerprint data'), 'fingerprint.jpg')
    }

    response = client.post('/register', data=data, content_type='multipart/form-data')
    assert response.status_code == 401
    assert response.json['success'] == False


@patch('routes.check_nic_exists')
def test_register_nic_already_exists(mock_check_nic_exists, client):
    mock_check_nic_exists.return_value = True

    client.post('/login', json={
        'username': config.REGISTRATION_USER,
        'password': config.REGISTRATION_PASSWORD
    })

    data = {
        'nic': '199012345678',
        'full_name': 'Test Voter',
        'address': '123 Test St',
        'electoral_division': 'Test Division',
        'dob': '1990-01-01',
        'face_image': (io.BytesIO(b'fake image data'), 'face.jpg'),
        'fingerprint': (io.BytesIO(b'fake fingerprint data'), 'fingerprint.jpg')
    }

    response = client.post('/register', data=data, content_type='multipart/form-data')
    assert response.status_code == 400
    assert response.json['success'] == False
    assert 'NIC already registered' in response.json['error']