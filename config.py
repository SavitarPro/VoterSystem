import os


class Config:
    # Database configuration
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '5432')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '1480')

    # Service ports
    REGISTRATION_PORT = 5001
    VALIDITY_PORT = 5002
    AUTH_PORT = 5003
    VOTE_PORT = 5004
    ADMIN_PORT = 5005
    FRAUD_PORT = 5006

    # Database names
    CENTRAL_DB = 'central_voter_db'
    REGISTRATION_DB = 'voter_registration_db'
    VALIDITY_DB = 'voter_validity_db'
    AUTH_DB = 'voter_auth_db'
    VOTE_DB = 'vote_db'
    ADMIN_DB = 'admin_db'

    # File upload settings
    UPLOAD_FOLDER = 'static/images/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

    # AI Model paths
    FACE_MODEL_PATH = 'ai_training/models/face_model.pkl'
    FINGERPRINT_MODEL_PATH = 'ai_training/models/fingerprint_model.pkl'

    # Training data paths
    FACE_TRAINING_DATA = 'ai_training/data/faces'
    FINGERPRINT_TRAINING_DATA = 'ai_training/data/fingerprints'


config = Config()