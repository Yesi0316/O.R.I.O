"""
Rutas del administrador de O.R.I.O.
"""

# ===========================
# LIBRERÍAS
# ===========================

import os
import uuid
import random
import re
from datetime import datetime

from flask import (
    render_template,
    request,
    redirect,
    url_for,
    session,
    jsonify,
    flash,
    current_app,
)

from werkzeug.utils import secure_filename
from psycopg2.extras import RealDictCursor

# ===========================
# COMPONENTES INTERNOS
# ===========================

from .database import conectar_db
from .decorators import login_required, admin_required

# Si tienes funciones auxiliares
# from .utils import allowed_file, guardar_imagen


def init_admin_routes(app):
    """
    Registra todas las rutas del administrador.
    """