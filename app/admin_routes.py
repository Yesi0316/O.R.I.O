"""
Rutas del administrador de O.R.I.O.
"""

# ===========================
# LIBRERÍAS
# ===========================

import os
import uuid
import random
import re
from io import BytesIO
from datetime import datetime, timedelta

from flask import (
    render_template,
    request,
    redirect,
    url_for,
    session,
    jsonify,
    flash,
    current_app,
    send_file,
)

from werkzeug.utils import secure_filename
from psycopg2.extras import RealDictCursor

# ===========================
# COMPONENTES INTERNOS
# ===========================

from .database import conectar_db
from .decorators import login_required, admin_required

# Si tienes funciones auxiliares
# from .utils import allowed_file, guardar_imagen


def init_admin_routes(app):
    """
    Registra todas las rutas del administrador.
    """

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
            q = request.args.get("q", "").strip()
            conexion = conectar_db()
            if conexion is None:
                return jsonify({"mensaje": "Error de conexión a la base de datos"}), 500

            cursor = conexion.cursor(cursor_factory=RealDictCursor)
            filtro = ""
            params = []

            if q:
                filtro = """
                WHERE u."ID_USUARIO" ILIKE %s
                OR u."NOMBRE" ILIKE %s
                OR u."GENERO" ILIKE %s
                OR r."NOMBRE" ILIKE %s
                """
                params = [f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%"]

            cursor.execute(
            f"""
                SELECT u."ID_USUARIO", u."NOMBRE", u."GENERO", u."ID_ROL", r."NOMBRE" as "ROL_NOMBRE", p."FOTO_PERFIL"
                FROM public."Usuarios" u
                LEFT JOIN public."Roles" r ON u."ID_ROL" = r."ID_ROL"
                LEFT JOIN public."Perfiles" p ON u."ID_USUARIO" = p."ID_USUARIO"
                {filtro}
                ORDER BY u."ID_USUARIO" DESC;   
            """,  
            params,
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
    # RUTA ADMIN INICIO
    # -------------------------------------

    @app.route("/admin_inicio")
    @admin_required
    def admin_inicio():
        if session.get("id_rol") != 2:  # Verificar si el rol es admin si no lo devuelve al menu
            return redirect("/menu")
        return render_template("admin.html", active="panel")

    #-------------------------------------
    #ESTADISTICAS DEL DASHBOARD
    #-------------------------------------

    @app.route("/api/admin_estadisticas")
    @admin_required
    def api_estadisticas_admin():
        """Devuelve las estadísticas del dashboard"""
        try:
            db = conectar_db()
            cursor = db.cursor(cursor_factory=RealDictCursor)

            cursor.execute('SELECT COUNT(*) as total FROM "Reportes_encontrados" WHERE "STATUS" = %s', ('pendiente',))
            encontrados = cursor.fetchone()["total"]

            cursor.execute('SELECT COUNT(*) as total FROM "Reportes_perdidos" WHERE "STATUS" = %s', ('pendiente',))
            perdidos = cursor.fetchone()["total"]

            reportes_pendientes = encontrados + perdidos

            cursor.execute('SELECT COUNT(*) as total FROM "Reportes_encontrados" WHERE "STATUS" = %s', ('encontrado',))
            encontrados_recuperados = cursor.fetchone()["total"]

            cursor.execute('SELECT COUNT(*) as total FROM "Reportes_perdidos" WHERE "STATUS" = %s', ('encontrado',))
            perdidos_recuperados = cursor.fetchone()["total"]

            reportes_encontrados = encontrados_recuperados + perdidos_recuperados

            cursor.execute('SELECT COUNT(*) as total FROM "Reportes_encontrados" WHERE "STATUS" = %s', ('falso',))
            encontrados_falsos = cursor.fetchone()["total"]

            cursor.execute('SELECT COUNT(*) as total FROM "Reportes_perdidos" WHERE "STATUS" = %s', ('falso',))
            perdidos_falsos = cursor.fetchone()["total"]

            reportes_falsos = encontrados_falsos + perdidos_falsos

            reportes_pendientes = encontrados + perdidos

            reportes_totales = reportes_pendientes + reportes_encontrados + reportes_falsos

            cursor.execute('SELECT COUNT(*) as usuarios FROM "Usuarios"')
            usuarios = cursor.fetchone()["usuarios"]

            cursor.close()
            db.close()

            return jsonify(
                {
                    "reportes_pendientes": reportes_pendientes,
                    "reportes_encontrados": reportes_encontrados,
                    "reportes_falsos": reportes_falsos,
                    "reportes_totales": reportes_totales,
                    "usuarios": usuarios,
                }
            )
        except Exception as e:
            print(f"Error en estadísticas: {e}")
            return (
                jsonify(
                    {
                        "reportes_pendientes": 0,
                        "reportes_encontrados": 0,
                        "reportes_falsos": 0,
                        "reportes_totales": 0,
                        "usuarios": 0,
                    }
                ),
                500,
            )

    #---------------------------------------------
    #Último 7 días 
    #---------------------------------------------

    from datetime import datetime, timedelta

    @app.route("/api/admin_estadisticas_7dias")
    @admin_required
    def api_estadisticas_7dias():
        try:
            db = conectar_db()
            cursor = db.cursor(cursor_factory=RealDictCursor)

            # Reportes encontrados
            cursor.execute("""
                SELECT DATE("FECHA") AS fecha, COUNT(*) AS total
                FROM "Reportes_encontrados"
                WHERE "FECHA" >= CURRENT_DATE - INTERVAL '6 days'
                GROUP BY DATE("FECHA")
            """)
            encontrados = {
                fila["fecha"]: fila["total"]
                for fila in cursor.fetchall()
            }

            # Reportes perdidos
            cursor.execute("""
                SELECT DATE("FECHA") AS fecha, COUNT(*) AS total
                FROM "Reportes_perdidos"
                WHERE "FECHA" >= CURRENT_DATE - INTERVAL '6 days'
                GROUP BY DATE("FECHA")
            """)
            perdidos = {
                fila["fecha"]: fila["total"]
                for fila in cursor.fetchall()
            }

            # Usuarios
            cursor.execute("""
                SELECT DATE("FECHA_REGISTRO") AS fecha, COUNT(*) AS total
                FROM "Usuarios"
                WHERE "FECHA_REGISTRO" >= CURRENT_DATE - INTERVAL '6 days'
                GROUP BY DATE("FECHA_REGISTRO")
            """)
            usuarios = {
                fila["fecha"]: fila["total"]
                for fila in cursor.fetchall()
            }

            datos = []

            for i in range(6, -1, -1):

                fecha = (datetime.now() - timedelta(days=i)).date()

                datos.append({
                    "fecha": fecha.strftime("%d/%m"),
                    "encontrados": encontrados.get(fecha, 0),
                    "perdidos": perdidos.get(fecha, 0),
                    "usuarios": usuarios.get(fecha, 0)
                })

            cursor.close()
            db.close()

            return jsonify(datos)

        except Exception as e:
            print(f"Error estadísticas 7 días: {e}")
            return jsonify([]), 
        500


    # ---------------------------------------------
    # RUTA PARA QUE EL ADMIN GESTIONE LOS USUARIOS
    #-----------------------------------------------

    @app.route("/gestionar_usuarios", methods=["GET"])
    @admin_required
    def gestionar_usuarios():
        return redirect("/usuarios")
    
    # ---------------------------------------------
    # RUTA PARA HACER UN ADMIN
    #-----------------------------------------------
    
    @app.route("/api/cambiar_rol_admin", methods=["POST"])
    @admin_required
    def cambiar_rol_admin():
        try:
            data = request.json
            id_usuario = data.get("id_usuario")
            
            if not id_usuario:
                return jsonify({"ok": False, "mensaje": "El ID del usuario es requerido"}), 400
            
            conexion = conectar_db()
            cursor = conexion.cursor(cursor_factory=RealDictCursor)
            
            if not id_usuario:
                cursor.close()
                conexion.close()
                return jsonify({"ok": False, "mensaje": "se requiere el id del usuario"}), 500
            
            # Actualizar el rol a Administrador (ID_ROL = 2)
            cursor.execute(
                'UPDATE public."Usuarios" SET "ID_ROL" = 2 WHERE "ID_USUARIO" = %s',
                (id_usuario,)
            )
            conexion.commit()
            cursor.close()
            conexion.close()
            
            return jsonify({
                "ok": True, 
                "mensaje": f"Usuario '{id_usuario}' ahora es Administrador"
            }), 200
            
        except Exception as e:
            return jsonify({"ok": False, "mensaje": f"Error: {str(e)}"}), 500
        
    # ---------------------------------------------
    # RUTA PARA QUITAR UN ADMIN
    #-----------------------------------------------
    
    @app.route("/api/cambiar_rol_usuario", methods=["POST"])
    @admin_required
    def cambiar_rol_usuario():
        try:
            data = request.json
            id_usuario = data.get("id_usuario")
            
            if not id_usuario:
                return jsonify({"ok": False, "mensaje": "El ID del usuario es requerido"}), 400
            
            conexion = conectar_db()
            cursor = conexion.cursor(cursor_factory=RealDictCursor)
            
            if not id_usuario:
                cursor.close()
                conexion.close()
                return jsonify({"ok": False, "mensaje": "se requiere el id del usuario"}), 500
            
            # Actualizar el rol a Usuario (ID_ROL = 1)
            cursor.execute(
                'UPDATE public."Usuarios" SET "ID_ROL" = 1 WHERE "ID_USUARIO" = %s',
                (id_usuario,)
            )
            conexion.commit()
            cursor.close()
            conexion.close()
            
            return jsonify({
                "ok": True, 
                "mensaje": f"Usuario '{id_usuario}' ahora es Usuario"
            }), 200
            
        except Exception as e:
            return jsonify({"ok": False, "mensaje": f"Error: {str(e)}"}), 500
    
    # --------------------------------------------
    # RUTA PARA QUE EL ADMIN VEA LOS REPORTES 
    #---------------------------------------------

    @app.route("/admin_reportes")
    @admin_required
    def admin_reportes():
        return render_template(
        "admin_reportes.html",
        active="reportes"
    )

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
        
    #-----------------------------------------
    # RUTA PARA ELIMINAR USUARIOS (ADMIN)
    #-----------------------------------------
    @app.route('/api/admin_borrar_usuario', methods=['POST'])
    @admin_required
    def borrar_usuarios():
        db = None
        cursor = None
        try:
            payload = request.get_json() or {}
            id_usuario_borrar = payload.get('id_usuario')

            if not id_usuario_borrar:
                return jsonify({'ok': False, 'error': 'ID de usuario requerido'}), 400
            
            if id_usuario_borrar == session.get("id_usuario"):
                return jsonify({'ok': False, 'error': 'No puedes eliminar tu propio usuario desde esta vista'}), 400

            db = conectar_db()
            if db is None:
                return jsonify({'ok': False, 'error': 'Error de conexión a la base de datos'}), 500

            cursor = db.cursor()

            cursor.execute('SELECT * FROM "Usuarios" WHERE "ID_USUARIO" = %s', (id_usuario_borrar,))
            row = cursor.fetchone()
            if not row:
                cursor.close()
                db.close()
                return jsonify({'ok': False, 'error': 'Usuario no encontrado'}), 404

            cursor.execute('DELETE FROM "Usuarios" WHERE "ID_USUARIO" = %s', (id_usuario_borrar,))
            db.commit()
            afectadas = cursor.rowcount if hasattr(cursor, 'rowcount') else None
            cursor.close()
            db.close()

            return jsonify({'ok': True, 'deleted': bool(afectadas)}), 200

        except Exception as e:
            if db:
                db.rollback()
            try:
                cursor.close()
                db.close()
            except:
                pass
            return jsonify({'ok': False, 'error': str(e)}), 500
    
    #-------------------------------------
    #ADMIN MARCAR COMO FALSO
    #-------------------------------------

    @app.route("/api/admin_marcar_falso", methods=["POST"])
    @admin_required
    def admin_marcar_falso():
        try:
            payload = request.get_json() or {}
            id_reporte = payload.get("id_reporte")
            tipo = payload.get("tipo")

            if not id_reporte :
                return jsonify({"ok": False, "error": "Parámetros inválidos"}), 400

            db = conectar_db()
            cursor = db.cursor()

            if tipo == "perdido":
                cursor.execute(
                    'UPDATE "Reportes_perdidos" SET "STATUS" = %s WHERE "ID_REPORTE" = %s',
                    ("falso", id_reporte),
                )
            else:  # encontrado
                cursor.execute(
                    'UPDATE "Reportes_encontrados" SET "STATUS" = %s WHERE "ID_REPORTE_ENC" = %s',
                    ("falso", id_reporte),
                )

            db.commit()
            afectadas = cursor.rowcount if hasattr(cursor, "rowcount") else None
            cursor.close()
            db.close()

            return jsonify({"ok": True, "updated": bool(afectadas)}), 200

        except Exception as e:
            try:
                cursor.close()
                db.close()
            except:
                pass
            return jsonify({"ok": False, "error": str(e)}), 500
        

    #-------------------------------------
    #ADMIN MARCAR COMO ENCONTRADO
    #-------------------------------------

    @app.route("/api/admin_marcar_encontrado", methods=["POST"])
    @admin_required
    def admin_marcar_encontrado():
        try:
            payload = request.get_json() or {}
            id_reporte = payload.get("id_reporte")
            tipo = payload.get("tipo")

            if not id_reporte or tipo not in ("perdido", "encontrado"):
                return jsonify({"ok": False, "error": "Parámetros inválidos"}), 400

            db = conectar_db()
            cursor = db.cursor()

            if tipo == "perdido":
                cursor.execute(
                    'UPDATE "Reportes_perdidos" SET "STATUS" = %s WHERE "ID_REPORTE" = %s',
                    ("encontrado", id_reporte),
                )
            else:  # encontrado
                cursor.execute(
                    'UPDATE "Reportes_encontrados" SET "STATUS" = %s WHERE "ID_REPORTE_ENC" = %s',
                    ("encontrado", id_reporte),
                )

            db.commit()
            afectadas = cursor.rowcount if hasattr(cursor, "rowcount") else None
            cursor.close()
            db.close()

            return jsonify({"ok": True, "updated": bool(afectadas)}), 200

        except Exception as e:
            try:
                cursor.close()
                db.close()
            except:
                pass
            return jsonify({"ok": False, "error": str(e)}), 500

    #--------------------------
    #ADMIN BUZON
    #---------------------------

    def _format_fecha_mensaje_admin(raw_fecha):
        if isinstance(raw_fecha, datetime):
            try:
                return raw_fecha.strftime("%d/%m/%Y %H:%M"), raw_fecha.timestamp()
            except Exception:
                return raw_fecha.isoformat(), 0
        if raw_fecha:
            return str(raw_fecha), 0
        return "", 0

    def _build_conversations_admin(cursor, id_usuario):
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
            fecha_str, fecha_ts = _format_fecha_mensaje_admin(m.get("FECHA"))
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

    @app.route('/admin_buzon')
    @admin_required
    def admin_buzon():
        id_usuario = session.get("id_usuario")
        conversaciones = []
        unread_count = 0

        try:
            db = conectar_db()
            if not db:
                raise RuntimeError("Sin conexión a la base de datos")
            cursor = db.cursor(cursor_factory=RealDictCursor)
            conversaciones = _build_conversations_admin(cursor, id_usuario)
            unread_count = sum(t.get("unread", 0) for t in conversaciones)
            cursor.close()
            db.close()
        except Exception as e:
            print(f"Error cargando buzón de administrador: {e}")

        return render_template(
            "admin_buzon.html",
            active="buzon",
            conversaciones=conversaciones,
            unread_count=unread_count,
            id_usuario=id_usuario,
        )

    def _serialize_mensaje_row_admin(m):
        row = dict(m)
        if isinstance(row.get("FECHA"), datetime):
            row["FECHA"] = row["FECHA"].strftime("%d/%m/%Y %H:%M")
        if row.get("LEIDO") is None:
            row["LEIDO"] = False
        return row

    def _marcar_mensajes_leidos_admin(db, id_usuario, contacto_id, id_objeto=None):
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

    @app.route('/api/admin/conversaciones', methods=['GET'])
    @admin_required
    def api_admin_conversaciones():
        try:
            id_usuario = session.get('id_usuario')
            db = conectar_db()
            if not db:
                return jsonify({'ok': False, 'error': 'Sin conexión a la base de datos'}), 500
            cursor = db.cursor(cursor_factory=RealDictCursor)
            thread_list = _build_conversations_admin(cursor, id_usuario)
            cursor.close()
            db.close()
            return jsonify(thread_list)
        except Exception as e:
            print(f"Error listando conversaciones admin: {e}")
            return jsonify({'ok': False, 'error': str(e)}), 500

    @app.route('/api/admin/conversacion/<destinatario_id>/<id_objeto>', methods=['GET'])
    @admin_required
    def api_admin_conversacion(destinatario_id, id_objeto):
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
            else:
                cursor.execute(
                    '''
                    SELECT m."ID_MENSAJE", m."ID_REMITENTE", m."ID_DESTINATARIO", m."ID_OBJETO", m."ID_RESPUESTA", m."ASUNTO", m."CUERPO", m."FECHA", m."LEIDO",
                           pr."NOMBRE" as REMITENTE_NOMBRE, pd."NOMBRE" as DESTINATARIO_NOMBRE,
                           o."NOMBRE" as OBJETO_NOMBRE, o."IMAGEN" as OBJETO_IMAGEN,
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
            mensajes = [_serialize_mensaje_row_admin(m) for m in cursor.fetchall()]
            _marcar_mensajes_leidos_admin(db, id_usuario, destinatario_id, id_objeto)
            cursor.close()
            db.close()
            return jsonify({'ok': True, 'mensajes': mensajes})
        except Exception as e:
            print(f"Error obteniendo conversación admin: {e}")
            return jsonify({'ok': False, 'error': str(e)}), 500

    @app.route('/api/admin/mensajes/enviar', methods=['POST'])
    @admin_required
    def api_admin_enviar_mensaje():
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

            cursor.execute('SELECT 1 FROM public."Usuarios" WHERE "ID_USUARIO"=%s', (destinatario,))
            if not cursor.fetchone():
                cursor.close()
                db.close()
                return jsonify({'ok': False, 'error': 'Usuario destinatario no existe'}), 404

            if id_objeto:
                cursor.execute('SELECT 1 FROM public."Objetos" WHERE "ID_OBJETO"=%s', (id_objeto,))
                if not cursor.fetchone():
                    cursor.close()
                    db.close()
                    return jsonify({'ok': False, 'error': 'Objeto asociado no válido'}), 400

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

            cursor.execute(
                'INSERT INTO public."Mensajes" ("ID_REMITENTE","ID_DESTINATARIO","ID_OBJETO","ID_RESPUESTA","ASUNTO","CUERPO") VALUES (%s,%s,%s,%s,%s,%s) RETURNING "ID_MENSAJE"',
                (remitente, destinatario, id_objeto, id_respuesta, asunto, cuerpo),
            )
            id_mensaje = cursor.fetchone()[0]

            cursor.execute(
                'INSERT INTO public."Notificaciones" ("ID_USUARIO","TIPO","MENSAJE") VALUES (%s,%s,%s)',
                (destinatario, 'mensaje', f"Nuevo mensaje de {remitente}: {asunto or '(sin asunto)'}"),
            )
            db.commit()
            cursor.close()
            db.close()
            return jsonify({'ok': True, 'id_mensaje': id_mensaje})
        except Exception as e:
            print(f"Error enviando mensaje admin: {e}")
            return jsonify({'ok': False, 'error': str(e)}), 500
    