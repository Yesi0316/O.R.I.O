import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()


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


# -------------------------------------
# FUNCIÓN PARA CREAR TODAS LAS TABLAS
# -------------------------------------
def crear_tablas():
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
