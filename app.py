import os
import random
from datetime import datetime

from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask import send_from_directory
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import uuid
from functools import wraps


# Carga las variables del archivo .env
load_dotenv()

# inicializar flask
app = Flask(__name__)

app.secret_key= os.getenv("SECRET_KEY")

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

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['STATIC_IMG_FOLDER'] = STATIC_IMG_FOLDER
# -------------------------
# CONFIGURACIÓN DE LA BASE DE DATOS
# -------------------------

DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'port': os.getenv('DB_PORT'),
}

# -------------------------
# CONEXIÓN A LA BASE DE DATOS
# -------------------------
def conectar_db():
    try:
        os.environ.setdefault('PGCLIENTENCODING', 'utf8')

        conexion = psycopg2.connect(
            options='-c client_encoding=UTF8',
            **DB_CONFIG
        )
        return conexion

    except UnicodeDecodeError as e:
        raise RuntimeError(
            "UnicodeDecodeError durante la conexión a PostgreSQL. "
            "Revisa que la base de datos, usuario y tablas no tengan tildes."
        ) from e

    except psycopg2.Error as e:
        print("Error al conectar:", e)
        return None

# -------------------------------------
# TABLA PAISES
# -------------------------------------
def crear_tabla_Paises():
    conexion = conectar_db()
    if conexion:
        cursor = conexion.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS public."Paises"(
                "ID_PAIS" TEXT NOT NULL,
                "NOMBRE" TEXT NOT NULL,
                PRIMARY KEY ("ID_PAIS")
            );
        """)
        conexion.commit()
        cursor.close()
        conexion.close()

# -------------------------------------
# TABLA DEPARTAMENTOS
# -------------------------------------
def crear_tabla_Departamentos():
    conexion = conectar_db()
    if conexion:
        cursor = conexion.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS public."Departamentos"(
                "ID_DEPARTAMENTO" TEXT NOT NULL,
                "NOMBRE" TEXT NOT NULL,
                "ID_PAIS" TEXT,
                PRIMARY KEY ("ID_DEPARTAMENTO"),
                FOREIGN KEY ("ID_PAIS")
                    REFERENCES public."Paises" ("ID_PAIS")
            );
        """)
        conexion.commit()
        cursor.close()
        conexion.close()

# -------------------------------------
# TABLA ESTADOS
# -------------------------------------
def crear_tabla_Estados():
    conexion = conectar_db()
    if conexion:
        cursor = conexion.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS public."Estados"(
                "ID_ESTADO" text COLLATE pg_catalog."default" NOT NULL,
                CONSTRAINT "Estados_pkey" PRIMARY KEY ("ID_ESTADO")
            );
        """)
        conexion.commit()
        cursor.close()
        conexion.close()


# -------------------------------------
# TABLA CIUDADES
# -------------------------------------
def crear_tabla_Ciudades():
    conexion = conectar_db()
    if conexion:
        cursor = conexion.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS public."Ciudades"(
                "ID_CIUDAD" TEXT NOT NULL,
                "NOMBRE" TEXT NOT NULL,
                "ID_DEPARTAMENTO" TEXT NOT NULL,
                PRIMARY KEY ("ID_CIUDAD"),
                FOREIGN KEY ("ID_DEPARTAMENTO")
                    REFERENCES public."Departamentos" ("ID_DEPARTAMENTO")
            );
        """)
        conexion.commit()
        cursor.close()
        conexion.close()

# -------------------------------------
# TABLA TIPO DE IDENTIFICACIONES
# -------------------------------------
def crear_tabla_Tipo_identificaciones():
    conexion = conectar_db()
    if conexion:
        cursor = conexion.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS public."Tipos_identificaciones"(
                "ID_IDENTIFICACION" text COLLATE pg_catalog."default" NOT NULL,
                CONSTRAINT "Tipos_identificaciones_pkey" PRIMARY KEY ("ID_IDENTIFICACION")
            );
        """)
        conexion.commit()
        cursor.close()
        conexion.close()

# -------------------------------------
# TABLA USUARIOS
# -------------------------------------
def crear_tabla_Usuario():
    conexion = conectar_db()
    if conexion:
        cursor = conexion.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS public."Usuarios"(
            "ID_USUARIO" TEXT PRIMARY KEY,
            "NOMBRE" TEXT,
            "CONTRASENA" TEXT NOT NULL,
            "PREGUNTA_1" TEXT NOT NULL,
            "PREGUNTA_2" TEXT NOT NULL,
            "RESPUESTA_1" TEXT NOT NULL,
            "RESPUESTA_2" TEXT NOT NULL
        );
        """)
        conexion.commit()
        cursor.close()
        conexion.close()


# -------------------------------------
# TABLA ROLES
# -------------------------------------

def crear_tabla_Roles():
    conexion = conectar_db()
    if conexion:
        cursor = conexion.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS public."Roles"(
            "ID_ROL" integer NOT NULL,
            "NOMBRE" text COLLATE pg_catalog."default" NOT NULL,
            CONSTRAINT "Roles_pkey" PRIMARY KEY ("ID_ROL")
            );
        """)
        conexion.commit()
        cursor.close()
        conexion.close()

# -------------------------------------
# TABLA REPORTES DE OBJETOS ENCONTRADOS
# -------------------------------------

def crear_tabla_Reportes_encontrados():
    conexion = conectar_db()
    if conexion:
        cursor = conexion.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS public."Reportes_encontrados"(
            "FECHA" date,
            "OBSERVACIONES" text COLLATE pg_catalog."default",
            "ID_OBJETO" text COLLATE pg_catalog."default" NOT NULL,
            "ID_USUARIO" text COLLATE pg_catalog."default" NOT NULL,
            "ID_REPORTE_ENC" text COLLATE pg_catalog."default" NOT NULL,
            "FICHA" integer,
            "ID_CATEGORIA" text NOT NULL,
            CONSTRAINT "Reportes_encontradospkey" PRIMARY KEY ("ID_REPORTE_ENC"),
            CONSTRAINT "ID_OBJETO" FOREIGN KEY ("ID_OBJETO")
                REFERENCES public."Objetos" ("ID_OBJETO") MATCH SIMPLE
                ON UPDATE NO ACTION
                ON DELETE NO ACTION
        );
        """)
        conexion.commit()
        cursor.close()
        conexion.close()

# -------------------------------------------------
# TABLA REPORTES OBJETOS QUE ESTÁN SIENDO BUSCADOS
# -------------------------------------------------

def crear_tabla_Reportes_perdidos():
    conexion = conectar_db()
    if conexion:
        cursor = conexion.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS public."Reportes_perdidos"(
            "FECHA" date,
            "OBSERVACIONES" text COLLATE pg_catalog."default",
            "ID_OBJETO" text COLLATE pg_catalog."default" NOT NULL,
            "ID_USUARIO" text COLLATE pg_catalog."default" NOT NULL,
            "ID_REPORTE" text COLLATE pg_catalog."default" NOT NULL,
            "FICHA" integer,
            "ID_CATEGORIA" text NOT NULL,
            CONSTRAINT "Reportes_pkey" PRIMARY KEY ("ID_REPORTE"),
            CONSTRAINT "ID_OBJETO" FOREIGN KEY ("ID_OBJETO")
                REFERENCES public."Objetos" ("ID_OBJETO") MATCH SIMPLE
                ON UPDATE NO ACTION
                ON DELETE NO ACTION
        );
        """)
        conexion.commit()
        cursor.close()
        conexion.close()



# -------------------------------------
# TABLA CATEGORIAS
# -------------------------------------

def crear_tabla_Categorias():
    conexion = conectar_db()
    if conexion:
        cursor = conexion.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS public."Categorias"(
            "ID_CATEGORIA" text COLLATE pg_catalog."default" NOT NULL,
        CONSTRAINT "Categorias_pkey" PRIMARY KEY ("ID_CATEGORIA")
        );
        """)
        conexion.commit()
        cursor.close()
        conexion.close()

# -------------------------------------
# TABLA OBJETOS
# -------------------------------------

def crear_tabla_Objetos():
    conexion = conectar_db()     
    if conexion:
        cursor = conexion.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS public."Objetos"(
            "ID_OBJETO" text COLLATE pg_catalog."default" NOT NULL,
            "NOMBRE" text COLLATE pg_catalog."default" NOT NULL,
            "COLOR" text COLLATE pg_catalog."default" NOT NULL,
            "ID_ESTADO" text COLLATE pg_catalog."default" NOT NULL,
            "LUGAR_ENCONTRADO" text COLLATE pg_catalog."default" NOT NULL,
            "ID_CATEGORIA" text COLLATE pg_catalog."default" NOT NULL,
            "IMAGEN" text COLLATE pg_catalog."default",
            CONSTRAINT "Objetos_pkey" PRIMARY KEY ("ID_OBJETO"),
            CONSTRAINT "ID_CATEGORIA" FOREIGN KEY ("ID_CATEGORIA")
            REFERENCES public."Categorias" ("ID_CATEGORIA") MATCH SIMPLE
            ON UPDATE NO ACTION
            ON DELETE NO ACTION
            NOT VALID,
            CONSTRAINT "ID_ESTADO" FOREIGN KEY ("ID_ESTADO")
            REFERENCES public."Estados" ("ID_ESTADO") MATCH SIMPLE
            ON UPDATE NO ACTION
            ON DELETE NO ACTION
        );
        """)
        conexion.commit()
        cursor.close()
        conexion.close()

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

# -----------------------------
# INICIAR SERVIDOR
# -----------------------------
if __name__ == "__main__":
    try:
        # Orden de creación respetando dependencias:
        # Paises -> Departamentos -> Ciudades -> Roles -> Estados -> Usuarios -> Objetos -> Reportes
        crear_tabla_Categorias()
        crear_tabla_Paises()
        crear_tabla_Departamentos()
        crear_tabla_Ciudades()
        crear_tabla_Roles()
        crear_tabla_Estados()
        crear_tabla_Tipo_identificaciones()  
        crear_tabla_Usuario()
        crear_tabla_Objetos()
        crear_tabla_Reportes_encontrados()
        crear_tabla_Reportes_perdidos()

        print("Tablas verificadas/creadas correctamente. Iniciando servidor...")
        app.run(debug=True)

    except Exception as e:
        # Mostrar error claro en consola para depuración
        import traceback
        print("Error al crear tablas o iniciar la aplicación:")
        traceback.print_exc()
        # No forzar exit silencioso; dejar que el desarrollador vea el stacktr  