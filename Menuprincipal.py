import streamlit as st
import os
import signal
import CMN_EG as cmn
import POI_Dashboard as poi

# --- CONFIGURACIÓN ESTÉTICA ---
st.set_page_config(page_title="Sistema de Gestión IPRESS", layout="wide")

# --- LÓGICA PARA CERRAR (Sin Ctrl+C) ---
def cerrar_sistema():
    st.warning("Cerrando el servidor... Puede cerrar esta pestaña ahora.")
    os.kill(os.getpid(), signal.SIGINT)

# --- MENÚ LATERAL (Identidad y Navegación) ---
with st.sidebar:
    st.title("🏛️ Gestión IPRESS")
    st.image("logo-calado.png", width=200) # Para cuando tengas el logo
    st.markdown("---")
    
    opcion = st.radio(
        "Seleccione el Módulo:",
        ["🏠 Inicio", "📊 Consistencia CMN-CEPLAN", "� Seguimiento POI", "�📈 Indicadores Hospitalarios"]
    )
    
    # st.markdown("---")
    # if st.button("🚪 Salir del Sistema"):
    #    cerrar_sistema()

   # Así debe quedar tu bloque de salida:
if st.sidebar.button("🚪 Salir del Sistema"):
    st.empty()  # <--- Estos espacios son la clave
    st.success("Sesión finalizada correctamente. Puede cerrar esta pestaña.")
    st.stop()   # <--- Todos alineados bajo el 'if'

# --- CUERPO PRINCIPAL (Las Ventanas) ---
if opcion == "🏠 Inicio":
    st.header("Bienvenido al Portal de Inteligencia de Datos")
    st.write("Seleccione un módulo en el menú de la izquierda para comenzar el análisis.")
    st.write("Este sistema centraliza la información estratégica para la toma de decisiones.")

elif opcion == "📊 Consistencia CMN-CEPLAN":
    st.header("Análisis de Consistencia Multianual")
    # Aquí es donde llamaremos al motor después
    st.info("Módulo de integración presupuestaria listo para procesar.")
    cmn.ejecutar_analisis()

elif opcion == "� Seguimiento POI":
    poi.ejecutar_dashboard_poi()

elif opcion == "�📈 Indicadores Hospitalarios":
    st.header("Histórico de Indicadores (10 años)")
    st.write("⌛ Próximamente: Curvas de tendencia y análisis epidemiológico.")