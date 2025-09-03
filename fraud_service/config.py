import os


class FraudConfig:
    # Database configuration
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '5432')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '1480')
    VOTE_DB = 'vote_db'

    # Service configuration
    FRAUD_SERVICE_PORT = 5006
    VOTE_SERVICE_URL = 'http://localhost:5004'

    # Admin credentials
    FRAUD_OFFICER_USERNAME = os.getenv('FRAUD_OFFICER_USERNAME', 'fraud_officer')
    FRAUD_OFFICER_PASSWORD = os.getenv('FRAUD_OFFICER_PASSWORD', 'fraud123')
    SECRET_KEY = os.getenv('FRAUD_SECRET_KEY', 'fraud-secret-key-here')

    # AI Model paths
    PERSON_DETECTION_MODEL = 'models/person_detector.pkl'

    # Fraud thresholds
    MIN_CONFIDENCE = 0.6
    FRAUD_PERSON_COUNT = 2

    # WebSocket configuration
    WEBSOCKET_PING_INTERVAL = 25
    WEBSOCKET_PING_TIMEOUT = 10


fraud_config = FraudConfig()