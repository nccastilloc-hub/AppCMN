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
# TABS COMO FUNCIONES INDEPENDIENTES
# ============================================================================

def tab_resumen_categoria(df, resumen, fse_cols, fre_cols, last_month, month_names, fecha_archivo, year):
    """
    Tab 1: Control de Gestión por Categoría Presupuestal.
    Esta función NO se modifica, solo se extrae del código original.
    """
    st.subheader("🎯 Control de Gestión y Consistencia POI")
    
    st.markdown("### 🎛️ Filtro de Control de Daños (Enfoque Ejecutivo)")
    
    opciones_semaforo = {
        "🔍 Ver Todo el Universo POI": "TODOS",
        "🟢 En Meta (Alto)": COLOR_VERDE,
        "🟡 En Riesgo (Medio)": COLOR_AMARILLO,
        "🔴 Crítico (Bajo)": COLOR_ROJO,
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
    
    # Gráficos
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
                xaxis=dict(range=[0, max(df_graf["% Ejecución"]) * 1.15]),
                margin=dict(l=150, r=50, t=40, b=30),
                height=380
            )
            st.plotly_chart(fig_dinamico, use_container_width=True)
    
    # Tabla interactiva
    st.markdown("---")
    st.subheader("📋 Control de Actividades Operativas")
    
    if resumen_gerencial.empty:
        st.info("No existen actividades operativas registradas bajo los filtros seleccionados.")
    else:
        st.markdown("💡 *Seleccione una actividad para ver su detalle mensual y su evolución mensual abajo.*")
        
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
        tabla_formateada["% Ejecución"] = tabla_formateada["% Ejecución"].apply(lambda x: f"{x*100:.1f}")
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
        
        # Determinar actividad seleccionada
        if evento_seleccion and "selection" in evento_seleccion and evento_seleccion["selection"]["rows"]:
            fila_index = evento_seleccion["selection"]["rows"][0]
            if fila_index < len(tabla_operativa):
                sel_actividad = tabla_operativa.iloc[fila_index]["Actividad Operativa"]
            else:
                sel_actividad = tabla_operativa.iloc[0]["Actividad Operativa"]
        else:
            sel_actividad = tabla_operativa.iloc[0]["Actividad Operativa"]
        
        # Detalle mensual
        st.markdown("---")
        st.markdown(f"### 📅 Evolución Mensual Automatizada")
        st.markdown(f"**Actividad Auditada:** {sel_actividad}")
        
        df_actividad_seleccionada = df[df["Actividad Operativa"] == sel_actividad]
        info_act = resumen_gerencial[resumen_gerencial["Actividad Operativa"] == sel_actividad].iloc[0]
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Unidad de Medida", info_act["Unidad de Medida"])
        c2.metric("Programado Acum. F(RE)", f"{info_act['F(RE) Acum']:,.0f}")
        c3.metric("Ejecutado Acum. F(SE)", f"{info_act['F(SE) Acum']:,.0f}")
        c4.metric("Cumplimiento Real", f"{info_act['% Ejecución']*100:.1f}%")
        
        mes_labels = month_names[1:len(fse_cols)+1]
        valores_se = [df_actividad_seleccionada[c].sum() for c in fse_cols]
        valores_re = [df_actividad_seleccionada[c].sum() for c in fre_cols]
        
        color_map_evolucion = {
            "TODOS": "#28a745",
            COLOR_VERDE: COLOR_VERDE,
            COLOR_AMARILLO: COLOR_AMARILLO,
            COLOR_ROJO: COLOR_ROJO,
            COLOR_MORADO: COLOR_MORADO,
            COLOR_GRIS: COLOR_GRIS
        }
        bar_color_evolucion = color_map_evolucion.get(color_filtrado, "#28a745")
        
        fig_mensual = make_subplots(specs=[[{"secondary_y": True}]])
        fig_mensual.add_trace(
            go.Bar(
                x=mes_labels,
                y=valores_se,
                name="Ejecutado Real F(SE)",
                marker_color=bar_color_evolucion
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
        
        pct_act = info_act['% Ejecución']
        if pct_act < 0.85:
            st.error(f"🚨 **Inconsistencia por Subejecución ({pct_act*100:.1f}%):** Esta actividad se encuentra críticamente por debajo de la meta física programada en el POI.")
        elif pct_act > 1.00:
            st.warning(f"⚠️ **Alerta por Sobreejecución ({pct_act*100:.1f}%):** La ejecución física supera lo planificado.")
        else:
            st.success("🟢 **Consistencia Correcta:** Los avances físicos se encuentran alineados con los rangos de tolerancia institucionales.")

def tab_unidad_organica(df, resumen, resumen_cc, fse_cols, fre_cols, last_month, month_names, fecha_archivo, year):
    """
    Tab 2: Ranking y detalle por Unidad Orgánica.
    El filtro de semáforo se aplica a nivel de ACTIVIDAD.
    """
    st.subheader("🏆 Ranking de Gestión por Unidad Orgánica")
    st.markdown("💡 *Haga clic en cualquier Unidad Orgánica para auditar sus metas físicas asignadas.*")

    # --- 1. FILTRO DE SEMÁFORO (A NIVEL ACTIVIDAD) ---
    opciones_semaforo = ["Todos", "🟢 En Meta", "🟡 En Riesgo", "🔴 Crítico", "🟣 Exceso", "⚫ Sin dato"]
    filtro_seleccionado = st.multiselect(
        "Filtrar por estado del semáforo",
        options=opciones_semaforo,
        default=["Todos"],
        key="filtro_tab2"
    )

    # Aplicar filtro a nivel actividad
    if "Todos" not in filtro_seleccionado and filtro_seleccionado:
        color_map = {
            "🟢 En Meta": COLOR_VERDE,
            "🟡 En Riesgo": COLOR_AMARILLO,
            "🔴 Crítico": COLOR_ROJO,
            "🟣 Exceso": COLOR_MORADO,
            "⚫ Sin dato": COLOR_GRIS
        }
        colores_seleccionados = [color_map[opt] for opt in filtro_seleccionado if opt in color_map]
        resumen_filtrado = resumen[resumen["Color"].isin(colores_seleccionados)].copy()
    else:
        resumen_filtrado = resumen.copy()

    if resumen_filtrado.empty:
        st.warning("⚠️ No hay actividades que coincidan con el filtro seleccionado.")
        return

    # Recalcular resumen por CC con las actividades filtradas
    resumen_cc_filtrado = get_resumen_cc_responsable(resumen_filtrado)

    if resumen_cc_filtrado.empty:
        st.warning("⚠️ No hay unidades orgánicas con actividades del filtro seleccionado.")
        return

    # --- 2. GRÁFICO DE BARRAS HORIZONTAL (Ranking) ---
    df_cc_graf = resumen_cc_filtrado.copy()
    df_cc_graf = df_cc_graf.sort_values("% Ejecución", ascending=True)

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
        xaxis=dict(range=[0, max(df_cc_graf["% Ejecución"] * 100) * 1.15]),
        margin=dict(l=250, r=50, t=40, b=20),
        height=max(400, len(df_cc_graf) * 25)
    )
    st.plotly_chart(fig_cc, use_container_width=True)

    # --- 3. TABLA DE UNIDADES ORGÁNICAS ---
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

        # --- GESTIONAR RESET DE SELECCIÓN ---
    if st.session_state.get("reset_seleccion", False):
        # Limpiar el estado del dataframe
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

    # --- 4. DETALLE DE UNIDAD SELECCIONADA ---
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

    # --- 5. KPIs DE LA UNIDAD SELECCIONADA ---
    st.markdown("---")
    st.subheader(f"📊 Detalle de: {sel_cc_nombre}")

    resumen_filtrado_cc = resumen_filtrado[resumen_filtrado["CC Responsable ID"] == sel_cc_id]
    
    if resumen_filtrado_cc.empty:
        st.info("No se encontraron actividades con el estado seleccionado en esta unidad orgánica.")
    else:
                # --- KPIs DE LA UNIDAD (6 tarjetas) ---
        total_unidad = len(resumen_filtrado_cc)
        verde_unidad = len(resumen_filtrado_cc[resumen_filtrado_cc["Color"] == COLOR_VERDE])
        amarillo_unidad = len(resumen_filtrado_cc[resumen_filtrado_cc["Color"] == COLOR_AMARILLO])
        rojo_unidad = len(resumen_filtrado_cc[resumen_filtrado_cc["Color"] == COLOR_ROJO])
        morado_unidad = len(resumen_filtrado_cc[resumen_filtrado_cc["Color"] == COLOR_MORADO])
        gris_unidad = len(resumen_filtrado_cc[resumen_filtrado_cc["Color"] == COLOR_GRIS])

        # Promedio ponderado (coherente con el gráfico)
        if resumen_filtrado_cc["F(RE) Acum"].sum() > 0:
            promedio_ponderado = (resumen_filtrado_cc["F(SE) Acum"].sum() / resumen_filtrado_cc["F(RE) Acum"].sum()) * 100
        else:
            promedio_ponderado = 0

        col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
        col1.metric("📋 Total", total_unidad)
        col2.metric("📈 Promedio", f"{promedio_ponderado:.1f}%")
        col3.metric("🟢 En Meta", verde_unidad)
        col4.metric("🟡 En Riesgo", amarillo_unidad)
        col5.metric("🔴 Crítico", rojo_unidad)
        col6.metric("🟣 Exceso", morado_unidad)
        col7.metric("⚫ Sin dato", gris_unidad)

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

        st.caption("📌 *Proyección calculada con promedio móvil de los últimos 3 meses. Puede ser imprecisa en actividades esporádicas (no regulares).*")

        if "selection" in st.session_state.get("df_act_cc_mejorado", {}) and st.session_state["df_act_cc_mejorado"]["selection"]["rows"]:
            idx_act = st.session_state["df_act_cc_mejorado"]["selection"]["rows"][0]
            if idx_act < len(tabla_act):
                sel_act = tabla_act.iloc[idx_act]["Actividad Operativa"]
            else:
                sel_act = tabla_act.iloc[0]["Actividad Operativa"]
        else:
            sel_act = tabla_act.iloc[0]["Actividad Operativa"]

        st.markdown("---")
        st.markdown(f"### 📅 Evolución Mensual: {sel_act}")

        df_act_sel = df[df["Actividad Operativa"] == sel_act]
        info_act = resumen_filtrado_cc[resumen_filtrado_cc["Actividad Operativa"] == sel_act].iloc[0]

        color_act = info_act["Color"]

        mes_labels = month_names[1:len(fse_cols)+1]
        valores_se = [df_act_sel[c].sum() for c in fse_cols]
        valores_re = [df_act_sel[c].sum() for c in fre_cols]

        fig_mensual = make_subplots(specs=[[{"secondary_y": True}]])
        fig_mensual.add_trace(
            go.Bar(
                x=mes_labels,
                y=valores_se,
                name="Ejecutado Real F(SE)",
                marker_color=color_act
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

        pct_act = info_act["% Ejecución"]
        if pct_act < 0.85:
            st.error(f"🚨 **Alerta de Subejecución ({pct_act*100:.1f}%):** Esta actividad se encuentra por debajo de la meta.")
        elif pct_act > 1.00:
            st.warning(f"⚠️ **Sobreejecución ({pct_act*100:.1f}%):** La ejecución supera lo planificado.")
        else:
            st.success("🟢 **Meta Alcanzada:** La actividad mantiene un ritmo de ejecución óptimo.")

        if st.button("🔙 Limpiar selección"):
            st.session_state["reset_seleccion"] = True
            st.rerun()

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

        # --- PROYECCIÓN A DICIEMBRE (PROMEDIO MÓVIL ÚLTIMOS 3 MESES) ---
    if len(fse_cols) >= 3:
        ult_3_meses = fse_cols[-3:]
        df["Prom_Ult_3M"] = df[ult_3_meses].sum(axis=1) / 3
    elif len(fse_cols) > 0:
        df["Prom_Ult_3M"] = df[fse_cols].sum(axis=1) / len(fse_cols)
    else:
        df["Prom_Ult_3M"] = 0

    df["Proyeccion_Dic"] = df["Prom_Ult_3M"] * 12

    df["Proyeccion_vs_Meta"] = np.where(
        df["F(RE) Acum"] > 0,
        (df["Proyeccion_Dic"] / df["F(RE) Acum"]) * 100,
        0
    )

    df["Alerta_Proyeccion"] = np.where(
        df["Proyeccion_vs_Meta"] < 85,
        "⚠️ Revisar meta",
        np.where(
            df["Proyeccion_vs_Meta"] > 115,
            "🟣 Sobreejecución",
            "🟢 OK"
        )
    )

    
    # Semáforo
    def semaforo(row):
        pct = row["% Ejecución"]
        if row["F(RE) Acum"] == 0:
            return "Sin ejecución", COLOR_GRIS
        elif pct == 0:
            return "GRIS", COLOR_GRIS
        elif pct < 0.75:
            return "ROJO - BAJO", COLOR_ROJO
        elif pct < 0.95:
            return "AMARILLO - MEDIO", COLOR_AMARILLO
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
        "Proyeccion_Dic": "sum",       # <-- ¿Está esta línea?
        "Prom_Ult_3M": "sum",          # <-- ¿Y esta?
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
        elif pct < 0.75:
            return "ROJO - BAJO", COLOR_ROJO
        elif pct < 0.95:
            return "AMARILLO - MEDIO", COLOR_AMARILLO
        elif pct <= 1.00:
            return "VERDE - BUENO", COLOR_VERDE
        else:
            return "MORADO - EXCESO", COLOR_MORADO
    
    resumen[["Estado", "Color"]] = resumen.apply(semaforo_agg, axis=1, result_type="expand")

    resumen["Proyeccion_vs_Meta"] = np.where(
        resumen["F(RE) Acum"] > 0,
        (resumen["Proyeccion_Dic"] / resumen["F(RE) Acum"]) * 100,
        0
    )

    resumen["Alerta_Proyeccion"] = np.where(
        resumen["Proyeccion_vs_Meta"] < 85,
        "⚠️ Revisar meta",
        np.where(resumen["Proyeccion_vs_Meta"] > 115, "🟣 Sobreejecución", "🟢 OK")
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
        elif pct < 0.75:
            return "ROJO - BAJO", COLOR_ROJO
        elif pct < 0.95:
            return "AMARILLO - MEDIO", COLOR_AMARILLO
        elif pct <= 1.00:
            return "VERDE - BUENO", COLOR_VERDE
        else:
            return "MORADO - EXCESO", COLOR_MORADO
    
    resumen[["Estado", "Color"]] = resumen.apply(semaforo_cc, axis=1, result_type="expand")

    resumen["Proyeccion_vs_Meta"] = np.where(
        resumen["F(RE) Acum"] > 0,
        (resumen["Proyeccion_Dic"] / resumen["F(RE) Acum"]) * 100,
        0
    )
    resumen["Alerta_Proyeccion"] = np.where(
        resumen["Proyeccion_vs_Meta"] < 85,
        "⚠️ Revisar meta",
        np.where(resumen["Proyeccion_vs_Meta"] > 115, "🟣 Sobreejecución", "🟢 OK")
    )
    
    return resumen

def formatear_estado_con_color(row):
    """Formatea el estado con un emoji de color (versión unificada)."""
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
    
    # Extraer solo la parte descriptiva del estado
    partes = estado.split(" - ")
    estado_limpio = partes[-1] if len(partes) > 1 else estado
    
    return f"{emoji} {estado_limpio}"

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

    # --- OBTENER FECHA DEL ARCHIVO (NUEVO) ---
    if os.path.exists(EXCEL_PATH):
        mod_time = os.path.getmtime(EXCEL_PATH)
        fecha_archivo = datetime.fromtimestamp(mod_time).strftime('%d/%m/%Y %H:%M')
    else:
        fecha_archivo = datetime.now().strftime('%d/%m/%Y %H:%M')

    # --- HEADER ---
    st.header("📊 Seguimiento de Metas Físicas POI")
    
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    with col1:
        st.markdown(f"**Año:** {year} | **Período:** Ene - {month_names[last_month]}")
    with col2:
        st.markdown(f"**Última actualización:** {fecha_archivo}")
    with col3:
        if os.path.exists(EXCEL_PATH):
            st.caption(f"📁 Archivo: {os.path.basename(EXCEL_PATH)}")
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
        
        # --- LEYENDA DEL SEMÁFORO (Directiva CEPLAN) ---
    st.markdown("---")
    st.caption("📘 **Criterios de semaforización (Directiva CEPLAN):**")
    st.caption("🟢 **En Meta:** 95% - 100%  |  🟡 **En Riesgo:** 75% - 95%  |  🔴 **Crítico:** < 75%  |  🟣 **Exceso:** > 100%  |  ⚫ **Sin dato:** 0%")

    with st.expander("📖 Ver detalle completo de la Directiva CEPLAN"):
        st.markdown("""
        **Criterios de semaforización para el seguimiento de metas físicas:**
        
        - **🟢 En Meta (Alto):** Actividades que han alcanzado un porcentaje de ejecución entre el 95% y el 100% de lo programado.
        - **🟡 En Riesgo (Medio):** Actividades con ejecución entre el 75% y el 95%, que requieren monitoreo para evitar caer en zona crítica.
        - **🔴 Crítico (Bajo):** Actividades con ejecución inferior al 75%, que requieren acciones correctivas inmediatas.
        - **🟣 Exceso (Sobreejecución):** Actividades que superan el 100% de ejecución, lo que puede indicar sobreesfuerzo o posibles errores de programación.
        - **⚫ Sin dato:** Actividades sin ejecución registrada o con programación en cero.
        
        *Fuente: Directiva CEPLAN para el seguimiento de metas físicas.*
        """)

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
            "🟢 En Meta (Alto)": COLOR_VERDE,
            "🟡 En Riesgo (Medio)": COLOR_AMARILLO,
            "🔴 Crítico (Bajo)": COLOR_ROJO,
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
        
        # Gráficos
        if not resumen_gerencial.empty:
            col1, col2 = st.columns([1, 2.5])  # La izquierda ocupa 1 parte, la derecha 2.5 partes
            
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
                        textposition="outside"
                    )
                ])
                fig_dinamico.update_layout(title=titulo_graf, xaxis_title="%", margin=dict(l=150, r=50, t=40, b=50), height=380)
                st.plotly_chart(fig_dinamico, use_container_width=True)
        
        # Tabla interactiva
        st.markdown("---")
        st.subheader("📋 Control de Actividades Operativas")
        
        if resumen_gerencial.empty:
            st.info("No existen actividades operativas registradas bajo los filtros seleccionados.")
        else:
            st.markdown("💡 *Seleccione una actividad para ver su detalle mensual y su evolución mensual abajo.*")
            
            columnas_visibles = [c for c in ["Categoria ID", "Producto ID", "Actividad Operativa", "Unidad de Medida", "F(SE) Acum", "F(RE) Acum", "% Ejecución", "Estado", "Color"] if c in resumen_gerencial.columns]
            tabla_operativa = resumen_gerencial[columnas_visibles].copy()
            
            if "Categoria ID" in tabla_operativa.columns:
                tabla_operativa = tabla_operativa.sort_values(by=["Categoria ID"])
                # Renombrar columnas para mejor legibilidad
                tabla_operativa = tabla_operativa.rename(columns={
                "F(SE) Acum": "Ejec. Acum",
                "F(RE) Acum": "Prog. Acum"
            })
            
            tabla_formateada = tabla_operativa.copy()
            tabla_formateada["Ejec. Acum"] = tabla_formateada["Ejec. Acum"].apply(lambda x: f"{x:,.0f}")
            tabla_formateada["Prog. Acum"] = tabla_formateada["Prog. Acum"].apply(lambda x: f"{x:,.0f}")
            tabla_formateada["% Ejecución"] = tabla_formateada["% Ejecución"].apply(lambda x: f"{x*100:.1f}")  # Sin %
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

            # --- DETERMINAR ACTIVIDAD SELECCIONADA ---
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
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            c1.metric("Unidad de Medida", info_act["Unidad de Medida"])
            c2.metric("Programado Acum. F(RE)", f"{info_act['F(RE) Acum']:,.0f}")
            c3.metric("Ejecutado Acum. F(SE)", f"{info_act['F(SE) Acum']:,.0f}")
            c4.metric("Cumplimiento Real", f"{info_act['% Ejecución']*100:.1f}%")

            c5, c6 = st.columns(2)    
            proy = info_act.get("Proyeccion_Dic", 0)
            alerta = info_act.get("Alerta_Proyeccion", "🟢 OK")
            c5.metric("📈 Proyección Dic", f"{proy:,.0f}")
            c6.metric("⚠️ Alerta", alerta)
            
            st.caption("📌 *Proyección calculada con **promedio móvil de los últimos 3 meses**. Puede ser imprecisa en actividades esporádicas (no regulares). Se ajustará cuando lleguen los datos oficiales.*")
            
            # Preparar datos del gráfico
            mes_labels = month_names[1:len(fse_cols)+1]
            valores_se = [df_actividad_seleccionada[c].sum() for c in fse_cols]
            valores_re = [df_actividad_seleccionada[c].sum() for c in fre_cols]

            # 🔥 COLOR DINÁMICO PARA EL GRÁFICO DE BARRAS
            color_map_evolucion = {
                "TODOS": "#28a745",
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
                    marker_color=bar_color_evolucion
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
  
    with tab2:
        tab_unidad_organica(df, resumen, resumen_cc, fse_cols, fre_cols, last_month, month_names, fecha_archivo, year)
  
# ============================================================================
# PUNTO DE ENTRADA
# ============================================================================
if __name__ == "__main__":
    ejecutar_dashboard_poi()