"""
Dashboard de Seguimiento Indicadores de Gestión - Versión Streamlit
Elaborado por: Unidad Funcional de Planeamiento - Oficina Ejecutiva de Planeamiento Estratégico (OEPE)
Asistente de Desarrollo: DeepSeek
Fecha de elaboración: 2026-10-17
Fecha de actualización: 2026-10-17
Objetivo: Proporcionar un tablero de control interactivo para la gestión de indicadores, permitiendo a los usuarios auditar y analizar actividades en tiempo real.
==================================================================
Módulo Streamlit para integración en el menú principal de Gestión IPRESS.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import os

# Colores (los mismos del POI)
COLOR_MORADO = "#6f42c1"
COLOR_VERDE = "#28a745"
COLOR_AMARILLO = "#ffc107"
COLOR_ROJO = "#dc3545"
COLOR_GRIS = "#495057"

# ============================================================================
# CARGA Y PROCESAMIENTO DE DATOS
# ============================================================================

@st.cache_data
def cargar_indicadores(excel_path):
    """Carga las 3 hojas y las une."""
    
    # 1. Cargar definiciones (la hoja Def_Indicadores)
    defs = pd.read_excel(excel_path, sheet_name="Def_Indicadores")
    
    # 2. Cargar valores (la hoja Fact_Valores)
    valores = pd.read_excel(excel_path, sheet_name="Fact_Valores")
    
    # 3. Cargar mapeo (la hoja Mapeo_ID)
    mapeo = pd.read_excel(excel_path, sheet_name="Mapeo_ID")
    
    # --- Limpieza de valores ---
    # Convertir fecha a datetime y extraer el año y mes
    valores["Fecha_Corte"] = pd.to_datetime(valores["Fecha_Corte"])
    valores["Año"] = valores["Fecha_Corte"].dt.year
    valores["Mes"] = valores["Fecha_Corte"].dt.month
    valores["Nombre_Mes"] = valores["Fecha_Corte"].dt.strftime('%b') # Ene, Feb...
    
    # Calcular el Valor_Resultado si viene como fórmula de Excel (C/D)
    # Si el valor es texto o nulo, calculamos C/D
    valores["Valor_Resultado"] = pd.to_numeric(valores["Valor_Resultado"], errors='coerce')
    
    # Si hay nulos y tenemos numerador/denominador, calculamos
    mask = valores["Valor_Resultado"].isna() & valores["Numerador"].notna() & valores["Denominador"].notna()
    valores.loc[mask, "Valor_Resultado"] = valores.loc[mask, "Numerador"] / valores.loc[mask, "Denominador"]
    
    # --- Unir valores con el mapeo (para obtener ID_Maestro) ---
    df = valores.merge(
        mapeo[["Año", "ID_Indicador", "ID_Maestro"]], 
        on=["Año", "ID_Indicador"], 
        how="left"
    )
    
    # Si no tiene ID_Maestro, usar el ID_Indicador como fallback
    df["ID_Maestro"] = df["ID_Maestro"].fillna(df["ID_Indicador"])
    
    # --- Unir con las definiciones (para obtener nombre, min, max, sentido) ---
    # Ojo: Un indicador puede tener definiciones en distintos años. Tomamos la más reciente.
    defs_sorted = defs.sort_values("Año").drop_duplicates("ID_Indicador", keep="last")
    
    df = df.merge(
        defs_sorted[["ID_Indicador", "Familia", "Descripción", "Sentido", "Minimo", "Maximo"]],
        on="ID_Indicador",
        how="left"
    )
    
    return df, defs, mapeo

def aplicar_semaforo_indicador(row):
    """Aplica el semáforo considerando si el sentido es ascendente o descendente."""
    val = row["Valor_Resultado"]
    minimo = row["Minimo"]
    maximo = row["Maximo"]
    sentido = str(row["Sentido"]).lower()
    
    if pd.isna(val):
        return "⚪ Sin dato", COLOR_GRIS
    
    # Si no hay umbrales definidos, no podemos semaforizar
    if pd.isna(minimo) and pd.isna(maximo):
        return "⚪ Sin umbral", COLOR_GRIS
        
    if sentido == "ascendente":
        # Más es mejor. Verde si supera el mínimo (o está cerca)
        if not pd.isna(minimo) and val < minimo:
            return "🔴 Crítico", COLOR_ROJO
        elif not pd.isna(maximo) and val > maximo:
            return "🟣 Exceso", COLOR_MORADO
        else:
            return "🟢 En Meta", COLOR_VERDE
            
    elif sentido == "descendente":
        # Menos es mejor. Verde si está por debajo del máximo (o cerca del mínimo)
        if not pd.isna(maximo) and val > maximo:
            return "🔴 Crítico", COLOR_ROJO
        elif not pd.isna(minimo) and val < minimo:
            # Si está muy por debajo del mínimo, ¿es bueno o malo? 
            # En descendentes, muy bajo suele ser excelente, pero lo marcamos como exceso
            return "🟣 Exceso", COLOR_MORADO
        else:
            return "🟢 En Meta", COLOR_VERDE
            
    else:
        return "⚪ Sin sentido", COLOR_GRIS

# ============================================================================
# INTERFAZ GRÁFICA (TAB 1: PANORAMA)
# ============================================================================

def tab_panorama(df):
    st.subheader("🎯 Panorama de Indicadores")
    
    # Aplicar semáforo a todos los datos
    df[["Estado_Indicador", "Color"]] = df.apply(aplicar_semaforo_indicador, axis=1, result_type="expand")
    
    # KPIs Globales
    total = len(df)
    verde = len(df[df["Estado_Indicador"] == "🟢 En Meta"])
    rojo = len(df[df["Estado_Indicador"] == "🔴 Crítico"])
    gris = len(df[df["Estado_Indicador"] == "⚪ Sin dato"])
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📊 Total Registros", total)
    c2.metric("🟢 En Meta", verde)
    c3.metric("🔴 Crítico", rojo)
    c4.metric("⚪ Sin dato/umbral", gris)
    
    st.markdown("---")
    
    # Tabla de datos
    st.markdown("### 📋 Últimos Valores Registrados")
    
    # Obtener el último valor por indicador
    ultimos = df.sort_values("Fecha_Corte").groupby("ID_Indicador").tail(1)
    
    st.dataframe(
        ultimos[["ID_Indicador", "ID_Maestro", "Descripción", "Fecha_Corte", "Valor_Resultado", "Estado_Indicador"]],
        use_container_width=True,
        column_config={
            "Valor_Resultado": st.column_config.NumberColumn("Valor", format="%.2f"),
            "Fecha_Corte": st.column_config.DateColumn("Último Corte", format="DD/MM/YYYY"),
            "Estado_Indicador": st.column_config.TextColumn("Estado")
        }
    )

# ============================================================================
# INTERFAZ GRÁFICA (TAB 2: EVOLUCIÓN)
# ============================================================================

def tab_evolucion(df):
    st.subheader("📈 Evolución Histórica de Indicadores")
    
    # Asegurarnos de que no haya nulos en ID_Maestro
    df_limpio = df.dropna(subset=["ID_Maestro"]).copy()
    
    if df_limpio.empty:
        st.warning("No hay datos históricos para esta familia.")
        return

    # Crear etiquetas de forma segura
    opciones = df_limpio[["ID_Maestro", "Descripción"]].drop_duplicates()
    
    # Si la descripción es nula, usamos solo el ID
    opciones["Label"] = opciones.apply(
        lambda row: f"{row['ID_Maestro']} - {str(row['Descripción'])[:50]}" if pd.notna(row['Descripción']) else row['ID_Maestro'], 
        axis=1
    )
    
    sel_label = st.selectbox("Seleccione un indicador:", opciones["Label"].tolist())
    sel_id_maestro = opciones[opciones["Label"] == sel_label]["ID_Maestro"].values[0]
    
    # Filtrar datos del indicador
    df_ind = df_limpio[df_limpio["ID_Maestro"] == sel_id_maestro].sort_values("Fecha_Corte")
    
    if df_ind.empty:
        st.warning("No hay datos para este indicador.")
        return
        
    # Gráfico de líneas por año
    fig = go.Figure()
    
    for año in df_ind["Año"].unique():
        df_año = df_ind[df_ind["Año"] == año]
        fig.add_trace(go.Scatter(
            x=df_año["Mes"],
            y=df_año["Valor_Resultado"],
            name=str(año),
            mode="lines+markers",
            hovertemplate="Mes: %{x}<br>Valor: %{y:.2%}<extra></extra>"
        ))
        
    fig.update_layout(
        title=f"Evolución: {sel_id_maestro}",
        xaxis_title="Mes del año",
        yaxis_title="Valor del indicador",
        xaxis=dict(
            tickmode='array', 
            tickvals=list(range(1, 13)), 
            ticktext=["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
        ),
        hovermode="x unified"
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Mostrar aviso si hubo cambio de definición
    st.info("💡 **Nota:** El indicador de vacunación (IND_VAC_BCG) cambió su definición en 2025 (de 'antes del alta' a 'dentro de las 24 horas'). Los datos de 2023-2024 pueden no ser directamente comparables.")

# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def ejecutar_dashboard_indicadores():
    """Punto de entrada del módulo desde Menuprincipal.py"""
    import os
    from datetime import datetime
    from Header_Modular import mostrar_cabecera

    # 1. Definir la ruta del archivo
    excel_path = "INDICADORES.xlsx"

    # 2. Calcular la fecha real de modificación del archivo
    if os.path.exists(excel_path):
        mod_time = os.path.getmtime(excel_path)
        fecha_actualizacion = datetime.fromtimestamp(mod_time).strftime('%d/%m/%Y a las %H:%M hrs')
    else:
        fecha_actualizacion = "Archivo no encontrado"

    # 3. Dibujar la cabecera con la fecha correcta
    mostrar_cabecera(
        titulo="Consola Gerencial de Operaciones - INMP",
        subtitulo="Dashboard de Indicadores",
        fecha_actualizacion=fecha_actualizacion
    )

    # 4. Verificar que el archivo exista para cargar los datos
    if not os.path.exists(excel_path):
        st.error(f"❌ No se encontró el archivo {excel_path}")
        return
        
    # 5. Cargar datos
    try:
        df, defs, mapeo = cargar_indicadores(excel_path)
    except Exception as e:
        st.error(f"Error al cargar datos: {e}")
        return

    # 6. Selector de Familia
    familias = defs["Familia"].dropna().unique().tolist()
    
    st.markdown("### 🗂️ Seleccione la familia de indicadores que desea analizar:")
    sel_familia = st.radio(
        "Familias disponibles:",
        options=familias,
        horizontal=True,
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    
    # 7. Filtrar datos y dibujar Tabs
    df_filtrado = df[df["Familia"] == sel_familia]
    
    if df_filtrado.empty:
        st.warning(f"No hay datos registrados para la familia: {sel_familia}")
        return

    tab1, tab2, tab3 = st.tabs(["📊 Panorama General", "📈 Evolución Histórica", "🏢 Ranking por Responsable"])
    
    with tab1:
        st.subheader(f"Panorama: {sel_familia}")
        tab_panorama(df_filtrado)
        
    with tab2:
        st.subheader(f"Evolución: {sel_familia}")
        tab_evolucion(df_filtrado)
        
    with tab3:
        st.subheader(f"Responsables: {sel_familia}")
        st.info("🚧 Próximamente: Ranking y semáforo por área responsable.")