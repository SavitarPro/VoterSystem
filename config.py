import os


class Config:
    
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '5432')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '1480')

    
    REGISTRATION_PORT = 5001
    VALIDITY_PORT = 5002
    AUTH_PORT = 5003
    VOTE_PORT = 5004
    ADMIN_PORT = 5005
    FRAUD_PORT = 5006

    
    CENTRAL_DB = 'central_voter_db'
    REGISTRATION_DB = 'voter_registration_db'
    VALIDITY_DB = 'voter_validity_db'
    AUTH_DB = 'voter_auth_db'
    VOTE_DB = 'vote_db'
    ADMIN_DB = 'admin_db'

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

config = Config()