import hashlib
import secrets

def generate_hash(data):
    """Generate SHA-256 hash of data"""
    return hashlib.sha256(data.encode()).hexdigest()

def generate_token():
    """Generate a secure random token"""
    return secrets.token_urlsafe(32)