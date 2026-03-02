"""Entrypoint que utiliza la Application Factory.

esta version delega toda la configuracion a "app.create_app()" dentro del
paquete "app". el fichero principal no contiene logica de negocio.
"""

from app import create_app

# la instancia global se puede importar desde aquí si otras librerías la necesitan
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
