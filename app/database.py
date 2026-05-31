"""
Módulo de configuración y conexión a la base de datos PostgreSQL.

Este módulo maneja:
- Configuración de conexión a PostgreSQL
- Creación de tablas base del sistema
- Inicialización de datos por defecto

Ahora reside dentro del paquete `app`, por lo que otras partes de la
aplicación lo importan con `from app.database import ...`.
"""

import os
import psycopg2
import time
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()


# ========================
# CONFIGURACIÓN
# ========================

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": os.getenv("DB_PORT"),
}

# Datos por defecto para las tablas
CATEGORIAS_DEFAULT = [
    "Documentos",
    "Tecnología",
    "Accesorios",
    "Ropa",
    "Llaves",
    "Otros",
]

ESTADOS_DEFAULT = ["Bueno", "Regular", "Malo"]

PLANES_DEFAULT = [
    (1, "Reporte verificado", 15000),
    (2, "Reporte Propietarios", 25000),
    (3, "Todo incluido", 30000),
]

ROLES_DEFAULT = [
    (1, "Usuario"),
    (2, "Administrador"),
]


def insertar_planes():
    conn = conectar_db()
    if not conn:
        return 

    cursor = conn.cursor()

    cursor.executemany(
        '''
        INSERT INTO public."Planes" ("ID_PLAN", "NAME", "PRECIO")
        VALUES (%s, %s, %s)
        ON CONFLICT ("ID_PLAN") DO NOTHING
        ''',
        PLANES_DEFAULT
    )

    conn.commit()
    cursor.close()
    conn.close()

NAME_METODOS_DEFAULT = [
    "Nequi",
    "BanColombia",
    "Paypal",
    "Tarjeta",

]

PAISES_DEFAULT = [
    ("1", "Colombia"),
    ("2", "México"),
    ("3", "Argentina"),
    ("4", "Chile"),
    ("5", "Perú"),
    ("6", "Ecuador"),
    ("7", "Venezuela"),
    ("8", "España"),
    ("9", "Estados Unidos"),
    ("10", "Canadá"),
    ("11", "Brasil"),
    ("12", "Uruguay"),
    ("13", "Paraguay"),
    ("14", "Bolivia"),
    ("15", "Costa Rica"),
]

def insertar_paises():
    conn = conectar_db()
    if not conn:
        return 

    cursor = conn.cursor()

    cursor.executemany(
        '''
        INSERT INTO public."Paises" ("ID_PAIS", "NOMBRE")
        VALUES (%s, %s)
        ON CONFLICT ("ID_PAIS") DO NOTHING
        ''',
        PAISES_DEFAULT
    )

    conn.commit()
    cursor.close()
    conn.close()

# ========================
# CONEXIÓN A LA BASE DE DATOS
# ========================


def conectar_db():
    """Establece conexión a PostgreSQL con reintentos (para Docker)."""
    os.environ.setdefault("PGCLIENTENCODING", "utf8") 

    intentos = 10

    for intento in range(intentos):
        try:
            conexion = psycopg2.connect(
                options="-c client_encoding=UTF8",
                **DB_CONFIG
            )

            print("✓ Conectado a PostgreSQL")
            return conexion

        except psycopg2.Error as e:
            print(f"Intento {intento+1}/{intentos}: PostgreSQL aún no está listo...")
            time.sleep(2)

    print("✗ No se pudo conectar a la base de datos.")
    return None


# ========================
# FUNCIONES GENÉRICAS
# ========================


def ejecutar_sql(sql, descripcion=""):
    """Ejecuta un comando SQL de forma segura.

    Args:
        sql (str): Comando SQL a ejecutar
        descripcion (str): Descripción de la operación (para logs)
    """
    conexion = conectar_db()
    if conexion:
        try:
            cursor = conexion.cursor()
            cursor.execute(sql)
            conexion.commit()
            cursor.close()
            if descripcion:
                print(f"✓ {descripcion}")
        except Exception as e:
            print(f"✗ Error en {descripcion}: {e}")
        finally:
            conexion.close()


# ========================
# DEFINICIÓN DE TABLAS
# ========================

TABLAS = {
    "Categorias": """
        CREATE TABLE IF NOT EXISTS public."Categorias"(
            "ID_CATEGORIA" TEXT PRIMARY KEY,
            "NOMBRE" TEXT NOT NULL
        );
    """,
    "Paises": """
        CREATE TABLE IF NOT EXISTS public."Paises"(
            "ID_PAIS" TEXT PRIMARY KEY,
            "NOMBRE" TEXT NOT NULL
        );
    """,
    "Departamentos": """
        CREATE TABLE IF NOT EXISTS public."Departamentos"(
            "ID_DEPARTAMENTO" TEXT PRIMARY KEY,
            "NOMBRE" TEXT NOT NULL,
            "ID_PAIS" TEXT,
            FOREIGN KEY ("ID_PAIS") REFERENCES public."Paises" ("ID_PAIS")
        );
    """,
    "Ciudades": """
        CREATE TABLE IF NOT EXISTS public."Ciudades"(
            "ID_CIUDAD" TEXT PRIMARY KEY,
            "NOMBRE" TEXT NOT NULL,
            "ID_DEPARTAMENTO" TEXT NOT NULL,
            FOREIGN KEY ("ID_DEPARTAMENTO") 
                REFERENCES public."Departamentos" ("ID_DEPARTAMENTO")
        );
    """,
    "Roles": """
        CREATE TABLE IF NOT EXISTS public."Roles"(
            "ID_ROL" INTEGER PRIMARY KEY,
            "NOMBRE" TEXT NOT NULL
        );
    """,
    "Estados": """
        CREATE TABLE IF NOT EXISTS public."Estados"(
            "ID_ESTADO" TEXT PRIMARY KEY
        );
    """,
    "Tipos_identificaciones": """
        CREATE TABLE IF NOT EXISTS public."Tipos_identificaciones"(
            "ID_IDENTIFICACION" TEXT PRIMARY KEY
        );
    """,
    "Usuarios": """
        CREATE TABLE IF NOT EXISTS public."Usuarios"(
            "ID_USUARIO" TEXT PRIMARY KEY,
            "NOMBRE" TEXT,
            "GENERO" VARCHAR(10) CHECK ("GENERO" IN ('masculino','femenino')) NOT NULL,
            "CONTRASENA" TEXT NOT NULL,
            "PREGUNTA_1" TEXT NOT NULL,
            "PREGUNTA_2" TEXT NOT NULL,
            "RESPUESTA_1" TEXT NOT NULL,
            "RESPUESTA_2" TEXT NOT NULL,
            "INTENTOS_RECUPERACION" INTEGER DEFAULT 0,
            "BLOQUEADO_HASTA" TIMESTAMP,
            "TEMA_PREFERENCIA" TEXT DEFAULT 'claro',
            "ID_ROL" INTEGER NOT NULL,
            FOREIGN KEY ("ID_ROL") REFERENCES public."Roles" ("ID_ROL")
        );
    """,
    "Objetos": """
        CREATE TABLE IF NOT EXISTS public."Objetos"(
            "ID_OBJETO" TEXT PRIMARY KEY,
            "NOMBRE" TEXT NOT NULL,
            "COLOR" TEXT NOT NULL,
            "ID_ESTADO" TEXT NOT NULL,
            "LUGAR_ENCONTRADO" TEXT NOT NULL,
            "ID_CATEGORIA" TEXT NOT NULL,
            "IMAGEN" TEXT,
            FOREIGN KEY ("ID_CATEGORIA") REFERENCES public."Categorias" ("ID_CATEGORIA"),
            FOREIGN KEY ("ID_ESTADO") REFERENCES public."Estados" ("ID_ESTADO")
        );
    """,
    "Reportes_encontrados": """
        CREATE TABLE IF NOT EXISTS public."Reportes_encontrados"(
            "ID_REPORTE_ENC" TEXT PRIMARY KEY,
            "FECHA" DATE,
            "OBSERVACIONES" TEXT,
            "ID_OBJETO" TEXT NOT NULL,
            "ID_USUARIO" TEXT NOT NULL,
            "FICHA" INTEGER,
            "ID_CATEGORIA" TEXT NOT NULL,
            FOREIGN KEY ("ID_OBJETO") REFERENCES public."Objetos" ("ID_OBJETO")
        );
    """,
    "Perfiles": """
        CREATE TABLE IF NOT EXISTS public."Perfiles"(
            "ID_PERFIL" SERIAL PRIMARY KEY,
            "ID_USUARIO" TEXT NOT NULL UNIQUE,
            "NOMBRE" TEXT,
            "APELLIDO" TEXT,
            "TELEFONO" TEXT,
            "CORREO" TEXT,
            "FOTO_PERFIL" TEXT,
            "FECHA_ACTUALIZACION" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY ("ID_USUARIO") REFERENCES public."Usuarios" ("ID_USUARIO") ON DELETE CASCADE
        );
    """,
    "Reportes_perdidos": """
        CREATE TABLE IF NOT EXISTS public."Reportes_perdidos"(
            "ID_REPORTE" TEXT PRIMARY KEY,
            "FECHA" DATE,
            "OBSERVACIONES" TEXT,
            "ID_OBJETO" TEXT NOT NULL,
            "ID_USUARIO" TEXT NOT NULL,
            "FICHA" INTEGER,
            "ID_CATEGORIA" TEXT NOT NULL,
            FOREIGN KEY ("ID_OBJETO") REFERENCES public."Objetos" ("ID_OBJETO")
        );
    """,

    "Planes":"""
        CREATE TABLE IF NOT EXISTS public."Planes"
        (
            "ID_PLAN" integer NOT NULL,
            "NAME" character varying(50) COLLATE pg_catalog."default" NOT NULL,
            "PRECIO" integer,
            CONSTRAINT "Planes_pkey" PRIMARY KEY ("ID_PLAN")
        );
    """,

    "Metodos_pago":"""
CREATE TABLE IF NOT EXISTS public."Metodos_pago"
    (
        "ID_METODO" serial NOT NULL,
        "NAME_METODO" text COLLATE pg_catalog."default" NOT NULL UNIQUE,
        CONSTRAINT "Metodos_pago_pkey" PRIMARY KEY ("ID_METODO")
    );
""",

    "facturas":"""
            CREATE TABLE IF NOT EXISTS public."Facturas"
        (
            "ID_FACTURA" SERIAL,
            "EMAIL" character varying(320) COLLATE pg_catalog."default" NOT NULL,
            "NOMBRES" text COLLATE pg_catalog."default" NOT NULL,
            "APELLIDOS" text COLLATE pg_catalog."default" NOT NULL,
            "DIRECCION" character varying(255) COLLATE pg_catalog."default" NOT NULL,
            "CODIGO_POSTAL" integer NOT NULL,
            "CIUDAD" text COLLATE pg_catalog."default" NOT NULL,
            "ID_PAIS" text NOT NULL,
            "ID_METODO" integer NOT NULL,
            "ID_PLAN" integer,
            CONSTRAINT "Facturas_pkey" PRIMARY KEY ("ID_FACTURA"),
            CONSTRAINT "ID_METODO" FOREIGN KEY ("ID_METODO")
                REFERENCES public."Metodos_pago" ("ID_METODO") MATCH SIMPLE
                ON UPDATE NO ACTION
                ON DELETE NO ACTION
                NOT VALID,
            CONSTRAINT "ID_PAIS" FOREIGN KEY ("ID_PAIS")
                REFERENCES public."Paises" ("ID_PAIS") MATCH SIMPLE
                ON UPDATE NO ACTION
                ON DELETE NO ACTION
                NOT VALID,
            CONSTRAINT "ID_PLAN" FOREIGN KEY ("ID_PLAN")
                REFERENCES public."Planes" ("ID_PLAN") MATCH SIMPLE
                ON UPDATE NO ACTION
                ON DELETE NO ACTION
                NOT VALID
        );
        """,
    

}


# ========================
# FUNCIONES DE CREACIÓN DE TABLAS
# ========================


def crear_tabla_Categorias():
    """Crea la tabla Categorias."""
    ejecutar_sql(TABLAS["Categorias"], "Tabla Categorias")


def crear_tabla_Paises():
    """Crea la tabla Paises."""
    ejecutar_sql(TABLAS["Paises"], "Tabla Paises")


def crear_tabla_Departamentos():
    """Crea la tabla Departamentos."""
    ejecutar_sql(TABLAS["Departamentos"], "Tabla Departamentos")


def crear_tabla_Ciudades():
    """Crea la tabla Ciudades."""
    ejecutar_sql(TABLAS["Ciudades"], "Tabla Ciudades")


def crear_tabla_Roles():
    """Crea la tabla Roles."""
    ejecutar_sql(TABLAS["Roles"], "Tabla Roles")


def crear_tabla_Estados():
    """Crea la tabla Estados."""
    ejecutar_sql(TABLAS["Estados"], "Tabla Estados")


def crear_tabla_Tipo_identificaciones():
    """Crea la tabla Tipos_identificaciones."""
    ejecutar_sql(TABLAS["Tipos_identificaciones"], "Tabla Tipos_identificaciones")


def crear_tabla_Usuario():
    """Crea la tabla Usuarios."""
    ejecutar_sql(TABLAS["Usuarios"], "Tabla Usuarios")


def crear_tabla_Perfiles():
    """Crea la tabla Perfiles."""
    ejecutar_sql(TABLAS["Perfiles"], "Tabla Perfiles")


def crear_tabla_Objetos():
    """Crea la tabla Objetos."""
    ejecutar_sql(TABLAS["Objetos"], "Tabla Objetos")


def crear_tabla_Reportes_encontrados():
    """Crea la tabla Reportes_encontrados."""
    ejecutar_sql(TABLAS["Reportes_encontrados"], "Tabla Reportes_encontrados")


def crear_tabla_Reportes_perdidos():
    """Crea la tabla Reportes_perdidos."""
    ejecutar_sql(TABLAS["Reportes_perdidos"], "Tabla Reportes_perdidos")

def crear_tabla_Planes():
    """Crea la tabla Planes."""
    ejecutar_sql(TABLAS["Planes"], "Tabla Planes")

def crear_tabla_Metodos_pago():
    """Crea la tabla Metodos_pago."""
    ejecutar_sql(TABLAS["Metodos_pago"], "Tabla Metodos_pago")

def crear_tabla_Facturas():
    """Crea la tabla Facturas."""
    ejecutar_sql(TABLAS["facturas"], "Tabla Facturas")



def aplicar_migraciones():
    """Aplica migraciones a la base de datos para versiones nuevas."""
    conexion = conectar_db()
    if not conexion:
        return
    

    
    cursor = conexion.cursor()
    try:
        # Migración: Agregar columna TEMA_PREFERENCIA si no existe
        cursor.execute("""
            ALTER TABLE public."Usuarios"
            ADD COLUMN IF NOT EXISTS "TEMA_PREFERENCIA" TEXT DEFAULT 'claro'
        """)
        cursor.execute("""
            ALTER TABLE public."Categorias"
            ADD COLUMN IF NOT EXISTS "NOMBRE" TEXT
        """)
        conexion.commit()
        print("✓ Migraciones aplicadas correctamente")
    except Exception as e:
        print(f"✗ Error aplicando migraciones: {e}")
    finally:
        cursor.close()
        conexion.close()


def crear_tablas():
    """
    Crea todas las tablas de la base de datos en el orden correcto,
    respetando las dependencias de claves foráneas.
    """
    crear_tabla_Categorias()
    crear_tabla_Paises()
    crear_tabla_Departamentos()
    crear_tabla_Ciudades()
    crear_tabla_Roles()
    crear_tabla_Estados()
    crear_tabla_Tipo_identificaciones()
    crear_tabla_Usuario()
    crear_tabla_Perfiles()
    crear_tabla_Objetos()
    crear_tabla_Reportes_encontrados()
    crear_tabla_Reportes_perdidos()
    crear_tabla_Planes()
    crear_tabla_Metodos_pago()
    crear_tabla_Facturas()
    insertar_planes()
    insertar_paises()


def inicializar_datos_default():
    """
    Inserta datos por defecto en las tablas de catálogos
    (Categorias y Estados) si no existen y crea perfiles para usuarios sin perfil.
    """
    conexion = conectar_db()
    if not conexion:
        return

    cursor = conexion.cursor()

    try:
        # Insertar categorías por defecto
        for cat in CATEGORIAS_DEFAULT:
            cursor.execute(
                '''
                INSERT INTO "Categorias" ("ID_CATEGORIA", "NOMBRE")
                VALUES (%s, %s)
                ON CONFLICT ("ID_CATEGORIA") DO UPDATE SET "NOMBRE" = EXCLUDED."NOMBRE"
                ''',
                (cat, cat),
            )

        # Insertar estados por defecto
        for est in ESTADOS_DEFAULT:
            cursor.execute(
                'INSERT INTO "Estados" ("ID_ESTADO") VALUES (%s) ON CONFLICT DO NOTHING',
                (est,),
            )

        for metodo in NAME_METODOS_DEFAULT:
            cursor.execute(
                '''
                INSERT INTO "Metodos_pago" ("NAME_METODO")
                VALUES (%s)
                ON CONFLICT ("NAME_METODO") DO NOTHING
                ''',
                (metodo,),
            )

        for roles in ROLES_DEFAULT:
            cursor.execute(
                '''
                INSERT INTO "Roles" ("ID_ROL", "NOMBRE")
                VALUES (%s, %s)
                ON CONFLICT ("ID_ROL") DO UPDATE SET "NOMBRE" = EXCLUDED."NOMBRE" 
                ''',
                roles,
            )

        # Crear perfiles para usuarios que no tengan perfil
        cursor.execute("""
            INSERT INTO "Perfiles" ("ID_USUARIO", "NOMBRE", "FOTO_PERFIL")
            SELECT u."ID_USUARIO", u."NOMBRE", 'https://via.placeholder.com/200'
            FROM "Usuarios" u
            LEFT JOIN "Perfiles" p ON u."ID_USUARIO" = p."ID_USUARIO"
            WHERE p."ID_USUARIO" IS NULL
            ON CONFLICT DO NOTHING
        """)


        conexion.commit()
        print("✓ Datos por defecto inicializados")

    except Exception as e:
        print(f"✗ Error inicializando datos: {e}")
    finally:
        cursor.close()
        conexion.close()