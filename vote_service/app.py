from flask import Flask, session, jsonify
import os
import sys
from datetime import timedelta


sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import config
from routes import vote_bp


def create_app():
    app = Flask(__name__)


    app.config['SECRET_KEY'] = 'your-secret-key-here'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
    app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH


    app.register_blueprint(vote_bp)

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'error': '404 - Page not found',
            'message': 'The requested URL was not found on the server.'
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            'success': False,
            'error': '500 - Internal server error',
            'message': 'Something went wrong on the server.'
        }), 500

    return app


if __name__ == '__main__':
    import sys

    port = int(sys.argv[1]) if len(sys.argv) > 1 else config.VOTE_PORT

    app = create_app()
    app.run(host='0.0.0.0', port=port, debug=True)