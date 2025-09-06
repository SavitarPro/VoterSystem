from flask import Flask
from flask.cli import load_dotenv
from routes import registration_bp
from utils import init_app
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config


def load_environment():
    
    env = os.getenv('ENV', 'development')
    env_file = f'.env.{env}'

    if os.path.exists(env_file):
        load_dotenv(env_file)
        print(f"Loaded environment from {env_file}")
    else:
        load_dotenv('.env')
        print("Loaded environment from .env")

load_environment()

def create_app():
    app = Flask(__name__)
    app.config.from_object(config)

    app.secret_key = config.SECRET_KEY

    init_app(app)

    app.register_blueprint(registration_bp)

    return app

if __name__ == "__main__":
    import sys

    port = int(sys.argv[1]) if len(sys.argv) > 1 else config.REGISTRATION_PORT
    app = create_app()
    app.run(host='0.0.0.0', port=port, debug=True)