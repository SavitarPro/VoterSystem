import os


class Config:

    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '5432')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '1480')

    SECRET_KEY = os.getenv('SECRET_KEY', 'super-secret-key')

    REGISTRATION_USER = os.getenv('REGISTRATION_USER', 'admin')
    REGISTRATION_PASSWORD = os.getenv('REGISTRATION_PASSWORD', 'admin123')

    REGISTRATION_PORT = 5001

    CENTRAL_DB = 'central_voter_db'
    REGISTRATION_DB = 'voter_registration_db'
    VALIDITY_DB = 'voter_validity_db'

    UPLOAD_FOLDER = 'static/images/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}


config = Config()