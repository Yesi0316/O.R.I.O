"""
Módulo de configuración y conexión a la base de datos PostgreSQL.

Este módulo maneja:
- Configuración de conexión a PostgreSQL
- Creación de tablas base del sistema
- Inicialización de datos por defecto
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()


# ========================
# CONFIGURACIÓN
# ========================

DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'port': os.getenv('DB_PORT'),
}

# Datos por defecto para las tablas
CATEGORIAS_DEFAULT = [
    'Documentos',
    'Tecnología',
    'Accesorios',
    'Ropa',
    'Llaves',
    'Otros'
]

ESTADOS_DEFAULT = [
    'Bueno',
    'Regular',
    'Malo'
]


# ========================
# CONEXIÓN A LA BASE DE DATOS
# ========================

def conectar_db():
    """
    Establece conexión a la base de datos PostgreSQL.
    
    Returns:
        psycopg2.connection: Conexión a la BD o None si hay error
        
    Raises:
        RuntimeError: Si hay problema de codificación UTF-8
    """
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


# ========================
# FUNCIONES GENÉRICAS
# ========================

def ejecutar_sql(sql, descripcion=""):
    """
    Ejecuta un comando SQL de forma segura.
    
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
    'Categorias': """
        CREATE TABLE IF NOT EXISTS public."Categorias"(
            "ID_CATEGORIA" TEXT PRIMARY KEY
        );
    """,
    
    'Paises': """
        CREATE TABLE IF NOT EXISTS public."Paises"(
            "ID_PAIS" TEXT PRIMARY KEY,
            "NOMBRE" TEXT NOT NULL
        );
    """,
    
    'Departamentos': """
        CREATE TABLE IF NOT EXISTS public."Departamentos"(
            "ID_DEPARTAMENTO" TEXT PRIMARY KEY,
            "NOMBRE" TEXT NOT NULL,
            "ID_PAIS" TEXT,
            FOREIGN KEY ("ID_PAIS") REFERENCES public."Paises" ("ID_PAIS")
        );
    """,
    
    'Ciudades': """
        CREATE TABLE IF NOT EXISTS public."Ciudades"(
            "ID_CIUDAD" TEXT PRIMARY KEY,
            "NOMBRE" TEXT NOT NULL,
            "ID_DEPARTAMENTO" TEXT NOT NULL,
            FOREIGN KEY ("ID_DEPARTAMENTO") 
                REFERENCES public."Departamentos" ("ID_DEPARTAMENTO")
        );
    """,
    
    'Roles': """
        CREATE TABLE IF NOT EXISTS public."Roles"(
            "ID_ROL" INTEGER PRIMARY KEY,
            "NOMBRE" TEXT NOT NULL
        );
    """,
    
    'Estados': """
        CREATE TABLE IF NOT EXISTS public."Estados"(
            "ID_ESTADO" TEXT PRIMARY KEY
        );
    """,
    
    'Tipos_identificaciones': """
        CREATE TABLE IF NOT EXISTS public."Tipos_identificaciones"(
            "ID_IDENTIFICACION" TEXT PRIMARY KEY
        );
    """,
    
    'Usuarios': """
        CREATE TABLE IF NOT EXISTS public."Usuarios"(
            "ID_USUARIO" TEXT PRIMARY KEY,
            "NOMBRE" TEXT,
            "CONTRASENA" TEXT NOT NULL,
            "PREGUNTA_1" TEXT NOT NULL,
            "PREGUNTA_2" TEXT NOT NULL,
            "RESPUESTA_1" TEXT NOT NULL,
            "RESPUESTA_2" TEXT NOT NULL
        );
    """,
    
    'Objetos': """
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
    
    'Reportes_encontrados': """
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
    
    'Reportes_perdidos': """
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
    """
}


# ========================
# FUNCIONES DE CREACIÓN DE TABLAS
# ========================

def crear_tabla_Categorias():
    """Crea la tabla Categorias."""
    ejecutar_sql(TABLAS['Categorias'], "Tabla Categorias")

def crear_tabla_Paises():
    """Crea la tabla Paises."""
    ejecutar_sql(TABLAS['Paises'], "Tabla Paises")

def crear_tabla_Departamentos():
    """Crea la tabla Departamentos."""
    ejecutar_sql(TABLAS['Departamentos'], "Tabla Departamentos")

def crear_tabla_Ciudades():
    """Crea la tabla Ciudades."""
    ejecutar_sql(TABLAS['Ciudades'], "Tabla Ciudades")

def crear_tabla_Roles():
    """Crea la tabla Roles."""
    ejecutar_sql(TABLAS['Roles'], "Tabla Roles")

def crear_tabla_Estados():
    """Crea la tabla Estados."""
    ejecutar_sql(TABLAS['Estados'], "Tabla Estados")

def crear_tabla_Tipo_identificaciones():
    """Crea la tabla Tipos_identificaciones."""
    ejecutar_sql(TABLAS['Tipos_identificaciones'], "Tabla Tipos_identificaciones")

def crear_tabla_Usuario():
    """Crea la tabla Usuarios."""
    ejecutar_sql(TABLAS['Usuarios'], "Tabla Usuarios")

def crear_tabla_Objetos():
    """Crea la tabla Objetos."""
    ejecutar_sql(TABLAS['Objetos'], "Tabla Objetos")

def crear_tabla_Reportes_encontrados():
    """Crea la tabla Reportes_encontrados."""
    ejecutar_sql(TABLAS['Reportes_encontrados'], "Tabla Reportes_encontrados")

def crear_tabla_Reportes_perdidos():
    """Crea la tabla Reportes_perdidos."""
    ejecutar_sql(TABLAS['Reportes_perdidos'], "Tabla Reportes_perdidos")


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
    crear_tabla_Objetos()
    crear_tabla_Reportes_encontrados()
    crear_tabla_Reportes_perdidos()


def inicializar_datos_default():
    """
    Inserta datos por defecto en las tablas de catálogos
    (Categorias y Estados) si no existen.
    """
    conexion = conectar_db()
    if not conexion:
        return
    
    cursor = conexion.cursor()
    
    try:
        # Insertar categorías por defecto
        for cat in CATEGORIAS_DEFAULT:
            cursor.execute(
                'INSERT INTO "Categorias" ("ID_CATEGORIA") VALUES (%s) ON CONFLICT DO NOTHING',
                (cat,)
            )
        
        # Insertar estados por defecto
        for est in ESTADOS_DEFAULT:
            cursor.execute(
                'INSERT INTO "Estados" ("ID_ESTADO") VALUES (%s) ON CONFLICT DO NOTHING',
                (est,)
            )
        
        conexion.commit()
        print("✓ Datos por defecto inicializados")
        
    except Exception as e:
        print(f"✗ Error inicializando datos: {e}")
    finally:
        cursor.close()
        conexion.close()
