# Librerías
import os
import re
import uuid
import random
from io import BytesIO
from datetime import datetime, timedelta

from flask import (
    render_template,
    request,
    redirect,
    url_for,
    session,
    jsonify,
    current_app,
    send_from_directory,
)
from werkzeug.utils import secure_filename

# Componentes internos
from .database import conectar_db
from .decorators import login_required, guest_required

# Si tienes utilidades
from psycopg2.extras import RealDictCursor
from werkzeug.security import check_password_hash, generate_password_hash

print (generate_password_hash("123456"))  # Esto es solo para mostrar cómo se ve una contraseña encriptada

def init_user_routes(app):
    """
    Registra todas las rutas del usuario.
    """
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
                    o."LUGAR_ENCONTRADO" AS LUGAR,
                    COALESCE(c."NOMBRE", o."ID_CATEGORIA") as CATEGORIA,
                    r."FECHA", 
                    r."OBSERVACIONES", 
                    r."ID_USUARIO", 
                    COALESCE(u."NOMBRE", r."ID_USUARIO") as NOMBRE_USUARIO,
                    'perdido' AS tipo
                FROM "Objetos" o
                LEFT JOIN "Reportes_perdidos" r ON o."ID_OBJETO" = r."ID_OBJETO"
                LEFT JOIN "Usuarios" u ON r."ID_USUARIO" = u."ID_USUARIO"
                LEFT JOIN "Categorias" c ON o."ID_CATEGORIA" = c."ID_CATEGORIA"
                WHERE o."ID_OBJETO" = %s OR r."ID_REPORTE" = %s

                UNION ALL

                SELECT 
                    o."NOMBRE", 
                    o."ID_OBJETO", 
                    o."COLOR", 
                    o."IMAGEN", 
                    o."LUGAR_ENCONTRADO" AS LUGAR,
                    COALESCE(c."NOMBRE", o."ID_CATEGORIA") as CATEGORIA,
                    r."FECHA", 
                    r."OBSERVACIONES", 
                    r."ID_USUARIO", 
                    COALESCE(u."NOMBRE", r."ID_USUARIO") as NOMBRE_USUARIO,
                    'encontrado' AS tipo
                FROM "Objetos" o
                LEFT JOIN "Reportes_encontrados" r ON o."ID_OBJETO" = r."ID_OBJETO"
                LEFT JOIN "Usuarios" u ON r."ID_USUARIO" = u."ID_USUARIO"
                LEFT JOIN "Categorias" c ON o."ID_CATEGORIA" = c."ID_CATEGORIA"
                WHERE o."ID_OBJETO" = %s OR r."ID_REPORTE_ENC" = %s
            ) t
            ORDER BY t."FECHA" DESC NULLS LAST
            LIMIT 1
            """,
            (id_objeto, id_objeto, id_objeto, id_objeto),
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
            telefono = request.form.get("telefono")

            if not id_usuario or not contrasena:
                return jsonify({"mensaje": "Usuario y contraseña obligatorios"}), 400
            if " " in id_usuario:
                return jsonify({"mensaje": "El Usuario no puede tener espacios"}), 400
            if contrasena != contrasena_repetida:
                return jsonify({"mensaje": "Las contraseñas no coinciden"}), 400
            if genero != "masculino" and genero != "femenino" and genero != "otro":
                return jsonify({"mensaje": "Debes seleccionar un genero"}), 400

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
                ("ID_USUARIO", "NOMBRE", "GENERO", "CONTRASENA", "PREGUNTA_1", "PREGUNTA_2", "RESPUESTA_1", "RESPUESTA_2", "ID_ROL", "TELEFONO")
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                telefono,
            ),
            )

            # crear perfil automáticamente para el nuevo usuario
            cursor.execute(
                """
                INSERT INTO public."Perfiles"
                ("ID_USUARIO", "NOMBRE", "FOTO_PERFIL", "TELEFONO")
                VALUES (%s, %s, %s, %s)
            """,
                (id_usuario, nombre, "https://via.placeholder.com/200", telefono),
            )

            conexion.commit()
            cursor.close()
            conexion.close()

            session["id_usuario"] = id_usuario
            session["nombre"] = nombre
            session["genero"] = genero
            session["telefono"] = telefono
            
            print("LLEGUÉ AL RETURN")

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
        fecha_inicio = request.args.get("fecha_inicio", "").strip() or None
        fecha_fin = request.args.get("fecha_fin", "").strip() or None

        print(f"[BUSQUEDAS] params q={q!r} categoria={categoria!r} tipo={tipo!r} fecha_inicio={fecha_inicio!r} fecha_fin={fecha_fin!r}")

        db = conectar_db()
        if db is None:
            error_msg = "Error de conexión a la base de datos"
            print(f"[BUSQUEDAS] {error_msg}")
            return jsonify({"ok": False, "error": error_msg}), 500

        cursor = db.cursor(cursor_factory=RealDictCursor)

        params = []
        conditions = ['1=1']

        if q:
            conditions.append(
                '(o."NOMBRE" ILIKE %s OR o."COLOR" ILIKE %s OR c."NOMBRE" ILIKE %s)'
            )
            params.extend([f"%{q}%"] * 3)

        if categoria:
            if categoria.isdigit():
                conditions.append('o."ID_CATEGORIA" = %s')
                params.append(int(categoria))
            else:
                conditions.append('c."NOMBRE" ILIKE %s')
                params.append(f"%{categoria}%")

        if fecha_inicio:
            conditions.append('r."FECHA" >= %s::DATE')
            params.append(fecha_inicio)

        if fecha_fin:
            conditions.append('r."FECHA" <= %s::DATE')
            params.append(fecha_fin)

        where = ' AND '.join(conditions)

        if tipo == "perdido":
            query = f'''
                SELECT o."NOMBRE", o."ID_OBJETO", o."COLOR", o."IMAGEN", 
                o."ID_CATEGORIA" AS CATEGORIA, c."NOMBRE" AS nombre_categoria,
                o."LUGAR_ENCONTRADO" AS "LUGAR", r."FECHA", 'perdido' AS tipo, r."ID_REPORTE" AS id_reporte
                FROM "Objetos" o
                JOIN "Reportes_perdidos" r ON o."ID_OBJETO" = r."ID_OBJETO"
                LEFT JOIN "Categorias" c ON o."ID_CATEGORIA" = c."ID_CATEGORIA"
                WHERE {where}
                ORDER BY r."FECHA" DESC
            '''
            print(f"[BUSQUEDAS] SQL PERDIDO: {query.strip()} params={params}")
            cursor.execute(query, params)
        elif tipo == "encontrado":
            query = f'''
                SELECT o."NOMBRE", o."ID_OBJETO", o."COLOR", o."IMAGEN", 
                o."ID_CATEGORIA" AS CATEGORIA, c."NOMBRE" AS nombre_categoria,
                o."LUGAR_ENCONTRADO" AS "LUGAR", r."FECHA", 'encontrado' AS tipo, r."ID_REPORTE_ENC" AS id_reporte
                FROM "Objetos" o
                JOIN "Reportes_encontrados" r ON o."ID_OBJETO" = r."ID_OBJETO"
                LEFT JOIN "Categorias" c ON o."ID_CATEGORIA" = c."ID_CATEGORIA"
                WHERE {where}
                ORDER BY r."FECHA" DESC
            '''
            print(f"[BUSQUEDAS] SQL ENCONTRADO: {query.strip()} params={params}")
            cursor.execute(query, params)
        else:
            params_union = params + params
            query = f'''
                SELECT o."NOMBRE", o."ID_OBJETO", o."COLOR", o."IMAGEN", 
                o."ID_CATEGORIA" AS CATEGORIA, c."NOMBRE" AS nombre_categoria,
                o."LUGAR_ENCONTRADO" AS "LUGAR", r."FECHA", 'perdido' AS tipo, r."ID_REPORTE" AS id_reporte
                FROM "Objetos" o
                JOIN "Reportes_perdidos" r ON o."ID_OBJETO" = r."ID_OBJETO"
                LEFT JOIN "Categorias" c ON o."ID_CATEGORIA" = c."ID_CATEGORIA"
                WHERE {where}
                UNION ALL
                SELECT o."NOMBRE", o."ID_OBJETO", o."COLOR", o."IMAGEN", 
                o."ID_CATEGORIA" AS CATEGORIA, c."NOMBRE" AS nombre_categoria,
                o."LUGAR_ENCONTRADO" AS "LUGAR", r."FECHA", 'encontrado' AS tipo, r."ID_REPORTE_ENC" AS id_reporte
                FROM "Objetos" o
                JOIN "Reportes_encontrados" r ON o."ID_OBJETO" = r."ID_OBJETO"
                LEFT JOIN "Categorias" c ON o."ID_CATEGORIA" = c."ID_CATEGORIA"
                WHERE {where}
                ORDER BY "FECHA" DESC
            '''
            print(f"[BUSQUEDAS] SQL UNION: {query.strip()} params={params_union}")
            cursor.execute(query, params_union)

        objetos = cursor.fetchall()
        print(f"[BUSQUEDAS] resultados={len(objetos)}")
        cursor.close()
        db.close()

        for objeto in objetos:
            fecha_val = objeto.get("FECHA")
            if fecha_val is not None and not isinstance(fecha_val, str):
                try:
                    objeto["FECHA"] = fecha_val.isoformat()
                except Exception:
                    objeto["FECHA"] = str(fecha_val)

        if not objetos:
            return jsonify({"datos": [], "mensaje": "No se encontraron resultados"})
        return jsonify({"ok": True, "datos": objetos})
    

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
    # RUTA MENU
    # -------------------------------------
    @app.route("/menu")
    @login_required
    def menu():
        return render_template("menu.html", active="panel")


    
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
        - categoria: ID_CATEGORIA o nombre de categoría para filtrar
        - tipo: 'perdido' o 'encontrado'
        - fecha_inicio: Fecha inicio (YYYY-MM-DD)
        - fecha_fin: Fecha fin (YYYY-MM-DD)
        """
        try:
            id_usuario = session["id_usuario"]
            categoria = request.args.get("categoria", "").strip() or None
            tipo = request.args.get("tipo", "").strip() or None
            fecha_inicio = request.args.get("fecha_inicio", "").strip() or None
            fecha_fin = request.args.get("fecha_fin", "").strip() or None
            
            def build_category_condition(alias):
                if not categoria:
                    return None, []
                if categoria.isdigit():
                    return f'{alias}."ID_CATEGORIA" = %s', [int(categoria)]
                return f'c."NOMBRE" ILIKE %s', [f"%{categoria}%"]

            db = conectar_db()
            cursor = db.cursor(cursor_factory=RealDictCursor)

            # Construir condiciones para PERDIDOS
            conditions_p = ['r."ID_USUARIO" = %s']
            params_p = [id_usuario]
            
            # Construir condiciones para ENCONTRADOS
            conditions_e = ['r."ID_USUARIO" = %s']
            params_e = [id_usuario]

            category_condition, category_params = build_category_condition('o')
            if category_condition:
                conditions_p.append(category_condition)
                conditions_e.append(category_condition)
                params_p.extend(category_params)
                params_e.extend(category_params)

            if fecha_inicio:
                conditions_p.append('r."FECHA" >= %s::DATE')
                conditions_e.append('r."FECHA" >= %s::DATE')
                params_p.append(fecha_inicio)
                params_e.append(fecha_inicio)
            
            if fecha_fin:
                conditions_p.append('r."FECHA" <= %s::DATE')
                conditions_e.append('r."FECHA" <= %s::DATE')
                params_p.append(fecha_fin)
                params_e.append(fecha_fin)

            if tipo == 'perdido':
                conditions_e.append('FALSE')
            elif tipo == 'encontrado':
                conditions_p.append('FALSE')

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

    @app.route('/api/reportes_recientes', methods=['GET'])
    def api_reportes_recientes():
        try:
            print('[API_REPORTES_RECIENTES] llamada recibida')
            db = conectar_db()
            if db is None:
                error_msg = 'Error de conexión a la base de datos'
                print(f'[API_REPORTES_RECIENTES] {error_msg}')
                return jsonify({'ok': False, 'error': error_msg}), 500

            cursor = db.cursor(cursor_factory=RealDictCursor)
            query = '''
                SELECT o."NOMBRE", o."ID_OBJETO", o."COLOR", o."IMAGEN",
                       o."ID_CATEGORIA" AS CATEGORIA, c."NOMBRE" AS nombre_categoria,
                       o."LUGAR_ENCONTRADO" AS "LUGAR", r."FECHA", 'perdido' AS tipo, r."ID_REPORTE" AS id_reporte,
                       COALESCE(u."NOMBRE", 'Usuario') AS NOMBRE_USUARIO
                FROM "Reportes_perdidos" r
                JOIN "Objetos" o ON r."ID_OBJETO" = o."ID_OBJETO"
                LEFT JOIN "Categorias" c ON o."ID_CATEGORIA" = c."ID_CATEGORIA"
                LEFT JOIN "Usuarios" u ON r."ID_USUARIO" = u."ID_USUARIO"
                UNION ALL
                SELECT o."NOMBRE", o."ID_OBJETO", o."COLOR", o."IMAGEN",
                       o."ID_CATEGORIA" AS CATEGORIA, c."NOMBRE" AS nombre_categoria,
                       o."LUGAR_ENCONTRADO" AS "LUGAR", r."FECHA", 'encontrado' AS tipo, r."ID_REPORTE_ENC" AS id_reporte,
                       COALESCE(u."NOMBRE", 'Usuario') AS NOMBRE_USUARIO
                FROM "Reportes_encontrados" r
                JOIN "Objetos" o ON r."ID_OBJETO" = o."ID_OBJETO"
                LEFT JOIN "Categorias" c ON o."ID_CATEGORIA" = c."ID_CATEGORIA"
                LEFT JOIN "Usuarios" u ON r."ID_USUARIO" = u."ID_USUARIO"
                ORDER BY "FECHA" DESC
            '''
            print(f'[API_REPORTES_RECIENTES] SQL: {query.strip()}')
            cursor.execute(query)
            reportes = cursor.fetchall()
            print(f'[API_REPORTES_RECIENTES] resultados={len(reportes)}')
            cursor.close()
            db.close()

            for reporte in reportes:
                fecha_val = reporte.get("FECHA")
                if fecha_val is not None and not isinstance(fecha_val, str):
                    try:
                        reporte["FECHA"] = fecha_val.isoformat()
                    except Exception:
                        reporte["FECHA"] = str(fecha_val)

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
            try:
                from weasyprint import HTML, CSS
                from weasyprint.text.fonts import FontConfiguration
            except Exception as e:
                return jsonify({"ok": False, "error": "WeasyPrint no disponible: " + str(e)}), 500

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
                    400,
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

    #-----------------------------------------
    # RUTA PARA EL BUZON
    #-----------------------------------------

    def _format_fecha_mensaje(raw_fecha):
        if isinstance(raw_fecha, datetime):
            try:
                return raw_fecha.strftime("%d/%m/%Y %H:%M"), raw_fecha.timestamp()
            except Exception:
                return raw_fecha.isoformat(), 0
        if raw_fecha:
            return str(raw_fecha), 0
        return "", 0

    def _build_conversations(cursor, id_usuario):
        cursor.execute(
            '''
            SELECT m."ID_MENSAJE", m."ID_REMITENTE", m."ID_DESTINATARIO", m."ID_OBJETO", m."ASUNTO", m."CUERPO", m."FECHA", m."LEIDO",
            o."NOMBRE" as OBJETO_NOMBRE, o."IMAGEN" as OBJETO_IMAGEN,
            pr."NOMBRE" as REMITENTE_NOMBRE,
            pd."NOMBRE" as DESTINATARIO_NOMBRE
            FROM public."Mensajes" m
            LEFT JOIN public."Objetos" o ON m."ID_OBJETO" = o."ID_OBJETO"
            LEFT JOIN public."Perfiles" pr ON m."ID_REMITENTE" = pr."ID_USUARIO"
            LEFT JOIN public."Perfiles" pd ON m."ID_DESTINATARIO" = pd."ID_USUARIO"
            WHERE m."ID_REMITENTE" = %s OR m."ID_DESTINATARIO" = %s
            ORDER BY m."FECHA" DESC
            ''',
            (id_usuario, id_usuario),
        )
        mensajes = cursor.fetchall()
        threads = {}
        for m in mensajes:
            remitente = m.get("ID_REMITENTE")
            destinatario = m.get("ID_DESTINATARIO")
            other_user = destinatario if remitente == id_usuario else remitente
            other_name = (
                m.get("DESTINATARIO_NOMBRE")
                if remitente == id_usuario
                else m.get("REMITENTE_NOMBRE")
            ) or other_user
            fecha_str, fecha_ts = _format_fecha_mensaje(m.get("FECHA"))
            if other_user not in threads:
                threads[other_user] = {
                    "contacto_id": other_user,
                    "destinatario": other_user,
                    "nombre": other_name,
                    "id_objeto": "0",
                    "objeto_nombre": m.get("OBJETO_NOMBRE") or "Chat general",
                    "objeto_imagen": m.get("OBJETO_IMAGEN") or None,
                    "ultimo_mensaje": m.get("CUERPO") or "",
                    "ultimo_asunto": m.get("ASUNTO") or "",
                    "ultima_fecha": fecha_str,
                    "ultima_fecha_ts": fecha_ts,
                    "sent": remitente == id_usuario,
                    "unread": 0,
                }
            elif fecha_ts > (threads[other_user].get("ultima_fecha_ts") or 0):
                threads[other_user].update(
                    {
                        "objeto_nombre": m.get("OBJETO_NOMBRE") or "Chat general",
                        "objeto_imagen": m.get("OBJETO_IMAGEN") or None,
                        "ultimo_mensaje": m.get("CUERPO") or "",
                        "ultimo_asunto": m.get("ASUNTO") or "",
                        "ultima_fecha": fecha_str,
                        "ultima_fecha_ts": fecha_ts,
                        "sent": remitente == id_usuario,
                    }
                )
            if destinatario == id_usuario and not m.get("LEIDO"):
                threads[other_user]["unread"] += 1
        thread_list = sorted(
            threads.values(), key=lambda x: x.get("ultima_fecha_ts", 0), reverse=True
        )
        for t in thread_list:
            t.pop("ultima_fecha_ts", None)
        return thread_list

    def _serialize_mensaje_row(m):
        row = dict(m)
        if isinstance(row.get("FECHA"), datetime):
            row["FECHA"] = row["FECHA"].strftime("%d/%m/%Y %H:%M")
        if row.get("LEIDO") is None:
            row["LEIDO"] = False
        return row

    def _marcar_mensajes_leidos(db, id_usuario, contacto_id, id_objeto=None):
        cursor = db.cursor()
        if id_objeto:
            cursor.execute(
                '''
                UPDATE public."Mensajes" SET "LEIDO"=TRUE
                WHERE "ID_DESTINATARIO"=%s AND "ID_REMITENTE"=%s
                AND COALESCE("ID_OBJETO", '') = %s AND "LEIDO"=FALSE
                ''',
                (id_usuario, contacto_id, id_objeto),
            )
        else:
            cursor.execute(
                '''
                UPDATE public."Mensajes" SET "LEIDO"=TRUE
                WHERE "ID_DESTINATARIO"=%s AND "ID_REMITENTE"=%s AND "LEIDO"=FALSE
                ''',
                (id_usuario, contacto_id),
            )
        db.commit()
        cursor.close()

    @app.route("/buzon")
    @login_required
    def buzon():
        id_usuario = session.get("id_usuario")
        conversaciones = []
        unread_count = 0
        try:
            db = conectar_db()
            if not db:
                raise RuntimeError("Sin conexión a la base de datos")
            cursor = db.cursor(cursor_factory=RealDictCursor)
            conversaciones = _build_conversations(cursor, id_usuario)
            unread_count = sum(t.get("unread", 0) for t in conversaciones)
            cursor.close()
            db.close()
        except Exception as e:
            print(f"Error cargando buzón: {e}")
        return render_template(
            "buzon.html",
            active="buzon",
            conversaciones=conversaciones,
            unread_count=unread_count,
            id_usuario=id_usuario,
        )


    # -----------------------------
    # API MENSAJERÍA
    # -----------------------------
    def usuario_tiene_reportes(cursor, id_usuario):
        cursor.execute(
            '''
            SELECT 1 FROM public."Reportes_perdidos" WHERE "ID_USUARIO" = %s
            UNION ALL
            SELECT 1 FROM public."Reportes_encontrados" WHERE "ID_USUARIO" = %s
            LIMIT 1
            ''',
            (id_usuario, id_usuario),
        )
        return cursor.fetchone() is not None

    @app.route('/api/mensajes/enviar', methods=['POST'])
    @login_required
    def api_enviar_mensaje():
        try:
            remitente = session.get('id_usuario')
            destinatario = request.form.get('destinatario') or request.form.get('to')
            id_objeto = request.form.get('id_objeto') or request.form.get('objeto')
            reply_to = request.form.get('reply_to') or request.form.get('id_respuesta')
            asunto = request.form.get('asunto') or request.form.get('subject')
            cuerpo = request.form.get('cuerpo') or request.form.get('body')

            if not destinatario or not cuerpo:
                return jsonify({'ok': False, 'error': 'Faltan campos requeridos'}), 400

            db = conectar_db()
            cursor = db.cursor()

            # verificar que el destinatario exista
            cursor.execute('SELECT 1 FROM public."Usuarios" WHERE "ID_USUARIO"=%s', (destinatario,))
            if not cursor.fetchone():
                cursor.close()
                db.close()
                return jsonify({'ok': False, 'error': 'Usuario destinatario no existe'}), 404

            # ambos usuarios deben haber publicado al menos un reporte
            if not usuario_tiene_reportes(cursor, destinatario):
                cursor.close()
                db.close()
                return jsonify({'ok': False, 'error': 'El destinatario no tiene reportes publicados'}), 403

            if not usuario_tiene_reportes(cursor, remitente):
                cursor.close()
                db.close()
                return jsonify({'ok': False, 'error': 'Debes tener al menos un reporte publicado para enviar mensajes'}), 403

            # validar objeto si se proporciona
            if id_objeto:
                cursor.execute('SELECT 1 FROM public."Objetos" WHERE "ID_OBJETO"=%s', (id_objeto,))
                if not cursor.fetchone():
                    cursor.close()
                    db.close()
                    return jsonify({'ok': False, 'error': 'Objeto asociado no válido'}), 400

            # validar respuesta si se proporciona
            id_respuesta = None
            if reply_to:
                try:
                    id_respuesta = int(reply_to)
                except (ValueError, TypeError):
                    id_respuesta = None
                if id_respuesta:
                    cursor.execute(
                        'SELECT "ID_OBJETO", "ID_REMITENTE", "ID_DESTINATARIO" FROM public."Mensajes" WHERE "ID_MENSAJE"=%s',
                        (id_respuesta,),
                    )
                    respuesta_row = cursor.fetchone()
                    if not respuesta_row:
                        cursor.close()
                        db.close()
                        return jsonify({'ok': False, 'error': 'Mensaje al que respondes no existe'}), 400
                    if respuesta_row[1] not in (remitente, destinatario) or respuesta_row[2] not in (remitente, destinatario):
                        cursor.close()
                        db.close()
                        return jsonify({'ok': False, 'error': 'No puedes responder a ese mensaje'}), 403
                    if not id_objeto:
                        id_objeto = respuesta_row[0]

            # insertar mensaje y obtener id
            cursor.execute(
                'INSERT INTO public."Mensajes" ("ID_REMITENTE","ID_DESTINATARIO","ID_OBJETO","ID_RESPUESTA","ASUNTO","CUERPO") VALUES (%s,%s,%s,%s,%s,%s) RETURNING "ID_MENSAJE"',
                (remitente, destinatario, id_objeto, id_respuesta, asunto, cuerpo),
            )
            id_mensaje = cursor.fetchone()[0]

            # manejar archivos adjuntos
            adjuntos = request.files.getlist('adjuntos') or request.files.getlist('files')
            for f in adjuntos:
                if f and f.filename:
                    filename = secure_filename(f.filename)
                    unique = f"{uuid.uuid4()}_{filename}"
                    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                    save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique)
                    f.save(save_path)
                    ruta_rel = f"/uploads/{unique}"
                    cursor.execute(
                        'INSERT INTO public."Adjuntos_mensajes" ("ID_MENSAJE","RUTA","NOMBRE_ORIGINAL","TIPO") VALUES (%s,%s,%s,%s)',
                        (id_mensaje, ruta_rel, filename, f.mimetype),
                    )

            # crear notificación interna para el destinatario
            notif_text = f"Nuevo mensaje de {remitente}: {asunto or '(sin asunto)'}"
            if id_objeto:
                notif_text += f" sobre el objeto {id_objeto}"
            cursor.execute(
                'INSERT INTO public."Notificaciones" ("ID_USUARIO","TIPO","MENSAJE") VALUES (%s,%s,%s)',
                (destinatario, 'mensaje', notif_text),
            )

            db.commit()
            cursor.close()
            db.close()

            return jsonify({'ok': True, 'id_mensaje': id_mensaje})
        except Exception as e:
            print(f"Error enviando mensaje: {e}")
            return jsonify({'ok': False, 'error': str(e)}), 500


    @app.route('/chat/<destinatario_id>/<id_objeto>')
    @login_required
    def chat(destinatario_id, id_objeto):
        id_usuario = session.get('id_usuario')
        if id_usuario == destinatario_id:
            return redirect('/buzon')

        show_all = id_objeto in (None, 'None', 'null', '0', '')
        if show_all:
            id_objeto = None

        db = conectar_db()
        cursor = db.cursor(cursor_factory=RealDictCursor)

        cursor.execute('SELECT "ID_USUARIO" FROM public."Usuarios" WHERE "ID_USUARIO"=%s', (destinatario_id,))
        if not cursor.fetchone():
            cursor.close()
            db.close()
            return redirect('/buzon')

        # comprobar que el destinatario y el usuario actual tienen reportes publicados
        if not usuario_tiene_reportes(cursor, destinatario_id):
            cursor.close()
            db.close()
            return render_template('chat.html', error='El usuario no tiene reportes publicados.', destinatario=None, mensajes=[])

        if not usuario_tiene_reportes(cursor, id_usuario):
            cursor.close()
            db.close()
            return render_template('chat.html', error='Debes tener un reporte publicado para chatear.', destinatario=None, mensajes=[])

        objeto_nombre = None
        objeto_imagen = None
        if not show_all and id_objeto:
            cursor.execute('SELECT "NOMBRE", "IMAGEN" FROM public."Objetos" WHERE "ID_OBJETO"=%s', (id_objeto,))
            objeto_row = cursor.fetchone()
            if not objeto_row:
                cursor.close()
                db.close()
                return render_template('chat.html', error='Objeto asociado no válido.', destinatario=None, mensajes=[])
            objeto_nombre = objeto_row['NOMBRE']
            objeto_imagen = objeto_row['IMAGEN']

        if show_all:
            cursor.execute(
                '''
                SELECT m."ID_MENSAJE", m."ID_REMITENTE", m."ID_DESTINATARIO", m."ID_OBJETO", m."ID_RESPUESTA", m."ASUNTO", m."CUERPO", m."FECHA", m."LEIDO", pr."NOMBRE" as REMITENTE_NOMBRE, pd."NOMBRE" as DESTINATARIO_NOMBRE,
                       rm."CUERPO" as RESPUESTA_CUERPO, rm."ID_REMITENTE" as RESPUESTA_REMITENTE
                FROM public."Mensajes" m
                LEFT JOIN public."Perfiles" pr ON m."ID_REMITENTE" = pr."ID_USUARIO"
                LEFT JOIN public."Perfiles" pd ON m."ID_DESTINATARIO" = pd."ID_USUARIO"
                LEFT JOIN public."Mensajes" rm ON m."ID_RESPUESTA" = rm."ID_MENSAJE"
                WHERE (m."ID_REMITENTE"=%s AND m."ID_DESTINATARIO"=%s)
                   OR (m."ID_REMITENTE"=%s AND m."ID_DESTINATARIO"=%s)
                ORDER BY m."FECHA" ASC
                ''',
                (id_usuario, destinatario_id, destinatario_id, id_usuario),
            )
        else:
            cursor.execute(
                '''
                SELECT m."ID_MENSAJE", m."ID_REMITENTE", m."ID_DESTINATARIO", m."ID_OBJETO", m."ID_RESPUESTA", m."ASUNTO", m."CUERPO", m."FECHA", m."LEIDO", pr."NOMBRE" as REMITENTE_NOMBRE, pd."NOMBRE" as DESTINATARIO_NOMBRE,
                       o."NOMBRE" as OBJETO_NOMBRE, o."IMAGEN" as OBJETO_IMAGEN,
                       rm."CUERPO" as RESPUESTA_CUERPO, rm."ID_REMITENTE" as RESPUESTA_REMITENTE
                FROM public."Mensajes" m
                LEFT JOIN public."Perfiles" pr ON m."ID_REMITENTE" = pr."ID_USUARIO"
                LEFT JOIN public."Perfiles" pd ON m."ID_DESTINATARIO" = pd."ID_USUARIO"
                LEFT JOIN public."Objetos" o ON m."ID_OBJETO" = o."ID_OBJETO"
                LEFT JOIN public."Mensajes" rm ON m."ID_RESPUESTA" = rm."ID_MENSAJE"
                WHERE ((m."ID_REMITENTE"=%s AND m."ID_DESTINATARIO"=%s)
                   OR (m."ID_REMITENTE"=%s AND m."ID_DESTINATARIO"=%s))
                  AND m."ID_OBJETO" = %s
                ORDER BY m."FECHA" ASC
                ''',
                (id_usuario, destinatario_id, destinatario_id, id_usuario, id_objeto),
            )
        mensajes = cursor.fetchall()

        _marcar_mensajes_leidos(db, id_usuario, destinatario_id, None if show_all else id_objeto)

        cursor.execute('SELECT p."NOMBRE" FROM public."Perfiles" p WHERE p."ID_USUARIO"=%s', (destinatario_id,))
        perfil = cursor.fetchone()
        destinatario_nombre = perfil['NOMBRE'] if perfil else destinatario_id
        report_id = request.args.get('report_id')

        cursor.close()
        db.close()

        return render_template(
            'chat.html',
            destinatario_id=destinatario_id,
            destinatario_nombre=destinatario_nombre,
            mensajes=[_serialize_mensaje_row(m) for m in mensajes],
            report_id=report_id,
            id_objeto=id_objeto,
            objeto_nombre=objeto_nombre,
            objeto_imagen=objeto_imagen,
            id_usuario=id_usuario,
        )


    @app.route('/api/mensajes', methods=['GET'])
    @login_required
    def api_listar_mensajes():
        try:
            id_usuario = session.get('id_usuario')
            db = conectar_db()
            if not db:
                return jsonify({'ok': False, 'error': 'Sin conexión a la base de datos'}), 500
            cursor = db.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                '''
                SELECT m."ID_MENSAJE", m."ID_REMITENTE", p."NOMBRE" as REMITENTE_NOMBRE,
                       m."ASUNTO", m."CUERPO", m."FECHA", m."LEIDO"
                FROM public."Mensajes" m
                LEFT JOIN public."Perfiles" p ON m."ID_REMITENTE" = p."ID_USUARIO"
                WHERE m."ID_DESTINATARIO" = %s
                ORDER BY m."FECHA" DESC
                LIMIT 200
                ''',
                (id_usuario,)
            )
            mensajes = [_serialize_mensaje_row(m) for m in cursor.fetchall()]
            cursor.close()
            db.close()
            return jsonify(mensajes)
        except Exception as e:
            print(f"Error listando mensajes: {e}")
            return jsonify([]), 500


    @app.route('/api/mensajes/no-leidos', methods=['GET'])
    @login_required
    def api_mensajes_no_leidos():
        try:
            id_usuario = session.get('id_usuario')
            db = conectar_db()
            if not db:
                return jsonify({'ok': False, 'error': 'Sin conexión a la base de datos'}), 500
            cursor = db.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                'SELECT COUNT(*) as total FROM public."Mensajes" WHERE "ID_DESTINATARIO"=%s AND "LEIDO"=FALSE',
                (id_usuario,),
            )
            total = cursor.fetchone()['total']
            cursor.close()
            db.close()
            return jsonify({'ok': True, 'total': total})
        except Exception as e:
            print(f"Error contando mensajes no leídos: {e}")
            return jsonify({'ok': False, 'total': 0}), 500


    @app.route('/api/conversaciones', methods=['GET'])
    @login_required
    def api_conversaciones():
        try:
            id_usuario = session.get('id_usuario')
            db = conectar_db()
            if not db:
                return jsonify({'ok': False, 'error': 'Sin conexión a la base de datos'}), 500
            cursor = db.cursor(cursor_factory=RealDictCursor)
            thread_list = _build_conversations(cursor, id_usuario)
            cursor.close()
            db.close()
            return jsonify(thread_list)
        except Exception as e:
            print(f"Error listando conversaciones: {e}")
            return jsonify({'ok': False, 'error': str(e)}), 500


    @app.route('/api/conversacion/<destinatario_id>/<id_objeto>', methods=['GET'])
    @login_required
    def api_conversacion(destinatario_id, id_objeto):
        try:
            id_usuario = session.get('id_usuario')
            db = conectar_db()
            if not db:
                return jsonify({'ok': False, 'error': 'Sin conexión a la base de datos'}), 500
            cursor = db.cursor(cursor_factory=RealDictCursor)
            cursor.execute('SELECT "ID_USUARIO" FROM public."Usuarios" WHERE "ID_USUARIO"=%s', (destinatario_id,))
            if not cursor.fetchone():
                cursor.close()
                db.close()
                return jsonify({'ok': False, 'error': 'Contacto no encontrado'}), 404

            if id_objeto in (None, 'None', 'null', '0', ''):
                id_objeto = None

            if id_objeto:
                cursor.execute(
                    '''
                    SELECT m."ID_MENSAJE", m."ID_REMITENTE", m."ID_DESTINATARIO", m."ID_OBJETO", m."ID_RESPUESTA", m."ASUNTO", m."CUERPO", m."FECHA", m."LEIDO",
                           pr."NOMBRE" as REMITENTE_NOMBRE, pd."NOMBRE" as DESTINATARIO_NOMBRE,
                           o."NOMBRE" as OBJETO_NOMBRE,
                           rm."CUERPO" as RESPUESTA_CUERPO, rm."ID_REMITENTE" as RESPUESTA_REMITENTE
                    FROM public."Mensajes" m
                    LEFT JOIN public."Perfiles" pr ON m."ID_REMITENTE" = pr."ID_USUARIO"
                    LEFT JOIN public."Perfiles" pd ON m."ID_DESTINATARIO" = pd."ID_USUARIO"
                    LEFT JOIN public."Objetos" o ON m."ID_OBJETO" = o."ID_OBJETO"
                    LEFT JOIN public."Mensajes" rm ON m."ID_RESPUESTA" = rm."ID_MENSAJE"
                    WHERE ((m."ID_REMITENTE"=%s AND m."ID_DESTINATARIO"=%s)
                       OR (m."ID_REMITENTE"=%s AND m."ID_DESTINATARIO"=%s))
                      AND m."ID_OBJETO" = %s
                    ORDER BY m."FECHA" ASC
                    ''',
                    (id_usuario, destinatario_id, destinatario_id, id_usuario, id_objeto),
                )
            else:
                cursor.execute(
                    '''
                    SELECT m."ID_MENSAJE", m."ID_REMITENTE", m."ID_DESTINATARIO", m."ID_OBJETO", m."ID_RESPUESTA", m."ASUNTO", m."CUERPO", m."FECHA", m."LEIDO",
                           pr."NOMBRE" as REMITENTE_NOMBRE, pd."NOMBRE" as DESTINATARIO_NOMBRE,
                           o."NOMBRE" as OBJETO_NOMBRE,
                           rm."CUERPO" as RESPUESTA_CUERPO, rm."ID_REMITENTE" as RESPUESTA_REMITENTE
                    FROM public."Mensajes" m
                    LEFT JOIN public."Perfiles" pr ON m."ID_REMITENTE" = pr."ID_USUARIO"
                    LEFT JOIN public."Perfiles" pd ON m."ID_DESTINATARIO" = pd."ID_USUARIO"
                    LEFT JOIN public."Objetos" o ON m."ID_OBJETO" = o."ID_OBJETO"
                    LEFT JOIN public."Mensajes" rm ON m."ID_RESPUESTA" = rm."ID_MENSAJE"
                    WHERE (m."ID_REMITENTE"=%s AND m."ID_DESTINATARIO"=%s)
                       OR (m."ID_REMITENTE"=%s AND m."ID_DESTINATARIO"=%s)
                    ORDER BY m."FECHA" ASC
                    ''',
                    (id_usuario, destinatario_id, destinatario_id, id_usuario),
                )
            mensajes = [_serialize_mensaje_row(m) for m in cursor.fetchall()]

            _marcar_mensajes_leidos(db, id_usuario, destinatario_id, id_objeto)

            cursor.close()
            db.close()

            return jsonify({'ok': True, 'mensajes': mensajes})
        except Exception as e:
            print(f"Error obteniendo conversación: {e}")
            return jsonify({'ok': False, 'error': str(e)}), 500


    @app.route('/api/mensajes/<int:id_mensaje>', methods=['GET'])
    @login_required
    def api_ver_mensaje(id_mensaje):
        try:
            id_usuario = session.get('id_usuario')
            db = conectar_db()
            cursor = db.cursor(cursor_factory=RealDictCursor)
            cursor.execute('SELECT * FROM public."Mensajes" WHERE "ID_MENSAJE"=%s', (id_mensaje,))
            mensaje = cursor.fetchone()
            if not mensaje:
                cursor.close()
                db.close()
                return jsonify({'ok': False, 'error': 'Mensaje no encontrado'}), 404

            # sólo destinatario o remitente pueden ver
            if mensaje['ID_DESTINATARIO'] != id_usuario and mensaje['ID_REMITENTE'] != id_usuario:
                cursor.close()
                db.close()
                return jsonify({'ok': False, 'error': 'Acceso denegado'}), 403

            # obtener adjuntos
            cursor.execute('SELECT "ID_ADJUNTO","RUTA","NOMBRE_ORIGINAL","TIPO" FROM public."Adjuntos_mensajes" WHERE "ID_MENSAJE"=%s', (id_mensaje,))
            adjuntos = cursor.fetchall()

            # si quien lo abre es el destinatario, marcar como leído
            if mensaje['ID_DESTINATARIO'] == id_usuario and not mensaje['LEIDO']:
                cursor2 = db.cursor()
                cursor2.execute('UPDATE public."Mensajes" SET "LEIDO"=TRUE WHERE "ID_MENSAJE"=%s', (id_mensaje,))
                db.commit()
                cursor2.close()

            cursor.close()
            db.close()
            return jsonify({'ok': True, 'mensaje': mensaje, 'adjuntos': adjuntos})
        except Exception as e:
            print(f"Error obteniendo mensaje: {e}")
            return jsonify({'ok': False, 'error': str(e)}), 500


    @app.route('/mensaje/adjunto/<int:id_adjunto>')
    @login_required
    def descargar_adjunto(id_adjunto):
        try:
            db = conectar_db()
            cursor = db.cursor()
            cursor.execute('SELECT "RUTA" FROM public."Adjuntos_mensajes" WHERE "ID_ADJUNTO"=%s', (id_adjunto,))
            row = cursor.fetchone()
            cursor.close()
            db.close()
            if not row:
                return 'Adjunto no encontrado', 404
            ruta = row[0]
            # ruta esperada: /uploads/filename
            filename = ruta.split('/')[-1]
            return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
        except Exception as e:
            print(f"Error descargando adjunto: {e}")
            return 'Error', 500


    # -----------------------------
    # NOTIFICACIONES
    # -----------------------------
    @app.route('/api/notificaciones', methods=['GET'])
    @login_required
    def api_listar_notificaciones():
        try:
            id_usuario = session.get('id_usuario')
            db = conectar_db()
            cursor = db.cursor(cursor_factory=RealDictCursor)
            cursor.execute('SELECT "ID_NOTIF","TIPO","MENSAJE","LEIDO","FECHA" FROM public."Notificaciones" WHERE "ID_USUARIO"=%s ORDER BY "FECHA" DESC LIMIT 100', (id_usuario,))
            notifs = cursor.fetchall()
            cursor.close()
            db.close()
            return jsonify(notifs)
        except Exception as e:
            print(f"Error listando notificaciones: {e}")
            return jsonify([]), 500


    @app.route('/api/notificaciones/leer/<int:id_notif>', methods=['POST'])
    @login_required
    def api_marcar_notificacion_leida(id_notif):
        try:
            id_usuario = session.get('id_usuario')
            db = conectar_db()
            cursor = db.cursor()
            cursor.execute('UPDATE public."Notificaciones" SET "LEIDO"=TRUE WHERE "ID_NOTIF"=%s AND "ID_USUARIO"=%s', (id_notif, id_usuario))
            db.commit()
            cursor.close()
            db.close()
            return jsonify({'ok': True})
        except Exception as e:
            print(f"Error marcando notificación: {e}")
            return jsonify({'ok': False, 'error': str(e)}), 500

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
    # RUTA CERRAR SESION
    # -------------------------------------
    @app.route("/logout")
    def logout():
        session.clear()
        return redirect("/inicio")


    # -------------------------------------
    # RUTA CONFIGURACION
    # -------------------------------------


    @app.route("/configuracion")
    @login_required
    def configuracion():
        return render_template(
            "configuracion_user.html",
            active="configuracion"
        )


    @app.route("/admin/configuracion")
    @login_required
    def configuracion_admin():
        if session.get("id_rol") != 2:
            return redirect(url_for("configuracion"))

        return render_template(
            "configuracion_admin.html",
            active="configuracion"
        )

    @app.route("/perfil")
    @login_required
    def perfil():
        return render_template("perfil.html", active="perfil")


    @app.route("/admin/perfil")
    @login_required
    def admin_perfil():
        if session.get("id_rol") != 2:
            return redirect(url_for("perfil"))

        return render_template("admin_perfil.html", active="perfil")