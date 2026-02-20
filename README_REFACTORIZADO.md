# Sistema de Gestión de Objetos Perdidos/Encontrados

Aplicación web Flask para reportar, buscar y gestionar objetos perdidos y encontrados.

---

## 📁 Estructura del Proyecto

```
.
├── app.py                       # Punto de entrada de la aplicación
├── database.py                  # Configuración y operaciones de BD
├── routes.py                    # Todas las rutas HTTP de la aplicación
├── utils.py                     # Funciones utilitarias reutilizables
├── requirements.txt             # Dependencias de Python
├── docker-compose.yml           # Configuración Docker
├── .env                         # Variables de entorno (no incluir en Git)
│
├── templates/                   # Plantillas HTML (Jinja2)
│   ├── base.html               # Plantilla base
│   ├── index.html              # Página de inicio
│   ├── inicio.html             # Login
│   ├── registro.html           # Registro
│   ├── recuperar.html          # Recuperación de contraseña
│   ├── menu.html               # Menú principal (autenticado)
│   ├── perfil.html             # Perfil de usuario
│   ├── dashboard.html          # Panel de estadísticas
│   ├── form_perdido.html       # Formulario: reportar objeto perdido
│   ├── form_encontrado.html    # Formulario: reportar objeto encontrado
│   ├── busquedas.html          # Resultados de búsqueda
│   ├── detalles_reportes.html  # Detalles de un objeto
│   └── ...
│
├── static/                      # Archivos estáticos
│   ├── css/                    # Estilos CSS
│   │   ├── global.css
│   │   └── perfil.css
│   ├── js/                     # Scripts JavaScript
│   │   └── modo_claro.js
│   └── img/                    # Imágenes
│
├── uploads/                     # Carpeta de uploads (ignorada en Git)
│   └── [imágenes subidas]
│
└── Data Base/
    └── ORIO_DB.sql            # Script SQL de respaldo
```

---

## 🚀 Instalación y Ejecución

### 1. Requisitos Previos

- Python 3.8+
- PostgreSQL 12+
- Docker y Docker Compose (opcional)

### 2. Configuración

Crea un archivo `.env` en la raíz del proyecto:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=orio_db
DB_USER=postgres
DB_PASSWORD=tu_contraseña
SECRET_KEY=tu_clave_secreta_muy_segura
UPLOAD_FOLDER=uploads
STATIC_IMG_FOLDER=static/img
```

### 3. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 4. Ejecutar la Aplicación

```bash
python app.py
```

La aplicación se ejecutará en `http://0.0.0.0:5000`

### 5. Con Docker Compose

```bash
docker-compose up -d
```

---

## 📋 Módulos Principales

### `app.py`
- Inicializa la aplicación Flask
- Crea las tablas de la base de datos
- Inserta datos por defecto
- Inicia el servidor

### `database.py`
Gestiona toda la conexión e inicialización de la BD:
- Función `conectar_db()`: crea conexiones seguras a PostgreSQL
- `crear_tablas()`: crea todas las tablas si no existen
- `inicializar_datos_default()`: inserta categorías y estados por defecto
- Constantes: `CATEGORIAS_DEFAULT` y `ESTADOS_DEFAULT`

**Tablas creadas:**
- `Usuarios`: datos de usuarios registrados
- `Objetos`: objetos reportados
- `Reportes_perdidos`: reportes de objetos perdidos
- `Reportes_encontrados`: reportes de objetos encontrados
- `Categorias`: categorías de objetos
- `Estados`: estados de los objetos
- Y más (Paises, Departamentos, Ciudades, Roles, Tipos_identificaciones)

### `routes.py`
Define todas las rutas HTTP, organizadas en secciones:

#### Rutas Públicas
- `GET /` - Página de inicio
- `GET /detalles/<id_objeto>` - Detalles de un objeto

#### Autenticación
- `GET/POST /registro` - Registro de usuario
- `POST /guardar_usuario` - Guardar nuevo usuario
- `GET/POST /inicio` - Login
- `POST /logout` - Logout
- `GET/POST /recuperar` - Recuperación de contraseña (paso 1)
- `POST /recuperar_respuestas` - Recuperación de contraseña (paso 2)

#### Búsquedas
- `GET /busquedas` - Búsqueda por filtros
- `GET /buscar_objetos` - Búsqueda avanzada (requiere login)
- `GET /usuarios` - API para obtener usuarios (debug)

#### Reportes - Objeto Perdido
- `GET/POST /formulario_perdido` - Formulario
- `POST /submit_per` - Enviar reporte

#### Reportes - Objeto Encontrado
- `GET/POST /formulario_objeto_encontrado` - Formulario
- `POST /submit_enc` - Enviar reporte

#### Privadas (requieren login)
- `GET /menu` - Menú principal
- `GET /perfil` - Perfil del usuario
- `GET /dashboard` - Panel de estadísticas
- `GET /reportes` - Página de reportes
- `GET /configuracion` - Configuración

#### Archivos
- `GET /uploads/<filename>` - Descargar archivo subido

### `utils.py`
Funciones auxiliares reutilizables:

```python
# Imágenes
guardar_imagen(imagen, app_folder)  # Guarda y devuelve ruta

# Base de Datos
obtener_categorias()                # Obtiene o crea categorías
obtener_estados()                   # Obtiene o crea estados
garantizar_categoria_existe(cat)    # Verifica/inserta categoría
garantizar_estado_existe(est)       # Verifica/inserta estado
generar_id_unico()                  # Genera ID para objetos/reportes
```

---

## 🔒 Seguridad

- ✅ Contraseñas encriptadas con `werkzeug.security`
- ✅ Preguntas de seguridad hasheadas
- ✅ Validación de entrada (espacios, campos obligatorios)
- ✅ Protección de rutas con decoradores `@login_required` y `@guest_required`
- ✅ Nombres de archivo sanitizados con `secure_filename`
- ✅ UUIDs para evitar colisiones de archivos

---

## 🗄️ Base de Datos

### Diagrama de Relaciones

```
Usuarios
  └─── Reportes_perdidos ──── Objetos ──── Categorias
  └─── Reportes_encontrados ─┘         └─── Estados
```

### Ejemplo de Inserción

```python
# El código se encarga automáticamente de crear tablas e insertar datos
python app.py  # ¡Listo!
```

---

## 🌍 Decoradores de Autenticación

### `@login_required`
Redirige a `/inicio` si el usuario no está autenticado.

```python
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')
```

### `@guest_required`
Redirige a `/menu` si el usuario YA está autenticado.
Usado en login, registro, recuperación de contraseña.

```python
@app.route('/registro')
@guest_required
def registro():
    return render_template('registro.html')
```

---

## 📝 Mejoras Realizadas

### Antes (Código Redundante)
- ❌ Función `crear_tabla_X()` repetida 11 veces
- ❌ Listas `categorias_default` y `estados_default` duplicadas
- ❌ `submit_per()` y `submit_enc()` con ~60% de código duplicado
- ❌ Lógica de inserción de categorías/estados repetida
- ❌ Sin documentación de funciones

### Después (Código Limpio)
- ✅ Diccionario centralizado `TABLAS` con definiciones SQL
- ✅ Función genérica `ejecutar_sql()` para cualquier tabla
- ✅ Constantes `CATEGORIAS_DEFAULT` y `ESTADOS_DEFAULT` en `database.py`
- ✅ Función `garantizar_categoria_existe()` y `garantizar_estado_existe()`
- ✅ `utils.py` con funciones reutilizables
- ✅ Documentación completa con docstrings

---

## 🛠️ Desarrollo

### Agregar Nueva Ruta

```python
@app.route('/nueva_ruta')
@login_required  # Si requiere autenticación
def nueva_funcion():
    """Descripción de la ruta."""
    db = conectar_db()
    cursor = db.cursor(cursor_factory=RealDictCursor)
    # Tu código aquí
    cursor.close()
    db.close()
    return render_template('template.html')
```

### Agregar Nueva Tabla

```python
# En database.py, agregar a TABLAS:
TABLAS = {
    'MiTabla': """
        CREATE TABLE IF NOT EXISTS public."MiTabla"(
            "ID" TEXT PRIMARY KEY,
            "NOMBRE" TEXT NOT NULL
        );
    """
}

# Luego crear función wrapper:
def crear_tabla_MiTabla():
    """Crea la tabla MiTabla."""
    ejecutar_sql(TABLAS['MiTabla'], "Tabla MiTabla")
```

---

## 📚 Referencias

- [Flask Documentation](https://flask.palletsprojects.com/)
- [PostgreSQL](https://www.postgresql.org/)
- [psycopg2](https://www.psycopg.org/)
- [Werkzeug Security](https://werkzeug.palletsprojects.com/en/2.1.x/utils/#module-werkzeug.security)

---

## 📄 Licencia

Este proyecto es de código abierto. Úsalo libremente.

---

## ✨ Notas Finales

- **Base sólida:** El código está limpio y bien documentado para futuros desarrollos
- **Fácil mantener:** Sin redundancias innecesarias
- **Escalable:** Estructura modular para agregar nuevas funcionalidades
- **Seguro:** Implementa mejores prácticas de seguridad

¡Feliz codificación! 🚀
