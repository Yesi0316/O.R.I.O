"""
fabrica de aplicacion flask e inicializacion del paquete.

este modulo expone create_app() que configura la instancia de flask,
registra las rutas y funciones de base de datos, y ejecuta configuraciones
iniciales como crear tablas y datos por defecto.

otros modulos dentro del paquete deben usar imports relativos
por ejemplo:
from .database import conectar_db
"""

import os
from flask import Flask
from dotenv import load_dotenv

# importar componentes internos del paquete
from .routes import init_routes
from .database import crear_tablas, inicializar_datos_default, aplicar_migraciones


def create_app():
    """
    crea y configura la aplicacion flask.
    """

    # cargar variables de entorno desde el archivo .env
    load_dotenv()

    # crear instancia principal de flask
    app = Flask(__name__)

    # configurar clave secreta desde variables de entorno
    app.secret_key = os.getenv("SECRET_KEY")

    # configurar carpeta de subidas
    app.config["UPLOAD_FOLDER"] = os.path.join(
        os.path.dirname(__file__), os.getenv("UPLOAD_FOLDER", "uploads")
    )

    # configurar carpeta estatica para imagenes u otros archivos
    app.config["STATIC_IMG_FOLDER"] = os.path.join(
        os.path.dirname(__file__), os.getenv("static_img_folder", "static")
    )

    # limitar el tamano maximo de archivos a 16 mb
    app.config["max_content_length"] = 16 * 1024 * 1024

    # asegurar que las carpetas existan
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["STATIC_IMG_FOLDER"], exist_ok=True)

    # registrar todas las rutas del sistema
    init_routes(app)

    # inicializar estructura de base de datos y datos por defecto
    # se usa el contexto de aplicacion porque algunas extensiones lo requieren
    with app.app_context():
        crear_tablas()
        aplicar_migraciones()
        inicializar_datos_default()

    # devolver la aplicacion configurada
    return app
