"""
Cabecera del Dashboard de Control de Gestión - Versión Streamlit
Elaborado por: Unidad Funcional de Planeamiento - Oficina Ejecutiva de Planeamiento Estratégico (OEPE)
Asistente de Desarrollo: DeepSeek
Fecha de elaboración: 2026-10-17
Fecha de actualización: 2026-10-17
Objetivo: Modularización del código para la integración en el menú principal de Gestión IPRESS.
=================================================================="""
import streamlit as st
import os
from datetime import datetime

def mostrar_cabecera(titulo, subtitulo, fecha_actualizacion, logo_izq="MINSA logo1.png", logo_der="logo-inmp.png"):
    """
    Dibuja la cabecera institucional modular.
    """
    # Usamos columnas idénticas a tu diseño original
    col_minsa, col_titulo, col_inmp = st.columns([2.1, 5, 1.5], vertical_alignment="center")

    with col_minsa:
        if os.path.exists(logo_izq):
            st.image(logo_izq, use_container_width=True)

    with col_titulo:
        st.markdown(f"<h2 style='text-align: center; margin-bottom: 0;'>{titulo}</h2>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; color: #4A90E2; margin-top: 2px; margin-bottom: 4px; font-weight: 600; font-size: 1.1rem;'>{subtitulo}</p>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; font-size: 0.85rem; color: #777;'>📅 Última actualización: <b>{fecha_actualizacion}</b></p>", unsafe_allow_html=True)

    with col_inmp:
        # Intentamos con el logo oscuro (si existe) o el clásico
        if os.path.exists(logo_der):
            st.image(logo_der, width=180)
        elif os.path.exists("logo_inmp.png"):
            st.image("logo_inmp.png", width=180)

    st.divider()