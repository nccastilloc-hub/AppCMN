# Sistema de Gestión IPRESS

Dashboard integrado en Streamlit que centraliza múltiples módulos de análisis estratégico.

## 📋 Módulos Disponibles

1. **🏠 Inicio** - Panel de bienvenida
2. **📊 Consistencia CMN-CEPLAN** - Análisis de consistencia presupuestaria multianual
3. **📊 Seguimiento POI** - Dashboard de metas físicas con seguimiento por actividades operativas y centros de costo
4. **📈 Indicadores Hospitalarios** - Histórico de indicadores (próximamente)

## 🚀 Instalación y Ejecución

### 1. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 2. Ejecutar la Aplicación

```bash
streamlit run Menuprincipal.py
```

La aplicación se abrirá automáticamente en tu navegador en `http://localhost:8501`

## 📁 Estructura de Carpetas

```
app/
├── Menuprincipal.py           # Aplicación principal con menú
├── CMN_EG.py                  # Módulo de análisis CMN-CEPLAN
├── POI_Dashboard.py           # Módulo de seguimiento POI
├── requirements.txt           # Dependencias del proyecto
├── POI/
│   ├── Seguimiento metas fisicas POI.xlsx  # Base de datos de POI
│   └── requirements.txt       # Requerimientos específicos del módulo POI
├── CMN-Mensualizado-127-2027-FasedeIdentificación.xlsx
└── EO.xlsx
```

## 🎯 Módulo: Seguimiento POI

El módulo POI proporciona dos vistas principales:

### Pestaña 1: Actividades Operativas
- **Filtros:** Categoría, Estado, Búsqueda libre
- **Gráficos:** 
  - Distribución de semáforos (Verde, Amarillo, Rojo, Sin dato)
  - Ejecución por categoría
  - Evolución mensual (ejecutado vs programado)
- **Tabla:** Detalle completo de actividades operativas

### Pestaña 2: CC Responsable
- **Resumen:** Agrupación por Centro de Costo Responsable
- **Tabla:** CC Responsable ID : CC Responsable con métricas de ejecución

## 📊 Esquema de Semáforos

| % Ejecución | Semáforo | Color |
|---|---|---|
| 0% | GRIS | Gris |
| (0% - 85%) | ROJO - DEFICIENTE | Rojo |
| [85% - 90%) | AMARILLO - REGULAR | Amarillo |
| [90% - 100%] | VERDE - BUENO | Verde |
| > 100% | MORADO - EXCESO | Morado |

## 📥 Actualizar Datos

Para actualizar los datos del POI:
1. Reemplaza o actualiza el archivo `POI/Seguimiento metas fisicas POI.xlsx`
2. Recarga la aplicación en Streamlit (Ctrl+R o botón de refresh)

## 🔧 Configuración

### Rutas de Archivos Excel

Las rutas se pueden ajustar en cada módulo:

- **CMN_EG.py** - Línea ~16: `CMN-Mensualizado-127-2027-FasedeIdentificación.xlsx`
- **POI_Dashboard.py** - Línea ~29: `POI/Seguimiento metas fisicas POI.xlsx`

### Variables de Configuración

En `POI_Dashboard.py` puedes ajustar:
- `EXCEL_PATH` - Ruta al archivo Excel de POI
- Colores de semáforos: `COLOR_MORADO`, `COLOR_VERDE`, `COLOR_AMARILLO`, `COLOR_ROJO`, `COLOR_GRIS`

## 📝 Notas

- La aplicación está optimizada para pantalla ancha (layout="wide")
- Los datos se cachean automáticamente para mejor rendimiento
- Las tablas son interactivas: permite ordenar, filtrar y exportar a Excel

## 👨‍💻 Contacto y Soporte

Para reportar errores o sugerencias, contacta al equipo de desarrollo.
