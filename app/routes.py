import os
import random
import traceback
import uuid
import re
from datetime import datetime, timedelta
from functools import wraps
from io import BytesIO

from flask import (
    request,
    jsonify,
    render_template,
    session,
    redirect,
    url_for,
    send_from_directory,
    send_file,
)
from werkzeug.security import generate_password_hash, check_password_hash
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
from werkzeug.utils import secure_filename
from app.correo import enviar_factura

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
# DECORADOR ADMIN REQUIRED
# -----------------------------

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):

        if "id_usuario" not in session:
            return redirect("/inicio")

        if session.get("id_rol") != 2:
            return redirect("/menu")

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
                SELECT 
                    o."NOMBRE", 
                    o."ID_OBJETO", 
                    o."COLOR", 
                    o."IMAGEN", 
                    COALESCE(c."NOMBRE", o."ID_CATEGORIA") as CATEGORIA,
                    r."FECHA", 
                    r."OBSERVACIONES", 
                    r."ID_USUARIO", 
                    u."NOMBRE" as NOMBRE_USUARIO,
                    'perdido' AS tipo
                FROM "Objetos" o
                LEFT JOIN "Reportes_perdidos" r ON o."ID_OBJETO" = r."ID_OBJETO"
                LEFT JOIN "Usuarios" u ON r."ID_USUARIO" = u."ID_USUARIO"
                LEFT JOIN "Categorias" c ON o."ID_CATEGORIA" = c."ID_CATEGORIA"
                WHERE o."ID_OBJETO" = %s

                UNION ALL

                SELECT 
                    o."NOMBRE", 
                    o."ID_OBJETO", 
                    o."COLOR", 
                    o."IMAGEN", 
                    COALESCE(c."NOMBRE", o."ID_CATEGORIA") as CATEGORIA,
                    r."FECHA", 
                    r."OBSERVACIONES", 
                    r."ID_USUARIO", 
                    u."NOMBRE" as NOMBRE_USUARIO,
                    'encontrado' AS tipo
                FROM "Objetos" o
                LEFT JOIN "Reportes_encontrados" r ON o."ID_OBJETO" = r."ID_OBJETO"
                LEFT JOIN "Usuarios" u ON r."ID_USUARIO" = u."ID_USUARIO"
                LEFT JOIN "Categorias" c ON o."ID_CATEGORIA" = c."ID_CATEGORIA"
                WHERE o."ID_OBJETO" = %s
            ) t
            ORDER BY t."FECHA" DESC NULLS LAST
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
            genero = request.form.get("genero")
            contrasena = request.form.get("contrasena")
            contrasena_repetida = request.form.get("contrasena_repetida")
            pregunta1 = request.form.get("pregunta1")
            respuesta1 = request.form.get("respuesta1")
            pregunta2 = request.form.get("pregunta2")
            respuesta2 = request.form.get("respuesta2")
            respuesta1_hash = generate_password_hash(respuesta1)
            respuesta2_hash = generate_password_hash(respuesta2)
            id_rol = 1 #rol de usuario por defecto

            if not id_usuario or not contrasena:
                return jsonify({"mensaje": "Usuario y contraseña obligatorios"}), 400
            if " " in id_usuario:
                return jsonify({"mensaje": "El Usuario no puede tener espacios"}), 400
            if contrasena != contrasena_repetida:
                return jsonify({"mensaje": "Las contraseñas no coinciden"}), 400
            if genero not in ["masculino", "femenino"]:
                return jsonify({"mensaje": "Debes seleccionar masculino o femenino"}), 400

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
                ("ID_USUARIO", "NOMBRE", "GENERO", "CONTRASENA", "PREGUNTA_1", "PREGUNTA_2", "RESPUESTA_1", "RESPUESTA_2", "ID_ROL")
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                id_usuario,
                nombre,
                genero,
                hashed_password,
                pregunta1,
                pregunta2,
                respuesta1_hash,
                respuesta2_hash,
                id_rol,
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
            session["nombre"] = nombre
            session["genero"] = genero

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
    
    # --------------------------------
    # RUTA PARA EL HTML DE USUARIOS
    # --------------------------------

    @app.route("/usuarios")
    @admin_required
    def usuarios():
        return render_template("usuarios.html", active="usuarios")


    #------------------------------
    # CONSULTAR USUARIOS
    # -----------------------------
    @app.route("/api/usuarios", methods=["GET"])
    @admin_required
    def obtener_usuarios():
        try:
            conexion = conectar_db()
            if conexion is None:
                return jsonify({"mensaje": "Error de conexión a la base de datos"}), 500

            cursor = conexion.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
            """
                SELECT u."ID_USUARIO", u."NOMBRE", u."GENERO", u."ID_ROL", r."NOMBRE" as ROL_NOMBRE
                FROM public."Usuarios" u
                LEFT JOIN public."Roles" r ON u."ID_ROL" = r."ID_ROL"
                ORDER BY u."ID_USUARIO" DESC;   
            """,  
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
                '''
                SELECT u."ID_USUARIO", u."CONTRASENA", u."GENERO", p."NOMBRE", u."ID_ROL"
                FROM public."Usuarios" u
                LEFT JOIN public."Perfiles" p 
                ON u."ID_USUARIO" = p."ID_USUARIO"
                WHERE u."ID_USUARIO" = %s
                ''',
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

            session.clear()
            session["id_usuario"] = user["ID_USUARIO"]
            session["nombre"] = user["NOMBRE"]
            session["genero"] = user["GENERO"]
            session["id_rol"] = user["ID_ROL"]

            if user["ID_ROL"] == 2:
                return jsonify({
                    "ok": True,
                    "mensaje": "Inicio de sesión exitoso",
                    "redirect": "/admin_inicio"
                })

            return jsonify({
                "ok": True,
                "mensaje": "Inicio de sesión exitoso",
                "redirect": "/menu"
            })  
        except Exception as e:
            import traceback

            # esto imprime el error completo
            traceback.print_exc()
            return jsonify({"ok": False, "mensaje": "Error en el servidor"}), 500
    

    # -------------------------------------
    # RUTA ADMIN INICIO
    # -------------------------------------

    @app.route("/admin_inicio")
    @admin_required
    def admin_inicio():
        if session.get("id_rol") != 2:  # Verificar si el rol es admin si no lo devuelve al menu
            return redirect("/menu")
        return render_template("admin.html", active="panel")

    @app.route("/admin_perfil")
    @admin_required
    def admin_perfil():
        return render_template("perfil.html", active="perfil")
    
    
    @app.route("/api/admin_estadisticas")
    @admin_required
    def api_estadisticas_admin():
        """Devuelve las estadísticas del dashboard"""
        try:
            db = conectar_db()
            cursor = db.cursor(cursor_factory=RealDictCursor)

            cursor.execute('SELECT COUNT(*) as total FROM "Reportes_encontrados"')
            encontrados = cursor.fetchone()["total"]

            cursor.execute('SELECT COUNT(*) as total FROM "Reportes_perdidos"')
            perdidos = cursor.fetchone()["total"]

            reportes_totales = encontrados + perdidos

            cursor.execute("""
                SELECT COUNT(DISTINCT rp."ID_OBJETO") as recuperados
                FROM "Reportes_perdidos" rp
                INNER JOIN "Reportes_encontrados" re ON rp."ID_OBJETO" = re."ID_OBJETO"
            """)
            recuperados = cursor.fetchone()["recuperados"]

            cursor.execute('SELECT COUNT(*) as usuarios FROM "Usuarios"')
            usuarios = cursor.fetchone()["usuarios"]

            cursor.close()
            db.close()

            return jsonify(
                {
                    "reportes_totales": reportes_totales,
                    "recuperados": recuperados,
                    "usuarios": usuarios,
                }
            )
        except Exception as e:
            print(f"Error en estadísticas: {e}")
            return (
                jsonify(
                    {
                        "reportes_totales": 0,
                        "recuperados": 0,
                        "reportes_falsos": 0,
                        "usuarios": 0,
                    }
                ),
                500,
            )

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
    # FORMULARIO UNICO DE REPORTE
    # -------------------------------------
    @app.route("/formulario_reporte")
    @login_required
    def formulario_reporte():

        db = conectar_db()
        cursor = db.cursor(cursor_factory=RealDictCursor)

        # Categorias
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

        cursor.close()
        db.close()

        return render_template(
            "form_reporte.html",
            categorias=categorias,
            active="panel",
            hide_fab=True,
        )
    
    # -------------------------------------
    # ENVIAR REPORTE YA SEA PERDIDO O ENCONTRADO
    # -------------------------------------
    @app.route("/submit_reporte", methods=["POST"])
    @login_required
    def submit_reporte():

        try:

            tipo = request.form.get("tipo_reporte")

            if tipo not in ["perdido", "encontrado"]:
                return jsonify({"mensaje": "Tipo de reporte inválido", "error": True}), 400

            id_usuario = session.get("id_usuario")

            nombre_objeto = request.form.get("nombre_objeto", "").strip()
            estado = request.form.get("estado", "").strip()
            color_dominante = request.form.get("color_dominante", "").strip()
            lugar = request.form.get("lugar", "").strip()
            fecha = request.form.get("fecha", "").strip()
            categoria = request.form.get("categoria", "").strip()
            comentario = request.form.get("comentario", "").strip()

            if not all([nombre_objeto, estado, color_dominante, lugar, fecha, categoria]):
                return jsonify({"mensaje": "Faltan campos requeridos", "error": True}), 400

            ficha = request.form.get("ficha")
            ficha = int(ficha) if ficha else None

            id_objeto = str(random.randint(100000, 999999))
            id_reporte = str(random.randint(100000, 999999))

            # -------------------------
            # IMAGEN
            # -------------------------

            imagen = request.files.get("imagen")
            ruta = None

            if imagen and imagen.filename:

                filename = secure_filename(imagen.filename)
                unique_filename = f"{uuid.uuid4()}_{filename}"

                os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

                save_path = os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    unique_filename,
                )

                imagen.save(save_path)

                ruta = f"/uploads/{unique_filename}"

            # -------------------------
            # DB
            # -------------------------

            bd = conectar_db()
            cursor = bd.cursor()

            # asegurar estado
            cursor.execute('SELECT 1 FROM "Estados" WHERE "ID_ESTADO"=%s', (estado,))
            if not cursor.fetchone():
                cursor.execute(
                    'INSERT INTO "Estados" ("ID_ESTADO") VALUES (%s) ON CONFLICT DO NOTHING',
                    (estado,),
                )

            # asegurar categoria
            cursor.execute(
                'SELECT 1 FROM "Categorias" WHERE "ID_CATEGORIA"=%s',
                (categoria,),
            )

            if not cursor.fetchone():
                cursor.execute(
                    'INSERT INTO "Categorias" ("ID_CATEGORIA") VALUES (%s) ON CONFLICT DO NOTHING',
                    (categoria,),
                )

            # -------------------------
            # INSERT OBJETO
            # -------------------------

            cursor.execute(
                """
                INSERT INTO "Objetos"
                ("ID_OBJETO","NOMBRE","COLOR","ID_ESTADO","LUGAR_ENCONTRADO","ID_CATEGORIA","IMAGEN")
                VALUES (%s,%s,%s,%s,%s,%s,%s)
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

            # -------------------------
            # INSERT REPORTE
            # -------------------------

            if tipo == "perdido":

                cursor.execute(
                    """
                    INSERT INTO "Reportes_perdidos"
                    ("FECHA","OBSERVACIONES","ID_OBJETO","ID_USUARIO","ID_REPORTE","FICHA","ID_CATEGORIA")
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
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

            else:

                cursor.execute(
                    """
                    INSERT INTO "Reportes_encontrados"
                    ("FECHA","OBSERVACIONES","ID_OBJETO","ID_USUARIO","ID_REPORTE_ENC","FICHA","ID_CATEGORIA")
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
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

            return jsonify({"mensaje": "Reporte enviado correctamente"}), 200

        except Exception as e:

            import traceback
            traceback.print_exc()

            return jsonify({
                "mensaje": f"Error al procesar el reporte: {str(e)}",
                "error": True
            }), 500

    # -----------------------------
    # RUTA PARA MOSTRAR IMAGENES SUBIDAS
    # -----------------------------
    @app.route("/uploads/<filename>")
    def uploaded_file(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    

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
                SELECT 
                    p."NOMBRE",
                    p."APELLIDO",
                    p."TELEFONO",
                    p."CORREO",
                    p."FOTO_PERFIL",
                    u."GENERO"
                FROM "Perfiles" p
                JOIN "Usuarios" u ON p."ID_USUARIO" = u."ID_USUARIO"
                WHERE p."ID_USUARIO" = %s
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
                            "GENERO": "",
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
            genero = request.form.get("genero", "").strip()

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
                
                # actualizar genero
                cursor.execute(
                    """
                    UPDATE "Usuarios"
                    SET "GENERO" = %s
                    WHERE "ID_USUARIO" = %s
                """,
                    (genero, id_usuario),
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

            # actualizar datos en la sesión
            session["genero"] = genero
            session["nombre"] = nombre
     
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
        return render_template("mis_reportes.html", active="reportes")

    @app.route("/api/mis_reportes", methods=["GET"])
    @login_required
    def api_mis_reportes():
        """Devuelve JSON con los reportes (perdidos/encontrados) del usuario en sesión
        
        Parámetros GET opcionales:
        - categoria: ID_CATEGORIA para filtrar por categoría
        - fecha_inicio: Fecha inicio (YYYY-MM-DD)
        - fecha_fin: Fecha fin (YYYY-MM-DD)
        """
        try:
            id_usuario = session["id_usuario"]
            categoria = request.args.get("categoria", "").strip() or None
            fecha_inicio = request.args.get("fecha_inicio", "").strip() or None
            fecha_fin = request.args.get("fecha_fin", "").strip() or None
            
            db = conectar_db()
            cursor = db.cursor(cursor_factory=RealDictCursor)

            # Construir condiciones para PERDIDOS
            conditions_p = ['r."ID_USUARIO" = %s']
            params_p = [id_usuario]
            
            if categoria:
                conditions_p.append('o."ID_CATEGORIA" = %s')
                params_p.append(categoria)
            
            if fecha_inicio:
                conditions_p.append('r."FECHA" >= %s::DATE')
                params_p.append(fecha_inicio)
            
            if fecha_fin:
                conditions_p.append('r."FECHA" <= %s::DATE')
                params_p.append(fecha_fin)
            
            # Construir condiciones para ENCONTRADOS (mismas condiciones)
            conditions_e = ['r."ID_USUARIO" = %s']
            params_e = [id_usuario]
            
            if categoria:
                conditions_e.append('o."ID_CATEGORIA" = %s')
                params_e.append(categoria)
            
            if fecha_inicio:
                conditions_e.append('r."FECHA" >= %s::DATE')
                params_e.append(fecha_inicio)
            
            if fecha_fin:
                conditions_e.append('r."FECHA" <= %s::DATE')
                params_e.append(fecha_fin)
            
            # Combinar todos los parámetros en el orden correcto
            params = params_p + params_e
            
            where_p = ' AND '.join(conditions_p)
            where_e = ' AND '.join(conditions_e)
            
            query = f"""
                SELECT r."ID_REPORTE" as id_reporte, 'perdido' as tipo, o."ID_OBJETO", o."NOMBRE", o."COLOR", o."IMAGEN", r."FECHA", r."OBSERVACIONES", o."ID_CATEGORIA" as categoria, c."NOMBRE" as nombre_categoria
                FROM "Reportes_perdidos" r
                JOIN "Objetos" o ON r."ID_OBJETO" = o."ID_OBJETO"
                LEFT JOIN "Categorias" c ON o."ID_CATEGORIA" = c."ID_CATEGORIA"
                WHERE {where_p}
                UNION ALL
                SELECT r."ID_REPORTE_ENC" as id_reporte, 'encontrado' as tipo, o."ID_OBJETO", o."NOMBRE", o."COLOR", o."IMAGEN", r."FECHA", r."OBSERVACIONES", o."ID_CATEGORIA" as categoria, c."NOMBRE" as nombre_categoria
                FROM "Reportes_encontrados" r
                JOIN "Objetos" o ON r."ID_OBJETO" = o."ID_OBJETO"
                LEFT JOIN "Categorias" c ON o."ID_CATEGORIA" = c."ID_CATEGORIA"
                WHERE {where_e}
                ORDER BY "FECHA" DESC
            """

            cursor.execute(query, params)
            reportes = cursor.fetchall()
            cursor.close()
            db.close()

            return jsonify({"ok": True, "datos": reportes})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route('/api/categorias', methods=['GET'])
    def api_categorias():
        """Retorna todas las categorías disponibles"""
        try:
            db = conectar_db()
            cursor = db.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute('SELECT "ID_CATEGORIA", "NOMBRE" FROM "Categorias" ORDER BY "NOMBRE"')
            categorias = cursor.fetchall()
            cursor.close()
            db.close()
            
            return jsonify({"ok": True, "datos": categorias})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route('/api/descargar_reportes', methods=['POST'])
    @login_required
    def api_descargar_reportes():
        """Genera y descarga un PDF con los reportes filtrados"""
        try:
            id_usuario = session["id_usuario"]
            payload = request.get_json() or {}
            
            categoria = (payload.get("categoria") or "").strip() or None
            fecha_inicio = (payload.get("fecha_inicio") or "").strip() or None
            fecha_fin = (payload.get("fecha_fin") or "").strip() or None

            tipo = (payload.get("tipo") or "").strip() or None
            busqueda = (payload.get("busqueda") or "").strip() or None
                        
            db = conectar_db()
            cursor = db.cursor(cursor_factory=RealDictCursor)

            # Construir condiciones para PERDIDOS
            conditions_p = ['r."ID_USUARIO" = %s']
            params_p = [id_usuario]
            
            if categoria:
                conditions_p.append('o."ID_CATEGORIA" = %s')
                params_p.append(categoria)

            if busqueda:
                conditions_p.append('(LOWER(o."NOMBRE") LIKE LOWER(%s) OR LOWER(o."COLOR") LIKE LOWER(%s))')
                params_p.extend([f"%{busqueda}%", f"%{busqueda}%"])

            if fecha_inicio:
                conditions_p.append('r."FECHA" >= %s::DATE')
                params_p.append(fecha_inicio)
            
            if fecha_fin:
                conditions_p.append('r."FECHA" <= %s::DATE')
                params_p.append(fecha_fin)
            
            # Construir condiciones para ENCONTRADOS
            conditions_e = ['r."ID_USUARIO" = %s']
            params_e = [id_usuario]
            
            if categoria:
                conditions_e.append('o."ID_CATEGORIA" = %s')
                params_e.append(categoria)
            
            if fecha_inicio:
                conditions_e.append('r."FECHA" >= %s::DATE')
                params_e.append(fecha_inicio)
            
            if fecha_fin:
                conditions_e.append('r."FECHA" <= %s::DATE')
                params_e.append(fecha_fin)
            
            params = params_p + params_e
            where_p = ' AND '.join(conditions_p)
            where_e = ' AND '.join(conditions_e)
            
            query = f"""
                SELECT r."ID_REPORTE" as id_reporte, 'perdido' as tipo, o."ID_OBJETO", o."NOMBRE", o."COLOR", o."IMAGEN", r."FECHA", r."OBSERVACIONES", o."ID_CATEGORIA" as categoria, c."NOMBRE" as nombre_categoria
                FROM "Reportes_perdidos" r
                JOIN "Objetos" o ON r."ID_OBJETO" = o."ID_OBJETO"
                LEFT JOIN "Categorias" c ON o."ID_CATEGORIA" = c."ID_CATEGORIA"
                WHERE {where_p}
                UNION ALL
                SELECT r."ID_REPORTE_ENC" as id_reporte, 'encontrado' as tipo, o."ID_OBJETO", o."NOMBRE", o."COLOR", o."IMAGEN", r."FECHA", r."OBSERVACIONES", o."ID_CATEGORIA" as categoria, c."NOMBRE" as nombre_categoria
                FROM "Reportes_encontrados" r
                JOIN "Objetos" o ON r."ID_OBJETO" = o."ID_OBJETO"
                LEFT JOIN "Categorias" c ON o."ID_CATEGORIA" = c."ID_CATEGORIA"
                WHERE {where_e}
                ORDER BY "FECHA" DESC
            """

            cursor.execute(query, params)
            reportes = cursor.fetchall()
            cursor.close()
            db.close()

            # Generar HTML para el PDF
            filas_tabla = ""
            for idx, r in enumerate(reportes, 1):
                fecha = r.get('FECHA')
                if isinstance(fecha, datetime):
                    fecha_str = fecha.strftime('%d/%m/%Y')
                else:
                    fecha_str = str(fecha) if fecha else 'N/A'
                
                tipoLabel = 'Perdido' if r['tipo'] == 'perdido' else 'Encontrado'
                
                filas_tabla += f"""
                <tr>
                    <td>{idx}</td>
                    <td>{r.get('NOMBRE', 'N/A')}</td>
                    <td>{r.get('COLOR', 'N/A')}</td>
                    <td>{r.get('nombre_categoria', 'N/A')}</td>
                    <td>{tipoLabel}</td>
                    <td>{fecha_str}</td>
                    <td>{(r.get('OBSERVACIONES') or '')[:100]}</td>
                </tr>
                """

            html_content = f"""
            <!DOCTYPE html>
            <html lang="es">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Reporte de Objetos</title>
                <style>
                    * {{
                        margin: 0;
                        padding: 0;
                        box-sizing: border-box;
                    }}
                    
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        color: #333;
                        background: white;
                        padding: 20px;
                    }}
                    
                    .header {{
                        text-align: center;
                        margin-bottom: 30px;
                        border-bottom: 3px solid #3498db;
                        padding-bottom: 15px;
                    }}
                    
                    .header h1 {{
                        color: #2c3e50;
                        font-size: 28px;
                        margin-bottom: 5px;
                    }}
                    
                    .header p {{
                        color: #7f8c8d;
                        font-size: 12px;
                    }}
                    
                    .info-filtros {{
                        background: #ecf0f1;
                        padding: 15px;
                        border-radius: 5px;
                        margin-bottom: 20px;
                        font-size: 12px;
                    }}
                    
                    .info-filtros p {{
                        margin: 5px 0;
                        color: #34495e;
                    }}
                    
                    table {{
                        width: 100%;
                        border-collapse: collapse;
                        margin-top: 20px;
                    }}
                    
                    thead {{
                        background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
                        color: white;
                    }}
                    
                    th {{
                        padding: 15px;
                        text-align: left;
                        font-weight: 600;
                        font-size: 12px;
                        text-transform: uppercase;
                        letter-spacing: 0.5px;
                        border: 1px solid #3498db;
                    }}
                    
                    td {{
                        padding: 12px 15px;
                        border: 1px solid #ecf0f1;
                        font-size: 11px;
                    }}
                    
                    tbody tr:nth-child(even) {{
                        background: #f8f9fa;
                    }}
                    
                    tbody tr:hover {{
                        background: #ecf0f1;
                    }}
                    
                    .tipo-perdido {{
                        background: #ff6b6b;
                        color: white;
                        padding: 4px 8px;
                        border-radius: 3px;
                        font-weight: 500;
                    }}
                    
                    .tipo-encontrado {{
                        background: #51cf66;
                        color: white;
                        padding: 4px 8px;
                        border-radius: 3px;
                        font-weight: 500;
                    }}
                    
                    .footer {{
                        text-align: center;
                        margin-top: 30px;
                        padding-top: 15px;
                        border-top: 1px solid #ecf0f1;
                        color: #7f8c8d;
                        font-size: 10px;
                    }}
                    
                    .total-registros {{
                        background: #e8f4f8;
                        padding: 10px;
                        border-left: 4px solid #3498db;
                        margin-top: 20px;
                        font-weight: 600;
                        color: #2c3e50;
                    }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>Reporte de Objetos</h1>
                    <p>Generado el: {datetime.now().strftime('%d de %B de %Y a las %H:%M')}</p>
                </div>
                
                <div class="info-filtros">
                    <p><strong>Filtros aplicados:</strong></p>
                    <p>• Categoría: {categoria or 'Todas'}</p>
                    <p>• Fecha desde: {fecha_inicio or 'Sin límite'}</p>
                    <p>• Fecha hasta: {fecha_fin or 'Sin límite'}</p>
                </div>
                
                <table>
                    <thead>
                        <tr>
                            <th width="5%">#</th>
                            <th width="15%">Nombre</th>
                            <th width="12%">Color</th>
                            <th width="15%">Categoría</th>
                            <th width="12%">Tipo</th>
                            <th width="12%">Fecha</th>
                            <th width="29%">Observaciones</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filas_tabla if filas_tabla else '<tr><td colspan="7" style="text-align:center; padding: 20px;">No hay registros para mostrar</td></tr>'}
                    </tbody>
                </table>
                
                <div class="total-registros">
                    Total de registros: {len(reportes)}
                </div>
                
                <div class="footer">
                    <p>© O.R.I.O - Sistema de Reporte de Objetos Perdidos y Encontrados</p>
                    <p>Este documento contiene información confidencial de tu cuenta</p>
                </div>
            </body>
            </html>
            """

            # Generar PDF
            html = HTML(string=html_content, base_url='.')
            pdf_bytes = html.write_pdf()
            
            # Enviar como descarga
            fecha_generacion = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"reportes_{fecha_generacion}.pdf"
            
            return send_file(
                BytesIO(pdf_bytes),
                mimetype='application/pdf',
                as_attachment=True,
                download_name=filename
            )
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route('/api/borrar_reporte', methods=['POST'])
    @login_required
    def api_borrar_reporte():
        """Borra un reporte si pertenece al usuario en sesión.
        Body JSON: { "id_reporte": "<id>", "tipo": "perdido"|"encontrado" }
        """
        try:
            payload = request.get_json() or {}
            id_reporte = payload.get('id_reporte')
            tipo = payload.get('tipo')

            if not id_reporte or tipo not in ('perdido', 'encontrado'):
                return jsonify({'ok': False, 'error': 'Parámetros inválidos'}), 400

            id_usuario = session.get('id_usuario')
            if not id_usuario:
                return jsonify({'ok': False, 'error': 'No autenticado'}), 401

            db = conectar_db()
            cursor = db.cursor()

            # Determinar tabla y columna según tipo
            if tipo == 'perdido':
                # verificar propietario
                cursor.execute('SELECT "ID_USUARIO" FROM "Reportes_perdidos" WHERE "ID_REPORTE" = %s', (id_reporte,))
                row = cursor.fetchone()
                if not row:
                    cursor.close()
                    db.close()
                    return jsonify({'ok': False, 'error': 'Reporte no encontrado'}), 404
                if row[0] != id_usuario:
                    cursor.close()
                    db.close()
                    return jsonify({'ok': False, 'error': 'No autorizado'}), 403

                cursor.execute('DELETE FROM "Reportes_perdidos" WHERE "ID_REPORTE" = %s', (id_reporte,))

            else:  # encontrado
                cursor.execute('SELECT "ID_USUARIO" FROM "Reportes_encontrados" WHERE "ID_REPORTE_ENC" = %s', (id_reporte,))
                row = cursor.fetchone()
                if not row:
                    cursor.close()
                    db.close()
                    return jsonify({'ok': False, 'error': 'Reporte no encontrado'}), 404
                if row[0] != id_usuario:
                    cursor.close()
                    db.close()
                    return jsonify({'ok': False, 'error': 'No autorizado'}), 403

                cursor.execute('DELETE FROM "Reportes_encontrados" WHERE "ID_REPORTE_ENC" = %s', (id_reporte,))

            db.commit()
            afectadas = cursor.rowcount if hasattr(cursor, 'rowcount') else None
            cursor.close()
            db.close()

            return jsonify({'ok': True, 'deleted': bool(afectadas)}), 200

        except Exception as e:
            try:
                cursor.close()
                db.close()
            except:
                pass
            return jsonify({'ok': False, 'error': str(e)}), 500

    @app.route("/configuracion")
    @login_required
    def configuracion():
        # Redirigir según el rol del usuario
        if session.get("id_rol") == 2:  # Admin
            return redirect(url_for("admin_configuracion"))
        else:  # Usuario normal
            return redirect(url_for("configuracion_user"))

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

    # ----TEMA DE USUARIO----
    @app.route("/api/tema/obtener", methods=["GET"])
    @login_required
    def api_obtener_tema():
        """Obtiene el tema preferido del usuario desde la BD"""
        try:
            id_usuario = session["id_usuario"]
            db = conectar_db()
            cursor = db.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute(
                'SELECT "TEMA_PREFERENCIA" FROM "Usuarios" WHERE "ID_USUARIO" = %s',
                (id_usuario,)
            )
            usuario = cursor.fetchone()
            cursor.close()
            db.close()
            
            if not usuario:
                return jsonify({"ok": False, "error": "Usuario no encontrado"}), 404
            
            tema = usuario.get("TEMA_PREFERENCIA", "claro")
            return jsonify({"ok": True, "tema": tema})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/tema/actualizar", methods=["POST"])
    @login_required
    def api_actualizar_tema():
        """Actualiza el tema preferido del usuario en la BD"""
        try:
            id_usuario = session["id_usuario"]
            tema = request.json.get("tema", "claro").strip().lower()
            
            # Validar que el tema sea uno de los permitidos
            temas_permitidos = ["claro", "oscuro", "alto-contraste"]
            if tema not in temas_permitidos:
                return jsonify({"ok": False, "error": "Tema no válido"}), 400
            
            db = conectar_db()
            cursor = db.cursor()
            
            cursor.execute(
                'UPDATE "Usuarios" SET "TEMA_PREFERENCIA" = %s WHERE "ID_USUARIO" = %s',
                (tema, id_usuario)
            )
            db.commit()
            cursor.close()
            db.close()
            
            return jsonify({"ok": True, "mensaje": "Tema actualizado correctamente"})
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


# -------------------------------------
# RUTA PARA PAGO SIMULADO
# -------------------------------------


    @app.route("/simular_pago", methods=['POST'])
    def simular_pago():

        data = request.get_json()

        nombre = data.get("nombre")
        apellidos = data.get("apellidos")
        email = data.get("email")
        pais_id = data.get("pais_id")
        direccion = data.get("direccion")
        ciudad = data.get("ciudad")
        cp = int(data.get("cp"))
        metodo_pago = int(data.get("metodo_pago"))
        plan_id = int(data.get("plan_id"))

        print("METODO:", metodo_pago)
        print("PLAN:", plan_id)

        resultado = random.choice(["aprobado", "rechazado"])

        if resultado == "rechazado":
            return jsonify({
                "status": "rechazado",
                "mensaje": "Pago rechazado"
            })

        else:
            try:
                conexion = conectar_db()
                cursor = conexion.cursor(cursor_factory=RealDictCursor)

                cursor.execute("""
                    INSERT INTO "Facturas" 
                    ("EMAIL", "NOMBRES", "APELLIDOS", "DIRECCION", "CODIGO_POSTAL", "CIUDAD", "ID_PAIS", "ID_METODO", "ID_PLAN")
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (email, nombre, apellidos, direccion, cp, ciudad, pais_id, metodo_pago, plan_id))

                conexion.commit()
                cursor.close()
                conexion.close()

                conexion = conectar_db()
                cursor = conexion.cursor(cursor_factory=RealDictCursor)

                cursor.execute("""
                    SELECT m."NAME_METODO", p."NAME", p."PRECIO"
                    FROM "Metodos_pago" m, "Planes" p
                    WHERE m."ID_METODO" = %s
                    AND p."ID_PLAN" = %s
                """, (metodo_pago, plan_id))

                resultado = cursor.fetchone()
                nombre_metodo = resultado["NAME_METODO"]
                nombre_plan = resultado["NAME"]
                precio = resultado["PRECIO"]

                #Obtener pais
                cursor.execute("""
                    SELECT "NOMBRE" FROM "Paises"
                    WHERE "ID_PAIS" = %s
                """, (pais_id,))
                pais_nombre = cursor.fetchone()["NOMBRE"]

                #enviar correo

                enviar_factura(
                    email,
                    nombre,
                    apellidos,
                    direccion,
                    ciudad,
                    cp,
                    pais_nombre,
                    nombre_metodo,
                    nombre_plan,
                    precio
                        )

                cursor.close()
                conexion.close()

                return jsonify({
                    "status": "aprobado",
                    "mensaje": "Pago aprobado y guardado"
                })

            except (TypeError, ValueError):
                return jsonify({
                    "status": "error",
                    "mensaje": "Datos inválidos"
                }), 400
        

            conexion.commit()
# -------------------------------------
# RUTA PASARELA DE PAGO
# -------------------------------------
    @app.route("/pasarela_pago")
    @login_required
    def pasarela_pago():
        return render_template("pasarela_pago.html")

# -------------------------------------
# RUTA FORMULARIO NORMAL DE PAGO
# -------------------------------------
    @app.route("/form_pago_normal")
    @login_required
    def form_normal_pago():
        plan_id = request.args.get("plan_id")
        if not plan_id:
            return "Plan no especificado", 400

        conn = conectar_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT "ID_PLAN", "NAME", "PRECIO"
            FROM "Planes"
            WHERE "ID_PLAN" = %s
        """, (plan_id,))

        plan = cursor.fetchone()

        cursor.close()
        conn.close()

        if not plan:
            return "Plan no encontrado", 404

        return render_template("form_pago_normal.html", plan=plan)

# -------------------------------------
# RUTA REPORTE DE PROBLEMAS
# -------------------------------------
    @app.route("/reporte_problema")
    @login_required
    def reporte_problem():
        return render_template("reporte_problemas.html")
    # ---------------------------------------------
    # RUTA PARA QUE EL ADMIN GESTIONE LOS USUARIOS
    #-----------------------------------------------

    @app.route("/gestionar_usuarios", methods=["GET"])
    @admin_required
    def gestionar_usuarios():
        return redirect("/usuarios")
    
    # -------------------------------------
    # RUTA PARA QUE EL USUARIO CONFIGURE SU PERFIL
    # -------------------------------------
    
    @app.route("/configuracion_user")
    @login_required
    def configuracion_user():
        return render_template("configuracion_user.html", active="configuracion")
    
    # -------------------------------------
    # ADMIN CONFIGURACIÓN
    # -------------------------------------

    @app.route("/admin_configuracion")
    @admin_required
    def admin_configuracion():
        return render_template("configuracion_admin.html", active="configuracion")
    
    # --------------------------------------------
    # RUTA PARA QUE EL ADMIN VEA LOS REPORTES 
    #---------------------------------------------

    @app.route("/admin_reportes")
    @admin_required
    def admin_reportes():
        return render_template("admin_reportes.html")
    
    #-----------------------------------------
    # RUTA PARA EL BUZON 
    #-----------------------------------------

    @app.route("/buzon")
    @login_required
    def buzon():
        return render_template("buzon.html", active="buzon")
    
    #-----------------------------------------
    # RUTA PARA QUE EL ADMIN BORRE REPORTES
    #-----------------------------------------

    @app.route('/api/admin_borrar_reporte', methods=['POST'])
    @login_required
    @admin_required
    def api_admin_borrar_reporte():

        try:
            payload = request.get_json() or {}
            id_reporte = payload.get('id_reporte')
            tipo = payload.get('tipo')

            if not id_reporte or tipo not in ('perdido', 'encontrado'):
                return jsonify({'ok': False, 'error': 'Parámetros inválidos'}), 400

            id_usuario = session.get('id_usuario')
            if not id_usuario:
                return jsonify({'ok': False, 'error': 'No autenticado'}), 401

            db = conectar_db()
            cursor = db.cursor()

            if tipo == 'perdido':
                cursor.execute(
                    'SELECT * FROM "Reportes_perdidos" WHERE "ID_REPORTE" = %s',
                    (id_reporte,)
                )

                row = cursor.fetchone()
                if not row:
                    cursor.close()
                    db.close()
                    return jsonify({'ok': False, 'error': 'Reporte no encontrado'}), 404

                cursor.execute('DELETE FROM "Reportes_perdidos" WHERE "ID_REPORTE" = %s', (id_reporte,))

            else:  # encontrado
                cursor.execute('SELECT "ID_USUARIO" FROM "Reportes_encontrados" WHERE "ID_REPORTE_ENC" = %s', (id_reporte,))
                row = cursor.fetchone()
                if not row:
                    cursor.close()
                    db.close()
                    return jsonify({'ok': False, 'error': 'Reporte no encontrado'}), 404

                cursor.execute('DELETE FROM "Reportes_encontrados" WHERE "ID_REPORTE_ENC" = %s', (id_reporte,))

            db.commit()
            afectadas = cursor.rowcount if hasattr(cursor, 'rowcount') else None
            cursor.close()
            db.close()

            return jsonify({'ok': True, 'deleted': bool(afectadas)}), 200

        except Exception as e:
            try:
                cursor.close()
                db.close()
            except:
                pass
            return jsonify({'ok': False, 'error': str(e)}), 500
        

    #-----------------------------------------
    # RUTA PARA QUE EL ADMIN VEA LOS REPORTES
    #-----------------------------------------

    @app.route("/api/admin_reportes", methods=["GET"])
    @login_required
    @admin_required
    def api_admin_reportes():

        try:
            id_usuario = session["id_usuario"]
            categoria = request.args.get("categoria", "").strip() or None
            fecha_inicio = request.args.get("fecha_inicio", "").strip() or None
            fecha_fin = request.args.get("fecha_fin", "").strip() or None
            
            db = conectar_db()
            cursor = db.cursor(cursor_factory=RealDictCursor)

            params_p = [id_usuario]
            
            if categoria:
                params_p.append(categoria)
            
            if fecha_inicio:
                params_p.append(fecha_inicio)
            
            if fecha_fin:
                params_p.append(fecha_fin)
            
            params_e = [id_usuario]
            
            if categoria:
                params_e.append(categoria)
            
            if fecha_inicio:
                params_e.append(fecha_inicio)
            
            if fecha_fin:
                params_e.append(fecha_fin)
            

            
            query = f"""
                SELECT r."ID_REPORTE" as id_reporte, 'perdido' as tipo, o."ID_OBJETO", o."NOMBRE", o."COLOR", o."IMAGEN", r."FECHA", r."OBSERVACIONES", o."ID_CATEGORIA" as categoria, c."NOMBRE" as nombre_categoria
                FROM "Reportes_perdidos" r
                JOIN "Objetos" o ON r."ID_OBJETO" = o."ID_OBJETO"
                LEFT JOIN "Categorias" c ON o."ID_CATEGORIA" = c."ID_CATEGORIA"
                UNION ALL
                SELECT r."ID_REPORTE_ENC" as id_reporte, 'encontrado' as tipo, o."ID_OBJETO", o."NOMBRE", o."COLOR", o."IMAGEN", r."FECHA", r."OBSERVACIONES", o."ID_CATEGORIA" as categoria, c."NOMBRE" as nombre_categoria
                FROM "Reportes_encontrados" r
                JOIN "Objetos" o ON r."ID_OBJETO" = o."ID_OBJETO"
                LEFT JOIN "Categorias" c ON o."ID_CATEGORIA" = c."ID_CATEGORIA"
                ORDER BY "FECHA" DESC
            """

            cursor.execute(query)
            reportes = cursor.fetchall()
            cursor.close()
            db.close()

            return jsonify({"ok": True, "datos": reportes})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"ok": False, "error": str(e)}), 500
    
    #----------------------------------------------
    # RUTA PARA QUE EL ADMIN DESCARGUE LOS REPORTES
    #----------------------------------------------
    @app.route('/api/admin_descargar_reportes', methods=['POST'])
    @admin_required
    def api_admin_descargar_reportes():
        try:
            id_usuario = session["id_usuario"]
            payload = request.get_json() or {}
            
            categoria = (payload.get("categoria") or "").strip() or None
            fecha_inicio = (payload.get("fecha_inicio") or "").strip() or None
            fecha_fin = (payload.get("fecha_fin") or "").strip() or None

            tipo = (payload.get("tipo") or "").strip() or None
            busqueda = (payload.get("busqueda") or "").strip() or None
                        
            db = conectar_db()
            cursor = db.cursor(cursor_factory=RealDictCursor)

            # Construir condiciones para PERDIDOS
            params_p = [id_usuario]
            
            if categoria:
                params_p.append(categoria)

            if busqueda:
                params_p.extend([f"%{busqueda}%", f"%{busqueda}%"])

            if fecha_inicio:
                params_p.append(fecha_inicio)
            
            if fecha_fin:
                params_p.append(fecha_fin)
            params_e = [id_usuario]
            
            if categoria:
                params_e.append(categoria)
            
            if fecha_inicio:
                params_e.append(fecha_inicio)
            
            if fecha_fin:
                params_e.append(fecha_fin)
            
            
            query = f"""
                SELECT r."ID_REPORTE" as id_reporte, 'perdido' as tipo, o."ID_OBJETO", o."NOMBRE", o."COLOR", o."IMAGEN", r."FECHA", r."OBSERVACIONES", o."ID_CATEGORIA" as categoria, c."NOMBRE" as nombre_categoria
                FROM "Reportes_perdidos" r
                JOIN "Objetos" o ON r."ID_OBJETO" = o."ID_OBJETO"
                LEFT JOIN "Categorias" c ON o."ID_CATEGORIA" = c."ID_CATEGORIA"
                UNION ALL
                SELECT r."ID_REPORTE_ENC" as id_reporte, 'encontrado' as tipo, o."ID_OBJETO", o."NOMBRE", o."COLOR", o."IMAGEN", r."FECHA", r."OBSERVACIONES", o."ID_CATEGORIA" as categoria, c."NOMBRE" as nombre_categoria
                FROM "Reportes_encontrados" r
                JOIN "Objetos" o ON r."ID_OBJETO" = o."ID_OBJETO"
                LEFT JOIN "Categorias" c ON o."ID_CATEGORIA" = c."ID_CATEGORIA"
                ORDER BY "FECHA" DESC
            """

            cursor.execute(query)
            reportes = cursor.fetchall()
            cursor.close()
            db.close()

            # Generar HTML para el PDF
            filas_tabla = ""
            for idx, r in enumerate(reportes, 1):
                fecha = r.get('FECHA')
                if isinstance(fecha, datetime):
                    fecha_str = fecha.strftime('%d/%m/%Y')
                else:
                    fecha_str = str(fecha) if fecha else 'N/A'
                
                tipoLabel = 'Perdido' if r['tipo'] == 'perdido' else 'Encontrado'
                
                filas_tabla += f"""
                <tr>
                    <td>{idx}</td>
                    <td>{r.get('NOMBRE', 'N/A')}</td>
                    <td>{r.get('COLOR', 'N/A')}</td>
                    <td>{r.get('nombre_categoria', 'N/A')}</td>
                    <td>{tipoLabel}</td>
                    <td>{fecha_str}</td>
                    <td>{(r.get('OBSERVACIONES') or '')[:100]}</td>
                </tr>
                """

            html_content = f"""
            <!DOCTYPE html>
            <html lang="es">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Reporte de Objetos</title>
                <style>
                    * {{
                        margin: 0;
                        padding: 0;
                        box-sizing: border-box;
                    }}
                    
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        color: #333;
                        background: white;
                        padding: 20px;
                    }}
                    
                    .header {{
                        text-align: center;
                        margin-bottom: 30px;
                        border-bottom: 3px solid #3498db;
                        padding-bottom: 15px;
                    }}
                    
                    .header h1 {{
                        color: #2c3e50;
                        font-size: 28px;
                        margin-bottom: 5px;
                    }}
                    
                    .header p {{
                        color: #7f8c8d;
                        font-size: 12px;
                    }}
                    
                    .info-filtros {{
                        background: #ecf0f1;
                        padding: 15px;
                        border-radius: 5px;
                        margin-bottom: 20px;
                        font-size: 12px;
                    }}
                    
                    .info-filtros p {{
                        margin: 5px 0;
                        color: #34495e;
                    }}
                    
                    table {{
                        width: 100%;
                        border-collapse: collapse;
                        margin-top: 20px;
                    }}
                    
                    thead {{
                        background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
                        color: white;
                    }}
                    
                    th {{
                        padding: 15px;
                        text-align: left;
                        font-weight: 600;
                        font-size: 12px;
                        text-transform: uppercase;
                        letter-spacing: 0.5px;
                        border: 1px solid #3498db;
                    }}
                    
                    td {{
                        padding: 12px 15px;
                        border: 1px solid #ecf0f1;
                        font-size: 11px;
                    }}
                    
                    tbody tr:nth-child(even) {{
                        background: #f8f9fa;
                    }}
                    
                    tbody tr:hover {{
                        background: #ecf0f1;
                    }}
                    
                    .tipo-perdido {{
                        background: #ff6b6b;
                        color: white;
                        padding: 4px 8px;
                        border-radius: 3px;
                        font-weight: 500;
                    }}
                    
                    .tipo-encontrado {{
                        background: #51cf66;
                        color: white;
                        padding: 4px 8px;
                        border-radius: 3px;
                        font-weight: 500;
                    }}
                    
                    .footer {{
                        text-align: center;
                        margin-top: 30px;
                        padding-top: 15px;
                        border-top: 1px solid #ecf0f1;
                        color: #7f8c8d;
                        font-size: 10px;
                    }}
                    
                    .total-registros {{
                        background: #e8f4f8;
                        padding: 10px;
                        border-left: 4px solid #3498db;
                        margin-top: 20px;
                        font-weight: 600;
                        color: #2c3e50;
                    }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>Reporte de Objetos</h1>
                    <p>Generado el: {datetime.now().strftime('%d de %B de %Y a las %H:%M')}</p>
                </div>
                
                <div class="info-filtros">
                    <p><strong>Filtros aplicados:</strong></p>
                    <p>• Categoría: {categoria or 'Todas'}</p>
                    <p>• Fecha desde: {fecha_inicio or 'Sin límite'}</p>
                    <p>• Fecha hasta: {fecha_fin or 'Sin límite'}</p>
                </div>
                
                <table>
                    <thead>
                        <tr>
                            <th width="5%">#</th>
                            <th width="15%">Nombre</th>
                            <th width="12%">Color</th>
                            <th width="15%">Categoría</th>
                            <th width="12%">Tipo</th>
                            <th width="12%">Fecha</th>
                            <th width="29%">Observaciones</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filas_tabla if filas_tabla else '<tr><td colspan="7" style="text-align:center; padding: 20px;">No hay registros para mostrar</td></tr>'}
                    </tbody>
                </table>
                
                <div class="total-registros">
                    Total de registros: {len(reportes)}
                </div>
                
                <div class="footer">
                    <p>© O.R.I.O - Sistema de Reporte de Objetos Perdidos y Encontrados</p>
                    <p>Este documento contiene información confidencial de tu cuenta</p>
                </div>
            </body>
            </html>
            """

            # Generar PDF
            html = HTML(string=html_content, base_url='.')
            pdf_bytes = html.write_pdf()
            
            # Enviar como descarga
            fecha_generacion = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"reportes_{fecha_generacion}.pdf"
            
            return send_file(
                BytesIO(pdf_bytes),
                mimetype='application/pdf',
                as_attachment=True,
                download_name=filename
            )
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"ok": False, "error": str(e)}), 500
