"""Entrypoint que utiliza la Application Factory.

esta version delega toda la configuracion a "app.create_app()" dentro del
paquete "app". el fichero principal no contiene logica de negocio.
"""


from app import create_app
import logging


app = create_app()

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)


if __name__ == "__main__":
    print("\n======================================")
    print("Servidor Flask iniciado")
    print("App: http://localhost:5000")
    print("Adminer: http://localhost:8081")
    print("======================================\n")

    app.run(host="0.0.0.0", port=5000, debug=True)