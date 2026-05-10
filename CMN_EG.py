import pandas as pd
import plotly.express as px
import streamlit as st

@st.cache_data
def cargar_datos_maestros():
    # Carga de CMN y EO (skiprows=1 por el formato del aplicativo)
    df_cmn = pd.read_excel("CMN-Mensualizado-127-2027-FasedeIdentificación.xlsx", skiprows=1)
    if "Unnamed: 0" in df_cmn.columns: 
        df_cmn = df_cmn.drop(columns=["Unnamed: 0"])
    
    df_eo = pd.read_excel("EO.xlsx")
    df_pp = pd.read_excel("PP.xlsx")
    df_csd = pd.read_excel("Cartera_Servicios_PP_2027_Desagregado_SCF-2.xls",engine='xlrd',skiprows=1)
            
    # Limpieza de nombres de columnas
    df_cmn.columns = df_cmn.columns.str.strip()
    df_eo.columns = df_eo.columns.str.strip()
    df_pp.columns = df_pp.columns.str.strip()
    df_csd.columns= df_csd.columns.str.strip()
          
    # Jerarquía por código (ADN del 01.XX.yy)
    df_cmn['CC_PADRE_CALCULADO'] = df_cmn['AUSUARIA_COD'].str.split('.').str[1]
    df_eo['CC Padre'] = df_eo['CC Padre'].astype(str).str.zfill(2)
    
    # Preparación de datos para el Programa
    df_cmn['PROGRAMA_LIMPIO'] = df_cmn['PROGRAMA'].astype(str).str.split('.').str[0].str.zfill(4)
    
    # Preparación del archivo PP (Programas y Responsables)
    df_pp['Categoria ID'] = df_pp['Categoria ID'].astype(str).str.zfill(4)
    # Agrupar responsables duplicados uniendo sus nombres con " / " para evitar multiplicar el presupuesto
    if 'Categoria' in df_pp.columns and 'Responsable' in df_pp.columns:
        df_pp = df_pp.groupby(['Categoria ID', 'Categoria'])['Responsable'].apply(lambda x: ' / '.join(x.dropna().unique())).reset_index()
    else:
        df_pp = df_pp.drop_duplicates(subset=['Categoria ID'])

    # Unión vinculando cada gasto con su Unidad Orgánica real
    df_unido = pd.merge(df_cmn, df_eo[['CC Padre', 'UO']].drop_duplicates(), 
                        left_on='CC_PADRE_CALCULADO', right_on='CC Padre', how='left')
                        
    # Unión con el archivo PP (Left join para no perder datos del CMN)
    df_unido = pd.merge(df_unido, df_pp, left_on='PROGRAMA_LIMPIO', right_on='Categoria ID', how='left')
    
    # Rellenar vacíos para los programas que no están en el archivo PP
    df_unido['Categoria'] = df_unido['Categoria'].fillna('OTROS / NO CLASIFICADO')
    df_unido['Responsable'] = df_unido['Responsable'].fillna('NO ASIGNADO')

    # Procesamiento de Cartera de Servicios para extraer diccionarios
    if len(df_csd.columns) >= 3:
        # Programa (columna 0)
        prog_series = df_csd.iloc[:, 0].dropna().astype(str)
        dict_prog = {val[:4].strip(): val[4:].strip(' -') for val in prog_series.unique() if len(val) >= 4}
        dict_prog['9001'] = "ACCIONES CENTRALES"
        dict_prog['9002'] = "ASIGNACIONES PRESUPUESTARIAS QUE NO RESULTAN EN PRODUCTOS (APNOP)"

        # Mapeamos Programa a df_unido si su categoria esta vacia o es OTROS
        mask_otros = df_unido['Categoria'] == 'OTROS / NO CLASIFICADO'
        mapped_prog = df_unido.loc[mask_otros, 'PROGRAMA_LIMPIO'].map(dict_prog)
        df_unido.loc[mask_otros, 'Categoria'] = mapped_prog.fillna('OTROS / NO CLASIFICADO')

        # Producto/Proyecto (columna 1)
        prod_series = df_csd.iloc[:, 1].dropna().astype(str)
        dict_prod = {val[:7].strip(): f"{val[:7].strip()} - {val[7:].strip(' -')}" for val in prod_series.unique() if len(val) >= 7}

        # Actividad (columna 2)
        act_series = df_csd.iloc[:, 2].dropna().astype(str)
        dict_act = {val[:7].strip(): f"{val[:7].strip()} - {val[7:].strip(' -')}" for val in act_series.unique() if len(val) >= 7}
        
        # Formatear columnas en df_unido
        df_unido['PROD_PROY_STR'] = df_unido['PROD_PROY'].astype(str).str.replace(r'\.0$', '', regex=True)
        df_unido['ACT_AI_OBR_STR'] = df_unido['ACT_AI_OBR'].astype(str).str.replace(r'\.0$', '', regex=True)
        
        df_unido['PROD_PROY_FULL'] = df_unido['PROD_PROY_STR'].map(dict_prod).fillna(df_unido['PROD_PROY_STR'])
        df_unido['ACT_AI_OBR_FULL'] = df_unido['ACT_AI_OBR_STR'].map(dict_act).fillna(df_unido['ACT_AI_OBR_STR'])
    else:
        df_unido['PROD_PROY_FULL'] = df_unido['PROD_PROY'].astype(str)
        df_unido['ACT_AI_OBR_FULL'] = df_unido['ACT_AI_OBR'].astype(str)

    return df_unido

@st.cache_data
def cargar_poi():
    import glob
    import os
    try:
        # Buscar el archivo POI más reciente en la carpeta
        archivos_poi = glob.glob("POI_PORACTIVIDADOPERATIVA_ANUAL_*.xls")
        if not archivos_poi:
            return pd.DataFrame(columns=['Categoria ID', 'Categoria', 'Producto ID', 'Actividad Presupuestal ID', 'Fn(SE) Total'])
            
        archivo_reciente = max(archivos_poi, key=os.path.getctime)
        
        # El archivo XLS del POI es en realidad un HTML exportado
        df_poi_raw = pd.read_html(archivo_reciente, header=0)[0]
        df_poi_raw.columns = df_poi_raw.columns.str.strip()
        
        # Filtrar solo registros activos
        if 'Activo AO' in df_poi_raw.columns:
            df_poi_activos = df_poi_raw[df_poi_raw['Activo AO'] == 'SI'].copy()
        else:
            df_poi_activos = df_poi_raw.copy()
            
        # Filtrar el año máximo que exista en la columna POI
        if 'POI' in df_poi_activos.columns:
            año_poi = str(df_poi_activos['POI'].max())
            df_poi_activos = df_poi_activos[df_poi_activos['POI'].astype(str) == año_poi]
            
        # Estandarizar IDs a 7 dígitos para que crucen con el CMN
        df_poi_activos['Categoria ID'] = df_poi_activos['Categoria ID'].astype(str).str.replace(r'\.0$', '', regex=True).str.zfill(4)
        df_poi_activos['Producto ID'] = df_poi_activos['Producto ID'].astype(str).str.replace(r'\.0$', '', regex=True).str.zfill(7)
        df_poi_activos['Actividad Presupuestal ID'] = df_poi_activos['Actividad Presupuestal ID'].astype(str).str.replace(r'\.0$', '', regex=True).str.zfill(7)
        
        # Convertir monto ejecutado
        df_poi_activos['Fn(SE) Total'] = pd.to_numeric(df_poi_activos['Fn(SE) Total'], errors='coerce').fillna(0)
        
        # Agrupar a nivel de Programa, Producto y Actividad Presupuestal
        df_poi_resumen = df_poi_activos.groupby(['Categoria ID', 'Categoria', 'Producto ID', 'Producto', 'Actividad Presupuestal ID', 'Actividad Presupuestal'])['Fn(SE) Total'].sum().reset_index()
        return df_poi_resumen
    except Exception as e:
        return pd.DataFrame(columns=['Categoria ID', 'Categoria', 'Producto ID', 'Producto', 'Actividad Presupuestal ID', 'Actividad Presupuestal', 'Fn(SE) Total'])

def ejecutar_analisis():
    try:
        df_final = cargar_datos_maestros()
        
        # Mapeo de Tipo de Bien para que sea más legible (médicos)
        df_final['TIPO_BIEN'] = df_final['TIPO_BIEN'].replace({'B': 'BIENES', 'S': 'SERVICIOS'})
        
        try:
            ano1 = str(int(float(df_final['PROGR_ANO_1'].dropna().iloc[0])))
            ano4 = str(int(float(df_final['PROGR_ANO_4'].dropna().iloc[0])))
            ano2 = str(int(ano1) + 1)
            ano3 = str(int(ano1) + 2)
        except:
            ano1 = "AÑO 1"
            ano2 = "AÑO 2"
            ano3 = "AÑO 3"
            ano4 = "AÑO 4"
            
        cols_montos = [f'MONTO {ano1}', f'MONTO {ano2}', f'MONTO {ano3}', f'MONTO {ano4}']
        th_props = [('text-align', 'right !important'), ('font-weight', 'bold !important')]
        estilos_montos = {col: [{'selector': 'th', 'props': th_props}] for col in cols_montos}
        estilos_con_porcentaje = {**estilos_montos, '%': [{'selector': 'th', 'props': th_props}]}
            
        # --- BARRA LATERAL: FILTROS DE AUDITORÍA ---
        st.sidebar.header("🎯 Filtros de Auditoría")
        
        lista_tipo = ["TODOS"] + sorted(df_final['TIPO_BIEN'].unique().tolist())
        sel_tipo = st.sidebar.selectbox("Bienes o Servicios:", lista_tipo)

        df_final['CLASIFICADOR_FULL'] = df_final['CLASIF_COD'].astype(str) + " - " + df_final['CLASIF_NOMBRE']
        lista_clasif = ["TODOS"] + sorted(df_final['CLASIFICADOR_FULL'].unique().tolist())
        sel_clasif = st.sidebar.selectbox("Seleccione Clasificador:", lista_clasif)

        # Aplicación de filtros
        df_act = df_final.copy()
        if sel_tipo != "TODOS":
            df_act = df_act[df_act['TIPO_BIEN'] == sel_tipo]
        if sel_clasif != "TODOS":
            df_act = df_act[df_act['CLASIFICADOR_FULL'] == sel_clasif]

        # --- CABECERA DE IMPACTO ---
        st.title(f"🖥️ Panel de Control CMN: {ano1} - {ano4}")
        monto_total = df_act['MONT_TOT_ANO1'].sum()
        
        st.write("**PRESUPUESTO TOTAL (SEGMENTO SELECCIONADO):**")
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        m_col1.metric(label=f"Año {ano1}", value=f"S/ {monto_total:,.2f}")
        m_col2.metric(label=f"Año {ano2}", value=f"S/ {df_act['MONT_TOT_ANO2'].sum():,.2f}")
        m_col3.metric(label=f"Año {ano3}", value=f"S/ {df_act['MONT_TOT_ANO3'].sum():,.2f}")
        m_col4.metric(label=f"Año {ano4}", value=f"S/ {df_act['MONT_TOT_ANO4'].sum():,.2f}")
        st.markdown("---")
        
        # --- PESTAÑAS ESTRATÉGICAS ---
        tab_uo, tab_prog, tab_poi = st.tabs(["🏛️ Vista por Órgano", "🎯 Vista por Programa/Categoría Presupuestal)", "⚖️ Consistencia POI vs CMN"])

        with tab_uo:
            opciones_ano = {
                ano1: 'MONT_TOT_ANO1',
                ano2: 'MONT_TOT_ANO2',
                ano3: 'MONT_TOT_ANO3',
                ano4: 'MONT_TOT_ANO4'
            }
            ano_sel_grafico = st.radio("🗓️ Seleccione el año a visualizar en los gráficos:", list(opciones_ano.keys()), horizontal=True)
            col_monto_grafico = opciones_ano[ano_sel_grafico]
            
            col_izq, col_der = st.columns(2)
            with col_izq:
                df_uo = df_act.groupby('UO')[col_monto_grafico].sum().reset_index().sort_values(col_monto_grafico, ascending=False)
                fig_dona = px.pie(df_uo, values=col_monto_grafico, names='UO', hole=0.5,
                                title=f"<b>Distribución por Órgano ({ano_sel_grafico})</b>", labels={col_monto_grafico: f'MONTO {ano_sel_grafico}', 'UO': 'ÓRGANO'})
                st.plotly_chart(fig_dona, use_container_width=True)

            with col_der:
                df_rank = df_act.groupby('AUSUARIA_NOMBRE')[col_monto_grafico].sum().reset_index().sort_values(col_monto_grafico, ascending=True).tail(10)
                fig_barras = px.bar(df_rank, x=col_monto_grafico, y='AUSUARIA_NOMBRE', orientation='h',
                                    title=f"<b>Top 10 Centros de Costo ({ano_sel_grafico})</b>", color_continuous_scale='GnBu',
                                    labels={col_monto_grafico: f'MONTO {ano_sel_grafico}', 'AUSUARIA_NOMBRE': 'DESCRIPCIÓN'})
                st.plotly_chart(fig_barras, use_container_width=True)
            
            st.subheader("🔍 Detalle por Oficina")
            uo_sel = st.selectbox("Seleccione oficina para auditar:", df_uo['UO'].unique())
            df_det_uo = df_act[df_act['UO'] == uo_sel].groupby(['AUSUARIA_COD', 'AUSUARIA_NOMBRE'])[['MONT_TOT_ANO1', 'MONT_TOT_ANO2', 'MONT_TOT_ANO3', 'MONT_TOT_ANO4']].sum().reset_index()
            df_det_uo = df_det_uo.rename(columns={
                'AUSUARIA_COD': 'USUARIO', 
                'AUSUARIA_NOMBRE': 'DESCRIPCIÓN', 
                'MONT_TOT_ANO1': f'MONTO {ano1}',
                'MONT_TOT_ANO2': f'MONTO {ano2}',
                'MONT_TOT_ANO3': f'MONTO {ano3}',
                'MONT_TOT_ANO4': f'MONTO {ano4}'
            })
            formato_moneda = {col: "S/ {:,.2f}" for col in df_det_uo.columns if 'MONTO' in col}
            # Ordenamos y reseteamos el índice para que coincida exactamente con la fila seleccionada
            df_det_uo = df_det_uo.sort_values(f'MONTO {ano1}', ascending=False).reset_index(drop=True)
            
            styled_df_det = df_det_uo.style.format(formato_moneda)\
                .set_properties(subset=cols_montos, **{'text-align': 'right'})\
                .set_table_styles(estilos_montos, overwrite=False)
            
            # DataFrame interactivo
            evento = st.dataframe(styled_df_det, use_container_width=True, on_select="rerun", selection_mode="single-row")
            
            if len(evento.selection.rows) > 0:
                idx_seleccionado = evento.selection.rows[0]
                usu_cod = df_det_uo.iloc[idx_seleccionado]['USUARIO']
                usu_nombre = df_det_uo.iloc[idx_seleccionado]['DESCRIPCIÓN']
                
                st.markdown("---")
                st.subheader(f"📦 Ítems registrados por: {usu_nombre}")
                
                df_items = df_act[(df_act['UO'] == uo_sel) & (df_act['AUSUARIA_COD'] == usu_cod)]
                cols_items = ['TIPO_BIEN', 'NOMBRE_ITEM', 'UNIDAD_MEDIDA', 'PRECIO_UNIT', 'CANT_TOT_ANO1', 'MONT_TOT_ANO1']
                df_items_disp = df_items[cols_items].copy().rename(columns={
                    'TIPO_BIEN': 'TIPO',
                    'NOMBRE_ITEM': 'DESCRIPCIÓN DEL ÍTEM',
                    'UNIDAD_MEDIDA': 'U.M.',
                    'PRECIO_UNIT': 'PRECIO UNIT.',
                    'CANT_TOT_ANO1': f'CANTIDAD {ano1}',
                    'MONT_TOT_ANO1': f'MONTO {ano1}'
                })
                
                st.dataframe(
                    df_items_disp.sort_values(f'MONTO {ano1}', ascending=False)\
                                 .style.format({f'MONTO {ano1}': "S/ {:,.2f}", 'PRECIO UNIT.': "S/ {:,.2f}"}),
                    use_container_width=True
                )

        with tab_prog:
            st.subheader("🎯 Auditoría por Categoría Presupuestal")
            st.info("Navegue desde el Programa Presupuestal hasta el detalle de la Actividad Operativa.")
            st.warning("**[D.L. Nº 1440, 13.6](https://cdn.www.gob.pe/uploads/document/file/206025/DL_1440.pdf?v=1594248074):** El Presupuesto del Sector Público se estructura, gestiona y evalúa bajo la lógica del Presupuesto por Resultado (PpR), la cual constituye una estrategia de gestión pública que vincula los recursos a productos y resultados medibles a favor de la población. Cada una de las fases del proceso presupuestario es realizada bajo la lógica del PpR, a través de sus instrumentos: programas presupuestales, seguimiento, evaluación e incentivos presupuestarios.", icon="⚠️")

            # Filtro opcional para ocultar programas 9xxx en esta vista
            if not st.checkbox("Incluir Categorias Especiales (9xxx)", value=False):
                df_act_tab2 = df_act[~df_act['PROGRAMA_LIMPIO'].str.startswith('9')]
            else:
                df_act_tab2 = df_act.copy()

            # 2. Resumen Ejecutivo (Tabla de arriba)
            df_p = df_act_tab2.groupby(['PROGRAMA_LIMPIO', 'Categoria', 'Responsable'])[['MONT_TOT_ANO1', 'MONT_TOT_ANO2', 'MONT_TOT_ANO3', 'MONT_TOT_ANO4']].sum().reset_index().sort_values('MONT_TOT_ANO1', ascending=False)
            df_p['%'] = (df_p['MONT_TOT_ANO1'] / monto_total) * 100
            
            # Formateamos el nombre del programa
            df_p['PROGRAMA_FULL'] = df_p['PROGRAMA_LIMPIO'] + " - " + df_p['Categoria']
            
            df_p_disp = df_p[['PROGRAMA_FULL', 'Responsable', 'MONT_TOT_ANO1', 'MONT_TOT_ANO2', 'MONT_TOT_ANO3', 'MONT_TOT_ANO4', '%']].rename(columns={
                'PROGRAMA_FULL': 'PROGRAMA', 
                'Responsable': 'RESPONSABLE',
                'MONT_TOT_ANO1': f'MONTO {ano1}',
                'MONT_TOT_ANO2': f'MONTO {ano2}',
                'MONT_TOT_ANO3': f'MONTO {ano3}',
                'MONT_TOT_ANO4': f'MONTO {ano4}'
            })
            st.write("**Concentración del Gasto:**")
            formato_moneda_p = {col: "S/ {:,.2f}" for col in df_p_disp.columns if 'MONTO' in col}
            formato_moneda_p['%'] = "{:.1f}%"
            styled_df_p = df_p_disp.style.format(formato_moneda_p)\
                .set_properties(subset=cols_montos + ['%'], **{'text-align': 'right'})\
                .set_table_styles(estilos_con_porcentaje, overwrite=False)
            st.dataframe(styled_df_p, use_container_width=True)

            st.markdown("---")
            st.subheader("🔍 Explorador de Actividades")
            
            # 3. Selectores en Cascada (El corazón de la auditoría)
            col1, col2 = st.columns(2)
            
            with col1:
                prog_sel = st.selectbox("1. Seleccione Programa:", df_p['PROGRAMA_FULL'].unique())
                prog_cod = prog_sel.split(" - ")[0]
                df_filtro_p = df_act[df_act['PROGRAMA_LIMPIO'] == prog_cod]
                
                prod_sel = st.selectbox("2. Seleccione Producto/Proyecto:", sorted(df_filtro_p['PROD_PROY_FULL'].unique()))
                df_filtro_prod = df_filtro_p[df_filtro_p['PROD_PROY_FULL'] == prod_sel]

            with col2:
                act_sel = st.selectbox("3. Seleccione Actividad (AI/OBR):", sorted(df_filtro_prod['ACT_AI_OBR_FULL'].unique()))
                df_filtro_act = df_filtro_prod[df_filtro_prod['ACT_AI_OBR_FULL'] == act_sel]

            # 4. Resultado Final: El detalle de la Actividad Operativa
            st.write(f"**Detalle de Actividades Operativas para: {act_sel}**")
            
            df_final_tab = df_filtro_act.groupby(['ACTIV_OPERAT_NOMBRE', 'TIPO_BIEN'])[['MONT_TOT_ANO1', 'MONT_TOT_ANO2', 'MONT_TOT_ANO3', 'MONT_TOT_ANO4']].sum().reset_index()
            df_final_tab_disp = df_final_tab.rename(columns={
                'ACTIV_OPERAT_NOMBRE': 'ACTIVIDAD OPERATIVA', 
                'TIPO_BIEN': 'TIPO DE INSUMO', 
                'MONT_TOT_ANO1': f'MONTO {ano1}',
                'MONT_TOT_ANO2': f'MONTO {ano2}',
                'MONT_TOT_ANO3': f'MONTO {ano3}',
                'MONT_TOT_ANO4': f'MONTO {ano4}'
            })
            
            # Mostramos el resultado con formato moneda
            formato_moneda_f = {col: "S/ {:,.2f}" for col in df_final_tab_disp.columns if 'MONTO' in col}
            styled_df_final = df_final_tab_disp.sort_values(f'MONTO {ano1}', ascending=False).style.format(formato_moneda_f)\
                .set_properties(subset=cols_montos, **{'text-align': 'right'})\
                .set_table_styles(estilos_montos, overwrite=False)
            st.dataframe(styled_df_final, use_container_width=True)
            
            # Un extra: ¿Cuánto suma este nivel de detalle?
            suma_ano1 = df_final_tab['MONT_TOT_ANO1'].sum()
            suma_ano2 = df_final_tab['MONT_TOT_ANO2'].sum()
            suma_ano3 = df_final_tab['MONT_TOT_ANO3'].sum()
            suma_ano4 = df_final_tab['MONT_TOT_ANO4'].sum()
            
            st.success(
                f"**Monto total por año en este nivel de selección:**\n\n"
                f"**{ano1}:** S/ {suma_ano1:,.2f} &nbsp;&nbsp;|&nbsp;&nbsp; "
                f"**{ano2}:** S/ {suma_ano2:,.2f} &nbsp;&nbsp;|&nbsp;&nbsp; "
                f"**{ano3}:** S/ {suma_ano3:,.2f} &nbsp;&nbsp;|&nbsp;&nbsp; "
                f"**{ano4}:** S/ {suma_ano4:,.2f}"
            )

        with tab_poi:
            st.subheader("⚖️ Consistencia Financiera: POI 2025 vs CMN")
            st.info(f"Comparación del presupuesto ejecutado en 2025 frente a la proyección de necesidades del CMN ({ano1}) a nivel de Actividad Presupuestal.")
            
            with st.expander("📌 Consideraciones Metodológicas (Alcance de los datos)"):
                st.markdown("""
                **¡Importante tener en cuenta al analizar esta brecha!**
                * **Ejecutado POI (2025):** Incluye **toda fuente de financiamiento** y **todas las genéricas de gasto** (Personal, Bienes y Servicios, Equipamiento, etc.).
                * **Programado CMN (2027):** Solo refleja requerimientos para la fuente **Recursos Ordinarios** y exclusivamente para las genéricas de gasto de **Bienes y Servicios**.
                * *Nota Adicional:* Este cruce aún no se compara contra la **APM (Asignación Presupuestal Multianual)**, la cual constituye el techo/piso financiero real del que se parte.
                """)
            
            df_poi = cargar_poi()
            
            # Agrupar CMN a nivel de Programa, Producto y Actividad
            cmn_agg = df_act.groupby(['PROGRAMA_LIMPIO', 'Categoria', 'PROD_PROY_STR', 'ACT_AI_OBR_STR', 'PROD_PROY_FULL', 'ACT_AI_OBR_FULL'])[f'MONT_TOT_ANO1'].sum().reset_index()
            cmn_agg['PROD_PROY_STR'] = cmn_agg['PROD_PROY_STR'].str.zfill(7)
            cmn_agg['ACT_AI_OBR_STR'] = cmn_agg['ACT_AI_OBR_STR'].str.zfill(7)
            
            # Cruce de información
            df_cruce = pd.merge(cmn_agg, df_poi, left_on=['PROGRAMA_LIMPIO', 'PROD_PROY_STR', 'ACT_AI_OBR_STR'], right_on=['Categoria ID', 'Producto ID', 'Actividad Presupuestal ID'], how='outer')
            
            # Limpieza para visualización
            df_cruce['PROGRAMA_LIMPIO'] = df_cruce['PROGRAMA_LIMPIO'].fillna(df_cruce['Categoria ID'])
            df_cruce['PROGRAMA_FULL'] = df_cruce['PROGRAMA_LIMPIO'] + " - " + df_cruce['Categoria_x'].fillna(df_cruce['Categoria_y'])
            
            df_cruce['PROD_PROY_FULL'] = df_cruce['PROD_PROY_FULL'].fillna(df_cruce['Producto ID'] + " - " + df_cruce['Producto'] + " (Solo en POI)")
            df_cruce['ACT_AI_OBR_FULL'] = df_cruce['ACT_AI_OBR_FULL'].fillna(df_cruce['Actividad Presupuestal ID'] + " - " + df_cruce['Actividad Presupuestal'] + " (Solo en POI)")
            df_cruce['Fn(SE) Total'] = df_cruce['Fn(SE) Total'].fillna(0)
            df_cruce[f'MONT_TOT_ANO1'] = df_cruce[f'MONT_TOT_ANO1'].fillna(0)
            df_cruce['BRECHA'] = df_cruce[f'MONT_TOT_ANO1'] - df_cruce['Fn(SE) Total']
            
            df_cruce_disp = df_cruce[['PROGRAMA_FULL', 'PROD_PROY_FULL', 'ACT_AI_OBR_FULL', 'Fn(SE) Total', f'MONT_TOT_ANO1', 'BRECHA']].rename(columns={
                'PROGRAMA_FULL': 'PROGRAMA PRESUPUESTAL',
                'PROD_PROY_FULL': 'PRODUCTO',
                'ACT_AI_OBR_FULL': 'ACTIVIDAD',
                'Fn(SE) Total': 'EJECUTADO POI',
                f'MONT_TOT_ANO1': f'PROGRAMADO CMN {ano1}'
            })
            
            # Alertas rápidas
            col_a, col_b = st.columns(2)
            sin_cmn = len(df_cruce[(df_cruce['Fn(SE) Total'] > 0) & (df_cruce[f'MONT_TOT_ANO1'] == 0)])
            sin_poi = len(df_cruce[(df_cruce['Fn(SE) Total'] == 0) & (df_cruce[f'MONT_TOT_ANO1'] > 0)])
            
            col_a.warning(f"⚠️ **{sin_cmn} Actividades** tienen ejecución en el POI pero **CERO** necesidades en el CMN {ano1}.")
            col_b.info(f"ℹ️ **{sin_poi} Actividades** son nuevas o no tuvieron ejecución en el POI pero piden presupuesto en el CMN {ano1}.")
            
            st.markdown("---")
            st.write("**Detalle del Cruce (Monto Programado vs Monto Ejecutado):**")
            
            format_dict = {
                'EJECUTADO POI': "S/ {:,.2f}",
                f'PROGRAMADO CMN {ano1}': "S/ {:,.2f}",
                'BRECHA': "S/ {:,.2f}"
            }
            
            # Formateo de estilo para resaltar la brecha
            def color_brecha(val):
                if val < 0:
                    return 'color: #ff4b4b; font-weight: bold'
                elif val > 0:
                    return 'color: #09ab3b; font-weight: bold'
                return ''
                
            # Estilo para resaltar filas que solo existen en el POI
            def highlight_solo_poi(row):
                # Usamos un amarillo oscuro/dorado que se lee bien en temas oscuros y claros
                color = 'color: #e6b800; font-weight: bold' 
                if "(Solo en POI)" in str(row['PRODUCTO']) or "(Solo en POI)" in str(row['ACTIVIDAD']):
                    return [color for _ in row]
                return ['' for _ in row]
                
            st.dataframe(
                df_cruce_disp.sort_values('EJECUTADO POI', ascending=False)
                .style.format(format_dict)
                .apply(highlight_solo_poi, axis=1)
                .map(color_brecha, subset=['BRECHA']),
                use_container_width=True
            )

    except Exception as e:
        st.error(f"Se detectó un problema: {e}")