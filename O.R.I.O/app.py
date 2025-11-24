import flask
from flask import Flask, request, jsonify, render_template
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from datetime import datetime

# Configuración de la aplicación
app = Flask(__name__)

DB_CONFIG = {
    'host': 'localhost',
    'database': 'postgres',
    'user': 'postgres',
    'password': 'S0lut3c2012*',
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


# -----------------------------
# RUTA PRINCIPAL
# -----------------------------
@app.route('/')
def inicio():
    return render_template('index.html')


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
    crear_tabla_Paises()
    crear_tabla_Departamentos()
    crear_tabla_Ciudades()
    app.run(debug=True)
