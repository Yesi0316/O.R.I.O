"""Entrypoint que utiliza la Application Factory.

Esta versión delega toda la configuración a `app.create_app()` dentro del
paquete `app`. El fichero principal no contiene lógica de negocio.
"""

from app import create_app

# la instancia global se puede importar desde aquí si otras librerías la necesitan
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
