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
    # -----------------------------
    # RUTA DETALLES DE OBJETO
    # -----------------------------
    @app.route('/detalles/<id_objeto>')
    def detalles_objeto(id_objeto):
        db = conectar_db()
        cursor = db.cursor(cursor_factory=RealDictCursor)
        # Buscar objeto y su reporte (perdido o encontrado)
        cursor.execute('''
            SELECT o."NOMBRE", o."ID_OBJETO", o."COLOR", o."IMAGEN", o."ID_CATEGORIA" as CATEGORIA,
                   r."FECHA", r."OBSERVACIONES", r."ID_USUARIO", u."NOMBRE" as NOMBRE_USUARIO
            FROM "Objetos" o
            LEFT JOIN "Reportes_perdidos" r ON o."ID_OBJETO" = r."ID_OBJETO"
            LEFT JOIN "Usuarios" u ON r."ID_USUARIO" = u."ID_USUARIO"
            WHERE o."ID_OBJETO" = %s AND r."ID_USUARIO" IS NOT NULL
            UNION
            SELECT o."NOMBRE", o."ID_OBJETO", o."COLOR", o."IMAGEN", o."ID_CATEGORIA" as CATEGORIA,
                   r."FECHA", r."OBSERVACIONES", r."ID_USUARIO", u."NOMBRE" as NOMBRE_USUARIO
            FROM "Objetos" o
            LEFT JOIN "Reportes_encontrados" r ON o."ID_OBJETO" = r."ID_OBJETO"
            LEFT JOIN "Usuarios" u ON r."ID_USUARIO" = u."ID_USUARIO"
            WHERE o."ID_OBJETO" = %s AND r."ID_USUARIO" IS NOT NULL
        ''', (id_objeto, id_objeto))
        item = cursor.fetchone()
        # Si no hay nombre visible, buscarlo manualmente
        if item and (not item.get('NOMBRE_USUARIO') or item['NOMBRE_USUARIO'] is None) and item.get('ID_USUARIO'):
            cursor.execute('SELECT "NOMBRE" FROM "Usuarios" WHERE "ID_USUARIO" = %s', (item['ID_USUARIO'],))
            user = cursor.fetchone()
            if user and user.get('NOMBRE'):
                item['NOMBRE_USUARIO'] = user['NOMBRE']
        cursor.close()
        db.close()
        if not item:
            return render_template('detalles_reportes.html', item=None, error="No se encontró el objeto")
        return render_template('detalles_reportes.html', item=item)
    

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

            respuesta1_hash = generate_password_hash(respuesta1)
            respuesta2_hash = generate_password_hash(respuesta2)

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
                respuesta1_hash, 
                respuesta2_hash
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
    # RUTA MOTOR DE BUSQUEDAS
    # -----------------------------
    @app.route('/busquedas')
    def buscar():
        q = request.args.get('q', '').strip()
        categoria = request.args.get('categoria', '').strip()
        tipo = request.args.get('tipo', '').strip()

        db = conectar_db()
        cursor = db.cursor(cursor_factory=RealDictCursor)

        # Selecciona la tabla según el tipo
        if tipo == "perdido":
            join = 'INNER JOIN "Reportes_perdidos" r ON o."ID_OBJETO" = r."ID_OBJETO"'
        elif tipo == "encontrado":
            join = 'INNER JOIN "Reportes_encontrados" r ON o."ID_OBJETO" = r."ID_OBJETO"'
        else:
            join = ''

        query = f'SELECT o."NOMBRE", o."ID_OBJETO", o."COLOR", o."IMAGEN", o."ID_CATEGORIA" FROM "Objetos" o {join} WHERE 1=1'
        params = []

        # Buscar por nombre o por categoría (nombre o id)
        if q:
            query += ' AND (o."NOMBRE" ILIKE %s OR o."ID_CATEGORIA" ILIKE %s)'
            params.append(f'%{q}%')
            params.append(f'%{q}%')
        if categoria:
            query += ' AND o."ID_CATEGORIA" = %s'
            params.append(categoria)

        query += ' ORDER BY o."NOMBRE" ASC'

        cursor.execute(query, params)
        objetos = cursor.fetchall()
        cursor.close()
        db.close()


        if not objetos:
            return jsonify({"datos": False, "mensaje": "No se encontraron resultados"})
        return jsonify({"datos": objetos})

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
        return render_template("menu.html", active="panel")
    # -------------------------------------
    # RUTA FORMULARIO REPORTE
    # -------------------------------------
    @app.route('/formulario_perdido', methods=['GET', 'POST'])
    @login_required
    def formulario_perdido():
        if request.method == 'POST':
            return redirect('/buscar_objetos')
        # Obtener categorías y estados de la base de datos, y si no existen, insertarlos
        db = conectar_db()
        cursor = db.cursor(cursor_factory=RealDictCursor)
        # Categorías
        cursor.execute('SELECT "ID_CATEGORIA" FROM "Categorias"')
        categorias = cursor.fetchall()
        if not categorias:
            categorias_default = [
                'Documentos',
                'Tecnología',
                'Accesorios',
                'Ropa',
                'Llaves',
                'Otros'
            ]
            for cat in categorias_default:
                cursor.execute('INSERT INTO "Categorias" ("ID_CATEGORIA") VALUES (%s) ON CONFLICT DO NOTHING', (cat,))
            db.commit()
            cursor.execute('SELECT "ID_CATEGORIA" FROM "Categorias"')
            categorias = cursor.fetchall()
        # Estados
        cursor.execute('SELECT "ID_ESTADO" FROM "Estados"')
        estados = cursor.fetchall()
        if not estados:
            estados_default = ['Bueno', 'Regular', 'Malo']
            for est in estados_default:
                cursor.execute('INSERT INTO "Estados" ("ID_ESTADO") VALUES (%s) ON CONFLICT DO NOTHING', (est,))
            db.commit()
        cursor.close()
        db.close()
        return render_template('form_perdido.html', categorias=categorias)


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

        # Asegurar que el estado existe
        cursor.execute('SELECT 1 FROM "Estados" WHERE "ID_ESTADO" = %s', (estado,))
        if not cursor.fetchone():
            estados_default = ['Bueno', 'Regular', 'Malo']
            for est in estados_default:
                cursor.execute('INSERT INTO "Estados" ("ID_ESTADO") VALUES (%s) ON CONFLICT DO NOTHING', (est,))
            bd.commit()
        # Asegurar que la categoría existe
        cursor.execute('SELECT 1 FROM "Categorias" WHERE "ID_CATEGORIA" = %s', (categoria,))
        if not cursor.fetchone():
            categorias_default = [
                'Documentos',
                'Tecnología',
                'Accesorios',
                'Ropa',
                'Llaves',
                'Otros'
            ]
            for cat in categorias_default:
                cursor.execute('INSERT INTO "Categorias" ("ID_CATEGORIA") VALUES (%s) ON CONFLICT DO NOTHING', (cat,))
            bd.commit()

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
        bd = conectar_db()
        cursor = bd.cursor(cursor_factory=RealDictCursor)
        cursor.execute('SELECT "ID_CATEGORIA" FROM "Categorias"')
        categorias = cursor.fetchall()
        cursor.close()
        bd.close()

        return render_template('form_encontrado.html', categorias=categorias)



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

        # Verificar si ya existe un reporte igual para este usuario y objeto
        cursor.execute('''
            SELECT 1 FROM "Reportes_encontrados" r
            JOIN "Objetos" o ON r."ID_OBJETO" = o."ID_OBJETO"
            WHERE r."ID_USUARIO" = %s AND o."NOMBRE" = %s AND o."COLOR" = %s AND o."ID_CATEGORIA" = %s
        ''', (id_usuario, nombre_objeto, color_dominante, categoria))
        existe = cursor.fetchone()
        if existe:
            cursor.close()
            bd.close()
            return jsonify({"mensaje": "Ya existe un reporte igual para este usuario.", "existe": true})

        cursor.execute("""
            INSERT INTO "Objetos"  
            ("ID_OBJETO", "NOMBRE", "COLOR", "ID_ESTADO", "LUGAR_ENCONTRADO", "ID_CATEGORIA", "IMAGEN")    
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (id_objeto, nombre_objeto, color_dominante, estado, lugar, categoria, ruta))
        cursor.execute("""
            INSERT INTO "Reportes_encontrados"
            ("FECHA", "OBSERVACIONES", "ID_OBJETO", "ID_USUARIO", "ID_REPORTE_ENC", "FICHA", "ID_CATEGORIA")
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (fecha, comentario, id_objeto, id_usuario, id_reporte, ficha, categoria))


        bd.commit()
        cursor.close()
        bd.close()

        session["img"] = ruta

        return jsonify({
            "mensaje": "Reporte enviado correctamente",
            "ruta": ruta,
            "existe": False
        })

    # -----------------------------
    # RUTA DEBUG: LISTAR TODOS LOS OBJETOS
    # -----------------------------
    @app.route('/debug_objetos')
    @login_required
    def debug_objetos():
        db = conectar_db()
        cursor = db.cursor(cursor_factory=RealDictCursor)
        cursor.execute('SELECT * FROM "Objetos" ORDER BY "NOMBRE" ASC')
        objetos = cursor.fetchall()
        cursor.close()
        db.close()
        return jsonify(objetos)

    # -----------------------------
    # RUTA MOTOR DE BUSQUEDAS CON FILTROS
    # -----------------------------
    @app.route('/buscar_objetos', methods=['GET'])
    @login_required
    def buscar_objeto():
        q = request.args.get('q', '')  # texto de búsqueda
        categoria = request.args.get('categoria', '')
        color = request.args.get('color', '')

        db = conectar_db()
        cursor = db.cursor(cursor_factory=RealDictCursor)

        # Construir consulta dinámica según los filtros
        query = 'SELECT "NOMBRE", "ID_OBJETO", "COLOR", "IMAGEN", "ID_CATEGORIA" FROM "Objetos" WHERE 1=1'
        params = []

        if q:
            query += ' AND "NOMBRE" ILIKE %s'
            params.append(f'%{q}%')
        if categoria:
            query += ' AND "ID_CATEGORIA" = %s'
            params.append(categoria)
        if color:
            query += ' AND "COLOR" ILIKE %s'
            params.append(f'%{color}%')

        cursor.execute(query, params)
        resultados = cursor.fetchall()
        cursor.close()
        db.close()

        return render_template('busquedas.html', active="panel", resultados=resultados, q=q, categoria=categoria, color=color,)

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

        # Validar respuestas encriptadas
        if not check_password_hash(user['RESPUESTA_1'], respuesta1) or not check_password_hash(user['RESPUESTA_2'], respuesta2):
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

    @app.route("/perfil")
    @login_required
    def perfil():
        return render_template("perfil.html", active="perfil")
    
    @app.route("/dashboard")
    @login_required
    def dashboard():
        return render_template("dashboard.html", active="dashboard")
    
    @app.route("/reportes")
    def reportes():
        return render_template("reportes.html", active="reportes")

    @app.route("/configuracion")
    def configuracion():
        return render_template("configuracion.html", active="configuracion")
