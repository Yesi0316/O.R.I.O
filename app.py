"""
Aplicación principal - Sistema de gestión de objetos perdidos/encontrados

Este módulo inicializa la aplicación Flask, crea las tablas de base de datos
y registra todas las rutas de la aplicación.
"""

from flask import Flask
import os

from routes import init_routes
from database import crear_tablas, inicializar_datos_default


# Configuración de la aplicación Flask
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

# Registrar todas las rutas de la aplicación
init_routes(app)


if __name__ == "__main__":
    try:
        print("\n" + "="*50)
        print("  Inicializando base de datos...")
        print("="*50 + "\n")
        
        # Crear todas las tablas en el orden correcto
        crear_tablas()
        
        # Insertar datos por defecto
        inicializar_datos_default()
        
        print("\n" + "="*50)
        print("  ✓ Base de datos lista")
        print("  ✓ Iniciando servidor en http://0.0.0.0:5000")
        print("="*50 + "\n")
        
        app.run(host="0.0.0.0", port=5000, debug=True)

    except Exception as e:
        import traceback
        print("\n" + "="*50)
        print("  ✗ Error al inicializar la aplicación")
        print("="*50 + "\n")
        traceback.print_exc()
