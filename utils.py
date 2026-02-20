"""
Funciones utilitarias y auxiliares para la aplicación.

Contiene funciones comunes reutilizables para:
- Manejo de imágenes
- Operaciones de base de datos
- Inicialización de datos
"""

import os
import uuid
from werkzeug.utils import secure_filename
from database import conectar_db, CATEGORIAS_DEFAULT, ESTADOS_DEFAULT
from psycopg2.extras import RealDictCursor


# ========================
# MANEJO DE IMÁGENES
# ========================

def guardar_imagen(imagen, app_folder):
    """
    Guarda una imagen subida en la carpeta de uploads.
    
    Args:
        imagen: Objeto FileStorage de Flask
        app_folder: Ruta de la carpeta de uploads
        
    Returns:
        str: Ruta relativa del archivo guardado o None si no hay imagen
    """
    if not imagen or imagen.filename == '':
        return None
    
    try:
        filename = secure_filename(imagen.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        save_path = os.path.join(app_folder, unique_filename)
        imagen.save(save_path)
        return f"/uploads/{unique_filename}"
    except Exception as e:
        print(f"Error al guardar imagen: {e}")
        return None


# ========================
# OPERACIONES DE BASE DE DATOS
# ========================

def obtener_categorias():
    """
    Obtiene todas las categorías de la BD.
    Si no existen, inserta las categorías por defecto.
    
    Returns:
        list: Lista de diccionarios con categorías
    """
    db = conectar_db()
    if not db:
        return []
    
    cursor = db.cursor(cursor_factory=RealDictCursor)
    cursor.execute('SELECT "ID_CATEGORIA" FROM "Categorias"')
    categorias = cursor.fetchall()
    
    # Si no hay categorías, insertar por defecto
    if not categorias:
        for cat in CATEGORIAS_DEFAULT:
            cursor.execute(
                'INSERT INTO "Categorias" ("ID_CATEGORIA") VALUES (%s) ON CONFLICT DO NOTHING',
                (cat,)
            )
        db.commit()
        cursor.execute('SELECT "ID_CATEGORIA" FROM "Categorias"')
        categorias = cursor.fetchall()
    
    cursor.close()
    db.close()
    return categorias


def obtener_estados():
    """
    Obtiene todos los estados de la BD.
    Si no existen, inserta los estados por defecto.
    
    Returns:
        list: Lista de diccionarios con estados
    """
    db = conectar_db()
    if not db:
        return []
    
    cursor = db.cursor(cursor_factory=RealDictCursor)
    cursor.execute('SELECT "ID_ESTADO" FROM "Estados"')
    estados = cursor.fetchall()
    
    # Si no hay estados, insertar por defecto
    if not estados:
        for est in ESTADOS_DEFAULT:
            cursor.execute(
                'INSERT INTO "Estados" ("ID_ESTADO") VALUES (%s) ON CONFLICT DO NOTHING',
                (est,)
            )
        db.commit()
        cursor.execute('SELECT "ID_ESTADO" FROM "Estados"')
        estados = cursor.fetchall()
    
    cursor.close()
    db.close()
    return estados


def garantizar_categoria_existe(categoria):
    """
    Verifica si una categoría existe en la BD. Si no, la inserta.
    
    Args:
        categoria (str): ID de la categoría
        
    Returns:
        bool: True si la categoría existe o se insertó correctamente
    """
    db = conectar_db()
    if not db:
        return False
    
    cursor = db.cursor()
    try:
        cursor.execute('SELECT 1 FROM "Categorias" WHERE "ID_CATEGORIA" = %s', (categoria,))
        if not cursor.fetchone():
            cursor.execute(
                'INSERT INTO "Categorias" ("ID_CATEGORIA") VALUES (%s)',
                (categoria,)
            )
            db.commit()
        cursor.close()
        db.close()
        return True
    except Exception as e:
        print(f"Error garantizando categoría: {e}")
        cursor.close()
        db.close()
        return False


def garantizar_estado_existe(estado):
    """
    Verifica si un estado existe en la BD. Si no, lo inserta.
    
    Args:
        estado (str): ID del estado
        
    Returns:
        bool: True si el estado existe o se insertó correctamente
    """
    db = conectar_db()
    if not db:
        return False
    
    cursor = db.cursor()
    try:
        cursor.execute('SELECT 1 FROM "Estados" WHERE "ID_ESTADO" = %s', (estado,))
        if not cursor.fetchone():
            cursor.execute(
                'INSERT INTO "Estados" ("ID_ESTADO") VALUES (%s)',
                (estado,)
            )
            db.commit()
        cursor.close()
        db.close()
        return True
    except Exception as e:
        print(f"Error garantizando estado: {e}")
        cursor.close()
        db.close()
        return False


def generar_id_unico():
    """
    Genera un ID único de 6 dígitos para objetos y reportes.
    
    Returns:
        str: ID único
    """
    import random
    return str(random.randint(100000, 999999))
