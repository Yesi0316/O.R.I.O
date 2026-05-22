# 📋 MÓDULO DE REPORTES - GUÍA DE IMPLEMENTACIÓN

## ✅ CAMBIOS REALIZADOS

### 1. **Documento SQL** 
📄 Archivo: `CONSULTAS_REPORTES.md`
- Contiene todas las consultas SQL necesarias
- Incluye ejemplos de filtros por categoría, fecha y combinados
- Ejemplo de uso en Python/Flask

### 2. **API Backend Mejorada**
📍 Archivo: `app/routes.py`

#### Endpoint: `/api/mis_reportes` (GET)
**Descripción:** Obtiene los reportes del usuario autenticado

**Parámetros opcionales:**
```
?categoria=Documentos&fecha_inicio=2024-01-01&fecha_fin=2024-12-31
```

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `categoria` | string | ID de la categoría para filtrar |
| `fecha_inicio` | date | Fecha inicio (YYYY-MM-DD) |
| `fecha_fin` | date | Fecha fin (YYYY-MM-DD) |

**Respuesta Exitosa:**
```json
{
  "ok": true,
  "datos": [
    {
      "id_reporte": "uuid",
      "tipo": "perdido|encontrado",
      "ID_OBJETO": "uuid",
      "NOMBRE": "Nombre del objeto",
      "COLOR": "Color",
      "IMAGEN": "URL de imagen",
      "FECHA": "2024-12-21",
      "OBSERVACIONES": "Detalles",
      "categoria": "ID",
      "nombre_categoria": "Nombre de categoría"
    }
  ]
}
```

#### Endpoint: `/api/categorias` (GET)
**Descripción:** Obtiene todas las categorías disponibles

**Respuesta:**
```json
{
  "ok": true,
  "datos": [
    {
      "ID_CATEGORIA": "Documentos",
      "NOMBRE": "Documentos"
    },
    ...
  ]
}
```

### 3. **Frontend Actualizado**
📄 Archivo: `app/templates/mis_reportes.html`

**Nuevas características:**
- ✅ Búsqueda por nombre/color
- ✅ Filtro por tipo (Perdido/Encontrado)
- ✅ Filtro por categoría
- ✅ **Filtro por fecha** (rango de fechas) - 🆕
- ✅ Botón "Limpiar filtros"
- ✅ Muestra nombre de categoría
- ✅ Muestra fecha en formato local
- ✅ Muestra color del objeto
- ✅ Botones: Ver detalles y Borrar

**UI Mejorada:**
- Filtros organizados en filas
- Estilos mejorados para inputs de fecha
- Respuesta dinámica a cambios de filtros
- Mensajes claros cuando no hay resultados

---

## 🚀 CÓMO USAR

### Acceder a la página
```
http://localhost:5000/reportes
```

### Filtrar reportes
1. **Por búsqueda:** Escribe en "Buscar por nombre o color..."
2. **Por tipo:** Selecciona "Todos los tipos", "Perdido" o "Encontrado"
3. **Por categoría:** Selecciona una categoría del dropdown
4. **Por fecha:** Elige fecha inicio y/o fecha fin
5. **Limpiar:** Click en "Limpiar filtros"

### Desde JavaScript
```javascript
// Obtener reportes sin filtros
fetch('/api/mis_reportes')
  .then(r => r.json())
  .then(data => console.log(data.datos));

// Con filtros
fetch('/api/mis_reportes?categoria=Documentos&fecha_inicio=2024-01-01&fecha_fin=2024-12-31')
  .then(r => r.json())
  .then(data => console.log(data.datos));

// Obtener categorías
fetch('/api/categorias')
  .then(r => r.json())
  .then(data => console.log(data.datos));
```

---

## 📊 ESTRUCTURA DE DATOS

### Tabla: Reportes_perdidos
```sql
ID_REPORTE (PK)
FECHA (DATE)
OBSERVACIONES (TEXT)
ID_OBJETO (FK → Objetos)
ID_USUARIO (FK → Usuarios)
FICHA (INTEGER)
ID_CATEGORIA (FK → Categorias)
```

### Tabla: Reportes_encontrados
```sql
ID_REPORTE_ENC (PK)
FECHA (DATE)
OBSERVACIONES (TEXT)
ID_OBJETO (FK → Objetos)
ID_USUARIO (FK → Usuarios)
FICHA (INTEGER)
ID_CATEGORIA (FK → Categorias)
```

---

## 🔧 EJEMPLO DE INTEGRACIÓN

### Crear un componente React (opcional)
```jsx
import { useState, useEffect } from 'react';

export default function MisReportes() {
  const [reportes, setReportes] = useState([]);
  const [categorias, setCategorias] = useState([]);
  const [filtros, setFiltros] = useState({
    categoria: '',
    fecha_inicio: '',
    fecha_fin: ''
  });

  useEffect(() => {
    cargarCategorias();
    cargarReportes();
  }, []);

  const cargarCategorias = async () => {
    const res = await fetch('/api/categorias');
    const data = await res.json();
    setCategorias(data.datos || []);
  };

  const cargarReportes = async () => {
    const params = new URLSearchParams(filtros);
    const res = await fetch(`/api/mis_reportes?${params}`);
    const data = await res.json();
    setReportes(data.datos || []);
  };

  const handleFiltroChange = (e) => {
    const { name, value } = e.target;
    setFiltros(prev => ({ ...prev, [name]: value }));
  };

  useEffect(() => {
    cargarReportes();
  }, [filtros]);

  return (
    <div>
      <h1>Mis Reportes</h1>
      
      <div className="filtros">
        <select name="categoria" value={filtros.categoria} onChange={handleFiltroChange}>
          <option value="">Todas las categorías</option>
          {categorias.map(cat => (
            <option key={cat.ID_CATEGORIA} value={cat.ID_CATEGORIA}>
              {cat.NOMBRE}
            </option>
          ))}
        </select>

        <input 
          type="date" 
          name="fecha_inicio" 
          value={filtros.fecha_inicio} 
          onChange={handleFiltroChange}
          placeholder="Desde"
        />

        <input 
          type="date" 
          name="fecha_fin" 
          value={filtros.fecha_fin} 
          onChange={handleFiltroChange}
          placeholder="Hasta"
        />
      </div>

      <div className="reportes">
        {reportes.map(reporte => (
          <div key={reporte.id_reporte} className="reporte-card">
            <h3>{reporte.NOMBRE}</h3>
            <p>Tipo: {reporte.tipo}</p>
            <p>Categoría: {reporte.nombre_categoria}</p>
            <p>Fecha: {new Date(reporte.FECHA).toLocaleDateString()}</p>
            <p>{reporte.OBSERVACIONES}</p>
            <a href={`/detalles/${reporte.ID_OBJETO}`}>Ver detalles</a>
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

## 🐛 TROUBLESHOOTING

### No aparecen reportes
- Verificar que el usuario esté autenticado
- Revisar console del navegador (F12) para errores
- Comprobar que existen reportes en la BD para el usuario

### Filtro de fecha no funciona
- Asegurar que el formato de fecha es YYYY-MM-DD
- Revisar que la columna FECHA en BD es de tipo DATE o TIMESTAMP

### Categoría no filtra
- Usar el ID de categoría, no el nombre (aunque la página muestra nombres)
- Verificar que los reportes tengan ID_CATEGORIA asignado

---

## 📝 NOTAS IMPORTANTES

1. **Autenticación:** La ruta `/api/mis_reportes` requiere sesión activa
2. **Formato de fechas:** Frontend/Backend usan ISO (YYYY-MM-DD)
3. **Performance:** Consultas optimizadas con índices en FK
4. **Seguridad:** Solo muestra reportes del usuario autenticado

---

## ✨ MEJORAS FUTURAS

- [ ] Exportar reportes a PDF/Excel
- [ ] Gráficos de estadísticas por categoría/mes
- [ ] Búsqueda avanzada con múltiples criterios
- [ ] Notificaciones de nuevos reportes
- [ ] Historial de cambios en reportes
- [ ] Compartir reportes con administradores

