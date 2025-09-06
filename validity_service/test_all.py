import pytest
import psycopg2
import os
import sys
import uuid
from unittest.mock import patch, MagicMock


sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from app import create_app
from config import config
from models import get_voter_by_id



@pytest.fixture(scope='session')
def test_db():
    
    try:
        conn = psycopg2.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database='postgres'
        )
        conn.autocommit = True
        cursor = conn.cursor()

        
        test_db_name = f"{config.VALIDITY_DB}_test"
        try:
            cursor.execute(f"DROP DATABASE IF EXISTS {test_db_name}")
            cursor.execute(f"CREATE DATABASE {test_db_name}")
        except Exception as e:
            print(f"Error creating test database: {e}")
            pytest.skip("Could not create test database")
        finally:
            cursor.close()
            conn.close()

        
        test_conn = psycopg2.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=test_db_name
        )
        cursor = test_conn.cursor()

        
        cursor.execute('''
                       CREATE TABLE voters
                       (
                           unique_id UUID PRIMARY KEY,
                           nic       VARCHAR(20)  NOT NULL,
                           full_name VARCHAR(100) NOT NULL
                       )
                       ''')

        
        uuid1 = str(uuid.uuid4())
        uuid2 = str(uuid.uuid4())

        
        cursor.execute('''
                       INSERT INTO voters (unique_id, nic, full_name)
                       VALUES (%s, '123456789X', 'John Doe'),
                              (%s, '987654321Y', 'Jane Smith')
                       ''', (uuid1, uuid2))

        test_conn.commit()
        cursor.close()

        
        test_conn.test_uuids = [uuid1, uuid2]

        yield test_conn

        
        test_conn.close()

        
        conn = psycopg2.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database='postgres'
        )
        conn.autocommit = True
        cursor = conn.cursor()
        cursor.execute(f"DROP DATABASE {test_db_name}")
        cursor.close()
        conn.close()

    except Exception as e:
        pytest.skip(f"Database connection failed: {e}")


@pytest.fixture
def app(test_db):
    
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    
    with patch('utils.get_db_connection') as mock_conn:
        mock_conn.return_value = test_db
        yield app


@pytest.fixture
def client(app):
    
    return app.test_client()


@pytest.fixture
def mock_logger():
    
    with patch('utils.logging.getLogger') as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        yield mock_logger


@pytest.fixture
def test_uuid(test_db):
    
    return test_db.test_uuids[0]



class TestModels:
    def test_get_voter_by_id_db_error(self, mock_logger):
        
        with patch('models.get_db_connection') as mock_conn:
            mock_conn.side_effect = Exception("Database connection failed")

            test_uuid = str(uuid.uuid4())
            voter = get_voter_by_id(test_uuid, '127.0.0.1')
            assert voter is None
            mock_logger.error.assert_called_once()
