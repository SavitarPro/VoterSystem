from flask import Flask
from routes import registration_bp
from utils import init_app
import sys
import os

# Add the parent directory to the path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config


def create_app():
    app = Flask(__name__)
    app.config.from_object(config)

    # Initialize app
    init_app(app)

    # Register blueprints
    app.register_blueprint(registration_bp)

    return app


if __name__ == "__main__":
    import sys

    port = int(sys.argv[1]) if len(sys.argv) > 1 else config.REGISTRATION_PORT

    app = create_app()
    app.run(host='0.0.0.0', port=port, debug=True)