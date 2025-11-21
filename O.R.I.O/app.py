import flask  #importar flask
from flask import Flask, request, jsonify, render_template  #importar funciones de flask
import psycopg2  #importar psycopg2 para conectar a la base de datos PostgreSQL
from psycopg2.extras import RealDictCursor  #importar RealDictCursor para obtener resultados en formato diccionario
import os  #importar os para manejar variables de entorno
from datetime import datetime  #importar datetime para manejar fechas y horas

# Configuración de la aplicación
app = Flask(__name__)

DB_CONFIG = {
    'host': 'localhost',
    'database': 'posgres',
    'user': 'postgres',
    'password': '123456',
    'port': '5432'
}

def conectar_db():  #crea una función para conectar con mi base de datos
    try:
        # Forzar codificación cliente a UTF-8 para evitar UnicodeDecodeError desde libpq
        os.environ.setdefault('PGCLIENTENCODING', 'utf8')

        # pasar la opción a libpq también (asegura que libpq use UTF8)
        conexion = psycopg2.connect(options='-c client_encoding=UTF8', **DB_CONFIG)
        return conexion
    except UnicodeDecodeError as e:
        # Mensaje más útil para depuración
        raise RuntimeError(
            "UnicodeDecodeError durante la conexión a PostgreSQL. "
            "Verifique que las credenciales y variables de entorno estén en UTF-8 "
            "y pruebe a exportar PGCLIENTENCODING=utf8 antes de ejecutar la app."
        ) from e
    except psycopg2.Error as e:
        print("Error al conectar:", e)  #Si ocurre un error lo muestra en consola
        return None  #retorna None si falla la conexión

#Crear la tabla Usuario
def crear_tabla_Paises():
    conexion = conectar_db()  #conectar a la base de datos
    #Crear la tabla Países
def crear_tabla_pPises():
    conexion = conectar_db()  #conectar a la base de datos
    if conexion:
        cursor = conexion.cursor()  #crear cursor para ejecutar consultas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "Países" (
                "ID_PAIS" TEXT NOT NULL,
                "NOMBRE" TEXT NOT NULL,
                PRIMARY KEY ("ID_PAIS")
            );
        """)  #crear la tabla Países si no existe
        conexion.commit()  #guardar cambios
        cursor.close()  #cerrar cursor
        conexion.close()  #cerrar conexión

def crear_tabla_Departamentos():
    conexion = conectar_db()  #conectar a la base de datos
    #Crear la tabla Departamentos
def crear_tabla_Departamentos():
    conexion = conectar_db()  #conectar a la base de datos
    if conexion:
        cursor = conexion.cursor()  #crear cursor para ejecutar consultas
        cursor.execute("""
         CREATE TABLE IF NOT EXISTS public."Departamentos"(
            "ID_DEPARTAMENTO" text COLLATE pg_catalog."default" NOT NULL,
            "NOMBRE" text COLLATE pg_catalog."default" NOT NULL,
            "ID_PAIS" text COLLATE pg_catalog."default",
            CONSTRAINT "Departamentos_pkey" PRIMARY KEY ("ID_DEPARTAMENTO"),
            CONSTRAINT "ID_PAIS" FOREIGN KEY ("ID_PAIS")
            REFERENCES public."Países" ("ID_PAIS") MATCH SIMPLE
            ON UPDATE NO ACTION
            ON DELETE NO ACTION
            );
        """)  #crear la tabla Departamento si no existe
        conexion.commit()  #guardar cambios
        cursor.close()  #cerrar cursor
        conexion.close()  #cerrar conexión

def crear_tabla_Ciudades():
    conexion = conectar_db()  #conectar a la base de datos
    #Crear la tabla 
def crear_tabla_Ciudades():
    conexion = conectar_db()  #conectar a la base de datos
    if conexion:
        cursor = conexion.cursor()  #crear cursor para ejecutar consultas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS public."Ciudades"(
                "ID_CIUDAD" text COLLATE pg_catalog."default" NOT NULL,
                "NOMBRE" text COLLATE pg_catalog."default" NOT NULL,
                "ID_DEPARTAMENTO" text COLLATE pg_catalog."default" NOT NULL,
                CONSTRAINT "Ciudad_pkey" PRIMARY KEY ("ID_CIUDAD"),
                CONSTRAINT "ID_DEPARTAMENTOS" FOREIGN KEY ("ID_DEPARTAMENTO")
                REFERENCES public."Departamentos" ("ID_DEPARTAMENTO") MATCH SIMPLE
                ON UPDATE NO ACTION
                ON DELETE NO ACTION
);
        """)  #crear la tabla si no existe
        conexion.commit()  #guardar cambios
        cursor.close()  #cerrar cursor
        conexion.close()  #cerrar conexión
    

#Ruta principal del sitio web
@app.route('/')
def inicio():
    return render_template('index.html')  #retorna el template index.html

#ruta para guardar los datos de un usuario
@app.route('/guardar_usuario', methods=['POST'])
def guardar_usuario():
    try:
        conexion = conectar_db()  #conectar a la base de datos
        if conexion is None:
            return jsonify({'mensaje': 'Error de conexión a la base de datos'}), 500

        #obtiene los datos enviados en Json
        datos = request.get_json()  #obtener datos en formato JSON
        nombre = datos.get('nombre')  #obtener nombre
        email = datos.get('email')  #obtener email
        fecha_creacion = datetime.now()  #obtener fecha y hora actual

        #validar datos obligatorios
        if not nombre or not email:
            return jsonify({'mensaje': 'El nombre y el correo son obligatorios'}), 400

        #crear cursor para ejecutar consultas
        cursor = conexion.cursor()

        sql_insert = """
            INSERT INTO Usuario (nombre, email, fecha_creacion)
            VALUES (%s, %s, %s)
            RETURNING id;
        """  #consulta SQL para insertar usuario

        cursor.execute(sql_insert, (nombre, email, fecha_creacion))
        usuario_id = cursor.fetchone()[0]  #obtener id generado

        conexion.commit()  #guardar cambios
        cursor.close()  #cerrar cursor
        conexion.close()  #cerrar conexión

        return jsonify({'mensaje': 'Usuario guardado exitosamente', 'usuario_id': usuario_id})

    except Exception as e:
        return jsonify({'mensaje': 'Error al guardar el usuario', 'error': str(e)}), 500

#Ruta para consultar lo guardado
@app.route('/usuarios', methods=['GET'])
def obtener_usuarios():
    try:
        conexion = conectar_db()  #conectar a la base de datos
        if conexion is None:
            return jsonify({'mensaje': 'Error de conexión a la base de datos'}), 500

        cursor = conexion.cursor(cursor_factory=RealDictCursor)  #obtener resultados como diccionario
        cursor.execute("SELECT * FROM Usuario ORDER BY id DESC;")  #consulta usuarios

        usuarios = cursor.fetchall()  #obtener registros

        #Formatear la fecha de creación para que sea legible
        for u in usuarios:
            if u['fecha_creacion']:
                u['fecha_creacion'] = u['fecha_creacion'].strftime('%Y-%m-%d %H:%M:%S')

        cursor.close()  #cerrar cursor
        conexion.close()  #cerrar conexión

        return jsonify(usuarios), 200

    except Exception as e:
        return jsonify({'mensaje': 'Error al obtener los usuarios', 'error': str(e)}), 500

#inicializar servidor
if __name__ == "__main__":
    crear_tabla_Paises()  #crear tabla si no existe
    crear_tabla_Departamentos
    app.run(debug=True)