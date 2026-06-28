from functools import wraps
from flask import session, request, jsonify, redirect, url_for

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "id_usuario" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"ok": False, "error": "No autenticado"}), 401
            return redirect("/inicio")
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "id_usuario" not in session:
            return redirect("/inicio")

        if session.get("id_rol") != 2:
            return redirect("/menu")

        return f(*args, **kwargs)
    return decorated_function


def guest_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "id_usuario" in session:
            if session.get("id_rol") == 2:
                return redirect(url_for("admin_inicio"))
            return redirect(url_for("menu"))
        return f(*args, **kwargs)
    return decorated_function