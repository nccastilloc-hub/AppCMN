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
    tab1, tab2 = st.tabs(["Actividades Operativas", "CC Responsable"])

    # ============================================================================
    # TAB 1: ACTIVIDADES OPERATIVAS
    # ============================================================================
    with tab1:
        st.subheader("Actividades Operativas")

        # Filtros
        col1, col2, col3 = st.columns(3)
        
        categorias_unicas = sorted(resumen["Categoria"].dropna().unique().tolist())
        with col1:
            sel_categorias = st.multiselect(
                "Categoría:",
                options=categorias_unicas,
                default=[]
            )
        
        with col2:
            estados_unicos = sorted(resumen["Estado"].unique().tolist())
            sel_estados = st.multiselect(
                "Estado:",
                options=estados_unicos,
                default=[]
            )
        
        with col3:
            busqueda = st.text_input("Búsqueda:", "")

        # Aplicar filtros
        resumen_filtrado = resumen.copy()
        if sel_categorias:
            resumen_filtrado = resumen_filtrado[resumen_filtrado["Categoria"].isin(sel_categorias)]
        if sel_estados:
            resumen_filtrado = resumen_filtrado[resumen_filtrado["Estado"].isin(sel_estados)]
        if busqueda:
            mask = (
                resumen_filtrado["Actividad Operativa"].astype(str).str.contains(busqueda, case=False, na=False) |
                resumen_filtrado["Actividad Presupuestal"].astype(str).str.contains(busqueda, case=False, na=False) |
                resumen_filtrado["Producto"].astype(str).str.contains(busqueda, case=False, na=False)
            )
            resumen_filtrado = resumen_filtrado[mask]

        # Gráficos
        col1, col2 = st.columns(2)

        # Gráfico 1: Distribución de semáforos
        with col1:
            fig_semaforo = go.Figure(data=[
                go.Bar(
                    x=["🟢 Verde", "🟡 Amarillo", "🔴 Rojo", "⚪ Sin dato"],
                    y=[
                        len(resumen_filtrado[resumen_filtrado["Color"] == COLOR_VERDE]),
                        len(resumen_filtrado[resumen_filtrado["Color"] == COLOR_AMARILLO]),
                        len(resumen_filtrado[resumen_filtrado["Color"] == COLOR_ROJO]),
                        len(resumen_filtrado[resumen_filtrado["Color"] == COLOR_GRIS]),
                    ],
                    marker_color=[COLOR_VERDE, COLOR_AMARILLO, COLOR_ROJO, COLOR_GRIS],
                    text=[
                        len(resumen_filtrado[resumen_filtrado["Color"] == COLOR_VERDE]),
                        len(resumen_filtrado[resumen_filtrado["Color"] == COLOR_AMARILLO]),
                        len(resumen_filtrado[resumen_filtrado["Color"] == COLOR_ROJO]),
                        len(resumen_filtrado[resumen_filtrado["Color"] == COLOR_GRIS]),
                    ],
                    textposition="auto",
                    hovertemplate="<b>%{x}</b><br>Actividades: %{y}<extra></extra>"
                )
            ])
            fig_semaforo.update_layout(
                title="Distribución por Semáforo",
                showlegend=False,
                margin=dict(l=20, r=20, t=50, b=20),
                height=350,
                yaxis_title="N° de Actividades"
            )
            st.plotly_chart(fig_semaforo, use_container_width=True)

        # Gráfico 2: Ejecución por categoría
        with col2:
            if "Categoria" in resumen_filtrado.columns:
                cat_resumen = resumen_filtrado.groupby("Categoria").agg({
                    "F(SE) Acum": "sum",
                    "F(RE) Acum": "sum"
                }).reset_index()
                cat_resumen["% Ejecución"] = np.where(
                    cat_resumen["F(RE) Acum"] > 0,
                    cat_resumen["F(SE) Acum"] / cat_resumen["F(RE) Acum"] * 100,
                    0
                )
                cat_resumen = cat_resumen.sort_values("% Ejecución", ascending=True)

                fig_categoria = go.Figure(data=[
                    go.Bar(
                        y=cat_resumen["Categoria"],
                        x=cat_resumen["% Ejecución"],
                        orientation="h",
                        marker_color=[
                            COLOR_MORADO if x > 100 else 
                            COLOR_VERDE if x >= 90 else 
                            COLOR_AMARILLO if x >= 85 else COLOR_ROJO
                            for x in cat_resumen["% Ejecución"]
                        ],
                        text=[f"{x:.1f}%" for x in cat_resumen["% Ejecución"]],
                        textposition="auto",
                        hovertemplate="<b>%{y}</b><br>% Ejecución: %{x:.1f}%<extra></extra>"
                    )
                ])
                fig_categoria.update_layout(
                    title="% Ejecución por Categoría",
                    xaxis_title="% Ejecución",
                    margin=dict(l=200, r=20, t=50, b=20),
                    height=350
                )
                st.plotly_chart(fig_categoria, use_container_width=True)

        # Tabla de detalle
        st.subheader("📋 Detalle de Actividades")
        
        tabla_display = resumen_filtrado[[
            "Categoria", "Producto", "Actividad Presupuestal",
            "Actividad Operativa", "Unidad de Medida",
            "F(SE) Acum", "F(RE) Acum", "% Ejecución", "Estimación Dic", "Estado"
        ]].copy()

        tabla_display["F(SE) Acum"] = tabla_display["F(SE) Acum"].apply(lambda x: f"{x:,.0f}")
        tabla_display["F(RE) Acum"] = tabla_display["F(RE) Acum"].apply(lambda x: f"{x:,.0f}")
        tabla_display["% Ejecución"] = tabla_display["% Ejecución"].apply(lambda x: f"{x*100:.1f}%")
        tabla_display["Estimación Dic"] = tabla_display["Estimación Dic"].apply(lambda x: f"{x:,.0f}")

        st.dataframe(
            tabla_display,
            use_container_width=True,
            height=400,
            column_config={
                "Estado": st.column_config.TextColumn(
                    help="Semáforo de ejecución"
                )
            }
        )

        # Gráfico temporal
        st.subheader("📈 Evolución Mensual")
        
        df_filtrado = df.copy()
        if sel_categorias:
            df_filtrado = df_filtrado[df_filtrado["Categoria"].isin(sel_categorias)]

        mes_labels = month_names[1:len(fse_cols)+1]
        se_mensual = [df_filtrado[c].sum() if c in df_filtrado.columns else 0 for c in fse_cols]
        re_mensual = [df_filtrado[c].sum() if c in df_filtrado.columns else 0 for c in fre_cols]

        fig = make_subplots(specs=[[{"secondary_y": True}]])

        fig.add_trace(
            go.Bar(
                x=mes_labels,
                y=se_mensual,
                name="Ejecutado",
                marker_color="#17a2b8"
            ),
            secondary_y=False
        )
        fig.add_trace(
            go.Scatter(
                x=mes_labels,
                y=re_mensual,
                name="Programado",
                mode="lines+markers",
                line=dict(color="#dc3545", width=2)
            ),
            secondary_y=True
        )

        fig.update_layout(
            title="Ejecutado vs Programado por Mes",
            hovermode="x unified",
            margin=dict(l=20, r=20, t=60, b=20),
            height=400
        )
        fig.update_yaxes(title_text="Ejecutado", secondary_y=False)
        fig.update_yaxes(title_text="Programado", secondary_y=True)

        st.plotly_chart(fig, use_container_width=True)

    # ============================================================================
    # TAB 2: CC RESPONSABLE
    # ============================================================================
    with tab2:
        st.subheader("CC Responsable")

        if resumen_cc.empty:
            st.warning("⚠️ No hay datos disponibles para CC Responsable en este período.")
        else:
            # Gráfico CC Responsable
            col1, col2 = st.columns([1, 2])
            
            with col1:
                fig_cc = go.Figure(data=[
                    go.Bar(
                        x=["🟢 Verde", "🟡 Amarillo", "🔴 Rojo", "⚪ Sin dato"],
                        y=[
                            len(resumen_cc[resumen_cc["Color"] == COLOR_VERDE]),
                            len(resumen_cc[resumen_cc["Color"] == COLOR_AMARILLO]),
                            len(resumen_cc[resumen_cc["Color"] == COLOR_ROJO]),
                            len(resumen_cc[resumen_cc["Color"] == COLOR_GRIS]),
                        ],
                        marker_color=[COLOR_VERDE, COLOR_AMARILLO, COLOR_ROJO, COLOR_GRIS],
                        text=[
                            len(resumen_cc[resumen_cc["Color"] == COLOR_VERDE]),
                            len(resumen_cc[resumen_cc["Color"] == COLOR_AMARILLO]),
                            len(resumen_cc[resumen_cc["Color"] == COLOR_ROJO]),
                            len(resumen_cc[resumen_cc["Color"] == COLOR_GRIS]),
                        ],
                        textposition="auto"
                    )
                ])
                fig_cc.update_layout(
                    title="Distribución por Semáforo",
                    showlegend=False,
                    margin=dict(l=20, r=20, t=50, b=20),
                    height=350
                )
                st.plotly_chart(fig_cc, use_container_width=True)

            with col2:
                # Tabla CC Responsable
                tabla_cc = resumen_cc[[
                    "CC Responsable ID", "CC Responsable",
                    "F(SE) Acum", "F(RE) Acum", "% Ejecución", "Estado"
                ]].copy().sort_values("CC Responsable ID")

                tabla_cc["F(SE) Acum"] = tabla_cc["F(SE) Acum"].apply(lambda x: f"{x:,.0f}")
                tabla_cc["F(RE) Acum"] = tabla_cc["F(RE) Acum"].apply(lambda x: f"{x:,.0f}")
                tabla_cc["% Ejecución"] = tabla_cc["% Ejecución"].apply(lambda x: f"{x*100:.1f}%")

                st.dataframe(
                    tabla_cc,
                    use_container_width=True,
                    height=400
                )

    # Footer
    st.markdown("---")
    st.markdown(
        "<small>Dashboard generado automáticamente desde datos POI | "
        "Actualizar archivo Excel para ver nuevos datos</small>",
        unsafe_allow_html=True
    )
