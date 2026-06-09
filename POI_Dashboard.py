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

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

# Ruta al archivo Excel
EXCEL_PATH = "Seguimiento metas fisicas POI.xlsx"

# Colores de semáforo
COLOR_MORADO = "#6f42c1"
COLOR_VERDE = "#28a745"
COLOR_AMARILLO = "#ffc107"
COLOR_ROJO = "#dc3545"
COLOR_GRIS = "#6c757d"

# ============================================================================
# FUNCIONES DE CARGA Y PROCESAMIENTO DE DATOS
# ============================================================================

def detect_last_month(df):
    """Detecta automáticamente el último mes con datos de ejecución real."""
    fse_cols = [f"F(SE) {i:02d}" for i in range(1, 13)]

    last_month = 0
    for i, col in enumerate(fse_cols, 1):
        if col in df.columns and df[col].sum() > 0:
            last_month = i

    # Si no hay datos en F(SE), usar F(RE) como fallback
    if last_month == 0:
        fre_cols = [f"F(RE) {i:02d}" for i in range(1, 13)]
        for i, col in enumerate(fre_cols, 1):
            if col in df.columns and df[col].sum() > 0:
                last_month = i

    return max(1, last_month)


@st.cache_data
def load_data(excel_path):
    """Carga y procesa los datos del archivo Excel."""
    # Leer hoja DATA
    df = pd.read_excel(excel_path, sheet_name="DATA", header=0)

    # Filtrar solo actividades activas
    if "Activo AO" in df.columns:
        df = df[df["Activo AO"] == "SI"].copy()

    # Detectar último mes con datos
    last_month = detect_last_month(df)

    # Columnas mensuales hasta el último mes detectado
    fse_cols = [f"F(SE) {i:02d}" for i in range(1, last_month + 1)]
    fre_cols = [f"F(RE) {i:02d}" for i in range(1, last_month + 1)]

    # Verificar que las columnas existan
    fse_cols = [c for c in fse_cols if c in df.columns]
    fre_cols = [c for c in fre_cols if c in df.columns]

    # Calcular totales acumulados
    df["F(SE) Acum"] = df[fse_cols].sum(axis=1)
    df["F(RE) Acum"] = df[fre_cols].sum(axis=1)

    # Calcular porcentaje de ejecución
    df["% Ejecución"] = np.where(
        df["F(RE) Acum"] > 0,
        df["F(SE) Acum"] / df["F(RE) Acum"],
        0
    )

    # Calcular estimación a diciembre (proyección lineal)
    df["Estimación Dic"] = np.where(
        last_month > 0,
        df["F(SE) Acum"] / last_month * 12,
        0
    )

    # Asignar semáforo
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
        else:  # pct > 1.00
            return "MORADO - EXCESO", COLOR_MORADO

    df[["Estado", "Color"]] = df.apply(semaforo, axis=1, result_type="expand")

    # Calcular coeficiente de variación (CV) para tendencia
    fse_data = df[fse_cols].values
    with np.errstate(divide="ignore", invalid="ignore"):
        df["CV"] = np.nanstd(fse_data, axis=1) / np.nanmean(fse_data, axis=1)
    df["CV"] = df["CV"].replace([np.inf, -np.inf], 0).fillna(0)

    # Tendencia: comparar último trimestre vs trimestre anterior
    if last_month >= 6:
        ult_trim_cols = [f"F(SE) {i:02d}" for i in range(max(1, last_month-2), last_month+1) if f"F(SE) {i:02d}" in df.columns]
        prev_trim_cols = [f"F(SE) {i:02d}" for i in range(max(1, last_month-5), max(1, last_month-2)) if f"F(SE) {i:02d}" in df.columns]
        if ult_trim_cols and prev_trim_cols:
            ult_trim = df[ult_trim_cols].sum(axis=1)
            prev_trim = df[prev_trim_cols].sum(axis=1)
            with np.errstate(divide="ignore", invalid="ignore"):
                df["Tendencia"] = np.where(prev_trim > 0, (ult_trim - prev_trim) / prev_trim * 100, 0)
        else:
            df["Tendencia"] = 0
    else:
        df["Tendencia"] = 0

    # Guardar metadatos
    df.attrs["last_month"] = last_month
    df.attrs["fse_cols"] = fse_cols
    df.attrs["fre_cols"] = fre_cols
    df.attrs["year"] = df["POI"].iloc[0] if "POI" in df.columns else datetime.now().year

    return df

def get_resumen(df):
    """Genera tabla resumen agregada por actividad operativa."""
    group_cols = [
        "CC Responsable ID", "CC Responsable", # 🌟 Agregados aquí para permitir el enlace en la Tab 2
        "Categoria ID", "Categoria", 
        "Producto ID", "Producto",
        "Actividad Presupuestal ID", "Actividad Presupuestal",
        "Actividad Operativa ID", "Actividad Operativa",
        "Unidad de Medida"
    ]

    # Solo columnas que existen
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

    # Recalcular % ejecución con los totales agregados
    resumen["% Ejecución"] = np.where(
        resumen["F(RE) Acum"] > 0,
        resumen["F(SE) Acum"] / resumen["F(RE) Acum"],
        0
    )

    # Asignar semáforo
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
        else:  # pct > 1.00
            return "MORADO - EXCESO", COLOR_MORADO

    resumen[["Estado", "Color"]] = resumen.apply(semaforo_agg, axis=1, result_type="expand")

    return resumen


def get_resumen_cc_responsable(df):
    """Genera tabla resumen agregada por CC Responsable."""
    group_cols = [
        "CC Responsable ID", "CC Responsable"
    ]

    # Solo columnas que existen
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

    # Recalcular % ejecución
    resumen["% Ejecución"] = np.where(
        resumen["F(RE) Acum"] > 0,
        resumen["F(SE) Acum"] / resumen["F(RE) Acum"],
        0
    )

    # Asignar semáforo
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
        else:  # pct > 1.00
            return "MORADO - EXCESO", COLOR_MORADO

    resumen[["Estado", "Color"]] = resumen.apply(semaforo_cc, axis=1, result_type="expand")

    return resumen

# ============================================================================
# FUNCIÓN PRINCIPAL DEL MÓDULO
# ============================================================================

def ejecutar_dashboard_poi():
    """Ejecuta el dashboard POI dentro de Streamlit."""
    
    # Verificar que existe el archivo
    if not os.path.exists(EXCEL_PATH):
        st.error(f"❌ Archivo no encontrado: '{EXCEL_PATH}'")
        st.info("Asegúrate de que el archivo esté en la carpeta POI/")
        return

    try:
        df = load_data(EXCEL_PATH)
        resumen = get_resumen(df)
        resumen_cc = get_resumen_cc_responsable(df)
    except Exception as e:
        st.error(f"❌ Error al cargar datos: {e}")
        return

    # Metadatos
    year = df.attrs.get("year", 2025)
    last_month = df.attrs.get("last_month", 11)
    fse_cols = df.attrs.get("fse_cols", [])
    fre_cols = df.attrs.get("fre_cols", [])

    month_names = ["", "Ene", "Feb", "Mar", "Abr", "May", "Jun", 
                   "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

    # --- HEADER ---
    st.header("📊 Seguimiento de Metas Físicas POI")
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown(f"**Año:** {year} | **Período:** Ene - {month_names[last_month]}")
    with col2:
        st.markdown(f"**Última actualización:** {datetime.now().strftime('%d/%m/%Y')}")

    # --- KPIs ---
    col1, col2, col3, col4, col5 = st.columns(5)
    
    total_act = len(resumen)
    act_verde = len(resumen[resumen["Color"] == COLOR_VERDE])
    act_amarillo = len(resumen[resumen["Color"] == COLOR_AMARILLO])
    act_rojo = len(resumen[resumen["Color"] == COLOR_ROJO])
    act_gris = len(resumen[resumen["Color"] == COLOR_GRIS])
    
    with col1:
        st.metric("Total Actividades", total_act)
    with col2:
        st.metric("🟢 En Meta", act_verde)
    with col3:
        st.metric("🟡 En Riesgo", act_amarillo)
    with col4:
        st.metric("🔴 Crítico", act_rojo)
    with col5:
        st.metric("⚪ Sin dato", act_gris)

    # --- PESTAÑAS ---
    tab1, tab2 = st.tabs(["Programa/Categoria Presupuestal", "Unidad Orgánica"])

    # ============================================================================
    # TAB 1: ACTIVIDADES OPERATIVAS (CON DRILLDOWN Y CONTROL DE SEMÁFORO GERENCIAL)
    # ============================================================================
    with tab1:
        st.subheader("🎯 Control de Gestión y Consistencia POI")

        # --------------------------------------------------------------------
        # NUEVA FUNCIÓN GERENCIAL: BOTONERA INTERACTIVA DE SEMÁFOROS
        # --------------------------------------------------------------------
        st.markdown("### 🎛️ Filtro de Control de Daños (Enfoque Ejecutivo)")
        
        # Mapeo de los estados reales que calcula tu función load_data
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

        # Filtrado inmediato del universo según el semáforo seleccionado
        if color_filtrado == "TODOS":
            df_filtrado_semaforo = resumen.copy()
        else:
            df_filtrado_semaforo = resumen[resumen["Color"] == color_filtrado]
            if df_filtrado_semaforo.empty:
                st.success("✨ **¡Excelente gestión!** No se encontraron actividades operativas en la situación seleccionada.")

        # --------------------------------------------------------------------
        # NIVEL 1: VISTA GERENCIAL (Se alimenta del filtro del semáforo)
        # --------------------------------------------------------------------
        st.markdown("---")
        # 🌟 SOLUCIÓN: Agrupamos y ordenamos estrictamente por el ID del Clasificador Institucional
        df_ordenado = df_filtrado_semaforo[['Categoria ID', 'Categoria']].drop_duplicates().sort_values('Categoria ID')
        categorias_unicas = df_ordenado['Categoria'].dropna().tolist()
        
        sel_categoria = st.selectbox(
            "🔍 Seleccione una Categoría para evaluar el detalle (Drilldown):",
            options=["-- Ver Resumen Seleccionado (Todas) --"] + categorias_unicas
        )
        
        if sel_categoria == "-- Ver Resumen Seleccionado (Todas) --":
            resumen_gerencial = df_filtrado_semaforo.copy()
            es_vista_macro = True
        else:
            resumen_gerencial = df_filtrado_semaforo[df_filtrado_semaforo["Categoria"] == sel_categoria]
            es_vista_macro = False

        # Renderizado de Gráficos Estadísticos
        col1, col2 = st.columns(2)

        with col1:
            # Gráfico de barras de distribución real filtrada
            cant_verde = len(resumen_gerencial[resumen_gerencial["Color"] == COLOR_VERDE])
            cant_amarillo = len(resumen_gerencial[resumen_gerencial["Color"] == COLOR_AMARILLO])
            cant_rojo = len(resumen_gerencial[resumen_gerencial["Color"] == COLOR_ROJO])
            cant_morado = len(resumen_gerencial[resumen_gerencial["Color"] == COLOR_MORADO])
            cant_gris = len(resumen_gerencial[resumen_gerencial["Color"] == COLOR_GRIS])

            fig_semaforo = go.Figure(data=[
                go.Bar(
                    x=["🟢 En Meta", "🟡 En Riesgo", "🔴 Crítico", "🟣 Exceso", "⚪ Sin dato"],
                    y=[cant_verde, cant_amarillo, cant_rojo, cant_morado, cant_gris],
                    marker_color=[COLOR_VERDE, COLOR_AMARILLO, COLOR_ROJO, COLOR_MORADO, COLOR_GRIS],
                    text=[cant_verde, cant_amarillo, cant_rojo, cant_morado, cant_gris],
                    textposition="auto"
                )
            ])
            fig_semaforo.update_layout(title="Distribución del Segmento Seleccionado", height=300, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_semaforo, use_container_width=True)

        with col2:
            # Gráfico ordenado estrictamente por los IDs estructurados de tu Excel
            if not resumen_gerencial.empty:
                if es_vista_macro:
                    eje_y = "Categoria"
                    titulo_graf = "% Ejecución por Categoría (Orden Clasificador)"
                    
                    df_graf = resumen_gerencial.groupby(["Categoria ID", "Categoria"]).agg({
                        "F(SE) Acum": "sum", "F(RE) Acum": "sum"
                    }).reset_index()
                    df_graf["% Ejecución"] = np.where(df_graf["F(RE) Acum"] > 0, (df_graf["F(SE) Acum"] / df_graf["F(RE) Acum"]) * 100, 0)
                    df_graf = df_graf.sort_values("Categoria ID", ascending=False)
                else:
                    eje_y = "Producto"
                    titulo_graf = f"Productos en: {sel_categoria[:30]}..."
                    
                    df_graf = resumen_gerencial.groupby(["Producto ID", "Producto"]).agg({
                        "F(SE) Acum": "sum", "F(RE) Acum": "sum"
                    }).reset_index()
                    df_graf["% Ejecución"] = np.where(df_graf["F(RE) Acum"] > 0, (df_graf["F(SE) Acum"] / df_graf["F(RE) Acum"]) * 100, 0)
                    df_graf = df_graf.sort_values("Producto ID", ascending=False)

                fig_dinamico = go.Figure(data=[
                    go.Bar(
                        y=df_graf[eje_y].astype(str).str.wrap(30), 
                        x=df_graf["% Ejecución"],
                        orientation="h",
                        marker_color=["#17a2b8"],
                        text=[f"{x:.1f}%" for x in df_graf["% Ejecución"]],
                        textposition="auto"
                    )
                ])
                fig_dinamico.update_layout(title=titulo_graf, xaxis_title="%", margin=dict(l=150, r=20, t=40, b=20), height=300)
                st.plotly_chart(fig_dinamico, use_container_width=True)
            else:
                st.info("No hay datos para estructurar el gráfico de clasificación.")

            # --------------------------------------------------------------------
        # NIVEL 2: VISTA DE SUPERVISOR (Tabla Interactiva con un solo Clic)
        # --------------------------------------------------------------------
        st.markdown("---")
        st.subheader("📋 Carpintería Operativa: Localizador de Inconsistencias")
        
        if resumen_gerencial.empty:
            st.info("No existen actividades operativas registradas bajo los filtros seleccionados.")
        else:
            st.markdown("💡 *Haga clic en **cualquier fila** de la tabla para cargar instantáneamente su radiografía y evolución mensual abajo.*")
            
            # Construimos la tabla de visualización directa
            columnas_visibles = [c for c in ["Categoria ID", "Producto ID", "Actividad Operativa", "Unidad de Medida", "F(SE) Acum", "F(RE) Acum", "% Ejecución", "Estado"] if c in resumen_gerencial.columns]
            tabla_operativa = resumen_gerencial[columnas_visibles].copy()
            
            # Ordenamiento estructurado institucional
            if "Categoria ID" in tabla_operativa.columns:
                tabla_operativa = tabla_operativa.sort_values(by=["Categoria ID"])

            # Clonamos para formateo visual sin romper la data cruda subyacente
            tabla_formateada = tabla_operativa.copy()
            tabla_formateada["F(SE) Acum"] = tabla_formateada["F(SE) Acum"].apply(lambda x: f"{x:,.0f}")
            tabla_formateada["F(RE) Acum"] = tabla_formateada["F(RE) Acum"].apply(lambda x: f"{x:,.0f}")
            tabla_formateada["% Ejecución"] = tabla_formateada["% Ejecución"].apply(lambda x: f"{x*100:.1f}%")
            
            # 🌟 MAGIA: Activamos la selección de filas nativa en Streamlit
            evento_seleccion = st.dataframe(
                tabla_formateada, 
                use_container_width=True, 
                height=250,
                on_select="rerun",           # Actualiza el dashboard inmediatamente al hacer clic
                selection_mode="single-row"  # Permite seleccionar una fila a la vez
            )

            # Lógica de asignación asincrónica: ¿El usuario seleccionó algo?
            if evento_seleccion and "selection" in evento_seleccion and evento_seleccion["selection"]["rows"]:
                fila_index = evento_seleccion["selection"]["rows"][0]
                sel_actividad = tabla_operativa.iloc[fila_index]["Actividad Operativa"]
            else:
                # Si no ha seleccionado nada, por defecto carga la primera actividad de la lista
                sel_actividad = tabla_operativa.iloc[0]["Actividad Operativa"]

            # --------------------------------------------------------------------
            # NIVEL 3: DETALLE MENSUAL AUTOMÁTICO
            # --------------------------------------------------------------------
            st.markdown("---")
            st.markdown(f"### 📅 Evolución Mensual Automatizada")
            st.markdown(f"**Actividad Auditada:** {sel_actividad}")

            # Filtrar el dataframe maestro para obtener los datos mensuales crudos
            df_actividad_seleccionada = df[df["Actividad Operativa"] == sel_actividad]
            info_act = resumen_gerencial[resumen_gerencial["Actividad Operativa"] == sel_actividad].iloc[0]
            
            # Renderizado de métricas clave de la actividad seleccionada
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Unidad de Medida", info_act["Unidad de Medida"])
            c2.metric("Programado Acum. F(RE)", f"{info_act['F(RE) Acum']:,.0f}")
            c3.metric("Ejecutado Acum. F(SE)", f"{info_act['F(SE) Acum']:,.0f}")
            c4.metric("Cumplimiento Real", f"{info_act['% Ejecución']*100:.1f}%")
            
            # Gráfico dinámico de barras y líneas
            mes_labels = month_names[1:len(fse_cols)+1]
            valores_se = [df_actividad_seleccionada[c].sum() for c in fse_cols]
            valores_re = [df_actividad_seleccionada[c].sum() for c in fre_cols]

            fig_mensual = make_subplots(specs=[[{"secondary_y": True}]])
            fig_mensual.add_trace(go.Bar(x=mes_labels, y=valores_se, name="Ejecutado Real F(SE)", marker_color="#28a745"), secondary_y=False)
            fig_mensual.add_trace(go.Scatter(x=mes_labels, y=valores_re, name="Programado POI F(RE)", mode="lines+markers", line=dict(color="#dc3545", width=3)), secondary_y=False)
            
            fig_mensual.update_layout(
                hovermode="x unified", 
                height=280, 
                margin=dict(l=20, r=20, t=20, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_mensual, use_container_width=True)
            
            # Mensajes dinámicos e institucionales de consistencia
            pct_act = info_act['% Ejecución']
            if pct_act < 0.85:
                st.error(f"🚨 **Inconsistencia por Subejecución ({pct_act*100:.1f}%):** Esta actividad se encuentra críticamente por debajo de la meta física programada en el POI. El responsable operativo debe ingresar a su aplicativo de origen y regularizar los registros.")
            elif pct_act > 1.00:
                st.warning(f"⚠️ **Alerta por Sobreejecución ({pct_act*100:.1f}%):** La ejecución física supera lo planificado. Verificar posibles duplicidades o errores de digitación en el sistema de origen.")
            else:
                st.success("🟢 **Consistencia Correcta:** Los avances físicos se encuentran alineados con los rangos de tolerancia institucionales.")
       
    # ============================================================================
    # TAB 2: CC RESPONSABLE (CON ENFOQUE COMPETITIVO Y DRILLDOWN DIRECTO)
    # ============================================================================
    with tab2:
        st.subheader("🏆 Ranking de Gestión por Unidad Orgánica")
        st.markdown("💡 *Haga clic en **cualquier Unidad Orgánica** para auditar sus metas físicas asignadas y ver su avance mensual.*")

        if resumen_cc.empty:
            st.warning("⚠️ No hay datos disponibles para Unidad Orgánica en este período.")
        else:
            # --------------------------------------------------------------------
            # NIVEL 1: VISTA GERENCIAL / RANKING (Tabla Interactiva Maestro)
            # --------------------------------------------------------------------
            
            # Clonamos y ordenamos el ranking de ejecución (los más eficientes primero)
            tabla_cc_master = resumen_cc[[
                "CC Responsable ID", "CC Responsable",
                "F(SE) Acum", "F(RE) Acum", "% Ejecución", "Estado"
            ]].copy().sort_values("% Ejecución", ascending=False)

            # Formateo visual para la visualización del usuario final
            tabla_cc_formateada = tabla_cc_master.copy()
            tabla_cc_formateada["F(SE) Acum"] = tabla_cc_formateada["F(SE) Acum"].apply(lambda x: f"{x:,.0f}")
            tabla_cc_formateada["F(RE) Acum"] = tabla_cc_formateada["F(RE) Acum"].apply(lambda x: f"{x:,.0f}")
            tabla_cc_formateada["% Ejecución"] = tabla_cc_formateada["% Ejecución"].apply(lambda x: f"{x*100:.1f}%")

            # Activamos la selección interactiva en la tabla de Centros de Costo
            selecciona_cc = st.dataframe(
                tabla_cc_formateada,
                use_container_width=True,
                height=230,
                on_select="rerun",
                selection_mode="single-row",
                key="df_cc_master"
            )

            # Asignación del CC seleccionado (por defecto el primer lugar del ranking)
            if selecciona_cc and "selection" in selecciona_cc and selecciona_cc["selection"]["rows"]:
                idx_cc = selecciona_cc["selection"]["rows"][0]
                sel_cc_id = tabla_cc_master.iloc[idx_cc]["CC Responsable ID"]
                sel_cc_nombre = tabla_cc_master.iloc[idx_cc]["CC Responsable"]
            else:
                sel_cc_id = tabla_cc_master.iloc[0]["CC Responsable ID"]
                sel_cc_nombre = tabla_cc_master.iloc[0]["CC Responsable"]

            # --------------------------------------------------------------------
            # NIVEL 2: CARTERA DE ACTIVIDADES ASIGNADAS (Filtro por CC seleccionado)
            # --------------------------------------------------------------------
            st.markdown("---")
            st.subheader(f"🎯 Cartera de Actividades: {sel_cc_nombre}")
            st.markdown("💡 *Seleccione una **actividad específica** abajo para ver su comportamiento histórico mes a mes.*")

            # 🌟 FILTRADO MATEMÁTICO DIRECTO: Filtramos las actividades del CC seleccionado
            resumen_filtrado_cc = resumen[resumen["CC Responsable ID"] == sel_cc_id]

            if resumen_filtrado_cc.empty:
                st.info("No se encontraron actividades operativas con metas físicas registradas para esta unidad orgánica.")
            else:
                columnas_act = [c for c in ["Producto ID", "Actividad Operativa", "Unidad de Medida", "F(SE) Acum", "F(RE) Acum", "% Ejecución", "Estado"] if c in resumen_filtrado_cc.columns]
                tabla_act_cc = resumen_filtrado_cc[columnas_act].copy().sort_values("% Ejecución")

                # Formateo de la subtabla de actividades
                tabla_act_cc_formateada = tabla_act_cc.copy()
                tabla_act_cc_formateada["F(SE) Acum"] = tabla_act_cc_formateada["F(SE) Acum"].apply(lambda x: f"{x:,.0f}")
                tabla_act_cc_formateada["F(RE) Acum"] = tabla_act_cc_formateada["F(RE) Acum"].apply(lambda x: f"{x:,.0f}")
                tabla_act_cc_formateada["% Ejecución"] = tabla_act_cc_formateada["% Ejecución"].apply(lambda x: f"{x*100:.1f}%")

                # Segunda tabla interactiva (Cartera de Actividades de la Oficina)
                selecciona_act_cc = st.dataframe(
                    tabla_act_cc_formateada,
                    use_container_width=True,
                    height=200,
                    on_select="rerun",
                    selection_mode="single-row",
                    key="df_act_cc"
                )

                # 🛡️ CONTROL ANTICAÍDAS: Validamos que el índice exista dentro del tamaño real de la tabla
                if selecciona_act_cc and "selection" in selecciona_act_cc and selecciona_act_cc["selection"]["rows"]:
                    idx_act = selecciona_act_cc["selection"]["rows"][0]
                    
                    # Verificamos matemáticamente que el índice no supere la cantidad de filas disponibles
                    if idx_act < len(tabla_act_cc):
                        sel_act_cc = tabla_act_cc.iloc[idx_act]["Actividad Operativa"]
                    else:
                        # Si quedó un índice fantasma del estado anterior, forzamos un reset seguro a la primera fila
                        sel_act_cc = tabla_act_cc.iloc[0]["Actividad Operativa"]
                else:
                    sel_act_cc = tabla_act_cc.iloc[0]["Actividad Operativa"]
                    
                # --------------------------------------------------------------------
                # NIVEL 3: EVOLUCIÓN MENSUAL DE LA OFICINA
                # --------------------------------------------------------------------
                st.markdown("---")
                st.markdown(f"### 📅 Comportamiento Mensual Automatizado")
                st.markdown(f"**Actividad Auditada:** {sel_act_cc}")

                # Filtrar el dataframe maestro de datos crudos usando la variable reactiva
                df_act_cc_sel = df[df["Actividad Operativa"] == sel_act_cc]
                info_act_cc = resumen_filtrado_cc[resumen_filtrado_cc["Actividad Operativa"] == sel_act_cc].iloc[0]

                # Renderizado de métricas flash de la actividad de la oficina
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Unidad de Medida", info_act_cc["Unidad de Medida"])
                c2.metric("Prog. Oficina F(RE)", f"{info_act_cc['F(RE) Acum']:,.0f}")
                c3.metric("Ejec. Oficina F(SE)", f"{info_act_cc['F(SE) Acum']:,.0f}")
                c4.metric("Nivel de Cumplimiento", f"{info_act_cc['% Ejecución']*100:.1f}%")

                # Gráfico dinámico de barras y líneas para el Centro de Costo
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

                # Sistema de semáforo gerencial y feedback directo
                pct_act_cc = info_act_cc['% Ejecución']
                if pct_act_cc < 0.85:
                    st.error(f"🚨 **Alerta de Subejecución de la Oficina ({pct_act_cc*100:.1f}%):** Esta jefatura se encuentra rezagada en la ejecución física de esta actividad. Requiere plan de acción inmediato.")
                elif pct_act_cc > 1.00:
                    st.warning(f"⚠️ **Alerta de Sobreejecución de la Oficina ({pct_act_cc*100:.1f}%):** Los registros superan la meta planificada. Coordinar con el responsable para verificar consistencia.")
                else:
                    st.success("🟢 **Metas Alcanzadas:** El Centro de Costo mantiene un ritmo de ejecución óptimo y consistente.")