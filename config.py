"""
config.py
Configuración centralizada y parámetros institucionales - CGGO (INMP)
"""

# =============================================================================
# 1. IDENTIDAD VISUAL Y RECURSOS
# =============================================================================
APP_TITLE = "Consola Gerencial de Operaciones - INMP"
APP_ICON = "🏥"

# Rutas de logos institucionales
LOGO_DARK = "logo_inmp_blanco.png"  # Fondo oscuro / letras blancas
LOGO_LIGHT = "logo_inmp_color.png"  # Fondo claro

# =============================================================================
# 2. UMBRALES DE SEMAFORIZACIÓN OFICIALES (CEPLAN / INSTITUCIONAL)
# =============================================================================
UMBRAL_EXCESO = 1.00       # > 100%
UMBRAL_META_MIN = 0.95     # >= 95%
UMBRAL_RIESGO_MIN = 0.75   # >= 75%
UMBRAL_CRITICO_MIN = 0.00  # > 0%

SEMAFORO_CONFIG = {
    "exceso": {
        "min": UMBRAL_EXCESO,
        "max": float("inf"),
        "label": "Exceso (> 100%)",
        "color": "#9b5de5",
        "badge": "🟣",
        "diagnostico": "Sobreejecución de meta física"
    },
    "meta": {
        "min": UMBRAL_META_MIN,
        "max": UMBRAL_EXCESO,
        "label": "En Meta [95 % - 100 %]",
        "color": "#2ec4b6",
        "badge": "🟢",
        "diagnostico": "Ejecución óptima programada"
    },
    "riesgo": {
        "min": UMBRAL_RIESGO_MIN,
        "max": UMBRAL_META_MIN,
        "label": "En Riesgo [75 % - 95 %)",
        "color": "#ffbf69",
        "badge": "🟡",
        "diagnostico": "Requiere monitoreo preventivo"
    },
    "critico": {
        "min": UMBRAL_CRITICO_MIN,
        "max": UMBRAL_RIESGO_MIN,
        "label": "Crítico (< 75 %)",
        "color": "#e71d36",
        "badge": "🔴",
        "diagnostico": "Subejecución severa"
    },
    "sin_dato": {
        "min": 0.00,
        "max": 0.00,
        "label": "Sin Ejecución (= 0%)",
        "color": "#6c757d",
        "badge": "⚪",
        "diagnostico": "Sin registro de avance físico"
    }
}

# =============================================================================
# 3. METAS Y PARÁMETROS GERENCIALES DE CIERRE
# =============================================================================
PROYECCION_OPTIMA = 95.0   # % cierre mínimo esperado para calificación verde
PROYECCION_MODERADA = 85.0 # % cierre límite para alerta amarilla

# Meses calendario para reportes
MESES_NOMBRE = {
    1: "ene", 2: "feb", 3: "mar", 4: "abr",
    5: "may", 6: "jun", 7: "jul", 8: "ago",
    9: "set", 10: "oct", 11: "nov", 12: "dic"
}