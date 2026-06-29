"""
fabrica de aplicacion flask e inicializacion del paquete.

este modulo expone create_app() que configura la instancia de flask,
registra las rutas y funciones de base de datos, y ejecuta configuraciones
iniciales como crear tablas y datos por defecto.

otros modulos dentro del paquete deben usar imports relativos
por ejemplo: from .database import conectar_db
"""

import os
from flask import Flask, request, session
from flask_cors import CORS #importar la librería de CORS
from dotenv import load_dotenv

# importar componentes internos del paquete
from .user_routes import init_user_routes
from .admin_routes import init_admin_routes
from .decorators import login_required, admin_required
from .database import conectar_db, crear_tablas, inicializar_datos_default, aplicar_migraciones
from psycopg2.extras import RealDictCursor



def create_app():
    """
    crea y configura la aplicacion flask.
    """

    # cargar variables de entorno desde el archivo .env
    load_dotenv()

    # crear instancia principal de flask
    app = Flask(__name__)
    CORS(app) #habilitar CORS para toda la aplicación para permitir qeu react se comunique con flask sin problemas 

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
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

    # asegurar que las carpetas existan
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["STATIC_IMG_FOLDER"], exist_ok=True)

    # registrar todas las rutas del sistema
    init_user_routes(app)
    init_admin_routes(app)

    @app.before_request
    def load_tema_preference():
        if 'id_usuario' in session and 'tema' not in session:
            try:
                db = conectar_db()
                cursor = db.cursor(cursor_factory=RealDictCursor)
                cursor.execute(
                    'SELECT "TEMA_PREFERENCIA" FROM "Usuarios" WHERE "ID_USUARIO" = %s',
                    (session['id_usuario'],)
                )
                usuario = cursor.fetchone()
                cursor.close()
                db.close()
                if usuario and usuario.get('TEMA_PREFERENCIA'):
                    session['tema'] = usuario['TEMA_PREFERENCIA']
                else:
                    session['tema'] = request.cookies.get('orio_tema', 'claro')
            except Exception:
                session['tema'] = request.cookies.get('orio_tema', 'claro')

    @app.context_processor
    def inject_tema():
        return {'theme': session.get('tema', request.cookies.get('orio_tema', 'claro'))}

    # inicializar estructura de base de datos y datos por defecto
    # se usa el contexto de aplicacion porque algunas extensiones lo requieren
    with app.app_context():
        crear_tablas()
        aplicar_migraciones()
        inicializar_datos_default()

    # devolver la aplicacion configurada
    return app