"""
Flask application factory and package initialization.

This module exposes `create_app()` which configures the Flask instance,
registers routes and database helpers, and performs any one-time setup
(like creating tables and default data).

Other modules inside the package should use relative imports (e.g.:
`from .database import conectar_db`).
"""

import os
from flask import Flask
from dotenv import load_dotenv

# import components from this package
from .routes import init_routes
from .database import crear_tablas, inicializar_datos_default


def create_app():
    """Create and configure the Flask application."""
    # load environment variables once
    load_dotenv()

    app = Flask(__name__)

    # secret key and upload configuration
    app.secret_key = os.getenv("SECRET_KEY")
    app.config['UPLOAD_FOLDER'] = os.path.join(
        os.path.dirname(__file__),
        os.getenv("UPLOAD_FOLDER", "uploads")
    )
    app.config['STATIC_IMG_FOLDER'] = os.path.join(
        os.path.dirname(__file__),
        os.getenv("STATIC_IMG_FOLDER", "static")
    )
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

    # make sure directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['STATIC_IMG_FOLDER'], exist_ok=True)

    # register all blueprints / routes
    init_routes(app)

    # initialize database structure and default values
    # we use the application context in case any extensions rely on it
    with app.app_context():
        crear_tablas()
        inicializar_datos_default()

    return app
