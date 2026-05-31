# Menuprincipal.py
import streamlit as st
import os
import signal
import CMN_EG as cmn
import POI_Dashboard as poi

def mostrar_menu():
    # --- CONFIGURACIÓN ESTÉTICA ---
    st.set_page_config(page_title="Sistema de Gestión IPRESS", layout="wide")
    
    # --- MENÚ LATERAL (Identidad y Navegación) ---
    with st.sidebar:
        st.title("🏛️ Gestión IPRESS")
        # st.image("logo-calado.png", width=200)  # Descomenta cuando tengas el logo
        st.markdown("---")
        
        opcion = st.radio(
            "Seleccione el Módulo:",
            ["🏠 Inicio", "📊 Consistencia CMN-CEPLAN", "📈 Seguimiento POI", "📈 Indicadores Hospitalarios"]
        )
    
    # Botón de salir (corregido)
    # En Menuprincipal.py, dentro de la función mostrar_menu()
    if st.sidebar.button("🚪 Salir del Sistema"):
        # Limpiar todas las claves de sesión
     for key in list(st.session_state.keys()):
           del st.session_state[key]
     # Mostrar mensaje y redirigir al login
     st.success("Sesión cerrada correctamente. Redirigiendo al login...")
     st.rerun()  # Esto recarga la app y como no hay authenticated, muestra el login
    
    # --- CUERPO PRINCIPAL (Las Ventanas) ---
    if opcion == "🏠 Inicio":
        st.header("Bienvenido al Portal de Inteligencia de Datos")
        st.write("Seleccione un módulo en el menú de la izquierda para comenzar el análisis.")
        st.write("Este sistema centraliza la información estratégica para la toma de decisiones.")
    
    elif opcion == "📊 Consistencia CMN-CEPLAN":
        st.header("Análisis de Consistencia Multianual")
        st.info("Módulo de integración presupuestaria listo para procesar.")
        cmn.ejecutar_analisis()
    
    elif opcion == "📈 Seguimiento POI":
        poi.ejecutar_dashboard_poi()
    
    elif opcion == "📈 Indicadores Hospitalarios":
        st.header("Histórico de Indicadores (10 años)")
        st.write("⌛ Próximamente: Curvas de tendencia y análisis epidemiológico.")