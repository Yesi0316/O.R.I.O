import os
import random
import uuid
from datetime import datetime
from functools import wraps

from flask import (
    request, jsonify, render_template,
    session, redirect, url_for, send_from_directory
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from database import conectar_db
from psycopg2.extras import RealDictCursor


# -----------------------------
# DECORADOR LOGIN REQUIRED
# -----------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'id_usuario' not in session:
            return redirect('/inicio')
        return f(*args, **kwargs)
    return decorated_function

# -----------------------------
# DECORADOR GUEST REQUIRED
# -----------------------------
def guest_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'id_usuario' in session:
            return redirect(url_for('menu'))
        return f(*args, **kwargs)
    return decorated_function


# obtener rutas a las carpetas
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), os.getenv("UPLOAD_FOLDER"))
STATIC_IMG_FOLDER = os.path.join(os.path.dirname(__file__), os.getenv("STATIC_IMG_FOLDER"))
# crear carpetas si no existen
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(STATIC_IMG_FOLDER, exist_ok=True)



"""RUTAS DE LA PAGINA"""
def init_routes(app):

    # CONFIGURAR CARPETAS DE SUBIDAS Y ESTATICAS    
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['STATIC_IMG_FOLDER'] = STATIC_IMG_FOLDER
    
    # -----------------------------
    # RUTA PRINCIPAL
    # -----------------------------
    @app.route('/')
    def index():
        return render_template('index.html')

    # -------------------------------------
    # RUTA REGISTRO
    # -------------------------------------
    @app.route('/registro')
    @guest_required
    def registro():
        return render_template('registro.html')

    # ----------------------------------
    # GUARDAR USUARIO AL REGISTRARSE
    # ----------------------------------
    @app.route('/guardar_usuario', methods=['POST'])
    def guardar_usuario():
        try:
            # obtener datos del formulario
            id_usuario = request.form.get('id_usuario')
            nombre = request.form.get('nombre')
            contrasena = request.form.get('contrasena')
            contrasena_repetida = request.form.get('contrasena_repetida')
            pregunta1 = request.form.get('pregunta1')
            respuesta1 = request.form.get('respuesta1')
            pregunta2 = request.form.get('pregunta2')
            respuesta2 = request.form.get('respuesta2')

            # validaciones básicas
            
            if not id_usuario or not contrasena:
                return jsonify({'mensaje': 'Usuario y contraseña obligatorios'}), 400
            if " " in id_usuario:
                return jsonify({'mensaje': 'El Usuario no puede tener espacios'}), 400
            if contrasena != contrasena_repetida:
                return jsonify({'mensaje': 'Las contraseñas no coinciden'}), 400

            # conectar DB
            conexion = conectar_db()
            cursor = conexion.cursor()

            # verificar si usuario existe
            cursor.execute(
                'SELECT "ID_USUARIO" FROM public."Usuarios" WHERE "ID_USUARIO" = %s', 
                (id_usuario,)
            )
            if cursor.fetchone():
                cursor.close()
                conexion.close()
                return jsonify({'mensaje': 'El usuario ya existe'}), 400

            # insertar usuario con contraseña encriptada
            hashed_password = generate_password_hash(contrasena)
            cursor.execute("""
                INSERT INTO public."Usuarios"
                ("ID_USUARIO", "NOMBRE", "CONTRASENA", "PREGUNTA_1", "PREGUNTA_2", "RESPUESTA_1", "RESPUESTA_2")
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                id_usuario, 
                nombre, 
                hashed_password, 
                pregunta1, 
                pregunta2, 
                respuesta1, 
                respuesta2
                ))

            conexion.commit()
            cursor.close()
            conexion.close()

            session['id_usuario'] = id_usuario
            return jsonify({
                'ok': True, 
                'mensaje': 'Usuario creado correctamente'
            })

        except Exception as e:
            return jsonify({'mensaje': 'Error al guardar el usuario', 'error': str(e)}), 500

    # -----------------------------
    # CONSULTAR USUARIOS
    # -----------------------------
    @app.route('/usuarios', methods=['GET'])
    def obtener_usuarios():
        try:
            conexion = conectar_db()
            if conexion is None:
                return jsonify({'mensaje': 'Error de conexión a la base de datos'}), 500
            

            cursor = conexion.cursor(cursor_factory=RealDictCursor)
            cursor.execute('SELECT * FROM public."Usuarios" ORDER BY "ID_USUARIO" DESC;')
            usuarios = cursor.fetchall()

            cursor.close()
            conexion.close()

            return jsonify(usuarios), 200

        except Exception as e:
            return jsonify({'mensaje': 'Error al obtener los usuarios', 'error': str(e)}), 500

    # -------------------------------------
    # RUTA INICIO DE SESIÓN
    # -------------------------------------
    @app.route('/inicio', methods=['GET'])
    @guest_required
    def vista_inicio():
        return render_template('inicio.html')

    @app.route('/inicio', methods=['POST'])
    @guest_required
    def inicio_sesion():
        try:
            id_usuario = request.form.get('id_usuario')
            contrasena = request.form.get('contrasena')

            if not id_usuario or not contrasena:
                return jsonify({
                    'ok': False, 
                    'mensaje': 'Debes completar todos los campos'
                    }), 400

            conexion = conectar_db()
            cursor = conexion.cursor(cursor_factory=RealDictCursor)

            cursor.execute(
                'SELECT "ID_USUARIO", "CONTRASENA" FROM public."Usuarios" WHERE "ID_USUARIO" = %s',
                (id_usuario,)
            )
            user = cursor.fetchone()

            cursor.close()
            conexion.close()

            if not user:
                return jsonify({
                    'ok': False, 
                    'mensaje': 'El usuario no está registrado'
                    }), 404

            if not check_password_hash(user["CONTRASENA"], contrasena):
                return jsonify({
                    'ok': False, 
                    'mensaje': 'Contraseña incorrecta'
                    }), 401

            session['id_usuario'] = user["ID_USUARIO"]
            return jsonify({
                'ok': True, 
                'mensaje': 'Inicio de sesión exitoso'
                })

        except Exception as e:
            import traceback
            # esto imprime el error completo
            traceback.print_exc()  
            return jsonify({
                'ok': False, 
                'mensaje': 'Error en el servidor'
                }), 500

    # -------------------------------------
    # RUTA CERRAR SESION
    # -------------------------------------
    @app.route('/logout')
    def logout():
        session.clear()
        return redirect('/inicio')

    # -------------------------------------
    # RUTA MENU
    # -------------------------------------
    @app.route('/menu')
    @login_required
    def menu():
        return render_template('menu.html')
    # -------------------------------------
    # RUTA FORMULARIO REPORTE
    # -------------------------------------
    @app.route('/formulario_perdido', methods=['GET', 'POST'])
    @login_required
    def formulario_perdido():
        if request.method == 'POST':
            return redirect('/buscar_objetos')
        return render_template('form_perdido.html')


    @app.route('/formulario_reporte2')
    def formulario_reporte2():
        bd = conectar_db()
        cursor = bd.cursor(cursor_factory=RealDictCursor)
        cursor.execute('SELECT "ID_ESTADO" FROM "Estados"')
        estados = cursor.fetchall()
        cursor.close()
        bd.close()
        return render_template('reportes_principal.html', estados=estados)


    @app.route("/submit_per", methods=["GET","POST"])
    def submit_per():
        if request.method != "POST":
            return jsonify({"mensaje": "Metodo no admitido"})

        id_objeto = str(random.randint(100000, 999999))
        id_reporte = str(random.randint(100000, 999999))

        id_usuario = session['id_usuario']
        nombre_objeto = request.form.get('nombre_objeto')
        estado = request.form.get('estado')
        color_dominante = request.form.get('color_dominante')
        lugar = request.form.get('lugar')
        fecha = request.form.get('fecha')
        ficha = request.form.get('ficha')
        if ficha:
            ficha = int(ficha)
        else:
            ficha = None  
        categoria = request.form.get('categoria')
        comentario = request.form.get('comentario')

        # Archivo
        imagen = request.files.get('imagen')
        ruta = None
        if imagen:
            # limpia el nombre del archivo
            filename = secure_filename(imagen.filename)
            # crea un nombre unico usando uuid para evitar colisiones
            unique_filename = f"{uuid.uuid4()}_{filename}"
            # guardarla en la carpeta uploads
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            imagen.save(save_path)
            # guarda la ruta que voy a usar en la base de datos
            ruta = f"/uploads/{unique_filename}"

        bd = conectar_db()
        cursor = bd.cursor()

        cursor.execute("""INSERT INTO "Objetos" ("ID_OBJETO", "NOMBRE", "COLOR", "ID_ESTADO", "LUGAR_ENCONTRADO", "ID_CATEGORIA", "IMAGEN") VALUES (%s, %s, %s, %s, %s, %s, %s)""", (id_objeto, nombre_objeto, color_dominante, estado, lugar, categoria, ruta))
        cursor.execute("""INSERT INTO "Reportes_perdidos" ("FECHA", "OBSERVACIONES", "ID_OBJETO", "ID_USUARIO", "ID_REPORTE", "FICHA", "ID_CATEGORIA")VALUES (%s, %s, %s, %s, %s, %s, %s) """, (fecha, comentario, id_objeto, id_usuario, id_reporte, ficha, categoria))

        bd.commit()
        cursor.close()
        bd.close()

        session["img"] = ruta

        return jsonify({"mensaje":'datos enviado', "ruta": ruta})

    # -----------------------------
    # RUTA PARA MOSTRAR IMAGENES SUBIDAS
    # -----------------------------
    @app.route('/uploads/<filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    # -----------------------------     
    # FORMULARIO REPORTE DE OBJETO ENCONTRADO
    # -----------------------------
    @app.route('/formulario_objeto_encontrado', methods=['GET', 'POST'])
    @login_required
    def formulario_objeto_encontrado():
        if request.method == 'POST':
            return redirect('/buscar_objetos')
        return render_template('form_encontrado.html')


    @app.route('/formulario_reporte3')
    def formulario_reporte3():
        bd = conectar_db()
        cursor = bd.cursor(cursor_factory=RealDictCursor)
        cursor.execute('SELECT "ID_ESTADO" FROM "Estados"')
        estados = cursor.fetchall()
        cursor.close()
        bd.close()
        return render_template('reportes_principal.html', estados=estados)

    @app.route("/submit_enc", methods=["GET","POST"])
    def submit_enc():
        if request.method != "POST":
            return jsonify({"mensaje": "Metodo no admitido"})

        id_objeto = str(random.randint(100000, 999999))
        id_reporte = str(random.randint(100000, 999999))

        id_usuario = session['id_usuario']
        nombre_objeto = request.form.get('nombre_objeto')
        estado = request.form.get('estado')
        color_dominante = request.form.get('color_dominante')
        lugar = request.form.get('lugar')
        fecha = request.form.get('fecha')
        ficha = request.form.get('ficha')
        if ficha:
            ficha = int(ficha)
        else:
            ficha = None  
        categoria = request.form.get('categoria')
        comentario = request.form.get('comentario')

        # Archivo
        imagen = request.files.get('imagen')
        ruta = None
        if imagen:
            # limpia el nombre del archivo
            filename = secure_filename(imagen.filename)
            # crea un nombre unico usando uuid para evitar colisiones
            unique_filename = f"{uuid.uuid4()}_{filename}"
            # guardarla en la carpeta uploads
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            imagen.save(save_path)
            # guarda la ruta que voy a usar en la base de datos
            ruta = f"/uploads/{unique_filename}"

        bd = conectar_db()
        cursor = bd.cursor()

        cursor.execute("""INSERT INTO "Objetos" ("ID_OBJETO", "NOMBRE", "COLOR", "ID_ESTADO", "LUGAR_ENCONTRADO", "ID_CATEGORIA", "IMAGEN") VALUES (%s, %s, %s, %s, %s, %s, %s)""", (id_objeto, nombre_objeto, color_dominante, estado, lugar, categoria, ruta))
        cursor.execute("""INSERT INTO "Reportes_encontrados" ("FECHA", "OBSERVACIONES", "ID_OBJETO", "ID_USUARIO", "ID_REPORTE", "FICHA", "ID_CATEGORIA")VALUES (%s, %s, %s, %s, %s, %s, %s) """, (fecha, comentario, id_objeto, id_usuario, id_reporte, ficha, categoria))

        bd.commit()
        cursor.close()
        bd.close()

        session["img"] = ruta

        return jsonify({
            "mensaje": "Reporte enviado correctamente",
            "ruta": ruta
        })

    # -----------------------------
    # RUTA MOTOR DE BUSQUEDAS
    # -----------------------------
    @app.route('/buscar_objetos')
    @login_required
    def buscaar_objeto():
        return render_template('busquedas.html')

    @app.route('/busquedas/<busca>')
    def buscar (busca):

        db=conectar_db()
        cursor=db.cursor(cursor_factory=RealDictCursor)
        cursor.execute(""" SELECT "NOMBRE", "ID_OBJETO", "COLOR", "IMAGEN", "ID_CATEGORIA" FROM "Objetos" WHERE "NOMBRE" ILIKE %s OR "ID_CATEGORIA" LIKE %s """, (f'{busca}%', f'{busca}%'))
        objetos = cursor.fetchall()
        if objetos == []:
            return jsonify({"datos": False, "mensaje":"No se encontraron resultados"})
        return jsonify({"datos": objetos}) 

    # -------------------------------------
    # RUTA RECUPERAR CONTRASEÑA - Formulario inicial (ID Usuario)
    # -------------------------------------
    @app.route('/recuperar', methods=['GET', 'POST'])
    @guest_required
    def recuperar():
        if request.method == 'GET':
            return render_template('recuperar.html')
        
        # POST: enviar ID de usuario
        id_usuario = request.form.get('id_usuario')
        conexion = conectar_db()
        cursor = conexion.cursor(cursor_factory=RealDictCursor)
        cursor.execute('SELECT "PREGUNTA_1", "PREGUNTA_2" FROM public."Usuarios" WHERE "ID_USUARIO" = %s', (id_usuario,))
        user = cursor.fetchone()
        cursor.close()
        conexion.close()

        if not user:
            return jsonify({'ok': False, 'mensaje': 'Usuario no encontrado'}), 404

        # Guardamos el ID temporalmente en sesión para validar respuestas
        session['recuperar_id'] = id_usuario
        return jsonify({'ok': True, 'pregunta1': user['PREGUNTA_1'], 'pregunta2': user['PREGUNTA_2']})

    # -------------------------------------
    # RUTA VALIDAR RESPUESTAS Y CAMBIAR CONTRASEÑA
    # -------------------------------------
    @app.route('/recuperar_respuestas', methods=['POST'])
    @guest_required
    def recuperar_respuestas():
        id_usuario = session.get('recuperar_id')
        if not id_usuario:
            return jsonify({'ok': False, 'mensaje': 'No hay usuario en recuperación'}), 400

        respuesta1 = request.form.get('respuesta1')
        respuesta2 = request.form.get('respuesta2')
        nueva_contrasena = request.form.get('nueva_contrasena')

        conexion = conectar_db()
        cursor = conexion.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            'SELECT "RESPUESTA_1", "RESPUESTA_2" FROM public."Usuarios" WHERE "ID_USUARIO" = %s',
            (id_usuario,)
        )
        user = cursor.fetchone()

        if not user:
            cursor.close()
            conexion.close()
            return jsonify({'ok': False, 'mensaje': 'Usuario no encontrado'}), 404

        # Validar respuestas
        if respuesta1.lower() != user['RESPUESTA_1'].lower() or respuesta2.lower() != user['RESPUESTA_2'].lower():
            cursor.close()
            conexion.close()
            return jsonify({'ok': False, 'mensaje': 'Respuestas incorrectas'}), 401

        # Actualizar contraseña
        hashed_password = generate_password_hash(nueva_contrasena)
        cursor.execute(
            'UPDATE public."Usuarios" SET "CONTRASENA" = %s WHERE "ID_USUARIO" = %s',
            (hashed_password, id_usuario)
        )
        conexion.commit()
        cursor.close()
        conexion.close()

        session.pop('recuperar_id', None)
        return jsonify({'ok': True, 'mensaje': 'Contraseña actualizada correctamente'})