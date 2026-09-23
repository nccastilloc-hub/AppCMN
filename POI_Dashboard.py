"""
Dashboard de Seguimiento de Metas Físicas POI del año fiscal - Versión Streamlit
Elaborado por: Unidad Funcional de Planeamiento - Oficina Ejecutiva de Planeamiento Estratégico (OEPE)
Asistente de Desarrollo: Gemini IA/DeepSeek
Fecha de elaboración: 2026-05-31
Fecha de actualización: 2026-09-22
Objetivo: Proporcionar un tablero de control interactivo para la gestión de metas físicas del POI, permitiendo a los usuarios auditar y analizar el desempeño de las actividades operativas en tiempo real.
==================================================================
Módulo Streamlit para integración en el menú principal de Gestión IPRESS.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
from openpyxl import load_workbook
import os
import glob
import re

# ============================================================================
# 1. PARÁMETROS CENTRALIZADOS DESDE CONFIG.PY
# ============================================================================
from config import (
    APP_TITLE,
    APP_ICON,
    LOGO_DARK,
    LOGO_LIGHT,
    SEMAFORO_CONFIG,
    UMBRAL_EXCESO,
    UMBRAL_META_MIN,
    UMBRAL_RIESGO_MIN,
    UMBRAL_CRITICO_MIN,
    PROYECCION_OPTIMA,
    PROYECCION_MODERADA,
    MESES_NOMBRE
)

# Colores mapeados desde el módulo de configuración
COLOR_MORADO = SEMAFORO_CONFIG["exceso"]["color"]
COLOR_VERDE = SEMAFORO_CONFIG["meta"]["color"]
COLOR_AMARILLO = SEMAFORO_CONFIG["riesgo"]["color"]
COLOR_ROJO = SEMAFORO_CONFIG["critico"]["color"]
COLOR_GRIS = SEMAFORO_CONFIG["sin_dato"]["color"]

# ==============================================================================
# 2. FUNCIONES DE UTILIDAD PARA ARCHIVOS Y FECHAS
# ==============================================================================

def extraer_fecha_corte(ruta_archivo: str) -> str:
    try:
        wb = load_workbook(ruta_archivo, read_only=True)
        if wb.properties and wb.properties.modified:
            from datetime import timedelta
            fecha_local = wb.properties.modified - timedelta(hours=5)
            return fecha_local.strftime("%d/%m/%Y a las %H:%M hrs")
    except Exception:
        pass

    if os.path.exists(ruta_archivo):
        timestamp = os.path.getmtime(ruta_archivo)
        return datetime.fromtimestamp(timestamp).strftime("%d/%m/%Y a las %H:%M hrs")

    return "No determinada"

def get_base_dir():
    """Detecta si estamos en local o en Streamlit Cloud."""
    if os.environ.get("STREAMLIT_SHARING") == "1" or os.environ.get("STREAMLIT_CLOUD"):
        return os.getcwd()
    
    if os.path.exists(r"D:\app\AppCMN"):
        return r"D:\app\AppCMN"
    
    return os.getcwd()

BASE_DIR = get_base_dir()

def formatear_estado(row):
    """Formatea el estado con un emoji de color según el semáforo centralizado."""
    color = row["Color"]
    estado = row["Estado"]
    
    emoji_map = {
        COLOR_VERDE: SEMAFORO_CONFIG["meta"]["badge"],
        COLOR_AMARILLO: SEMAFORO_CONFIG["riesgo"]["badge"], 
        COLOR_ROJO: SEMAFORO_CONFIG["critico"]["badge"],
        COLOR_MORADO: SEMAFORO_CONFIG["exceso"]["badge"],
        COLOR_GRIS: SEMAFORO_CONFIG["sin_dato"]["badge"]
    }
    
    emoji = emoji_map.get(color, "⚫")
    partes = estado.split(" - ")
    estado_limpio = partes[-1] if len(partes) > 1 else estado
    
    return f"{emoji} {estado_limpio}"

def encontrar_archivo_ceplan():
    """Busca el archivo de POI en el directorio de trabajo."""
    if not os.path.exists(BASE_DIR):
        os.makedirs(BASE_DIR)
        st.info(f"📁 Carpeta creada: {BASE_DIR}")
        return None
    
    patrones = [
        os.path.join(BASE_DIR, "Seguimiento metas fisicas POI.xlsx"),
        os.path.join(BASE_DIR, "Seguimiento metas fisicas POI.xls"),
        os.path.join(BASE_DIR, "POI_*.xlsx"),
        os.path.join(BASE_DIR, "*.xlsx"),
        os.path.join(BASE_DIR, "*.xls"),
    ]
    
    for patron in patrones:
        if "*" not in patron:
            if os.path.exists(patron):
                return patron
        else:
            archivos = glob.glob(patron)
            archivos_filtrados = [a for a in archivos if "POI" in a.upper() or "METAS" in a.upper() or "SEGUIMIENTO" in a.upper()]
            if archivos_filtrados:
                archivos_filtrados.sort(key=os.path.getmtime, reverse=True)
                return archivos_filtrados[0]
            elif archivos:
                archivos.sort(key=os.path.getmtime, reverse=True)
                return archivos[0]
    
    st.warning("⚠️ No se encontró el archivo de seguimiento POI")
    st.info(f"📥 Coloca el archivo en: `{BASE_DIR}`")
    return None

def extract_month(col):
    match = re.search(r'(\d{1,2})', str(col))
    return int(match.group(1)) if match else 0

def detect_last_month(df):
    """Detecta automáticamente el último mes con datos de ejecución real."""
    fse_cols = [col for col in df.columns if "F(SE)" in col and any(str(i).zfill(2) in col for i in range(1, 13))]
    
    if not fse_cols:
        fse_cols = [col for col in df.columns if "F(RE)" in col and any(str(i).zfill(2) in col for i in range(1, 13))]
    
    fse_cols = sorted(fse_cols, key=extract_month)
    
    last_month = 0
    for col in reversed(fse_cols):
        if col in df.columns and df[col].sum() > 0:
            month = extract_month(col)
            if month > 0:
                last_month = month
                break
    
    if last_month == 0:
        last_month = datetime.now().month
    
    return last_month

def get_month_from_col(col):
    match = re.search(r'(\d{1,2})', str(col))
    return int(match.group(1)) if match else 99

# ============================================================================
# 3. CARGA Y PROCESAMIENTO
# ============================================================================

@st.cache_data
def load_data(excel_path):
    """Carga y procesa la data del Excel de CEPLAN."""
    try:
        df = pd.read_excel(excel_path, sheet_name="DATA", header=0)
    except Exception:
        df = pd.read_excel(excel_path, header=0)
    
    df.columns = df.columns.str.strip()
    
    if "Activo AO" in df.columns:
        df = df[df["Activo AO"] == "SI"].copy()
    
    fse_cols = []
    fre_cols = []
    for col in df.columns:
        col_clean = col.strip()
        if "F(SE)" in col_clean and any(str(i).zfill(2) in col_clean for i in range(1, 13)):
            fse_cols.append(col_clean)
        elif "F(RE)" in col_clean and any(str(i).zfill(2) in col_clean for i in range(1, 13)):
            fre_cols.append(col_clean)
    
    if not fse_cols:
        fse_cols = [f"F(SE) {i:02d}" for i in range(1, 13) if f"F(SE) {i:02d}" in df.columns]
    if not fre_cols:
        fre_cols = [f"F(RE) {i:02d}" for i in range(1, 13) if f"F(RE) {i:02d}" in df.columns]
    
    fse_cols = sorted(set(fse_cols), key=get_month_from_col)
    fre_cols = sorted(set(fre_cols), key=get_month_from_col)
    
    last_month = detect_last_month(df)
    
    fse_cols = [c for c in fse_cols if get_month_from_col(c) <= last_month]
    fre_cols = [c for c in fre_cols if get_month_from_col(c) <= last_month]
    
    df["F(SE) Acum"] = df[fse_cols].sum(axis=1) if fse_cols else 0
    df["F(RE) Acum"] = df[fre_cols].sum(axis=1) if fre_cols else 0
    
    df["% Ejecución"] = np.where(
        df["F(RE) Acum"] > 0,
        df["F(SE) Acum"] / df["F(RE) Acum"],
        0.0
    )
    
    # Ritmo móvil de los últimos 3 meses
    if len(fse_cols) >= 3:
        ult_3_meses = fse_cols[-3:]
        df["Prom_Ult_3M"] = df[ult_3_meses].sum(axis=1) / 3
    elif len(fse_cols) > 0:
        df["Prom_Ult_3M"] = df[fse_cols].sum(axis=1) / len(fse_cols)
    else:
        df["Prom_Ult_3M"] = 0

    meses_faltantes = max(0, 12 - last_month)
    df["Proyeccion_Dic"] = df["F(SE) Acum"] + (df["Prom_Ult_3M"] * meses_faltantes)

    df["Proyeccion_vs_Meta"] = np.where(
        df["F(RE) Acum"] > 0,
        (df["Proyeccion_Dic"] / df["F(RE) Acum"]) * 100,
        0.0
    )

    df["Alerta_Proyeccion"] = np.where(
        df["Proyeccion_vs_Meta"] < PROYECCION_MODERADA,
        "⚠️ Revisar meta",
        np.where(
            df["Proyeccion_vs_Meta"] > (UMBRAL_EXCESO * 100),
            f"{SEMAFORO_CONFIG['exceso']['badge']} Sobreejecución",
            f"{SEMAFORO_CONFIG['meta']['badge']} OK"
        )
    )
    
    # Cálculos desacoplados (Real vs Truncado CEPLAN)
    df["% Avance_Real"] = np.where(
        df["F(RE) Acum"] > 0,
        df["F(SE) Acum"] / df["F(RE) Acum"],
        0.0
    )
    factor_anual = 12.0 / last_month if last_month > 0 else 1.0
    df["% Proy_Real"] = df["% Avance_Real"] * factor_anual

    df["% Avance_CEPLAN"] = np.minimum(1.0, df["% Avance_Real"])
    df["% Proy_CEPLAN"] = np.minimum(1.0, df["% Proy_Real"])

    def semaforo(row):
        pct = row["% Ejecución"]
        if row["F(RE) Acum"] == 0:
            return SEMAFORO_CONFIG["sin_dato"]["label"], COLOR_GRIS
        elif pct == 0:
            return SEMAFORO_CONFIG["sin_dato"]["label"], COLOR_GRIS
        elif pct < UMBRAL_RIESGO_MIN:
            return SEMAFORO_CONFIG["critico"]["label"], COLOR_ROJO
        elif pct < UMBRAL_META_MIN:
            return SEMAFORO_CONFIG["riesgo"]["label"], COLOR_AMARILLO
        elif pct <= UMBRAL_EXCESO:
            return SEMAFORO_CONFIG["meta"]["label"], COLOR_VERDE
        else:
            return SEMAFORO_CONFIG["exceso"]["label"], COLOR_MORADO
    
    df[["Estado", "Color"]] = df.apply(semaforo, axis=1, result_type="expand")
    
    fse_data = df[fse_cols].values if fse_cols else np.zeros((len(df), 1))
    with np.errstate(divide='ignore', invalid='ignore'):
        df["CV"] = np.nanstd(fse_data, axis=1) / np.nanmean(fse_data, axis=1)
    df["CV"] = df["CV"].replace([np.inf, -np.inf], 0).fillna(0)
    
    df.attrs["last_month"] = last_month
    df.attrs["fse_cols"] = fse_cols
    df.attrs["fre_cols"] = fre_cols
    df.attrs["year"] = df["POI"].iloc[0] if "POI" in df.columns else 2026
    
    return df

def get_resumen(df):
    """Genera tabla resumen agregada por actividad operativa."""
    group_cols = [
        "CC Responsable ID", "CC Responsable",
        "Categoria ID", "Categoria", 
        "Producto ID", "Producto",
        "Actividad Presupuestal ID", "Actividad Presupuestal",
        "Actividad Operativa ID", "Actividad Operativa",
        "Unidad de Medida"
    ]
    group_cols = [c for c in group_cols if c in df.columns]
    
    agg_dict = {
        "F(SE) Acum": "sum",
        "F(RE) Acum": "sum",
        "Proyeccion_Dic": "sum",
        "Prom_Ult_3M": "sum",
        "CV": "mean"
    }
    
    resumen = df.groupby(group_cols, as_index=False).agg(agg_dict)
    
    resumen["% Ejecución"] = np.where(
        resumen["F(RE) Acum"] > 0,
        resumen["F(SE) Acum"] / resumen["F(RE) Acum"],
        0.0
    )
    
    def semaforo_agg(row):
        pct = row["% Ejecución"]
        if row["F(RE) Acum"] == 0 or pct == 0:
            return SEMAFORO_CONFIG["sin_dato"]["label"], COLOR_GRIS
        elif pct < UMBRAL_RIESGO_MIN:
            return SEMAFORO_CONFIG["critico"]["label"], COLOR_ROJO
        elif pct < UMBRAL_META_MIN:
            return SEMAFORO_CONFIG["riesgo"]["label"], COLOR_AMARILLO
        elif pct <= UMBRAL_EXCESO:
            return SEMAFORO_CONFIG["meta"]["label"], COLOR_VERDE
        else:
            return SEMAFORO_CONFIG["exceso"]["label"], COLOR_MORADO
    
    resumen[["Estado", "Color"]] = resumen.apply(semaforo_agg, axis=1, result_type="expand")

    resumen["Proyeccion_vs_Meta"] = np.where(
        resumen["F(RE) Acum"] > 0,
        (resumen["Proyeccion_Dic"] / resumen["F(RE) Acum"]) * 100,
        0.0
    )

    resumen["Alerta_Proyeccion"] = np.where(
        resumen["Proyeccion_vs_Meta"] < PROYECCION_MODERADA,
        "⚠️ Revisar meta",
        np.where(
            resumen["Proyeccion_vs_Meta"] > (UMBRAL_EXCESO * 100),
            f"{SEMAFORO_CONFIG['exceso']['badge']} Sobreejecución",
            f"{SEMAFORO_CONFIG['meta']['badge']} OK"
        )
    )
    return resumen

def get_resumen_cc_responsable(df):
    """Genera tabla resumen agregada por CC Responsable."""
    group_cols = ["CC Responsable ID", "CC Responsable"]
    group_cols = [c for c in group_cols if c in df.columns]
    
    if not group_cols:
        return pd.DataFrame()
    
    agg_dict = {
        "F(SE) Acum": "sum",
        "F(RE) Acum": "sum",
        "Proyeccion_Dic": "sum",
        "Prom_Ult_3M": "sum",
        "CV": "mean"
    }
    
    resumen = df.groupby(group_cols, as_index=False).agg(agg_dict)
    
    resumen["% Ejecución"] = np.where(
        resumen["F(RE) Acum"] > 0,
        resumen["F(SE) Acum"] / resumen["F(RE) Acum"],
        0.0
    )
    
    def semaforo_cc(row):
        pct = row["% Ejecución"]
        if row["F(RE) Acum"] == 0 or pct == 0:
            return SEMAFORO_CONFIG["sin_dato"]["label"], COLOR_GRIS
        elif pct < UMBRAL_RIESGO_MIN:
            return SEMAFORO_CONFIG["critico"]["label"], COLOR_ROJO
        elif pct < UMBRAL_META_MIN:
            return SEMAFORO_CONFIG["riesgo"]["label"], COLOR_AMARILLO
        elif pct <= UMBRAL_EXCESO:
            return SEMAFORO_CONFIG["meta"]["label"], COLOR_VERDE
        else:
            return SEMAFORO_CONFIG["exceso"]["label"], COLOR_MORADO
    
    resumen[["Estado", "Color"]] = resumen.apply(semaforo_cc, axis=1, result_type="expand")

    resumen["Proyeccion_vs_Meta"] = np.where(
        resumen["F(RE) Acum"] > 0,
        (resumen["Proyeccion_Dic"] / resumen["F(RE) Acum"]) * 100,
        0.0
    )
    resumen["Alerta_Proyeccion"] = np.where(
        resumen["Proyeccion_vs_Meta"] < PROYECCION_MODERADA,
        "⚠️ Revisar meta",
        np.where(
            resumen["Proyeccion_vs_Meta"] > (UMBRAL_EXCESO * 100),
            f"{SEMAFORO_CONFIG['exceso']['badge']} Sobreejecución",
            f"{SEMAFORO_CONFIG['meta']['badge']} OK"
        )
    )
    
    return resumen

# ============================================================================
# 4. TABS MODULARES
# ============================================================================

def tab_resumen_categoria(df, resumen, fse_cols, fre_cols, last_month, month_names, fecha_archivo, year):
    """Tab 1: Control de Gestión por Categoría Presupuestal y Proyección."""
    st.subheader("🎯 Control de Gestión y Consistencia POI")
    st.markdown("### 🎛️ Filtro de Control de Daños (Enfoque Ejecutivo)")
    
    opciones_semaforo = {
        "🔍 Ver Todo el Universo POI": "TODOS",
        f"{SEMAFORO_CONFIG['meta']['badge']} {SEMAFORO_CONFIG['meta']['label']}": COLOR_VERDE,
        f"{SEMAFORO_CONFIG['riesgo']['badge']} {SEMAFORO_CONFIG['riesgo']['label']}": COLOR_AMARILLO,
        f"{SEMAFORO_CONFIG['critico']['badge']} {SEMAFORO_CONFIG['critico']['label']}": COLOR_ROJO,
        f"{SEMAFORO_CONFIG['exceso']['badge']} {SEMAFORO_CONFIG['exceso']['label']}": COLOR_MORADO,
        f"{SEMAFORO_CONFIG['sin_dato']['badge']} {SEMAFORO_CONFIG['sin_dato']['label']}": COLOR_GRIS
    }
    
    sel_estado = st.radio(
        "Seleccione un estado del semáforo para auditar las actividades afectadas:",
        options=list(opciones_semaforo.keys()),
        horizontal=True
    )
    
    color_filtrado = opciones_semaforo[sel_estado]
    
    if color_filtrado == "TODOS":
        df_filtrado_semaforo = resumen.copy()
    else:
        df_filtrado_semaforo = resumen[resumen["Color"] == color_filtrado]
        if df_filtrado_semaforo.empty:
            st.success("✨ **¡Excelente gestión!** No se encontraron actividades operativas en la situación seleccionada.")
    
    st.markdown("---")
    
    if "Categoria ID" in df_filtrado_semaforo.columns and not df_filtrado_semaforo.empty:
        df_ordenado = df_filtrado_semaforo[['Categoria ID', 'Categoria']].drop_duplicates().sort_values('Categoria ID')
        categorias_unicas = df_ordenado['Categoria'].dropna().tolist()
    else:
        categorias_unicas = []
    
    sel_categoria = st.selectbox(
        "🔍 Seleccione una Categoría/Programa para evaluar el detalle (Drilldown):",
        options=["-- Ver Resumen Seleccionado (Todas) --"] + categorias_unicas
    )
    
    if sel_categoria == "-- Ver Resumen Seleccionado (Todas) --" or not df_filtrado_semaforo.empty:
        if sel_categoria == "-- Ver Resumen Seleccionado (Todas) --":
            resumen_gerencial = df_filtrado_semaforo.copy()
            es_vista_macro = True
        else:
            resumen_gerencial = df_filtrado_semaforo[df_filtrado_semaforo["Categoria"] == sel_categoria]
            es_vista_macro = False
    else:
        resumen_gerencial = pd.DataFrame()
        es_vista_macro = True
    
    if not resumen_gerencial.empty:
        col1, col2 = st.columns([1, 2.5])
        
        with col1:
            cant_verde = len(resumen_gerencial[resumen_gerencial["Color"] == COLOR_VERDE])
            cant_amarillo = len(resumen_gerencial[resumen_gerencial["Color"] == COLOR_AMARILLO])
            cant_rojo = len(resumen_gerencial[resumen_gerencial["Color"] == COLOR_ROJO])
            cant_morado = len(resumen_gerencial[resumen_gerencial["Color"] == COLOR_MORADO])
            cant_gris = len(resumen_gerencial[resumen_gerencial["Color"] == COLOR_GRIS])
            
            fig_semaforo = go.Figure(data=[
                go.Bar(
                    x=[SEMAFORO_CONFIG['meta']['label'], SEMAFORO_CONFIG['riesgo']['label'], 
                       SEMAFORO_CONFIG['critico']['label'], SEMAFORO_CONFIG['exceso']['label'], 
                       SEMAFORO_CONFIG['sin_dato']['label']],
                    y=[cant_verde, cant_amarillo, cant_rojo, cant_morado, cant_gris],
                    marker_color=[COLOR_VERDE, COLOR_AMARILLO, COLOR_ROJO, COLOR_MORADO, COLOR_GRIS],
                    text=[cant_verde, cant_amarillo, cant_rojo, cant_morado, cant_gris],
                    textposition="auto"
                )
            ])
            fig_semaforo.update_layout(title="Distribución del Segmento Seleccionado", height=300, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_semaforo, use_container_width=True)
        
        with col2:
            if es_vista_macro:
                eje_y = "Categoria"
                titulo_graf = "% Ejecución por Categoría (Orden Clasificador)"
                df_graf = resumen_gerencial.groupby(["Categoria ID", "Categoria"]).agg({
                    "F(SE) Acum": "sum", "F(RE) Acum": "sum"
                }).reset_index()
                df_graf["% Ejecución"] = np.where(df_graf["F(RE) Acum"] > 0, (df_graf["F(SE) Acum"] / df_graf["F(RE) Acum"]) * 100, 0)
                if "Categoria ID" in df_graf.columns:
                    df_graf = df_graf.sort_values("Categoria ID", ascending=False)
            else:
                eje_y = "Producto"
                titulo_graf = f"Productos en: {sel_categoria[:30]}..."
                df_graf = resumen_gerencial.groupby(["Producto ID", "Producto"]).agg({
                    "F(SE) Acum": "sum", "F(RE) Acum": "sum"
                }).reset_index()
                df_graf["% Ejecución"] = np.where(df_graf["F(RE) Acum"] > 0, (df_graf["F(SE) Acum"] / df_graf["F(RE) Acum"]) * 100, 0)
                if "Producto ID" in df_graf.columns:
                    df_graf = df_graf.sort_values("Producto ID", ascending=False)
            
            color_map = {
                "TODOS": "#17a2b8",
                COLOR_VERDE: COLOR_VERDE,
                COLOR_AMARILLO: COLOR_AMARILLO,
                COLOR_ROJO: COLOR_ROJO,
                COLOR_MORADO: COLOR_MORADO,
                COLOR_GRIS: COLOR_GRIS
            }
            bar_color = color_map.get(color_filtrado, "#17a2b8")
            
            fig_dinamico = go.Figure(data=[
                go.Bar(
                    y=df_graf[eje_y].astype(str).str.wrap(30),
                    x=df_graf["% Ejecución"],
                    orientation="h",
                    marker_color=bar_color,
                    text=[f"{x:.1f}%" for x in df_graf["% Ejecución"]],
                    textposition="outside"
                )
            ])
            fig_dinamico.add_vline(x=100, line_width=2, line_dash="dash", line_color="gray", opacity=0.7)
            fig_dinamico.update_layout(
                title=titulo_graf,
                xaxis_title="%",
                xaxis=dict(range=[0, max(df_graf["% Ejecución"]) * 1.15 if not df_graf.empty and max(df_graf["% Ejecución"]) > 0 else 100]),
                margin=dict(l=150, r=50, t=40, b=30),
                height=380
            )
            st.plotly_chart(fig_dinamico, use_container_width=True)
    
    st.markdown("---")
    st.subheader("📋 Control de Actividades Operativas")
    
    if resumen_gerencial.empty:
        st.info("No existen actividades operativas registradas bajo los filtros seleccionados.")
    else:
        st.markdown("💡 *Seleccione una actividad para ver su detalle mensual y su proyección abajo.*")

        columnas_visibles = [c for c in ["Categoria ID", "Producto ID", "Actividad Operativa", "Unidad de Medida", "F(SE) Acum", "F(RE) Acum", "% Ejecución", "Estado", "Color"] if c in resumen_gerencial.columns]
        tabla_operativa = resumen_gerencial[columnas_visibles].copy()
        
        if "Categoria ID" in tabla_operativa.columns:
            tabla_operativa = tabla_operativa.sort_values(by=["Categoria ID"])
            tabla_operativa = tabla_operativa.rename(columns={
                "F(SE) Acum": "Ejec. Acum",
                "F(RE) Acum": "Prog. Acum"
            })
        
        tabla_formateada = tabla_operativa.copy()
        tabla_formateada["Ejec. Acum"] = tabla_formateada["Ejec. Acum"].apply(lambda x: f"{x:,.0f}")
        tabla_formateada["Prog. Acum"] = tabla_formateada["Prog. Acum"].apply(lambda x: f"{x:,.0f}")
        tabla_formateada["% Ejecución"] = tabla_formateada["% Ejecución"].apply(lambda x: f"{x*100:.1f}%")
        tabla_formateada["Estado"] = tabla_formateada.apply(formatear_estado, axis=1)
        
        if "Color" in tabla_formateada.columns:
            tabla_formateada = tabla_formateada.drop(columns=["Color"])
        
        evento_seleccion = st.dataframe(
            tabla_formateada,
            use_container_width=True,
            height=250,
            on_select="rerun",
            selection_mode="single-row",
            column_config={
                "Estado": st.column_config.TextColumn("Estado", help="Estado del semáforo", width="medium")
            }
        )
        
        if evento_seleccion and "selection" in evento_seleccion and evento_seleccion["selection"]["rows"]:
            fila_index = evento_seleccion["selection"]["rows"][0]
            if fila_index < len(tabla_operativa):
                sel_actividad = tabla_operativa.iloc[fila_index]["Actividad Operativa"]
            else:
                sel_actividad = tabla_operativa.iloc[0]["Actividad Operativa"]
        else:
            sel_actividad = tabla_operativa.iloc[0]["Actividad Operativa"]
        
        # --- DETALLE Y PROYECCIÓN FIN DE AÑO ---
        st.markdown("---")
        st.markdown(f"### 📅 Evolución Mensual y Proyección al Cierre")
        st.markdown(f"**Actividad Auditada:** `{sel_actividad}`")

        df_act_sel = df[df["Actividad Operativa"] == sel_actividad]
        info_act = resumen_gerencial[resumen_gerencial["Actividad Operativa"] == sel_actividad].iloc[0]

        meses_restantes = [MESES_NOMBRE[m] for m in range(last_month + 1, 13)]
        n_restantes = len(meses_restantes)

        if last_month >= 3:
            ult_cols = fse_cols[-3:]
            ritmo_mensual = df_act_sel[ult_cols].sum(axis=1).values[0] / 3
            fuente_ritmo = "Promedio móvil (últimos 3 meses)"
        elif last_month > 0:
            ritmo_mensual = df_act_sel[fse_cols].sum(axis=1).values[0] / len(fse_cols)
            fuente_ritmo = f"Promedio Ene-{month_names[last_month]}"
        else:
            ritmo_mensual = 0
            fuente_ritmo = "Sin datos suficientes"

        ejec_actual = info_act['F(SE) Acum']
        prog_acumulado = info_act['F(RE) Acum']
        proyeccion_cierre = ejec_actual + (ritmo_mensual * n_restantes)

        todas_fre_cols = [c for c in df.columns if "F(RE)" in c and any(str(i).zfill(2) in c for i in range(1, 13))]
        meta_anual_programada = df_act_sel[todas_fre_cols].sum(axis=1).values[0] if todas_fre_cols else prog_acumulado
        
        pct_proy = (proyeccion_cierre / meta_anual_programada * 100) if meta_anual_programada > 0 else 0

        # Tarjetas Sombreadas en CSS
        st.markdown("""
        <style>
        .kpi-card {
            background-color: #1e2129;
            border-radius: 8px;
            padding: 14px 18px;
            border: 1px solid #313745;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            margin-bottom: 12px;
        }
        .kpi-title { font-size: 0.80rem; color: #a0aec0; text-transform: uppercase; font-weight: 600; }
        .kpi-value { font-size: 1.45rem; font-weight: 700; color: #ffffff; margin: 4px 0; }
        .kpi-sub { font-size: 0.75rem; color: #718096; }
        </style>
        """, unsafe_allow_html=True)

        # Fila 1: Métricas de Ejecución Actual
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Unidad de Medida", str(info_act["Unidad de Medida"]))
        m2.metric(f"Programado (Ene-{month_names[last_month]})", f"{prog_acumulado:,.0f}")
        m3.metric(f"Ejecutado (Ene-{month_names[last_month]})", f"{ejec_actual:,.0f}")
        m4.metric("Cumplimiento Actual", f"{info_act['% Ejecución']*100:.1f}%")

        # Fila 2: Cajas de Proyección
        c_proy1, c_proy2, c_proy3, c_proy4 = st.columns(4)

        with c_proy1:
            st.markdown(f"""
            <div class="kpi-card" style="border-left: 5px solid #17a2b8;">
                <div class="kpi-title">Ritmo Mensual Reciente</div>
                <div class="kpi-value">{ritmo_mensual:,.0f} <span style="font-size:0.85rem; font-weight: normal;">/ mes</span></div>
                <div class="kpi-sub">{fuente_ritmo}</div>
            </div>
            """, unsafe_allow_html=True)

        with c_proy2:
            st.markdown(f"""
            <div class="kpi-card" style="border-left: 5px solid {COLOR_AMARILLO};">
                <div class="kpi-title">Proyección Cierre (Dic)</div>
                <div class="kpi-value">{proyeccion_cierre:,.0f}</div>
                <div class="kpi-sub">Real Ene-{month_names[last_month]} + {n_restantes} m. proy.</div>
            </div>
            """, unsafe_allow_html=True)

        with c_proy3:
            st.markdown(f"""
            <div class="kpi-card" style="border-left: 5px solid {COLOR_GRIS};">
                <div class="kpi-title">Meta Anual Programada</div>
                <div class="kpi-value">{meta_anual_programada:,.0f}</div>
                <div class="kpi-sub">Total POI (Ene - Dic)</div>
            </div>
            """, unsafe_allow_html=True)

        with c_proy4:
            color_meta = COLOR_VERDE if (UMBRAL_META_MIN * 100) <= pct_proy <= (UMBRAL_EXCESO * 100) else (COLOR_ROJO if pct_proy < (UMBRAL_RIESGO_MIN * 100) else COLOR_AMARILLO)
            st.markdown(f"""
            <div class="kpi-card" style="border-left: 5px solid {color_meta};">
                <div class="kpi-title">Cumplimiento al Cierre</div>
                <div class="kpi-value">{pct_proy:.1f}%</div>
                <div class="kpi-sub">Proyección vs Meta Anual</div>
            </div>
            """, unsafe_allow_html=True)

        st.caption("📌 *Proyección calculada con el promedio móvil de los últimos 3 meses para el periodo restante.*")

        mes_labels = month_names[1:len(fse_cols)+1]
        valores_se = [df_act_sel[c].sum() for c in fse_cols]
        valores_re = [df_act_sel[c].sum() for c in fre_cols]

        color_map_evolucion = {
            "TODOS": COLOR_VERDE,
            COLOR_VERDE: COLOR_VERDE,
            COLOR_AMARILLO: COLOR_AMARILLO,
            COLOR_ROJO: COLOR_ROJO,
            COLOR_MORADO: COLOR_MORADO,
            COLOR_GRIS: COLOR_GRIS
        }
        bar_color_evolucion = color_map_evolucion.get(color_filtrado, COLOR_VERDE)

        pct_mensual = [(se / re * 100) if re > 0 else 0 for se, re in zip(valores_se, valores_re)]

        fig_mensual = make_subplots(specs=[[{"secondary_y": False}]])

        fig_mensual.add_trace(
            go.Bar(
                x=mes_labels,
                y=valores_se,
                name="Ejecutado Real F(SE)",
                marker_color=bar_color_evolucion,
                customdata=np.array([valores_re, pct_mensual]).T,
                hovertemplate=(
                    "<b>Ejecutado:</b> %{y:,.0f}<br>"
                    "<b>Programado:</b> %{customdata[0]:,.0f}<br>"
                    "<b>% Ejecución:</b> %{customdata[1]:.1f}%"
                    "<extra></extra>"
                )
            )
        )

        if ritmo_mensual > 0 and n_restantes > 0:
            fig_mensual.add_trace(
                go.Bar(
                    x=meses_restantes,
                    y=[ritmo_mensual] * n_restantes,
                    name=f"Proyectado ({fuente_ritmo})",
                    marker=dict(
                        color="rgba(23, 162, 184, 0.20)",
                        line=dict(color="#17a2b8", width=1.5),
                        pattern_shape="/"
                    ),
                    hovertemplate=(
                        "<b>Proyección %{x}:</b> %{y:,.0f}<br>"
                        "<i>Estimado mensual</i><extra></extra>"
                    )
                )
            )

        fig_mensual.add_trace(
            go.Scatter(
                x=mes_labels,
                y=valores_re,
                name="Programado POI F(RE)",
                mode="lines+markers",
                line=dict(color=COLOR_ROJO, width=2.5),
                hoverinfo="skip"
            )
        )

        fig_mensual.update_layout(
            hovermode="closest",
            height=300,
            margin=dict(l=20, r=20, t=20, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(
                categoryorder="array",
                categoryarray=month_names[1:]
            )
        )
        st.plotly_chart(fig_mensual, use_container_width=True)
        
        pct_act = info_act['% Ejecución']
        if pct_act < UMBRAL_RIESGO_MIN:
            st.error(f"🚨 **Inconsistencia por Subejecución ({pct_act*100:.1f}%):** Esta actividad se encuentra por debajo de la meta física programada.")
        elif pct_act > UMBRAL_EXCESO:
            st.warning(f"⚠️ **Alerta por Sobreejecución ({pct_act*100:.1f}%):** La ejecución física supera lo planificado.")
        else:
            st.success("🟢 **Consistencia Correcta:** Avance físico dentro de rangos institucionales óptimos.")

def tab_unidad_organica(df, resumen, resumen_cc, fse_cols, fre_cols, last_month, month_names, fecha_archivo, year):
    """Tab 2: Ranking y detalle por Unidad Orgánica."""
    st.subheader("🏆 Ranking de Gestión por Unidad Orgánica")
    st.markdown("💡 *Haga clic en cualquier Unidad Orgánica para auditar sus metas físicas asignadas.*")

    opciones_semaforo = [
        "Todos",
        f"{SEMAFORO_CONFIG['meta']['badge']} {SEMAFORO_CONFIG['meta']['label']}",
        f"{SEMAFORO_CONFIG['riesgo']['badge']} {SEMAFORO_CONFIG['riesgo']['label']}",
        f"{SEMAFORO_CONFIG['critico']['badge']} {SEMAFORO_CONFIG['critico']['label']}",
        f"{SEMAFORO_CONFIG['exceso']['badge']} {SEMAFORO_CONFIG['exceso']['label']}",
        f"{SEMAFORO_CONFIG['sin_dato']['badge']} {SEMAFORO_CONFIG['sin_dato']['label']}"
    ]
    filtro_seleccionado = st.multiselect(
        "Filtrar por estado del semáforo",
        options=opciones_semaforo,
        default=["Todos"],
        key="filtro_tab2"
    )

    if "Todos" not in filtro_seleccionado and filtro_seleccionado:
        color_map = {
            f"{SEMAFORO_CONFIG['meta']['badge']} {SEMAFORO_CONFIG['meta']['label']}": COLOR_VERDE,
            f"{SEMAFORO_CONFIG['riesgo']['badge']} {SEMAFORO_CONFIG['riesgo']['label']}": COLOR_AMARILLO,
            f"{SEMAFORO_CONFIG['critico']['badge']} {SEMAFORO_CONFIG['critico']['label']}": COLOR_ROJO,
            f"{SEMAFORO_CONFIG['exceso']['badge']} {SEMAFORO_CONFIG['exceso']['label']}": COLOR_MORADO,
            f"{SEMAFORO_CONFIG['sin_dato']['badge']} {SEMAFORO_CONFIG['sin_dato']['label']}": COLOR_GRIS
        }
        colores_seleccionados = [color_map[opt] for opt in filtro_seleccionado if opt in color_map]
        resumen_filtrado = resumen[resumen["Color"].isin(colores_seleccionados)].copy()
    else:
        resumen_filtrado = resumen.copy()

    if resumen_filtrado.empty:
        st.warning("⚠️ No hay actividades que coincidan con el filtro seleccionado.")
        return

    resumen_cc_filtrado = get_resumen_cc_responsable(resumen_filtrado)

    if resumen_cc_filtrado.empty:
        st.warning("⚠️ No hay unidades orgánicas con actividades del filtro seleccionado.")
        return

    df_cc_graf = resumen_cc_filtrado.copy().sort_values("% Ejecución", ascending=True)

    fig_cc = go.Figure(data=[
        go.Bar(
            y=df_cc_graf["CC Responsable"].astype(str).str.wrap(45),
            x=df_cc_graf["% Ejecución"] * 100,
            orientation="h",
            marker_color=df_cc_graf["Color"],
            text=[f"{x:.1f}%" for x in df_cc_graf["% Ejecución"] * 100],
            textposition="outside",
            textfont=dict(size=10)
        )
    ])
    fig_cc.update_layout(
        title="% Ejecución Promedio por Unidad Orgánica",
        xaxis_title="%",
        xaxis=dict(range=[0, max(df_cc_graf["% Ejecución"] * 100) * 1.15 if not df_cc_graf.empty else 100]),
        margin=dict(l=250, r=50, t=40, b=20),
        height=max(400, len(df_cc_graf) * 25)
    )
    st.plotly_chart(fig_cc, use_container_width=True)

    st.markdown("---")
    st.subheader("📋 Lista de Unidades Orgánicas")

    tabla_cc = resumen_cc_filtrado[[
        "CC Responsable ID", "CC Responsable",
        "F(SE) Acum", "F(RE) Acum", "% Ejecución", "Estado", "Color"
    ]].copy().sort_values("% Ejecución", ascending=False)

    tabla_cc_formateada = tabla_cc.copy()
    tabla_cc_formateada["F(SE) Acum"] = tabla_cc_formateada["F(SE) Acum"].apply(lambda x: f"{x:,.0f}")
    tabla_cc_formateada["F(RE) Acum"] = tabla_cc_formateada["F(RE) Acum"].apply(lambda x: f"{x:,.0f}")
    tabla_cc_formateada["% Ejecución"] = tabla_cc_formateada["% Ejecución"].apply(lambda x: f"{x*100:.1f}%")
    tabla_cc_formateada["Estado"] = tabla_cc_formateada.apply(formatear_estado, axis=1)

    if "Color" in tabla_cc_formateada.columns:
        tabla_cc_formateada = tabla_cc_formateada.drop(columns=["Color"])

    if st.session_state.get("reset_seleccion", False):
        if "df_cc_mejorado" in st.session_state:
            del st.session_state["df_cc_mejorado"]
        st.session_state["reset_seleccion"] = False

    seleccion_cc = st.dataframe(
        tabla_cc_formateada,
        use_container_width=True,
        height=250,
        on_select="rerun",
        selection_mode="single-row",
        key="df_cc_mejorado",
        column_config={
            "Estado": st.column_config.TextColumn("Estado", width="medium")
        }
    )

    if seleccion_cc and "selection" in seleccion_cc and seleccion_cc["selection"]["rows"]:
        idx = seleccion_cc["selection"]["rows"][0]
        if idx < len(tabla_cc):
            sel_cc_id = tabla_cc.iloc[idx]["CC Responsable ID"]
            sel_cc_nombre = tabla_cc.iloc[idx]["CC Responsable"]
        else:
            sel_cc_id = tabla_cc.iloc[0]["CC Responsable ID"]
            sel_cc_nombre = tabla_cc.iloc[0]["CC Responsable"]
    else:
        sel_cc_id = tabla_cc.iloc[0]["CC Responsable ID"]
        sel_cc_nombre = tabla_cc.iloc[0]["CC Responsable"]

    # --- KPIS DE LA UNIDAD SELECCIONADA ---
    st.markdown("---")
    st.subheader(f"📊 Detalle de: {sel_cc_nombre}")

    resumen_filtrado_cc = resumen_filtrado[resumen_filtrado["CC Responsable ID"] == sel_cc_id]
    
    if resumen_filtrado_cc.empty:
        st.info("No se encontraron actividades con el estado seleccionado en esta unidad orgánica.")
    else:
        total_unidad = len(resumen_filtrado_cc)
        verde_unidad = len(resumen_filtrado_cc[resumen_filtrado_cc["Color"] == COLOR_VERDE])
        amarillo_unidad = len(resumen_filtrado_cc[resumen_filtrado_cc["Color"] == COLOR_AMARILLO])
        rojo_unidad = len(resumen_filtrado_cc[resumen_filtrado_cc["Color"] == COLOR_ROJO])
        morado_unidad = len(resumen_filtrado_cc[resumen_filtrado_cc["Color"] == COLOR_MORADO])
        gris_unidad = len(resumen_filtrado_cc[resumen_filtrado_cc["Color"] == COLOR_GRIS])

        if resumen_filtrado_cc["F(RE) Acum"].sum() > 0:
            promedio_ponderado = (resumen_filtrado_cc["F(SE) Acum"].sum() / resumen_filtrado_cc["F(RE) Acum"].sum()) * 100
        else:
            promedio_ponderado = 0

        col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
        col1.metric("📋 Total", total_unidad)
        col2.metric("📈 Promedio", f"{promedio_ponderado:.1f}%")
        col3.metric(f"{SEMAFORO_CONFIG['meta']['badge']} En Meta", verde_unidad)
        col4.metric(f"{SEMAFORO_CONFIG['riesgo']['badge']} En Riesgo", amarillo_unidad)
        col5.metric(f"{SEMAFORO_CONFIG['critico']['badge']} Crítico", rojo_unidad)
        col6.metric(f"{SEMAFORO_CONFIG['exceso']['badge']} Exceso", morado_unidad)
        col7.metric(f"{SEMAFORO_CONFIG['sin_dato']['badge']} Sin dato", gris_unidad)

        st.markdown("#### 📋 Cartera de Actividades")

        tabla_act = resumen_filtrado_cc[[
            "Producto ID", "Actividad Operativa", "Unidad de Medida",
            "F(SE) Acum", "F(RE) Acum", "% Ejecución",
            "Proyeccion_Dic", "Alerta_Proyeccion",
            "Estado", "Color"
        ]].copy().sort_values("% Ejecución", ascending=False)

        tabla_act["Estado"] = tabla_act.apply(formatear_estado, axis=1)
        tabla_act = tabla_act.drop(columns=["Color"])

        st.dataframe(
            tabla_act,
            column_config={
                "Actividad Operativa": st.column_config.TextColumn("Actividad", width="large"),
                "Unidad de Medida": st.column_config.TextColumn("U.M.", width="small"),
                "F(SE) Acum": st.column_config.NumberColumn("Ejecutado", format="%.0f"),
                "F(RE) Acum": st.column_config.NumberColumn("Programado", format="%.0f"),
                "% Ejecución": st.column_config.ProgressColumn(
                    "Cumplimiento",
                    format="%.1f %%",
                    min_value=0,
                    max_value=100,
                    width="medium"
                ),
                "Proyeccion_Dic": st.column_config.NumberColumn("Proy. Dic", format="%.0f"),
                "Alerta_Proyeccion": st.column_config.TextColumn("Alerta", width="small"),
                "Estado": st.column_config.TextColumn("Estado", width="small")
            },
            use_container_width=True,
            height=250,
            on_select="rerun",
            selection_mode="single-row",
            key="df_act_cc_mejorado"
        )

        if "selection" in st.session_state.get("df_act_cc_mejorado", {}) and st.session_state["df_act_cc_mejorado"]["selection"]["rows"]:
            idx_act = st.session_state["df_act_cc_mejorado"]["selection"]["rows"][0]
            if idx_act < len(tabla_act):
                sel_act = tabla_act.iloc[idx_act]["Actividad Operativa"]
            else:
                sel_act = tabla_act.iloc[0]["Actividad Operativa"]
        else:
            sel_act = tabla_act.iloc[0]["Actividad Operativa"]

        st.markdown("---")
        st.markdown(f"### 📅 Evolución Mensual y Proyección al Cierre")
        st.markdown(f"**Actividad Auditada:** `{sel_act}`")

        df_act_sel = df[df["Actividad Operativa"] == sel_act]
        info_act = resumen_filtrado_cc[resumen_filtrado_cc["Actividad Operativa"] == sel_act].iloc[0]

        meses_restantes = [MESES_NOMBRE[m] for m in range(last_month + 1, 13)]
        n_restantes = len(meses_restantes)

        if last_month >= 3:
            ult_cols = fse_cols[-3:]
            ritmo_mensual = df_act_sel[ult_cols].sum(axis=1).values[0] / 3
            fuente_ritmo = "Promedio móvil (últimos 3 meses)"
        elif last_month > 0:
            ritmo_mensual = df_act_sel[fse_cols].sum(axis=1).values[0] / len(fse_cols)
            fuente_ritmo = f"Promedio Ene-{month_names[last_month]}"
        else:
            ritmo_mensual = 0
            fuente_ritmo = "Sin datos suficientes"

        ejec_actual = info_act['F(SE) Acum']
        prog_acumulado = info_act['F(RE) Acum']
        proyeccion_cierre = ejec_actual + (ritmo_mensual * n_restantes)

        todas_fre_cols = [c for c in df.columns if "F(RE)" in c and any(str(i).zfill(2) in c for i in range(1, 13))]
        meta_anual_programada = df_act_sel[todas_fre_cols].sum(axis=1).values[0] if todas_fre_cols else prog_acumulado
        
        pct_proy = (proyeccion_cierre / meta_anual_programada * 100) if meta_anual_programada > 0 else 0

        # Fila 1: Métricas
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Unidad de Medida", str(info_act["Unidad de Medida"]))
        m2.metric(f"Programado (ene-{month_names[last_month]})", f"{prog_acumulado:,.0f}")
        m3.metric(f"Ejecutado (ene-{month_names[last_month]})", f"{ejec_actual:,.0f}")
        m4.metric("Cumplimiento Actual", f"{info_act['% Ejecución']*100:.1f}%")

        # Fila 2: Cajas Sombreadas
        c_proy1, c_proy2, c_proy3, c_proy4 = st.columns(4)

        with c_proy1:
            st.markdown(f"""
            <div class="kpi-card" style="border-left: 5px solid #17a2b8;">
                <div class="kpi-title">Ritmo Mensual Reciente</div>
                <div class="kpi-value">{ritmo_mensual:,.0f} <span style="font-size:0.85rem; font-weight: normal;">/ mes</span></div>
                <div class="kpi-sub">{fuente_ritmo}</div>
            </div>
            """, unsafe_allow_html=True)

        with c_proy2:
            st.markdown(f"""
            <div class="kpi-card" style="border-left: 5px solid {COLOR_AMARILLO};">
                <div class="kpi-title">Proyección Cierre (Dic)</div>
                <div class="kpi-value">{proyeccion_cierre:,.0f}</div>
                <div class="kpi-sub">Real ene-{month_names[last_month]} + {n_restantes} m. proy.</div>
            </div>
            """, unsafe_allow_html=True)

        with c_proy3:
            st.markdown(f"""
            <div class="kpi-card" style="border-left: 5px solid {COLOR_GRIS};">
                <div class="kpi-title">Meta Anual Programada</div>
                <div class="kpi-value">{meta_anual_programada:,.0f}</div>
                <div class="kpi-sub">Total POI (Ene - Dic)</div>
            </div>
            """, unsafe_allow_html=True)

        with c_proy4:
            color_meta = COLOR_VERDE if (UMBRAL_META_MIN * 100) <= pct_proy <= (UMBRAL_EXCESO * 100) else (COLOR_ROJO if pct_proy < (UMBRAL_RIESGO_MIN * 100) else COLOR_AMARILLO)
            st.markdown(f"""
            <div class="kpi-card" style="border-left: 5px solid {color_meta};">
                <div class="kpi-title">Cumplimiento al Cierre</div>
                <div class="kpi-value">{pct_proy:.1f}%</div>
                <div class="kpi-sub">Proyección vs Meta Anual</div>
            </div>
            """, unsafe_allow_html=True)

        st.caption("📌 *Proyección calculada con el promedio móvil de los últimos 3 meses para el periodo restante.*")

        color_act = info_act["Color"]
        mes_labels = month_names[1:len(fse_cols)+1]
        valores_se = [df_act_sel[c].sum() for c in fse_cols]
        valores_re = [df_act_sel[c].sum() for c in fre_cols]
        pct_mensual = [(se / re * 100) if re > 0 else 0 for se, re in zip(valores_se, valores_re)]

        fig_mensual = make_subplots(specs=[[{"secondary_y": False}]])

        fig_mensual.add_trace(
            go.Bar(
                x=mes_labels,
                y=valores_se,
                name="Ejecutado Real F(SE)",
                marker_color=color_act,
                customdata=np.array([valores_re, pct_mensual]).T,
                hovertemplate=(
                    "<b>Ejecutado:</b> %{y:,.0f}<br>"
                    "<b>Programado:</b> %{customdata[0]:,.0f}<br>"
                    "<b>% Ejecución:</b> %{customdata[1]:.1f}%"
                    "<extra></extra>"
                )
            )
        )

        if ritmo_mensual > 0 and n_restantes > 0:
            fig_mensual.add_trace(
                go.Bar(
                    x=meses_restantes,
                    y=[ritmo_mensual] * n_restantes,
                    name=f"Proyectado ({fuente_ritmo})",
                    marker=dict(
                        color="rgba(23, 162, 184, 0.20)",
                        line=dict(color="#17a2b8", width=1.5),
                        pattern_shape="/"
                    ),
                    hovertemplate=(
                        "<b>Proyección %{x}:</b> %{y:,.0f}<br>"
                        "<i>Estimado mensual</i><extra></extra>"
                    )
                )
            )

        fig_mensual.add_trace(
            go.Scatter(
                x=mes_labels,
                y=valores_re,
                name="Programado POI F(RE)",
                mode="lines+markers",
                line=dict(color=COLOR_ROJO, width=2.5),
                hoverinfo="skip"
            )
        )

        fig_mensual.update_layout(
            hovermode="closest",
            height=300,
            margin=dict(l=20, r=20, t=20, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(
                categoryorder="array",
                categoryarray=month_names[1:]
            )
        )
        st.plotly_chart(fig_mensual, use_container_width=True)

        pct_act = info_act['% Ejecución']
        if pct_act < UMBRAL_RIESGO_MIN:
            st.error(f"🚨 **Inconsistencia por Subejecución ({pct_act*100:.1f}%):** Esta actividad se encuentra críticamente por debajo de la meta física.")
        elif pct_act > UMBRAL_EXCESO:
            st.warning(f"⚠️ **Alerta por Sobreejecución ({pct_act*100:.1f}%):** La ejecución física supera lo planificado.")
        else:
            st.success("🟢 **Consistencia Correcta:** Avance físico dentro de los rangos óptimos.")

        if st.button("🔙 Limpiar selección"):
            st.session_state["reset_seleccion"] = True
            st.rerun()

# ============================================================================
# 5. FUNCIÓN PRINCIPAL
# ============================================================================

def ejecutar_dashboard_poi():
    """Punto de entrada de la aplicación Streamlit."""
    archivo_encontrado = encontrar_archivo_ceplan()
    
    if archivo_encontrado:
        EXCEL_PATH = archivo_encontrado
        fecha_actualizacion = extraer_fecha_corte(EXCEL_PATH)
        st.sidebar.success(f"✅ Archivo: {os.path.basename(EXCEL_PATH)}")
        st.sidebar.caption(f"📅 **Corte de datos:** {fecha_actualizacion}")
    else:
        st.error("❌ No se encontró ningún archivo de CEPLAN")
        st.info("📥 Coloca un archivo descargado de CEPLAN en la raíz o en la carpeta **POI/**")
        if not os.path.exists("POI"):
            os.makedirs("POI")
        return

    # --- CABECERA INSTITUCIONAL CON LOGO PARAMETRIZADO ---
    col_minsa, col_titulo, col_inmp = st.columns([2.2, 5, 1.5], vertical_alignment="center")

    with col_minsa:
        if os.path.exists("MINSA logo1.png"):
            st.image("MINSA logo1.png", use_container_width=True)

    with col_titulo:
        st.markdown(f"<h2 style='text-align: center; margin-bottom: 0;'>{APP_TITLE}</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #555; margin-top: 2px; margin-bottom: 4px; font-weight: 500;'>Oficina Ejecutiva de Planeamiento Estratégico</p>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; font-size: 0.85rem; color: #777;'>📅 Última actualización: <b>{fecha_actualizacion}</b></p>", unsafe_allow_html=True)

    with col_inmp:
        # Usa el logo nuevo en blanco si existe en assets, o retrocede al clásico
        if os.path.exists(LOGO_DARK):
            st.image(LOGO_DARK, width=120)
        elif os.path.exists("logo-inmp.png"):
            st.image("logo-inmp.png", width=120)

    st.divider()

    try:
        df = load_data(EXCEL_PATH)
        resumen = get_resumen(df)
        resumen_cc = get_resumen_cc_responsable(df)
    except Exception as e:
        st.error(f"❌ Error al cargar datos: {e}")
        import traceback
        st.code(traceback.format_exc())
        return
    
    year = df.attrs.get("year", 2026)
    last_month = df.attrs.get("last_month", datetime.now().month)
    fse_cols = df.attrs.get("fse_cols", [])
    fre_cols = df.attrs.get("fre_cols", [])
    
    if last_month < 1 or last_month > 12:
        last_month = datetime.now().month
    
    month_names = [""] + [MESES_NOMBRE[i] for i in range(1, 13)]
    mod_time = os.path.getmtime(EXCEL_PATH)
    fecha_archivo = datetime.fromtimestamp(mod_time).strftime('%d/%m/%Y %H:%M')

    # Header de Período
    st.header(f"{APP_ICON} Seguimiento de Metas Físicas POI")
    
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    with col1:
        st.markdown(f"**Año:** {year} | **Período:** ene - {month_names[last_month]}")
    with col2:
        st.markdown(f"**Última actualización:** {fecha_archivo}")
    with col3:
        st.caption(f"📁 Archivo: {os.path.basename(EXCEL_PATH)}")
    with col4:
        if st.button("🔄 Recargar", help="Forzar recarga de datos"):
            st.cache_data.clear()
            st.rerun()

    # =========================================================================
    # PREPARACIÓN DE DATOS MACRO INSTITUCIONALES (205 AO ACTIVAS)
    # =========================================================================
    ao_activas = df[(df["Activo AO"] == "SI") & (df["F(RE) Acum"] > 0)].copy()

    # Conteo con umbrales de config.py
    n_exceso = (ao_activas["% Avance_Real"] > UMBRAL_EXCESO).sum()
    n_meta = ((ao_activas["% Avance_Real"] >= UMBRAL_META_MIN) & (ao_activas["% Avance_Real"] <= UMBRAL_EXCESO)).sum()
    n_riesgo = ((ao_activas["% Avance_Real"] >= UMBRAL_RIESGO_MIN) & (ao_activas["% Avance_Real"] < UMBRAL_META_MIN)).sum()
    n_critico = ((ao_activas["% Avance_Real"] > UMBRAL_CRITICO_MIN) & (ao_activas["% Avance_Real"] < UMBRAL_RIESGO_MIN)).sum()
    n_sin_dato = (ao_activas["% Avance_Real"] == 0.0).sum()

    # =========================================================================
    # PANEL GERENCIAL - DIRECCIÓN GENERAL
    # =========================================================================
    with st.container(border=True):
        col_tit, col_toggle = st.columns([3.5, 1.5], vertical_alignment="center")
        
        with col_tit:
            st.markdown("### 🏛️ Situación Global y Pronóstico POI")
        
        with col_toggle:
            criterio_ceplan = st.toggle(
                "🔒 Truncar avances al 100% (Norma CEPLAN)",
                value=False,
                help="Activado: Aplica el tope del 100 % de la directiva CEPLAN para auditorías. Desactivado: Muestra la sobreejecución y el avance real del gasto operativo."
            )

        if criterio_ceplan:
            avance_institucional = ao_activas["% Avance_CEPLAN"].mean() * 100
            cierre_institucional = ao_activas["% Proy_CEPLAN"].mean() * 100
            txt_modo = "Cálculo oficial con Avance Truncado al 100% (Metodología aplicativo CEPLAN)"
        else:
            avance_institucional = ao_activas["% Avance_Real"].mean() * 100
            cierre_institucional = ao_activas["% Proy_Real"].mean() * 100
            txt_modo = "Cálculo con Avance Real Acumulado (Permite auditar sobreejecución y desvíos)"

        st.caption(f"📌 **Metodología activa:** {txt_modo}")

        col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
        
        with col_kpi1:
            st.metric(
                label=f"📈 Avance Global Ene-{month_names[last_month]}",
                value=f"{avance_institucional:.1f} %",
                delta="Consolidado Institucional"
            )
        
        with col_kpi2:
            delta_val = cierre_institucional - avance_institucional
            st.metric(
                label="🎯 Pronóstico Cierre Anual",
                value=f"{cierre_institucional:.1f} %",
                delta=f"{delta_val:+.1f}% estimado",
                delta_color="normal" if cierre_institucional >= PROYECCION_MODERADA else "inverse"
            )
            
        with col_kpi3:
            st.metric(
                label=f"{SEMAFORO_CONFIG['exceso']['badge']} {SEMAFORO_CONFIG['exceso']['label']}",
                value=f"{n_exceso} AO",
                help="Metas físicas que ya superaron lo programado para el período",
                delta="Revisión de consistencia",
                delta_color="inverse"
            )
            
        with col_kpi4:
            st.metric(
                label=f"{SEMAFORO_CONFIG['critico']['badge']} Alerta Crítica (< 75%)",
                value=f"{n_critico + n_sin_dato} AO",
                delta=f"{n_sin_dato} sin ejecución",
                delta_color="inverse"
            )

        # Diagnóstico gerencial dinámico
        if cierre_institucional >= PROYECCION_OPTIMA and not criterio_ceplan:
            st.success(
                f"🟢 **Diagnóstico:** El INMP proyecta una ejecución real anual del **{cierre_institucional:.1f}%**. "
                f"Existen **{n_exceso} actividades en exceso** que impulsan el promedio y ameritan reprogramación."
            )
        elif cierre_institucional >= PROYECCION_MODERADA:
            st.warning(
                f"🟡 **Diagnóstico:** Pronóstico dentro del margen moderado (**{cierre_institucional:.1f}%**). "
                f"Se requiere acelerar las **{n_critico} actividades con ejecución deficiente**."
            )
        else:
            st.error(
                f"🔴 **Alerta Directiva:** Tendencia de subejecución crítica. Se proyecta un cierre global de **{cierre_institucional:.1f}%**."
            )
    
    # Métricas Globales Semáforo
    total_act = len(resumen)
    act_verde = len(resumen[resumen["Color"] == COLOR_VERDE])
    act_amarillo = len(resumen[resumen["Color"] == COLOR_AMARILLO])
    act_rojo = len(resumen[resumen["Color"] == COLOR_ROJO])
    act_morado = len(resumen[resumen["Color"] == COLOR_MORADO])
    act_gris = len(resumen[resumen["Color"] == COLOR_GRIS])
    
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("📊 Total", total_act)
    c2.metric(f"{SEMAFORO_CONFIG['meta']['badge']} En Meta", act_verde)
    c3.metric(f"{SEMAFORO_CONFIG['riesgo']['badge']} En Riesgo", act_amarillo)
    c4.metric(f"{SEMAFORO_CONFIG['critico']['badge']} Crítico", act_rojo)
    c5.metric(f"{SEMAFORO_CONFIG['exceso']['badge']} Exceso", act_morado)
    c6.metric(f"{SEMAFORO_CONFIG['sin_dato']['badge']} Sin dato", act_gris)
        
    st.markdown("##### 📘 **Criterios de semaforización (Directiva CEPLAN):**")
    st.markdown(
        f"<div style='background-color:#1e1e1e; padding:10px; border-radius:8px; "
        f"border-left:4px solid #17a2b8; font-size:14px; color:#e0e0e0; margin-bottom:15px;'>"
        f"{SEMAFORO_CONFIG['meta']['badge']} <b>{SEMAFORO_CONFIG['meta']['label']}</b>  |  "
        f"{SEMAFORO_CONFIG['riesgo']['badge']} <b>{SEMAFORO_CONFIG['riesgo']['label']}</b>  |  "
        f"{SEMAFORO_CONFIG['critico']['badge']} <b>{SEMAFORO_CONFIG['critico']['label']}</b>  |  "
        f"{SEMAFORO_CONFIG['exceso']['badge']} <b>{SEMAFORO_CONFIG['exceso']['label']}</b>  |  "
        f"{SEMAFORO_CONFIG['sin_dato']['badge']} <b>{SEMAFORO_CONFIG['sin_dato']['label']}</b>"
        f"</div>",
        unsafe_allow_html=True
    )

    with st.expander("📖 Ver detalle completo de la Directiva CEPLAN"):
        st.markdown(f"""
        **Criterios de semaforización para el seguimiento de metas físicas:**
        - **{SEMAFORO_CONFIG['meta']['badge']} {SEMAFORO_CONFIG['meta']['label']}:** {SEMAFORO_CONFIG['meta']['diagnostico']}.
        - **{SEMAFORO_CONFIG['riesgo']['badge']} {SEMAFORO_CONFIG['riesgo']['label']}:** {SEMAFORO_CONFIG['riesgo']['diagnostico']}.
        - **{SEMAFORO_CONFIG['critico']['badge']} {SEMAFORO_CONFIG['critico']['label']}:** {SEMAFORO_CONFIG['critico']['diagnostico']}.
        - **{SEMAFORO_CONFIG['exceso']['badge']} {SEMAFORO_CONFIG['exceso']['label']}:** {SEMAFORO_CONFIG['exceso']['diagnostico']}.
        - **{SEMAFORO_CONFIG['sin_dato']['badge']} {SEMAFORO_CONFIG['sin_dato']['label']}:** {SEMAFORO_CONFIG['sin_dato']['diagnostico']}.
        """)

    # Renderizado de pestañas
    tab1, tab2 = st.tabs(["Programa / Categoría Presupuestal", "Unidad Orgánica"])
    
    with tab1:
        tab_resumen_categoria(df, resumen, fse_cols, fre_cols, last_month, month_names, fecha_archivo, year)
  
    with tab2:
        tab_unidad_organica(df, resumen, resumen_cc, fse_cols, fre_cols, last_month, month_names, fecha_archivo, year)

if __name__ == "__main__":
    ejecutar_dashboard_poi()