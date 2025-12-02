import flask
from flask import Flask, request, jsonify, render_template, session, redirect
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from datetime import datetime
import random

# Configuración de la aplicación
app = Flask(__name__)

app.secret_key= "ffggfghgjfghgfhfghfghfgh"

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# -------------------------
# CONFIGURACIÓN DE LA BASE DE DATOS

DB_CONFIG = {
    'host': 'localhost',
    'database': 'ORIO_DB',
    'user': 'postgres',
    'password': '123456',
    'port': '5432'
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
                "NOMBRE" text COLLATE pg_catalog."default" NOT NULL,
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
# TABLA USUARIOS
# -------------------------------------

def crear_tabla_Usuario():
    conexion = conectar_db()
    if conexion:
        cursor = conexion.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS public."Usuarios"(
            "NOMBRE1" text COLLATE pg_catalog."default" NOT NULL,
            "NOMBRE2" text COLLATE pg_catalog."default",
            "APELLIDO1" text COLLATE pg_catalog."default" NOT NULL,
            "APELLIDO2" text COLLATE pg_catalog."default",
            "FECHA DE NACIMIENTO" date NOT NULL,
            "ID_CIUDAD" text COLLATE pg_catalog."default" NOT NULL,
            "ID_ROL" integer NOT NULL,
            "ID_USUARIO" text COLLATE pg_catalog."default" NOT NULL,
            CONSTRAINT "Usuarios_pkey" PRIMARY KEY ("ID_USUARIO"),
            CONSTRAINT "ID_CIUDAD" FOREIGN KEY ("ID_CIUDAD")
            REFERENCES public."Ciudades" ("ID_CIUDAD") MATCH SIMPLE
            ON UPDATE NO ACTION
            ON DELETE NO ACTION,
            CONSTRAINT "ID_ROL" FOREIGN KEY ("ID_ROL")
            REFERENCES public."Roles" ("ID_ROL") MATCH SIMPLE
            ON UPDATE NO ACTION
            ON DELETE NO ACTION

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
# TABLA REPORTES
# -------------------------------------

def crear_tabla_Reportes():
    conexion = conectar_db()
    if conexion:
        cursor = conexion.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS public."Reportes"(
            "FECHA" date,
            "OBSERVACIONES" text COLLATE pg_catalog."default",
            "ID_OBJETO" text COLLATE pg_catalog."default" NOT NULL,
            "ID_USUARIO" text COLLATE pg_catalog."default" NOT NULL,
            "ID_REPORTE" text COLLATE pg_catalog."default" NOT NULL,
            "FICHA" integer,
            "ID_CATEGORIA" integer NOT NULL,
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
            "NOMBRE" text COLLATE pg_catalog."default" NOT NULL,
        CONSTRAINT "Categorias_pkey" PRIMARY KEY ("ID_CATEGORIA")
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
# RUTA INICIO DE SESIÓN
# -------------------------------------

@app.route('/inicio')
def inicio_sesion():
    return render_template('inicio.html')

# -------------------------------------
# RUTA REGISTRO
# -------------------------------------

@app.route('/registro')
def registro():
    return render_template('registro.html')

# -------------------------------------
# RUTA FORMULARIO REPORTE
# -------------------------------------
@app.route('/formulario_reporte')
def formulario_reporte():
    return render_template('formulario_reporte.html')

@app.route('/formulario_reporte2')
def formulario_reporte2():
    bd = conectar_db()
    cursor = bd.cursor(cursor_factory=RealDictCursor)
    cursor.execute('SELECT "ID_ESTADO" FROM "Estados"')
    estados = cursor.fetchall()
    cursor.close()
    bd.close()
    return render_template('formulario_reporte.html', estados=estados)


@app.route("/submit", methods=["GET","POST"])
def submit():
    if request.method != "POST":
        return jsonify({"mensaje": "Metodo no admitido"})

    id_objeto = str(random.randint(100000, 999999))
    id_reporte = str(random.randint(100000, 999999))

    identificacion = request.form.get('identificacion')
    nombre_objeto = request.form.get('nombre_objeto')
    estado = request.form.get('estado')
    color_dominante = request.form.get('color_dominante')
    lugar = request.form.get('lugar')
    fecha = request.form.get('fecha')
    ficha = request.form.get('ficha')
    categoria = request.form.get('categoria')
    comentario = request.form.get('comentario')

    # Archivo
    imagen = request.files.get('imagen')
    ruta = None
    if imagen:
        save_path = os.path.join(UPLOAD_FOLDER, imagen.filename)
        print(save_path)
        imagen.save(save_path)
        ruta = f"static/{imagen.filename}"

    bd = conectar_db()
    cursor = bd.cursor()

    cursor.execute("""INSERT INTO "Objetos" ("ID_OBJETO", "NOMBRE", "COLOR", "ID_ESTADO", "LUGAR_ENCONTRADO", "ID_CATEGORIA", "IMAGEN") VALUES (%s, %s, %s, %s, %s, %s, %s)""", (id_objeto, nombre_objeto, color_dominante, estado, lugar, categoria, ruta))
    cursor.execute("""INSERT INTO "Reportes" ("FECHA", "OBSERVACIONES", "ID_OBJETO", "ID_USUARIO", "ID_REPORTE", "FICHA", "ID_CATEGORIA")VALUES (%s, %s, %s, %s, %s, %s, %s) """, (fecha, comentario, id_objeto, identificacion, id_reporte, ficha, categoria))

    bd.commit()
    cursor.close()
    bd.commit()
    bd.close()

    session["img"] = ruta

    return jsonify('/formulari_reporte')



# -----------------------------
# GUARDAR USUARIO
# -----------------------------
@app.route('/guardar_usuario', methods=['POST'])
def guardar_usuario():
    try:
        conexion = conectar_db()
        if conexion is None:
            return jsonify({'mensaje': 'Error de conexión a la base de datos'}), 500

        datos = request.get_json()
        nombre = datos.get('nombre')
        email = datos.get('email')
        fecha_creacion = datetime.now()

        if not nombre or not email:
            return jsonify({'mensaje': 'El nombre y el correo son obligatorios'}), 400

        cursor = conexion.cursor()

        sql_insert = """
            INSERT INTO Usuario (nombre, email, fecha_creacion)
            VALUES (%s, %s, %s)
            RETURNING id;
        """ 

        cursor.execute(sql_insert, (nombre, email, fecha_creacion))
        usuario_id = cursor.fetchone()[0]

        conexion.commit()
        cursor.close()
        conexion.close()

        return jsonify({
            'mensaje': 'Usuario guardado exitosamente',
            'usuario_id': usuario_id
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
        cursor.execute("SELECT * FROM Usuario ORDER BY id DESC;")
        usuarios = cursor.fetchall()

        for u in usuarios:
            if u['fecha_creacion']:
                u['fecha_creacion'] = u['fecha_creacion'].strftime('%Y-%m-%d %H:%M:%S')

        cursor.close()
        conexion.close()

        return jsonify(usuarios), 200

    except Exception as e:
        return jsonify({'mensaje': 'Error al obtener los usuarios', 'error': str(e)}), 500


# -----------------------------
# INICIAR SERVIDOR
# -----------------------------

if __name__ == "__main__":
    try:
        # Orden de creación respetando dependencias:
        # Paises -> Departamentos -> Ciudades -> Roles -> Estados -> Usuarios -> Objetos -> Reportes
        crear_tabla_Paises()
        crear_tabla_Departamentos()
        crear_tabla_Ciudades()
        crear_tabla_Roles()
        crear_tabla_Estados()
        crear_tabla_Usuario()
        crear_tabla_Objetos()
        crear_tabla_Reportes()

        print("Tablas verificadas/creadas correctamente. Iniciando servidor...")
        app.run(debug=True)

    except Exception as e:
        # Mostrar error claro en consola para depuración
        import traceback
        print("Error al crear tablas o iniciar la aplicación:")
        traceback.print_exc()
        # No forzar exit silencioso; dejar que el desarrollador vea el stacktr  