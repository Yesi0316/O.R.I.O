import os
import random
import uuid
import re
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    request,
    jsonify,
    render_template,
    session,
    redirect,
    url_for,
    send_from_directory,
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from .database import conectar_db
from psycopg2.extras import RealDictCursor


# -----------------------------
# DECORADOR LOGIN REQUIRED
# -----------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "id_usuario" not in session:
            return redirect("/inicio")
        return f(*args, **kwargs)

    return decorated_function


# -----------------------------
# DECORADOR GUEST REQUIRED
# -----------------------------
def guest_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "id_usuario" in session:
            return redirect(url_for("menu"))
        return f(*args, **kwargs)

    return decorated_function


"""RUTAS DE LA PAGINA"""


def init_routes(app):
    # -----------------------------
    # RUTA DETALLES DE OBJETO
    # -----------------------------
    @app.route("/detalles/<id_objeto>")
    def detalles_objeto(id_objeto):
        db = conectar_db()
        cursor = db.cursor(cursor_factory=RealDictCursor)
        # recuperar la información del objeto y al menos un reporte asociado
        # (se toma el más reciente mediante ORDER BY y LIMIT)
        cursor.execute(
            """
            SELECT * FROM (
                SELECT o."NOMBRE", o."ID_OBJETO", o."COLOR", o."IMAGEN", o."ID_CATEGORIA" as CATEGORIA,
                       r."FECHA", r."OBSERVACIONES", r."ID_USUARIO", u."NOMBRE" as NOMBRE_USUARIO,
                       'perdido' AS tipo
                FROM "Objetos" o
                LEFT JOIN "Reportes_perdidos" r ON o."ID_OBJETO" = r."ID_OBJETO"
                LEFT JOIN "Usuarios" u ON r."ID_USUARIO" = u."ID_USUARIO"
                WHERE o."ID_OBJETO" = %s
                UNION ALL
                SELECT o."NOMBRE", o."ID_OBJETO", o."COLOR", o."IMAGEN", o."ID_CATEGORIA" as CATEGORIA,
                       r."FECHA", r."OBSERVACIONES", r."ID_USUARIO", u."NOMBRE" as NOMBRE_USUARIO,
                       'encontrado' AS tipo
                FROM "Objetos" o
                LEFT JOIN "Reportes_encontrados" r ON o."ID_OBJETO" = r."ID_OBJETO"
                LEFT JOIN "Usuarios" u ON r."ID_USUARIO" = u."ID_USUARIO"
                WHERE o."ID_OBJETO" = %s
            ) t
            ORDER BY t."FECHA" DESC
            LIMIT 1
        """,
            (id_objeto, id_objeto),
        )
        item = cursor.fetchone()

        # si el reporte existe pero no trajo el nombre de usuario, intentar obtenerlo
        if item and (not item.get("NOMBRE_USUARIO")) and item.get("ID_USUARIO"):
            cursor.execute(
                'SELECT "NOMBRE" FROM "Usuarios" WHERE "ID_USUARIO" = %s',
                (item["ID_USUARIO"],),
            )
            user = cursor.fetchone()
            if user and user.get("NOMBRE"):
                item["NOMBRE_USUARIO"] = user["NOMBRE"]

        # formatear fecha para mostrar
        if item and isinstance(item.get("FECHA"), datetime):
            item["FECHA"] = item["FECHA"].strftime("%d/%m/%Y")

        cursor.close()
        db.close()

        if not item:
            return render_template(
                "detalles_reportes.html",
                item=None,
                error="No se encontró el objeto",
                hide_fab=True,
                active="",
            )
        # pasar variables al template para que herede base.html correctamente
        return render_template(
            "detalles_reportes.html", item=item, hide_fab=True, active=""
        )

    # CONFIGURAR CARPETAS DE SUBIDAS Y ESTATICAS
    app.config["UPLOAD_FOLDER"] = app.config.get("UPLOAD_FOLDER")
    app.config["STATIC_IMG_FOLDER"] = app.config.get("STATIC_IMG_FOLDER")

    # -----------------------------
    # RUTA PRINCIPAL
    # -----------------------------
    @app.route("/")
    def index():
        return render_template("index.html")

    # -------------------------------------
    # RUTA REGISTRO
    # -------------------------------------
    @app.route("/registro")
    @guest_required
    def registro():
        return render_template("registro.html")

    # ----------------------------------
    # GUARDAR USUARIO AL REGISTRARSE
    # ----------------------------------

    @app.route("/guardar_usuario", methods=["POST"])
    def guardar_usuario():
        try:
            # obtener datos del formulario
            id_usuario = request.form.get("id_usuario")
            nombre = request.form.get("nombre")
            contrasena = request.form.get("contrasena")
            contrasena_repetida = request.form.get("contrasena_repetida")
            pregunta1 = request.form.get("pregunta1")
            respuesta1 = request.form.get("respuesta1")
            pregunta2 = request.form.get("pregunta2")
            respuesta2 = request.form.get("respuesta2")

            respuesta1_hash = generate_password_hash(respuesta1)
            respuesta2_hash = generate_password_hash(respuesta2)

            if not id_usuario or not contrasena:
                return jsonify({"mensaje": "Usuario y contraseña obligatorios"}), 400
            if " " in id_usuario:
                return jsonify({"mensaje": "El Usuario no puede tener espacios"}), 400
            if contrasena != contrasena_repetida:
                return jsonify({"mensaje": "Las contraseñas no coinciden"}), 400

            # validaciones de seguridad de contraseña
            if len(contrasena) < 6:
                return (
                    jsonify(
                        {"mensaje": "La contraseña debe tener mínimo 6 caracteres"}
                    ),
                    400,
                )

            if not re.search(r"[A-Za-z]", contrasena):
                return (
                    jsonify(
                        {"mensaje": "La contraseña debe contener al menos una letra"}
                    ),
                    400,
                )

            if not re.search(r"[0-9]", contrasena):
                return (
                    jsonify(
                        {"mensaje": "La contraseña debe contener al menos un número"}
                    ),
                    400,
                )

            # conectar DB
            conexion = conectar_db()
            cursor = conexion.cursor()

            # verificar si usuario existe
            cursor.execute(
                'SELECT "ID_USUARIO" FROM public."Usuarios" WHERE "ID_USUARIO" = %s',
                (id_usuario,),
            )
            if cursor.fetchone():
                cursor.close()
                conexion.close()
                return jsonify({"mensaje": "El usuario ya existe"}), 400

            # insertar usuario con contraseña encriptada
            hashed_password = generate_password_hash(contrasena)
            cursor.execute(
                """
                INSERT INTO public."Usuarios"
                ("ID_USUARIO", "NOMBRE", "CONTRASENA", "PREGUNTA_1", "PREGUNTA_2", "RESPUESTA_1", "RESPUESTA_2")
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
                (
                    id_usuario,
                    nombre,
                    hashed_password,
                    pregunta1,
                    pregunta2,
                    respuesta1_hash,
                    respuesta2_hash,
                ),
            )

            # crear perfil automáticamente para el nuevo usuario
            cursor.execute(
                """
                INSERT INTO public."Perfiles"
                ("ID_USUARIO", "NOMBRE", "FOTO_PERFIL")
                VALUES (%s, %s, %s)
            """,
                (id_usuario, nombre, "https://via.placeholder.com/200"),
            )

            conexion.commit()
            cursor.close()
            conexion.close()

            session["id_usuario"] = id_usuario
            return jsonify({"ok": True, "mensaje": "Usuario creado correctamente"})

        except Exception as e:
            return (
                jsonify({"mensaje": "Error al guardar el usuario", "error": str(e)}),
                500,
            )

    # -----------------------------
    # RUTA MOTOR DE BUSQUEDAS
    # -----------------------------
    @app.route("/busquedas")
    def buscar():
        q = request.args.get("q", "").strip()
        categoria = request.args.get("categoria", "").strip()
        tipo = request.args.get("tipo", "").strip()

        db = conectar_db()
        cursor = db.cursor(cursor_factory=RealDictCursor)

        # Selecciona la tabla según el tipo
        if tipo == "perdido":
            join = 'INNER JOIN "Reportes_perdidos" r ON o."ID_OBJETO" = r."ID_OBJETO"'
        elif tipo == "encontrado":
            join = (
                'INNER JOIN "Reportes_encontrados" r ON o."ID_OBJETO" = r."ID_OBJETO"'
            )
        else:
            join = ""

        query = f'SELECT o."NOMBRE", o."ID_OBJETO", o."COLOR", o."IMAGEN", o."ID_CATEGORIA" AS CATEGORIA FROM "Objetos" o {join} WHERE 1=1'
        params = []

        # Buscar por nombre o por categoría (nombre o id)
        if q:
            query += ' AND (o."NOMBRE" ILIKE %s OR o."ID_CATEGORIA" ILIKE %s)'
            params.append(f"%{q}%")
            params.append(f"%{q}%")
        if categoria:
            query += ' AND o."ID_CATEGORIA" = %s'
            params.append(categoria)

        query += ' ORDER BY o."NOMBRE" ASC'

        cursor.execute(query, params)
        objetos = cursor.fetchall()
        cursor.close()
        db.close()

        if not objetos:
            return jsonify({"datos": False, "mensaje": "No se encontraron resultados"})
        return jsonify({"datos": objetos})

    # -----------------------------
    # CONSULTAR USUARIOS
    # -----------------------------
    @app.route("/usuarios", methods=["GET"])
    def obtener_usuarios():
        try:
            conexion = conectar_db()
            if conexion is None:
                return jsonify({"mensaje": "Error de conexión a la base de datos"}), 500

            cursor = conexion.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                'SELECT * FROM public."Usuarios" ORDER BY "ID_USUARIO" DESC;'
            )
            usuarios = cursor.fetchall()

            cursor.close()
            conexion.close()

            return jsonify(usuarios), 200

        except Exception as e:
            return (
                jsonify({"mensaje": "Error al obtener los usuarios", "error": str(e)}),
                500,
            )

    # -------------------------------------
    # RUTA INICIO DE SESIÓN
    # -------------------------------------
    @app.route("/inicio", methods=["GET"])
    @guest_required
    def vista_inicio():
        return render_template("inicio.html")

    @app.route("/inicio", methods=["POST"])
    @guest_required
    def inicio_sesion():
        try:
            id_usuario = request.form.get("id_usuario")
            contrasena = request.form.get("contrasena")

            if not id_usuario or not contrasena:
                return (
                    jsonify(
                        {"ok": False, "mensaje": "Debes completar todos los campos"}
                    ),
                    400,
                )

            conexion = conectar_db()
            cursor = conexion.cursor(cursor_factory=RealDictCursor)

            cursor.execute(
                'SELECT "ID_USUARIO", "CONTRASENA" FROM public."Usuarios" WHERE "ID_USUARIO" = %s',
                (id_usuario,),
            )
            user = cursor.fetchone()

            cursor.close()
            conexion.close()

            if not user:
                return (
                    jsonify({"ok": False, "mensaje": "El usuario no está registrado"}),
                    404,
                )

            if not check_password_hash(user["CONTRASENA"], contrasena):
                return jsonify({"ok": False, "mensaje": "Contraseña incorrecta"}), 401

            session["id_usuario"] = user["ID_USUARIO"]
            return jsonify({"ok": True, "mensaje": "Inicio de sesión exitoso"})

        except Exception as e:
            import traceback

            # esto imprime el error completo
            traceback.print_exc()
            return jsonify({"ok": False, "mensaje": "Error en el servidor"}), 500

    # -------------------------------------
    # RUTA CERRAR SESION
    # -------------------------------------
    @app.route("/logout")
    def logout():
        session.clear()
        return redirect("/inicio")

    # -------------------------------------
    # RUTA MENU
    # -------------------------------------
    @app.route("/menu")
    @login_required
    def menu():
        return render_template("menu.html", active="panel")

    # -------------------------------------
    # RUTA FORMULARIO REPORTE
    # -------------------------------------
    @app.route("/formulario_perdido", methods=["GET", "POST"])
    @login_required
    def formulario_perdido():
        if request.method == "POST":
            return redirect("/buscar_objetos")
        # Obtener categorías y estados de la base de datos, y si no existen, insertarlos
        db = conectar_db()
        cursor = db.cursor(cursor_factory=RealDictCursor)
        # Categorías
        cursor.execute('SELECT "ID_CATEGORIA" FROM "Categorias"')
        categorias = cursor.fetchall()
        if not categorias:
            categorias_default = [
                "Documentos",
                "Tecnología",
                "Accesorios",
                "Ropa",
                "Llaves",
                "Otros",
            ]
            for cat in categorias_default:
                cursor.execute(
                    'INSERT INTO "Categorias" ("ID_CATEGORIA") VALUES (%s) ON CONFLICT DO NOTHING',
                    (cat,),
                )
            db.commit()
            cursor.execute('SELECT "ID_CATEGORIA" FROM "Categorias"')
            categorias = cursor.fetchall()
        # Estados
        cursor.execute('SELECT "ID_ESTADO" FROM "Estados"')
        estados = cursor.fetchall()
        if not estados:
            estados_default = ["Bueno", "Regular", "Malo"]
            for est in estados_default:
                cursor.execute(
                    'INSERT INTO "Estados" ("ID_ESTADO") VALUES (%s) ON CONFLICT DO NOTHING',
                    (est,),
                )
            db.commit()
        cursor.close()
        db.close()
        return render_template(
            "form_perdido.html", categorias=categorias, active="panel", hide_fab=True
        )

    @app.route("/formulario_reporte2")
    def formulario_reporte2():
        bd = conectar_db()
        cursor = bd.cursor(cursor_factory=RealDictCursor)
        cursor.execute('SELECT "ID_ESTADO" FROM "Estados"')
        estados = cursor.fetchall()
        cursor.close()
        bd.close()
        return render_template("reportes_principal.html", estados=estados)

    @app.route("/submit_per", methods=["GET", "POST"])
    @login_required
    def submit_per():
        try:
            if request.method != "POST":
                return jsonify({"mensaje": "Metodo no admitido"}), 405

            # Validar campos requeridos
            id_usuario = session.get("id_usuario")
            nombre_objeto = request.form.get("nombre_objeto", "").strip()
            estado = request.form.get("estado", "").strip()
            color_dominante = request.form.get("color_dominante", "").strip()
            lugar = request.form.get("lugar", "").strip()
            fecha = request.form.get("fecha", "").strip()
            categoria = request.form.get("categoria", "").strip()
            comentario = request.form.get("comentario", "").strip()

            if not all(
                [nombre_objeto, estado, color_dominante, lugar, fecha, categoria]
            ):
                return (
                    jsonify({"mensaje": "Faltan campos requeridos", "error": True}),
                    400,
                )

            ficha = request.form.get("ficha")
            if ficha:
                try:
                    ficha = int(ficha)
                except ValueError:
                    return (
                        jsonify(
                            {"mensaje": "La ficha debe ser un número", "error": True}
                        ),
                        400,
                    )
            else:
                ficha = None

            id_objeto = str(random.randint(100000, 999999))
            id_reporte = str(random.randint(100000, 999999))

            # Archivo
            imagen = request.files.get("imagen")
            ruta = None
            if imagen and imagen.filename:
                try:
                    # limpia el nombre del archivo
                    filename = secure_filename(imagen.filename)
                    # crea un nombre unico usando uuid para evitar colisiones
                    unique_filename = f"{uuid.uuid4()}_{filename}"
                    # crear carpeta si no existe
                    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
                    # guardarla en la carpeta uploads
                    save_path = os.path.join(
                        app.config["UPLOAD_FOLDER"], unique_filename
                    )
                    imagen.save(save_path)
                    # guarda la ruta que voy a usar en la base de datos
                    ruta = f"/uploads/{unique_filename}"
                except Exception as e:
                    print(f"Error al guardar imagen: {e}")
                    return (
                        jsonify(
                            {"mensaje": "Error al guardar la imagen", "error": True}
                        ),
                        500,
                    )

            bd = conectar_db()
            if not bd:
                return (
                    jsonify(
                        {
                            "mensaje": "Error de conexión a la base de datos",
                            "error": True,
                        }
                    ),
                    500,
                )

            cursor = bd.cursor()

            # Asegurar que el estado existe
            cursor.execute('SELECT 1 FROM "Estados" WHERE "ID_ESTADO" = %s', (estado,))
            if not cursor.fetchone():
                cursor.execute(
                    'INSERT INTO "Estados" ("ID_ESTADO") VALUES (%s) ON CONFLICT DO NOTHING',
                    (estado,),
                )
                bd.commit()

            # Asegurar que la categoría existe
            cursor.execute(
                'SELECT 1 FROM "Categorias" WHERE "ID_CATEGORIA" = %s', (categoria,)
            )
            if not cursor.fetchone():
                cursor.execute(
                    'INSERT INTO "Categorias" ("ID_CATEGORIA") VALUES (%s) ON CONFLICT DO NOTHING',
                    (categoria,),
                )
                bd.commit()

            # Insertar objeto
            cursor.execute(
                """INSERT INTO "Objetos" ("ID_OBJETO", "NOMBRE", "COLOR", "ID_ESTADO", "LUGAR_ENCONTRADO", "ID_CATEGORIA", "IMAGEN") 
                            VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (
                    id_objeto,
                    nombre_objeto,
                    color_dominante,
                    estado,
                    lugar,
                    categoria,
                    ruta,
                ),
            )

            # Insertar reporte
            cursor.execute(
                """INSERT INTO "Reportes_perdidos" ("FECHA", "OBSERVACIONES", "ID_OBJETO", "ID_USUARIO", "ID_REPORTE", "FICHA", "ID_CATEGORIA")
                            VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (
                    fecha,
                    comentario,
                    id_objeto,
                    id_usuario,
                    id_reporte,
                    ficha,
                    categoria,
                ),
            )

            bd.commit()
            cursor.close()
            bd.close()

            session["img"] = ruta

            return (
                jsonify({"mensaje": "Reporte enviado correctamente", "ruta": ruta}),
                200,
            )

        except Exception as e:
            print(f"Error en submit_per: {e}")
            import traceback

            traceback.print_exc()
            return (
                jsonify(
                    {
                        "mensaje": f"Error al procesar el reporte: {str(e)}",
                        "error": True,
                    }
                ),
                500,
            )

    # -----------------------------
    # RUTA PARA MOSTRAR IMAGENES SUBIDAS
    # -----------------------------
    @app.route("/uploads/<filename>")
    def uploaded_file(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    # -----------------------------
    # FORMULARIO REPORTE DE OBJETO ENCONTRADO
    # -----------------------------
    @app.route("/formulario_objeto_encontrado", methods=["GET", "POST"])
    @login_required
    def formulario_objeto_encontrado():
        if request.method == "POST":
            return redirect("/buscar_objetos")
        bd = conectar_db()
        cursor = bd.cursor(cursor_factory=RealDictCursor)
        cursor.execute('SELECT "ID_CATEGORIA" FROM "Categorias"')
        categorias = cursor.fetchall()
        cursor.close()
        bd.close()

        return render_template(
            "form_encontrado.html", categorias=categorias, active="panel", hide_fab=True
        )

    @app.route("/formulario_reporte3")
    def formulario_reporte3():
        bd = conectar_db()
        cursor = bd.cursor(cursor_factory=RealDictCursor)
        cursor.execute('SELECT "ID_ESTADO" FROM "Estados"')
        estados = cursor.fetchall()
        cursor.close()
        bd.close()
        return render_template("reportes_principal.html", estados=estados)

    @app.route("/submit_enc", methods=["GET", "POST"])
    @login_required
    def submit_enc():
        try:
            if request.method != "POST":
                return jsonify({"mensaje": "Metodo no admitido"}), 405

            # Validar campos requeridos
            id_usuario = session.get("id_usuario")
            nombre_objeto = request.form.get("nombre_objeto", "").strip()
            estado = request.form.get("estado", "").strip()
            color_dominante = request.form.get("color_dominante", "").strip()
            lugar = request.form.get("lugar", "").strip()
            fecha = request.form.get("fecha", "").strip()
            categoria = request.form.get("categoria", "").strip()
            comentario = request.form.get("comentario", "").strip()

            if not all(
                [nombre_objeto, estado, color_dominante, lugar, fecha, categoria]
            ):
                return (
                    jsonify({"mensaje": "Faltan campos requeridos", "error": True}),
                    400,
                )

            ficha = request.form.get("ficha")
            if ficha:
                try:
                    ficha = int(ficha)
                except ValueError:
                    return (
                        jsonify(
                            {"mensaje": "La ficha debe ser un número", "error": True}
                        ),
                        400,
                    )
            else:
                ficha = None

            id_objeto = str(random.randint(100000, 999999))
            id_reporte = str(random.randint(100000, 999999))

            # Archivo
            imagen = request.files.get("imagen")
            ruta = None
            if imagen and imagen.filename:
                try:
                    # limpia el nombre del archivo
                    filename = secure_filename(imagen.filename)
                    # crea un nombre unico usando uuid para evitar colisiones
                    unique_filename = f"{uuid.uuid4()}_{filename}"
                    # crear carpeta si no existe
                    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
                    # guardarla en la carpeta uploads
                    save_path = os.path.join(
                        app.config["UPLOAD_FOLDER"], unique_filename
                    )
                    imagen.save(save_path)
                    # guarda la ruta que voy a usar en la base de datos
                    ruta = f"/uploads/{unique_filename}"
                except Exception as e:
                    print(f"Error al guardar imagen: {e}")
                    return (
                        jsonify(
                            {"mensaje": "Error al guardar la imagen", "error": True}
                        ),
                        500,
                    )

            bd = conectar_db()
            if not bd:
                return (
                    jsonify(
                        {
                            "mensaje": "Error de conexión a la base de datos",
                            "error": True,
                        }
                    ),
                    500,
                )

            cursor = bd.cursor()

            # Verificar si ya existe un reporte igual para este usuario y objeto
            cursor.execute(
                """
                SELECT 1 FROM "Reportes_encontrados" r
                JOIN "Objetos" o ON r."ID_OBJETO" = o."ID_OBJETO"
                WHERE r."ID_USUARIO" = %s AND o."NOMBRE" = %s AND o."COLOR" = %s AND o."ID_CATEGORIA" = %s
            """,
                (id_usuario, nombre_objeto, color_dominante, categoria),
            )
            existe = cursor.fetchone()
            if existe:
                cursor.close()
                bd.close()
                return (
                    jsonify(
                        {
                            "mensaje": "Ya existe un reporte igual para este usuario.",
                            "existe": True,
                        }
                    ),
                    400,
                )

            # Asegurar que el estado existe
            cursor.execute('SELECT 1 FROM "Estados" WHERE "ID_ESTADO" = %s', (estado,))
            if not cursor.fetchone():
                cursor.execute(
                    'INSERT INTO "Estados" ("ID_ESTADO") VALUES (%s) ON CONFLICT DO NOTHING',
                    (estado,),
                )
                bd.commit()

            # Asegurar que la categoría existe
            cursor.execute(
                'SELECT 1 FROM "Categorias" WHERE "ID_CATEGORIA" = %s', (categoria,)
            )
            if not cursor.fetchone():
                cursor.execute(
                    'INSERT INTO "Categorias" ("ID_CATEGORIA") VALUES (%s) ON CONFLICT DO NOTHING',
                    (categoria,),
                )
                bd.commit()

            # Insertar objeto
            cursor.execute(
                """
                INSERT INTO "Objetos"  
                ("ID_OBJETO", "NOMBRE", "COLOR", "ID_ESTADO", "LUGAR_ENCONTRADO", "ID_CATEGORIA", "IMAGEN")    
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    id_objeto,
                    nombre_objeto,
                    color_dominante,
                    estado,
                    lugar,
                    categoria,
                    ruta,
                ),
            )

            # Insertar reporte
            cursor.execute(
                """
                INSERT INTO "Reportes_encontrados"
                ("FECHA", "OBSERVACIONES", "ID_OBJETO", "ID_USUARIO", "ID_REPORTE_ENC", "FICHA", "ID_CATEGORIA")
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    fecha,
                    comentario,
                    id_objeto,
                    id_usuario,
                    id_reporte,
                    ficha,
                    categoria,
                ),
            )

            bd.commit()
            cursor.close()
            bd.close()

            session["img"] = ruta

            return (
                jsonify(
                    {
                        "mensaje": "Reporte enviado correctamente",
                        "ruta": ruta,
                        "existe": False,
                    }
                ),
                200,
            )

        except Exception as e:
            print(f"Error en submit_enc: {e}")
            import traceback

            traceback.print_exc()
            return (
                jsonify(
                    {
                        "mensaje": f"Error al procesar el reporte: {str(e)}",
                        "error": True,
                    }
                ),
                500,
            )

    # -----------------------------
    # RUTA DEBUG: LISTAR TODOS LOS OBJETOS
    # -----------------------------
    @app.route("/debug_objetos")
    @login_required
    def debug_objetos():
        db = conectar_db()
        cursor = db.cursor(cursor_factory=RealDictCursor)
        cursor.execute('SELECT * FROM "Objetos" ORDER BY "NOMBRE" ASC')
        objetos = cursor.fetchall()
        cursor.close()
        db.close()
        return jsonify(objetos)

    # -----------------------------
    # RUTA MOTOR DE BUSQUEDAS CON FILTROS
    # -----------------------------
    @app.route("/buscar_objetos", methods=["GET"])
    @login_required
    def buscar_objeto():
        q = request.args.get("q", "")  # texto de búsqueda
        categoria = request.args.get("categoria", "")
        color = request.args.get("color", "")

        db = conectar_db()
        cursor = db.cursor(cursor_factory=RealDictCursor)

        # Construir consulta dinámica según los filtros
        query = 'SELECT "NOMBRE", "ID_OBJETO", "COLOR", "IMAGEN", "ID_CATEGORIA" FROM "Objetos" WHERE 1=1'
        params = []

        if q:
            query += ' AND "NOMBRE" ILIKE %s'
            params.append(f"%{q}%")
        if categoria:
            query += ' AND "ID_CATEGORIA" = %s'
            params.append(categoria)
        if color:
            query += ' AND "COLOR" ILIKE %s'
            params.append(f"%{color}%")

        cursor.execute(query, params)
        resultados = cursor.fetchall()
        cursor.close()
        db.close()

        return render_template(
            "busquedas.html",
            active="panel",
            resultados=resultados,
            q=q,
            categoria=categoria,
            color=color,
        )

    # -------------------------------------
    # RUTA RECUPERAR CONTRASEÑA - Formulario inicial (ID Usuario)
    # -------------------------------------
    @app.route("/recuperar", methods=["GET", "POST"])
    @guest_required
    def recuperar():
        if request.method == "GET":
            return render_template("recuperar.html")

        # POST: enviar ID de usuario
        id_usuario = request.form.get("id_usuario")
        conexion = conectar_db()
        cursor = conexion.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            'SELECT "PREGUNTA_1", "PREGUNTA_2" FROM public."Usuarios" WHERE "ID_USUARIO" = %s',
            (id_usuario,),
        )
        user = cursor.fetchone()
        cursor.close()
        conexion.close()

        if not user:
            return jsonify({"ok": False, "mensaje": "Usuario no encontrado"}), 404

        # Guardamos el ID temporalmente en sesión para validar respuestas
        session["recuperar_id"] = id_usuario
        return jsonify(
            {
                "ok": True,
                "pregunta1": user["PREGUNTA_1"],
                "pregunta2": user["PREGUNTA_2"],
            }
        )

    # -------------------------------------
    # RUTA VALIDAR RESPUESTAS Y CAMBIAR CONTRASEÑA
    # -------------------------------------
    @app.route("/recuperar_respuestas", methods=["POST"])
    @guest_required
    def recuperar_respuestas():

        id_usuario = session.get("recuperar_id")
        if not id_usuario:
            return (
                jsonify({"ok": False, "mensaje": "No hay usuario en recuperación"}),
                400,
            )

        respuesta1 = request.form.get("respuesta1")
        respuesta2 = request.form.get("respuesta2")
        nueva_contrasena = request.form.get("nueva_contrasena")

        conexion = conectar_db()
        cursor = conexion.cursor(cursor_factory=RealDictCursor)

        cursor.execute(
            """
            SELECT "RESPUESTA_1", "RESPUESTA_2",
                "INTENTOS_RECUPERACION",
                "BLOQUEADO_HASTA"
            FROM public."Usuarios"
            WHERE "ID_USUARIO" = %s
            """,
            (id_usuario,),
        )

        user = cursor.fetchone()

        if not user:
            cursor.close()
            conexion.close()
            return jsonify({"ok": False, "mensaje": "Usuario no encontrado"}), 404

        # Verificar si está bloqueado
        ahora = datetime.utcnow()

        if user["BLOQUEADO_HASTA"] and user["BLOQUEADO_HASTA"] > ahora:
            segundos_restantes = int((user["BLOQUEADO_HASTA"] - ahora).total_seconds())
            cursor.close()
            conexion.close()
            return (
                jsonify(
                    {
                        "ok": False,
                        "bloqueado": True,
                        "segundos_restantes": segundos_restantes,
                    }
                ),
                403,
            )

        # Validar respuestas
        respuestas_correctas = check_password_hash(
            user["RESPUESTA_1"], respuesta1
        ) and check_password_hash(user["RESPUESTA_2"], respuesta2)

        if not respuestas_correctas:

            intentos = user["INTENTOS_RECUPERACION"] + 1

            # Si llega a 5 intentos → bloquear 10 minutos
            if intentos >= 5:
                bloqueo_hasta = ahora + timedelta(minutes=10)

                cursor.execute(
                    """
                    UPDATE public."Usuarios"
                    SET "INTENTOS_RECUPERACION" = 0,
                        "BLOQUEADO_HASTA" = %s
                    WHERE "ID_USUARIO" = %s
                    """,
                    (bloqueo_hasta, id_usuario),
                )

                conexion.commit()
                cursor.close()
                conexion.close()

                return (
                    jsonify(
                        {"ok": False, "bloqueado": True, "segundos_restantes": 600}
                    ),
                    403,
                )

            # Si aún no llega a 5
            cursor.execute(
                """
                UPDATE public."Usuarios"
                SET "INTENTOS_RECUPERACION" = %s
                WHERE "ID_USUARIO" = %s
                """,
                (intentos, id_usuario),
            )

            conexion.commit()
            cursor.close()
            conexion.close()

            return (
                jsonify(
                    {"ok": False, "mensaje": f"Respuestas incorrectas ({intentos}/5)"}
                ),
                401,
            )

        # Si respuestas correctas → resetear intentos
        cursor.execute(
            """
            UPDATE public."Usuarios"
            SET "INTENTOS_RECUPERACION" = 0,
                "BLOQUEADO_HASTA" = NULL
            WHERE "ID_USUARIO" = %s
            """,
            (id_usuario,),
        )

        conexion.commit()

        # solo estamos validando respuestas
        if not nueva_contrasena:
            cursor.close()
            conexion.close()
            return jsonify({"ok": True})

        # Validaciones de seguridad
        if len(nueva_contrasena) < 6:
            cursor.close()
            conexion.close()
            return jsonify({"ok": False, "mensaje": "Mínimo 6 caracteres"}), 400

        if not re.search(r"[A-Za-z]", nueva_contrasena):
            cursor.close()
            conexion.close()
            return (
                jsonify({"ok": False, "mensaje": "Debe contener al menos una letra"}),
                400,
            )

        if not re.search(r"[0-9]", nueva_contrasena):
            cursor.close()
            conexion.close()
            return (
                jsonify({"ok": False, "mensaje": "Debe contener al menos un número"}),
                400,
            )

        # Actualizar contraseña
        hashed_password = generate_password_hash(nueva_contrasena)

        cursor.execute(
            """
            UPDATE public."Usuarios"
            SET "CONTRASENA" = %s
            WHERE "ID_USUARIO" = %s
            """,
            (hashed_password, id_usuario),
        )

        conexion.commit()
        cursor.close()
        conexion.close()

        session.pop("recuperar_id", None)

        return jsonify({"ok": True})

    @app.route("/perfil")
    @login_required
    def perfil():
        return render_template("perfil.html", active="perfil")

    @app.route("/datos_perfil", methods=["GET"])
    @login_required
    def datos_perfil():
        """Obtiene los datos del perfil del usuario actual"""
        try:
            id_usuario = session["id_usuario"]
            db = conectar_db()
            cursor = db.cursor(cursor_factory=RealDictCursor)

            # Obtener datos del perfil
            cursor.execute(
                """
                SELECT "NOMBRE", "APELLIDO", "TELEFONO", "CORREO", "FOTO_PERFIL"
                FROM "Perfiles"
                WHERE "ID_USUARIO" = %s
            """,
                (id_usuario,),
            )

            perfil = cursor.fetchone()
            cursor.close()
            db.close()

            if perfil:
                return jsonify({"ok": True, "datos": perfil})
            else:
                # Si no existe perfil, devolver datos vacíos (aunque debería existir por registro)
                return jsonify(
                    {
                        "ok": True,
                        "datos": {
                            "NOMBRE": "",
                            "APELLIDO": "",
                            "TELEFONO": "",
                            "CORREO": "",
                            "FOTO_PERFIL": "https://via.placeholder.com/200",
                        },
                    }
                )
        except Exception as e:
            print(f"Error en datos_perfil: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/guardar_perfil", methods=["POST"])
    @login_required
    def guardar_perfil():
        """Guarda los datos del perfil del usuario"""
        try:
            id_usuario = session["id_usuario"]
            nombre = request.form.get("nombre", "").strip()
            apellido = request.form.get("apellido", "").strip()
            telefono = request.form.get("telefono", "").strip()
            correo = request.form.get("correo", "").strip()

            if not nombre:
                return jsonify({"ok": False, "error": "El nombre es obligatorio"}), 400

            db = conectar_db()
            cursor = db.cursor()

            # Verificar si ya existe perfil
            cursor.execute(
                'SELECT 1 FROM "Perfiles" WHERE "ID_USUARIO" = %s', (id_usuario,)
            )
            existe = cursor.fetchone()

            if existe:
                # Actualizar perfil existente
                cursor.execute(
                    """
                    UPDATE "Perfiles"
                    SET "NOMBRE" = %s, "APELLIDO" = %s, "TELEFONO" = %s, "CORREO" = %s, "FECHA_ACTUALIZACION" = CURRENT_TIMESTAMP
                    WHERE "ID_USUARIO" = %s
                """,
                    (nombre, apellido, telefono, correo, id_usuario),
                )
            else:
                # Crear nuevo perfil (no debería pasar si se creó al registrarse)
                cursor.execute(
                    """
                    INSERT INTO "Perfiles" ("ID_USUARIO", "NOMBRE", "APELLIDO", "TELEFONO", "CORREO", "FOTO_PERFIL")
                    VALUES (%s, %s, %s, %s, %s, %s)
                """,
                    (
                        id_usuario,
                        nombre,
                        apellido,
                        telefono,
                        correo,
                        "https://via.placeholder.com/200",
                    ),
                )

            db.commit()
            cursor.close()
            db.close()

            return jsonify({"ok": True, "mensaje": "Perfil actualizado correctamente"})

        except Exception as e:
            print(f"Error en guardar_perfil: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/subir_foto_perfil", methods=["POST"])
    @login_required
    def subir_foto_perfil():
        """Sube la foto de perfil del usuario"""
        try:
            id_usuario = session["id_usuario"]

            if "foto" not in request.files:
                return jsonify({"ok": False, "error": "No se encontró imagen"}), 400

            foto = request.files["foto"]

            if foto.filename == "":
                return jsonify({"ok": False, "error": "No se seleccionó imagen"}), 400

            # Validar extensión
            ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
            if not (
                "." in foto.filename
                and foto.filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
            ):
                return (
                    jsonify({"ok": False, "error": "Formato de imagen no permitido"}),
                    400,
                )

            # Guardar archivo
            filename = f"perfil_{id_usuario}_{uuid.uuid4().hex}.{foto.filename.rsplit('.', 1)[1].lower()}"
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            foto.save(filepath)

            ruta_guardada = f"/uploads/{filename}"

            db = conectar_db()
            cursor = db.cursor()

            # Verificar si existe perfil
            cursor.execute(
                'SELECT 1 FROM "Perfiles" WHERE "ID_USUARIO" = %s', (id_usuario,)
            )
            existe = cursor.fetchone()

            if existe:
                cursor.execute(
                    """
                    UPDATE "Perfiles"
                    SET "FOTO_PERFIL" = %s, "FECHA_ACTUALIZACION" = CURRENT_TIMESTAMP
                    WHERE "ID_USUARIO" = %s
                """,
                    (ruta_guardada, id_usuario),
                )
            else:
                # Crear perfil si no existe (no debería pasar)
                cursor.execute(
                    """
                    INSERT INTO "Perfiles" ("ID_USUARIO", "FOTO_PERFIL")
                    VALUES (%s, %s)
                """,
                    (id_usuario, ruta_guardada),
                )

            db.commit()
            cursor.close()
            db.close()

            return jsonify(
                {
                    "ok": True,
                    "ruta": ruta_guardada,
                    "mensaje": "Foto actualizada correctamente",
                }
            )

        except Exception as e:
            print(f"Error en subir_foto_perfil: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/dashboard")
    @login_required
    def dashboard():
        return render_template("dashboard.html", active="dashboard")

    @app.route("/reportes")
    def reportes():
        return render_template("reportes.html", active="reportes")

    @app.route("/api/mis_reportes", methods=["GET"])
    @login_required
    def api_mis_reportes():
        """Devuelve JSON con los reportes (perdidos/encontrados) del usuario en sesión"""
        try:
            id_usuario = session["id_usuario"]
            db = conectar_db()
            cursor = db.cursor(cursor_factory=RealDictCursor)

            query = """
                SELECT r."ID_REPORTE" as id_reporte, 'perdido' as tipo, o."ID_OBJETO", o."NOMBRE", o."COLOR", o."IMAGEN", r."FECHA", r."OBSERVACIONES", o."ID_CATEGORIA" as categoria
                FROM "Reportes_perdidos" r
                JOIN "Objetos" o ON r."ID_OBJETO" = o."ID_OBJETO"
                WHERE r."ID_USUARIO" = %s
                UNION ALL
                SELECT r."ID_REPORTE_ENC" as id_reporte, 'encontrado' as tipo, o."ID_OBJETO", o."NOMBRE", o."COLOR", o."IMAGEN", r."FECHA", r."OBSERVACIONES", o."ID_CATEGORIA" as categoria
                FROM "Reportes_encontrados" r
                JOIN "Objetos" o ON r."ID_OBJETO" = o."ID_OBJETO"
                WHERE r."ID_USUARIO" = %s
                ORDER BY "FECHA" DESC
            """

            cursor.execute(query, (id_usuario, id_usuario))
            reportes = cursor.fetchall()
            cursor.close()
            db.close()

            return jsonify({"ok": True, "datos": reportes})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/configuracion")
    @login_required
    def configuracion():
        return render_template("configuracion.html", active="configuracion")

    @app.route("/api/configuracion", methods=["GET"])
    @login_required
    def api_get_configuracion():
        """Obtiene configuración del usuario"""
        try:
            id_usuario = session["id_usuario"]
            db = conectar_db()
            cursor = db.cursor(cursor_factory=RealDictCursor)

            # Verificar si existe configuración (por ahora devolvemos defaults)
            config = {
                "tema": request.cookies.get("tema", "claro"),
                "notificaciones": request.cookies.get("notificaciones", "true")
                == "true",
                "privacidad": request.cookies.get("privacidad", "publica"),
                "email_reportes": request.cookies.get("email_reportes", "true")
                == "true",
            }

            cursor.close()
            db.close()

            return jsonify({"ok": True, "config": config})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/configuracion", methods=["POST"])
    @login_required
    def api_guardar_configuracion():
        """Guarda configuración del usuario mediante cookies"""
        try:
            tema = request.json.get("tema", "claro")
            notificaciones = request.json.get("notificaciones", True)
            privacidad = request.json.get("privacidad", "publica")
            email_reportes = request.json.get("email_reportes", True)

            response = jsonify({"ok": True, "mensaje": "Configuración guardada"})
            response.set_cookie("tema", tema, max_age=31536000)
            response.set_cookie(
                "notificaciones", str(notificaciones).lower(), max_age=31536000
            )
            response.set_cookie("privacidad", privacidad, max_age=31536000)
            response.set_cookie(
                "email_reportes", str(email_reportes).lower(), max_age=31536000
            )

            return response
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/cambiar_contrasena", methods=["POST"])
    @login_required
    def api_cambiar_contrasena():
        """Cambia la contraseña del usuario"""
        try:
            id_usuario = session["id_usuario"]
            contrasena_actual = request.json.get("contrasena_actual", "").strip()
            contrasena_nueva = request.json.get("contrasena_nueva", "").strip()
            contrasena_confirmar = request.json.get("contrasena_confirmar", "").strip()

            if (
                not contrasena_actual
                or not contrasena_nueva
                or not contrasena_confirmar
            ):
                return (
                    jsonify({"ok": False, "error": "Todos los campos son requeridos"}),
                    400,
                )

            if contrasena_nueva != contrasena_confirmar:
                return (
                    jsonify({"ok": False, "error": "Las contraseñas no coinciden"}),
                    400,
                )

            if len(contrasena_nueva) < 6:
                return jsonify({"ok": False, "error": "Mínimo 6 caracteres"}), 400

            if not re.search(r"[A-Za-z]", contrasena_nueva):
                return (
                    jsonify({"ok": False, "error": "Debe contener al menos una letra"}),
                    400,
                )

            if not re.search(r"[0-9]", contrasena_nueva):
                return (
                    jsonify({"ok": False, "error": "Debe contener al menos un número"}),
                    400,
                )

            if contrasena_nueva == contrasena_actual:
                return (
                    jsonify(
                        {
                            "ok": False,
                            "error": "La nueva contraseña no puede ser igual a la actual",
                        }
                    ),
                    400,
                )

            db = conectar_db()
            cursor = db.cursor(cursor_factory=RealDictCursor)

            # Obtener contraseña actual
            cursor.execute(
                'SELECT "CONTRASENA" FROM "Usuarios" WHERE "ID_USUARIO" = %s',
                (id_usuario,),
            )
            usuario = cursor.fetchone()

            if not usuario:
                cursor.close()
                db.close()
                return jsonify({"ok": False, "error": "Usuario no encontrado"}), 404

            # Verificar contraseña actual
            if not check_password_hash(usuario["CONTRASENA"], contrasena_actual):
                cursor.close()
                db.close()
                return (
                    jsonify({"ok": False, "error": "Contraseña actual incorrecta"}),
                    401,
                )

            # Actualizar contraseña
            nueva_hash = generate_password_hash(contrasena_nueva)
            cursor.execute(
                'UPDATE "Usuarios" SET "CONTRASENA" = %s WHERE "ID_USUARIO" = %s',
                (nueva_hash, id_usuario),
            )
            db.commit()
            cursor.close()
            db.close()

            return jsonify(
                {"ok": True, "mensaje": "Contraseña actualizada correctamente"}
            )
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/estadisticas")
    @login_required
    def api_estadisticas():
        """Devuelve las estadísticas del dashboard"""
        try:
            db = conectar_db()
            cursor = db.cursor(cursor_factory=RealDictCursor)

            # Reportes totales (suma de encontrados y perdidos)
            cursor.execute('SELECT COUNT(*) as total FROM "Reportes_encontrados"')
            encontrados = cursor.fetchone()["total"]

            cursor.execute('SELECT COUNT(*) as total FROM "Reportes_perdidos"')
            perdidos = cursor.fetchone()["total"]

            reportes_totales = encontrados + perdidos

            # Recuperados: objetos que fueron perdidos Y encontrados
            cursor.execute("""
                SELECT COUNT(DISTINCT rp."ID_OBJETO") as recuperados
                FROM "Reportes_perdidos" rp
                INNER JOIN "Reportes_encontrados" re ON rp."ID_OBJETO" = re."ID_OBJETO"
            """)
            recuperados = cursor.fetchone()["recuperados"]

            # Pendientes: reportes perdidos sin correspondencia en encontrados
            cursor.execute("""
                SELECT COUNT(*) as pendientes
                FROM "Reportes_perdidos" rp
                WHERE rp."ID_OBJETO" NOT IN (
                    SELECT DISTINCT "ID_OBJETO" FROM "Reportes_encontrados"
                )
            """)
            pendientes = cursor.fetchone()["pendientes"]

            # Usuarios activos (usuarios únicos que han reportado algo)
            cursor.execute("""
                SELECT COUNT(DISTINCT id_usuario) as activos FROM (
                    SELECT "ID_USUARIO" as id_usuario FROM "Reportes_encontrados"
                    UNION
                    SELECT "ID_USUARIO" as id_usuario FROM "Reportes_perdidos"
                ) usuarios_unicos
            """)
            usuarios_activos = cursor.fetchone()["activos"]

            cursor.close()
            db.close()

            return jsonify(
                {
                    "reportes_totales": reportes_totales,
                    "recuperados": recuperados,
                    "pendientes": pendientes,
                    "usuarios_activos": usuarios_activos,
                }
            )
        except Exception as e:
            print(f"Error en estadísticas: {e}")
            return (
                jsonify(
                    {
                        "reportes_totales": 0,
                        "recuperados": 0,
                        "pendientes": 0,
                        "usuarios_activos": 0,
                    }
                ),
                500,
            )

    @app.route("/api/actividad")
    @login_required
    def api_actividad():
        """Devuelve el historial de actividad del usuario"""
        try:
            id_usuario = session.get("id_usuario")
            db = conectar_db()
            cursor = db.cursor(cursor_factory=RealDictCursor)

            # traer los últimos 10 eventos del usuario (perdidos o encontrados)
            cursor.execute(
                """
                SELECT 'perdido' AS tipo, rp."FECHA" as fecha, o."NOMBRE" as nombre
                FROM "Reportes_perdidos" rp
                JOIN "Objetos" o ON rp."ID_OBJETO" = o."ID_OBJETO"
                WHERE rp."ID_USUARIO" = %s
                UNION ALL
                SELECT 'encontrado' AS tipo, re."FECHA" as fecha, o."NOMBRE" as nombre
                FROM "Reportes_encontrados" re
                JOIN "Objetos" o ON re."ID_OBJETO" = o."ID_OBJETO"
                WHERE re."ID_USUARIO" = %s
                ORDER BY fecha DESC
                LIMIT 10
            """,
                (id_usuario, id_usuario),
            )
            eventos = cursor.fetchall()
            cursor.close()
            db.close()
            # convertir fecha a string ISO para JS
            for ev in eventos:
                if isinstance(ev.get("fecha"), datetime):
                    ev["fecha"] = ev["fecha"].isoformat()
            return jsonify({"eventos": eventos})
        except Exception as e:
            print(f"Error en actividad: {e}")
            return jsonify({"eventos": []}), 500
