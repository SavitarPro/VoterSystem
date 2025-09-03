from flask import Flask, session
from datetime import timedelta
import os
import sys

# Add the current directory to the path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from config import fraud_config
from routes import fraud_bp


def create_fraud_app():
    app = Flask(__name__, template_folder='templates')

    # Configuration
    app.config['SECRET_KEY'] = fraud_config.SECRET_KEY
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)

    # Register blueprint
    app.register_blueprint(fraud_bp, url_prefix='/')


    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return {'error': 'Endpoint not found'}, 404

    @app.errorhandler(500)
    def internal_error(error):
        return {'error': 'Internal server error'}, 500

    return app


if __name__ == '__main__':
    app = create_fraud_app()
    app.run(debug=True, host='0.0.0.0', port=5006)