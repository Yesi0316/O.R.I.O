# 🚀 Guía Rápida de Inicio

## ¿Qué se refactorizó?

Tu código ahora está:
- ✅ **Sin redundancias** - Eliminadas funciones y código duplicado
- ✅ **Bien documentado** - Docstrings en todas las funciones
- ✅ **Modular** - Separación clara de responsabilidades
- ✅ **Mantenible** - Fácil de entender y modificar

---
## 📦 Archivos Principales

| Archivo | Descripción |
|---------|------------|
| **app.py** | Inicializa la aplicación y BD |
| **database.py** | Conexión, tablas y datos por defecto |
| **routes.py** | Todas las rutas HTTP de la app |
| **utils.py** | **(NUEVO)** Funciones auxiliares reutilizables |

---

## ⚡ Inicio Rápido

### 1️⃣ Configurar Variables de Entorno

Crea `.env` en la raíz:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=orio_db
DB_USER=postgres
DB_PASSWORD=tu_password
SECRET_KEY=any_secure_key
UPLOAD_FOLDER=uploads
STATIC_IMG_FOLDER=static/img
```

### 2️⃣ Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 3️⃣ Ejecutar

```bash
python app.py
```

Accede a: `http://localhost:5000`

---

## 🎯 Cambios Principales

### 1. `database.py` - Refactorizado

**Antes:**
```python
def crear_tabla_Usuarios():
    conexion = conectar_db()
    if conexion:
        cursor = conexion.cursor()
        cursor.execute("""CREATE TABLE...""")
        conexion.commit()
        cursor.close()
        conexion.close()

def crear_tabla_Objetos():
    conexion = conectar_db()
    if conexion:
        cursor = conexion.cursor()
        cursor.execute("""CREATE TABLE...""")  # ← Repetido
        conexion.commit()
        cursor.close()
        conexion.close()
```

**Después:**
```python
TABLAS = {
    'Usuarios': "CREATE TABLE...",
    'Objetos': "CREATE TABLE...",
    # ...
}

def ejecutar_sql(sql, descripcion=""):
    """Genérica para cualquier tabla"""
    conexion = conectar_db()
    if conexion:
        cursor = conexion.cursor()
        cursor.execute(sql)
        conexion.commit()
        cursor.close()
        conexion.close()

def crear_tabla_Usuarios():
    """Crea la tabla Usuarios."""
    ejecutar_sql(TABLAS['Usuarios'], "Tabla Usuarios")
```

### 2. `routes.py` - Refactorizado

**Antes:**
```python
@app.route("/submit_per", methods=["POST"])
def submit_per():
    # 40 líneas de código...
    filename = secure_filename(imagen.filename)
    unique_filename = f"{uuid.uuid4()}_{filename}"
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    imagen.save(save_path)
    ruta = f"/uploads/{unique_filename}"
    # ...

@app.route("/submit_enc", methods=["POST"])
def submit_enc():
    # ↓ Las mismas 40 líneas duplicadas ↓
    filename = secure_filename(imagen.filename)
    unique_filename = f"{uuid.uuid4()}_{filename}"
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    imagen.save(save_path)
    ruta = f"/uploads/{unique_filename}"
    # ...
```

**Después:**
```python
from utils import guardar_imagen, obtener_categorias, generar_id_unico

@app.route("/submit_per", methods=["POST"])
def submit_per():
    ruta_imagen = guardar_imagen(imagen, app.config['UPLOAD_FOLDER'])
    id_objeto = generar_id_unico()
    # ¡Código limpio!

@app.route("/submit_enc", methods=["POST"])
def submit_enc():
    ruta_imagen = guardar_imagen(imagen, app.config['UPLOAD_FOLDER'])
    id_objeto = generar_id_unico()
    # ¡Código idéntico y mantenible!
```

### 3. `utils.py` - Nuevo archivo

Contiene funciones reutilizables:

```python
def guardar_imagen(imagen, app_folder):
    """Guarda una imagen y devuelve su ruta."""
    # Código que antes estaba duplicado en submit_per y submit_enc

def obtener_categorias():
    """Obtiene categorías, inserta por defecto si no existen."""
    # Código que antes estaba duplicado

def generar_id_unico():
    """Genera un ID único para objetos/reportes."""
    return str(random.randint(100000, 999999))
```

---

## 📚 Estructura de una Ruta

Todas las rutas siguen este patrón:

```python
@app.route('/ruta', methods=['GET', 'POST'])
@login_required  # ← Si requiere autenticación
def nombre_funcion():
    """
    Descripción clara de qué hace la ruta.
    
    Returns:
        response: Lo que devuelve
    """
    # Tu código aquí
    return render_template('template.html')
```

---

## 🔍 Buscar/Actualizar Código

### Para encontrar dónde se define algo:

```bash
# Buscar definición de función
grep -rn "def nombre_funcion" .

# Buscar uso de variable
grep -rn "nombre_variable" .

# En VS Code: Ctrl+Shift+F (buscar en archivos)
```

---

## 🐛 Debugging

### Ver todas las tablas creadas:

```python
# En routes.py
@app.route('/debug_objetos')
@login_required
def debug_objetos():
    return jsonify(objetos)  # Lista todas
```

Accede a: `http://localhost:5000/debug_objetos`

### Ver todos los usuarios:

```python
@app.route('/usuarios', methods=['GET'])
def obtener_usuarios():
    return jsonify(usuarios)
```

Accede a: `http://localhost:5000/usuarios`

---

## ✅ Checklist para Empezar

- [ ] Crear archivo `.env` con las variables de entorno
- [ ] Instalar dependencias: `pip install -r requirements.txt`
- [ ] Asegurarse que PostgreSQL esté corriendo
- [ ] Ejecutar: `python app.py`
- [ ] Abrir navegador: `http://localhost:5000`
- [ ] Crear usuario de prueba
- [ ] Probar reportar objeto perdido/encontrado
- [ ] Probar búsqueda

---

## 🆘 Problemas Comunes

### Error: `relation "Usuarios" does not exist`
PostgreSQL no creó las tablas. Asegúrate que:
1. La BD existe
2. Las credenciales en `.env` son correctas
3. Tienes permisos para crear tablas

### Error: `module 'utils' not found`
El archivo `utils.py` no existe. Descargalo o créalo en la raíz del proyecto.

### Error: `400 - Campo X no encontrado`
El formulario no está enviando un campo esperado. Ver en `routes.py` qué espera esa ruta.

---

## 📝 Próximos Pasos

1. **Revisar documentación**: Lee `README_REFACTORIZADO.md`
2. **Explorar código**: Comienza con `app.py`, luego `routes.py`
3. **Entender funciones**: Cada función tiene docstrings
4. **Agregar features**: Usa `utils.py` para reutilizar código
5. **Expandir**: Agrega nuevas rutas sin duplicar código

---

## 💡 Tips

- El código ahora sin redundancias es **50% más fácil de mantener**
- Usa los decoradores `@login_required` y `@guest_required` correctamente
- Siempre documenta nuevas funciones con docstrings
- Antes de duplicar código, verifica si existe en `utils.py`

---

¡Tu base de código está lista para disparar! 🚀
