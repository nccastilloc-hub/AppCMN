"""
Dashboard de Seguimiento de Metas Físicas POI - Versión Streamlit
==================================================================
Módulo Streamlit para integración en el menú principal de Gestión IPRESS.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import os
import glob
import re

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

# Colores de semáforo
COLOR_MORADO = "#6f42c1"
COLOR_VERDE = "#28a745"
COLOR_AMARILLO = "#ffc107"
COLOR_ROJO = "#dc3545"
COLOR_GRIS = "#495057"

# Detectar entorno automáticamente
def get_base_dir():
    """Detecta si estamos en local o en Streamlit Cloud."""
    # En Streamlit Cloud, usar la raíz del repo
    if os.environ.get("STREAMLIT_SHARING") == "1" or os.environ.get("STREAMLIT_CLOUD"):
        return os.getcwd()
    
    # En local, verificar si existe D:\app\AppCMN
    if os.path.exists(r"D:\app\AppCMN"):
        return r"D:\app\AppCMN"
    
    # Fallback: usar la carpeta actual
    return os.getcwd()

BASE_DIR = get_base_dir()

def formatear_estado(row):
    """Formatea el estado con un emoji de color según el semáforo."""
    color = row["Color"]
    estado = row["Estado"]
    
    emoji_map = {
        COLOR_VERDE: "🟢",
        COLOR_AMARILLO: "🟡", 
        COLOR_ROJO: "🔴",
        COLOR_MORADO: "🟣",
        COLOR_GRIS: "⚫"
    }
    
    emoji = emoji_map.get(color, "⚫")
    
    # Extraer solo la parte descriptiva
    partes = estado.split(" - ")
    estado_limpio = partes[-1] if len(partes) > 1 else estado
    
    return f"{emoji} {estado_limpio}"

# ============================================================================
# FUNCIONES DE UTILIDAD
# ============================================================================

#import os

def encontrar_archivo_ceplan():
    """Busca el archivo de POI ya convertido por el asistente."""
    
    # Crear carpeta si no existe
    if not os.path.exists(BASE_DIR):
        os.makedirs(BASE_DIR)
        st.info(f"📁 Carpeta creada: {BASE_DIR}")
        return None
    
    # Buscar el archivo convertido
    patrones = [
        os.path.join(BASE_DIR, "Seguimiento metas fisicas POI.xlsx"),
        os.path.join(BASE_DIR, "Seguimiento metas fisicas POI.xls"),
        os.path.join(BASE_DIR, "*.xlsx"),
        os.path.join(BASE_DIR, "*.xls"),
    ]
    
    for patron in patrones:
        if "*" not in patron:
            if os.path.exists(patron):
                return patron
        else:
            archivos = glob.glob(patron)
            # Filtrar solo archivos que parezcan de POI
            archivos_filtrados = [a for a in archivos if "POI" in a.upper() or "METAS" in a.upper() or "SEGUIMIENTO" in a.upper()]
            if archivos_filtrados:
                archivos_filtrados.sort(key=os.path.getmtime, reverse=True)
                return archivos_filtrados[0]
            elif archivos:
                archivos.sort(key=os.path.getmtime, reverse=True)
                return archivos[0]
    
    # Si no encuentra, mostrar mensaje
    st.warning("⚠️ No se encontró el archivo 'Seguimiento metas fisicas POI.xlsx'")
    st.info(f"📥 Coloca el archivo en: `{BASE_DIR}`")
    
    return None

def detect_last_month(df):
    """Detecta automáticamente el último mes con datos de ejecución real."""
    fse_cols = [col for col in df.columns if "F(SE)" in col and any(str(i).zfill(2) in col for i in range(1, 13))]
    
    if not fse_cols:
        fse_cols = [col for col in df.columns if "F(RE)" in col and any(str(i).zfill(2) in col for i in range(1, 13))]
    
    def extract_month(col):
        match = re.search(r'(\d{1,2})', col)
        return int(match.group(1)) if match else 0
    
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
    """Extrae el número de mes de una columna."""
    match = re.search(r'(\d{1,2})', str(col))
    return int(match.group(1)) if match else 99

# ============================================================================
# FUNCIONES DE CARGA Y PROCESAMIENTO
# ============================================================================

@st.cache_data
def load_data(excel_path):
    """Carga el archivo Excel ya convertido por el asistente."""
    
    try:
        # Leer el archivo Excel directamente
        df = pd.read_excel(excel_path, sheet_name="DATA", header=0)
        st.success("✅ Archivo Excel cargado correctamente")
        
    except Exception as e:
        # Si falla, intentar leer sin especificar hoja
        try:
            df = pd.read_excel(excel_path, header=0)
            st.success("✅ Archivo Excel cargado correctamente")
        except Exception as e2:
            st.error(f"❌ Error al leer el archivo Excel: {e2}")
            raise e2
    
    # Limpiar nombres de columnas
    df.columns = df.columns.str.strip()
    
    # Filtrar solo actividades activas
    if "Activo AO" in df.columns:
        df = df[df["Activo AO"] == "SI"].copy()
    
    # Detectar columnas de meses
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
    
    # Calcular totales
    df["F(SE) Acum"] = df[fse_cols].sum(axis=1) if fse_cols else 0
    df["F(RE) Acum"] = df[fre_cols].sum(axis=1) if fre_cols else 0
    
    df["% Ejecución"] = np.where(
        df["F(RE) Acum"] > 0,
        df["F(SE) Acum"] / df["F(RE) Acum"],
        0
    )
    
    df["Estimación Dic"] = np.where(
        last_month > 0,
        df["F(SE) Acum"] / last_month * 12,
        0
    )
    
    # Semáforo
    def semaforo(row):
        pct = row["% Ejecución"]
        if row["F(RE) Acum"] == 0:
            return "Sin ejecución", COLOR_GRIS
        elif pct == 0:
            return "GRIS", COLOR_GRIS
        elif pct < 0.85:
            return "ROJO - DEFICIENTE", COLOR_ROJO
        elif pct < 0.90:
            return "AMARILLO - REGULAR", COLOR_AMARILLO
        elif pct <= 1.00:
            return "VERDE - BUENO", COLOR_VERDE
        else:
            return "MORADO - EXCESO", COLOR_MORADO
    
    df[["Estado", "Color"]] = df.apply(semaforo, axis=1, result_type="expand")
    
    # CV y tendencia
    fse_data = df[fse_cols].values if fse_cols else np.zeros((len(df), 1))
    with np.errstate(divide='ignore', invalid='ignore'):
        df["CV"] = np.nanstd(fse_data, axis=1) / np.nanmean(fse_data, axis=1)
    df["CV"] = df["CV"].replace([np.inf, -np.inf], 0).fillna(0)
    
    if last_month >= 6:
        ult_trim_cols = fse_cols[-3:] if len(fse_cols) >= 3 else fse_cols
        prev_trim_cols = fse_cols[-6:-3] if len(fse_cols) >= 6 else []
        if ult_trim_cols and prev_trim_cols:
            ult_trim = df[ult_trim_cols].sum(axis=1)
            prev_trim = df[prev_trim_cols].sum(axis=1)
            with np.errstate(divide='ignore', invalid='ignore'):
                df["Tendencia"] = np.where(prev_trim > 0, (ult_trim - prev_trim) / prev_trim * 100, 0)
        else:
            df["Tendencia"] = 0
    else:
        df["Tendencia"] = 0
    
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
        "% Ejecución": "mean",
        "Estimación Dic": "sum",
        "CV": "mean",
        "Tendencia": "mean"
    }
    
    resumen = df.groupby(group_cols, as_index=False).agg(agg_dict)
    
    resumen["% Ejecución"] = np.where(
        resumen["F(RE) Acum"] > 0,
        resumen["F(SE) Acum"] / resumen["F(RE) Acum"],
        0
    )
    
    def semaforo_agg(row):
        pct = row["% Ejecución"]
        if row["F(RE) Acum"] == 0:
            return "Sin ejecución", COLOR_GRIS
        elif pct == 0:
            return "GRIS", COLOR_GRIS
        elif pct < 0.85:
            return "ROJO - DEFICIENTE", COLOR_ROJO
        elif pct < 0.90:
            return "AMARILLO - REGULAR", COLOR_AMARILLO
        elif pct <= 1.00:
            return "VERDE - BUENO", COLOR_VERDE
        else:
            return "MORADO - EXCESO", COLOR_MORADO
    
    resumen[["Estado", "Color"]] = resumen.apply(semaforo_agg, axis=1, result_type="expand")
    
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
        "CV": "mean",
        "Tendencia": "mean"
    }
    
    resumen = df.groupby(group_cols, as_index=False).agg(agg_dict)
    
    resumen["% Ejecución"] = np.where(
        resumen["F(RE) Acum"] > 0,
        resumen["F(SE) Acum"] / resumen["F(RE) Acum"],
        0
    )
    
    def semaforo_cc(row):
        pct = row["% Ejecución"]
        if row["F(RE) Acum"] == 0:
            return "Sin ejecución", COLOR_GRIS
        elif pct == 0:
            return "GRIS", COLOR_GRIS
        elif pct < 0.85:
            return "ROJO - DEFICIENTE", COLOR_ROJO
        elif pct < 0.90:
            return "AMARILLO - REGULAR", COLOR_AMARILLO
        elif pct <= 1.00:
            return "VERDE - BUENO", COLOR_VERDE
        else:
            return "MORADO - EXCESO", COLOR_MORADO
    
    resumen[["Estado", "Color"]] = resumen.apply(semaforo_cc, axis=1, result_type="expand")
    
    return resumen

def formatear_estado_con_color(row):
    """Formatea el estado con un círculo de color HTML."""
    color = row["Color"]
    estado = row["Estado"]
    return f'<span style="color:{color};font-size:16px;">●</span> {estado}'

# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def ejecutar_dashboard_poi():
    """Ejecuta el dashboard POI dentro de Streamlit."""
    
    # --- BUSCAR ARCHIVO ---
    archivo_encontrado = encontrar_archivo_ceplan()
    
    if archivo_encontrado:
        EXCEL_PATH = archivo_encontrado
        st.sidebar.success(f"✅ Archivo: {os.path.basename(EXCEL_PATH)}")
        st.sidebar.caption(f"📁 Última modificación: {datetime.fromtimestamp(os.path.getmtime(EXCEL_PATH)).strftime('%d/%m/%Y %H:%M')}")
    else:
        st.error("❌ No se encontró ningún archivo de CEPLAN")
        st.info("📥 Coloca un archivo descargado de CEPLAN en la carpeta **POI/**")
        if not os.path.exists("POI"):
            os.makedirs("POI")
            st.success("✅ Carpeta POI/ creada")
        return
    
    if not os.path.exists(EXCEL_PATH):
        st.error(f"❌ Archivo no encontrado: '{EXCEL_PATH}'")
        return
    
    # --- CARGAR DATOS ---
    try:
        df = load_data(EXCEL_PATH)
        resumen = get_resumen(df)
        resumen_cc = get_resumen_cc_responsable(df)
    except Exception as e:
        st.error(f"❌ Error al cargar datos: {e}")
        import traceback
        st.code(traceback.format_exc())
        return
    
    # --- METADATOS ---
    year = df.attrs.get("year", 2026)
    last_month = df.attrs.get("last_month", datetime.now().month)
    fse_cols = df.attrs.get("fse_cols", [])
    fre_cols = df.attrs.get("fre_cols", [])
    
    if last_month < 1 or last_month > 12:
        last_month = datetime.now().month
    
    month_names = ["", "Ene", "Feb", "Mar", "Abr", "May", "Jun", 
                   "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    
    # --- HEADER ---
    st.header("📊 Seguimiento de Metas Físicas POI")
    
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    with col1:
        st.markdown(f"**Año:** {year} | **Período:** Ene - {month_names[last_month]}")
    with col2:
        st.markdown(f"**Última actualización:** {datetime.now().strftime('%d/%m/%Y')}")
    with col3:
        if os.path.exists(EXCEL_PATH):
            mod_time = os.path.getmtime(EXCEL_PATH)
            st.caption(f"📁 Archivo: {datetime.fromtimestamp(mod_time).strftime('%H:%M:%S')}")
    with col4:
        if st.button("🔄 Recargar", help="Forzar recarga de datos desde el archivo"):
            st.cache_data.clear()
            st.rerun()
    
    # --- KPIS (CON MORADO INCLUIDO) ---
    total_act = len(resumen)
    act_verde = len(resumen[resumen["Color"] == COLOR_VERDE])
    act_amarillo = len(resumen[resumen["Color"] == COLOR_AMARILLO])
    act_rojo = len(resumen[resumen["Color"] == COLOR_ROJO])
    act_morado = len(resumen[resumen["Color"] == COLOR_MORADO])
    act_gris = len(resumen[resumen["Color"] == COLOR_GRIS])
    
    # Mostrar KPIs en 6 columnas
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        st.metric("📊 Total", total_act)
    with col2:
        st.metric("🟢 En Meta", act_verde)
    with col3:
        st.metric("🟡 En Riesgo", act_amarillo)
    with col4:
        st.metric("🔴 Crítico", act_rojo)
    with col5:
        st.metric("🟣 Exceso", act_morado)  # ¡MORADO!
    with col6:
        st.metric("⚫ Sin dato", act_gris)
    
    # --- PESTAÑAS ---
    tab1, tab2 = st.tabs(["Programa/Categoria Presupuestal", "Unidad Orgánica"])
    
    # ========================================================================
    # TAB 1
    # ========================================================================
    with tab1:
        st.subheader("🎯 Control de Gestión y Consistencia POI")
        
        st.markdown("### 🎛️ Filtro de Control de Daños (Enfoque Ejecutivo)")
        
        opciones_semaforo = {
            "🔍 Ver Todo el Universo POI": "TODOS",
            "🟢 En Meta (Bueno)": COLOR_VERDE,
            "🟡 En Riesgo (Regular)": COLOR_AMARILLO,
            "🔴 Crítico (Deficiente)": COLOR_ROJO,
            "🟣 En Exceso (Sobreejecución)": COLOR_MORADO,
            "⚪ Sin Ejecución Registrada": COLOR_GRIS
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
        
        # Selector de categoría
        if "Categoria ID" in df_filtrado_semaforo.columns and not df_filtrado_semaforo.empty:
            df_ordenado = df_filtrado_semaforo[['Categoria ID', 'Categoria']].drop_duplicates().sort_values('Categoria ID')
            categorias_unicas = df_ordenado['Categoria'].dropna().tolist()
        else:
            categorias_unicas = []
        
        sel_categoria = st.selectbox(
            "🔍 Seleccione una Categoría para evaluar el detalle (Drilldown):",
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
        
        # Gráficos
        if not resumen_gerencial.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                cant_verde = len(resumen_gerencial[resumen_gerencial["Color"] == COLOR_VERDE])
                cant_amarillo = len(resumen_gerencial[resumen_gerencial["Color"] == COLOR_AMARILLO])
                cant_rojo = len(resumen_gerencial[resumen_gerencial["Color"] == COLOR_ROJO])
                cant_morado = len(resumen_gerencial[resumen_gerencial["Color"] == COLOR_MORADO])
                cant_gris = len(resumen_gerencial[resumen_gerencial["Color"] == COLOR_GRIS])
                
                fig_semaforo = go.Figure(data=[
                    go.Bar(
                        x=["🟢 En Meta", "🟡 En Riesgo", "🔴 Crítico", "🟣 Exceso", "⚫ Sin dato"],
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
                
                # 🔥 COLOR DINÁMICO SEGÚN FILTRO SELECCIONADO
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
                        textposition="auto"
                    )
                ])
                fig_dinamico.update_layout(title=titulo_graf, xaxis_title="%", margin=dict(l=150, r=20, t=40, b=20), height=300)
                st.plotly_chart(fig_dinamico, use_container_width=True)
        
        # Tabla interactiva
        st.markdown("---")
        st.subheader("📋 Carpintería Operativa: Localizador de Inconsistencias")
        
        if resumen_gerencial.empty:
            st.info("No existen actividades operativas registradas bajo los filtros seleccionados.")
        else:
            st.markdown("💡 *Haga clic en **cualquier fila** de la tabla para cargar instantáneamente su radiografía y evolución mensual abajo.*")
            
            columnas_visibles = [c for c in ["Categoria ID", "Producto ID", "Actividad Operativa", "Unidad de Medida", "F(SE) Acum", "F(RE) Acum", "% Ejecución", "Estado", "Color"] if c in resumen_gerencial.columns]
            tabla_operativa = resumen_gerencial[columnas_visibles].copy()
            
            if "Categoria ID" in tabla_operativa.columns:
                tabla_operativa = tabla_operativa.sort_values(by=["Categoria ID"])
            
            tabla_formateada = tabla_operativa.copy()
            tabla_formateada["F(SE) Acum"] = tabla_formateada["F(SE) Acum"].apply(lambda x: f"{x:,.0f}")
            tabla_formateada["F(RE) Acum"] = tabla_formateada["F(RE) Acum"].apply(lambda x: f"{x:,.0f}")
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
            
                # --- DETALLE MENSUAL CON COLOR DINÁMICO ---
                st.markdown("---")
                st.markdown(f"### 📅 Evolución Mensual Automatizada")
                st.markdown(f"**Actividad Auditada:** {sel_actividad}")

                # Obtener información de la actividad seleccionada
                df_actividad_seleccionada = df[df["Actividad Operativa"] == sel_actividad]
                info_act = resumen_gerencial[resumen_gerencial["Actividad Operativa"] == sel_actividad].iloc[0]

                # Métricas
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Unidad de Medida", info_act["Unidad de Medida"])
                c2.metric("Programado Acum. F(RE)", f"{info_act['F(RE) Acum']:,.0f}")
                c3.metric("Ejecutado Acum. F(SE)", f"{info_act['F(SE) Acum']:,.0f}")
                c4.metric("Cumplimiento Real", f"{info_act['% Ejecución']*100:.1f}%")

                # Preparar datos del gráfico
                mes_labels = month_names[1:len(fse_cols)+1]
                valores_se = [df_actividad_seleccionada[c].sum() for c in fse_cols]
                valores_re = [df_actividad_seleccionada[c].sum() for c in fre_cols]

                # 🔥 COLOR DINÁMICO PARA EL GRÁFICO DE BARRAS
                color_map_evolucion = {
                    "TODOS": "#28a745",  # Verde por defecto
                    COLOR_VERDE: COLOR_VERDE,
                    COLOR_AMARILLO: COLOR_AMARILLO,
                    COLOR_ROJO: COLOR_ROJO,
                    COLOR_MORADO: COLOR_MORADO,
                    COLOR_GRIS: COLOR_GRIS
                }
                bar_color_evolucion = color_map_evolucion.get(color_filtrado, "#28a745")

                # Crear gráfico con color dinámico
                fig_mensual = make_subplots(specs=[[{"secondary_y": True}]])
                fig_mensual.add_trace(
                    go.Bar(
                        x=mes_labels, 
                        y=valores_se, 
                        name="Ejecutado Real F(SE)", 
                        marker_color=bar_color_evolucion  # ← Color dinámico
                    ), 
                    secondary_y=False
                )
                fig_mensual.add_trace(
                    go.Scatter(
                        x=mes_labels, 
                        y=valores_re, 
                        name="Programado POI F(RE)", 
                        mode="lines+markers", 
                        line=dict(color="#dc3545", width=3)
                    ), 
                    secondary_y=False
                )

                fig_mensual.update_layout(
                    hovermode="x unified", 
                    height=280, 
                    margin=dict(l=20, r=20, t=20, b=20),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig_mensual, use_container_width=True)

                # Mensajes de consistencia
                pct_act = info_act['% Ejecución']
                if pct_act < 0.85:
                    st.error(f"🚨 **Inconsistencia por Subejecución ({pct_act*100:.1f}%):** Esta actividad se encuentra críticamente por debajo de la meta física programada en el POI.")
                elif pct_act > 1.00:
                    st.warning(f"⚠️ **Alerta por Sobreejecución ({pct_act*100:.1f}%):** La ejecución física supera lo planificado.")
                else:
                    st.success("🟢 **Consistencia Correcta:** Los avances físicos se encuentran alineados con los rangos de tolerancia institucionales.")
  
    
    # ========================================================================
    # TAB 2: CC RESPONSABLE
    # ========================================================================
    with tab2:
        st.subheader("🏆 Ranking de Gestión por Unidad Orgánica")
        st.markdown("💡 *Haga clic en **cualquier Unidad Orgánica** para auditar sus metas físicas asignadas.*")
        
        if resumen_cc.empty:
            st.warning("⚠️ No hay datos disponibles para Unidad Orgánica en este período.")
        else:
            tabla_cc_master = resumen_cc[[
                "CC Responsable ID", "CC Responsable",
                "F(SE) Acum", "F(RE) Acum", "% Ejecución", "Estado", "Color"
            ]].copy().sort_values("% Ejecución", ascending=False)
            
            tabla_cc_formateada = tabla_cc_master.copy()
            tabla_cc_formateada["F(SE) Acum"] = tabla_cc_formateada["F(SE) Acum"].apply(lambda x: f"{x:,.0f}")
            tabla_cc_formateada["F(RE) Acum"] = tabla_cc_formateada["F(RE) Acum"].apply(lambda x: f"{x:,.0f}")
            tabla_cc_formateada["% Ejecución"] = tabla_cc_formateada["% Ejecución"].apply(lambda x: f"{x*100:.1f}%")
            tabla_cc_formateada["Estado"] = tabla_cc_formateada.apply(formatear_estado_con_color, axis=1)
            
            if "Color" in tabla_cc_formateada.columns:
                tabla_cc_formateada = tabla_cc_formateada.drop(columns=["Color"])
            
            selecciona_cc = st.dataframe(
                tabla_cc_formateada,
                use_container_width=True,
                height=230,
                on_select="rerun",
                selection_mode="single-row",
                key="df_cc_master",
                column_config={
                    "Estado": st.column_config.TextColumn("Estado", help="Estado del semáforo", width="medium")
                }
            )
            
            if selecciona_cc and "selection" in selecciona_cc and selecciona_cc["selection"]["rows"]:
                idx_cc = selecciona_cc["selection"]["rows"][0]
                if idx_cc < len(tabla_cc_master):
                    sel_cc_id = tabla_cc_master.iloc[idx_cc]["CC Responsable ID"]
                    sel_cc_nombre = tabla_cc_master.iloc[idx_cc]["CC Responsable"]
                else:
                    sel_cc_id = tabla_cc_master.iloc[0]["CC Responsable ID"]
                    sel_cc_nombre = tabla_cc_master.iloc[0]["CC Responsable"]
            else:
                sel_cc_id = tabla_cc_master.iloc[0]["CC Responsable ID"]
                sel_cc_nombre = tabla_cc_master.iloc[0]["CC Responsable"]
            
            st.markdown("---")
            st.subheader(f"🎯 Cartera de Actividades: {sel_cc_nombre}")
            
            resumen_filtrado_cc = resumen[resumen["CC Responsable ID"] == sel_cc_id]
            
            if resumen_filtrado_cc.empty:
                st.info("No se encontraron actividades operativas para esta unidad orgánica.")
            else:
                columnas_act = [c for c in ["Producto ID", "Actividad Operativa", "Unidad de Medida", "F(SE) Acum", "F(RE) Acum", "% Ejecución", "Estado", "Color"] if c in resumen_filtrado_cc.columns]
                tabla_act_cc = resumen_filtrado_cc[columnas_act].copy().sort_values("% Ejecución")
                
                tabla_act_cc_formateada = tabla_act_cc.copy()
                tabla_act_cc_formateada["F(SE) Acum"] = tabla_act_cc_formateada["F(SE) Acum"].apply(lambda x: f"{x:,.0f}")
                tabla_act_cc_formateada["F(RE) Acum"] = tabla_act_cc_formateada["F(RE) Acum"].apply(lambda x: f"{x:,.0f}")
                tabla_act_cc_formateada["% Ejecución"] = tabla_act_cc_formateada["% Ejecución"].apply(lambda x: f"{x*100:.1f}%")
                tabla_act_cc_formateada["Estado"] = tabla_act_cc_formateada.apply(formatear_estado_con_color, axis=1)
                
                if "Color" in tabla_act_cc_formateada.columns:
                    tabla_act_cc_formateada = tabla_act_cc_formateada.drop(columns=["Color"])
                
                selecciona_act_cc = st.dataframe(
                    tabla_act_cc_formateada,
                    use_container_width=True,
                    height=200,
                    on_select="rerun",
                    selection_mode="single-row",
                    key="df_act_cc",
                    column_config={
                        "Estado": st.column_config.TextColumn("Estado", help="Estado del semáforo", width="medium")
                    }
                )
                
                if selecciona_act_cc and "selection" in selecciona_act_cc and selecciona_act_cc["selection"]["rows"]:
                    idx_act = selecciona_act_cc["selection"]["rows"][0]
                    if idx_act < len(tabla_act_cc):
                        sel_act_cc = tabla_act_cc.iloc[idx_act]["Actividad Operativa"]
                    else:
                        sel_act_cc = tabla_act_cc.iloc[0]["Actividad Operativa"]
                else:
                    sel_act_cc = tabla_act_cc.iloc[0]["Actividad Operativa"]
                
                st.markdown("---")
                st.markdown(f"### 📅 Comportamiento Mensual Automatizado")
                st.markdown(f"**Actividad Auditada:** {sel_act_cc}")
                
                df_act_cc_sel = df[df["Actividad Operativa"] == sel_act_cc]
                info_act_cc = resumen_filtrado_cc[resumen_filtrado_cc["Actividad Operativa"] == sel_act_cc].iloc[0]
                
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Unidad de Medida", info_act_cc["Unidad de Medida"])
                c2.metric("Prog. Oficina F(RE)", f"{info_act_cc['F(RE) Acum']:,.0f}")
                c3.metric("Ejec. Oficina F(SE)", f"{info_act_cc['F(SE) Acum']:,.0f}")
                c4.metric("Nivel de Cumplimiento", f"{info_act_cc['% Ejecución']*100:.1f}%")
                
                mes_labels = month_names[1:len(fse_cols)+1]
                valores_se_cc = [df_act_cc_sel[c].sum() for c in fse_cols]
                valores_re_cc = [df_act_cc_sel[c].sum() for c in fre_cols]
                
                fig_mensual_cc = make_subplots(specs=[[{"secondary_y": True}]])
                fig_mensual_cc.add_trace(go.Bar(x=mes_labels, y=valores_se_cc, name="Ejecutado Oficina F(SE)", marker_color="#007bff"), secondary_y=False)
                fig_mensual_cc.add_trace(go.Scatter(x=mes_labels, y=valores_re_cc, name="Programado POI F(RE)", mode="lines+markers", line=dict(color="#dc3545", width=3)), secondary_y=False)
                
                fig_mensual_cc.update_layout(
                    hovermode="x unified",
                    height=280,
                    margin=dict(l=20, r=20, t=20, b=20),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig_mensual_cc, use_container_width=True)
                
                pct_act_cc = info_act_cc['% Ejecución']
                if pct_act_cc < 0.85:
                    st.error(f"🚨 **Alerta de Subejecución ({pct_act_cc*100:.1f}%):** Esta jefatura se encuentra rezagada en la ejecución física.")
                elif pct_act_cc > 1.00:
                    st.warning(f"⚠️ **Alerta de Sobreejecución ({pct_act_cc*100:.1f}%):** Los registros superan la meta planificada.")
                else:
                    st.success("🟢 **Metas Alcanzadas:** El Centro de Costo mantiene un ritmo de ejecución óptimo.")

# ============================================================================
# PUNTO DE ENTRADA
# ============================================================================
if __name__ == "__main__":
    ejecutar_dashboard_poi()