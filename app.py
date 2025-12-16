from flask import Flask
import os

from routes import init_routes
from database import (
    crear_tabla_Categorias,
    crear_tabla_Paises,
    crear_tabla_Departamentos,
    crear_tabla_Ciudades,
    crear_tabla_Roles,
    crear_tabla_Estados,
    crear_tabla_Tipo_identificaciones,
    crear_tabla_Usuario,
    crear_tabla_Objetos,
    crear_tabla_Reportes_encontrados,
    crear_tabla_Reportes_perdidos
)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

# registrar rutas
init_routes(app)

if __name__ == "__main__":
    try:
        # Orden de creación respetando dependencias
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
        import traceback
        print("Error al crear tablas o iniciar la aplicación:")
        traceback.print_exc()
