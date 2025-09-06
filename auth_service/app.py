from flask import Flask, render_template
import os
import sys


sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import config
from routes import auth_bp


def create_app():
    app = Flask(__name__)


    app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH


    app.register_blueprint(auth_bp)



    @app.errorhandler(404)
    def not_found(error):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('500.html'), 500

    return app


if __name__ == '__main__':
    import sys

    port = int(sys.argv[1]) if len(sys.argv) > 1 else config.AUTH_PORT

    app = create_app()
    app.run(host='0.0.0.0', port=port, debug=True)