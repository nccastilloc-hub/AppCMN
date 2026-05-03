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
    
    # Limpieza de nombres de columnas
    df_cmn.columns = df_cmn.columns.str.strip()
    df_eo.columns = df_eo.columns.str.strip()
    df_pp.columns = df_pp.columns.str.strip()
      
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

    return df_unido

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
        tab_uo, tab_prog = st.tabs(["🏛️ Vista por Órgano", "🎯 Vista por Programa (BID)"])

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
            styled_df_det = df_det_uo.sort_values(f'MONTO {ano1}', ascending=False).style.format(formato_moneda)\
                .set_properties(subset=cols_montos, **{'text-align': 'right'})\
                .set_table_styles(estilos_montos, overwrite=False)
            st.table(styled_df_det)

        with tab_prog:
            st.subheader("🎯 Auditoría por Categoría Presupuestal")
            st.info("Navegue desde el Programa Presupuestal hasta el detalle de la Actividad Operativa.")

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
            st.table(styled_df_p)

            st.markdown("---")
            st.subheader("🔍 Explorador de Actividades")
            
            # 3. Selectores en Cascada (El corazón de la auditoría)
            col1, col2 = st.columns(2)
            
            with col1:
                prog_sel = st.selectbox("1. Seleccione Programa:", df_p['PROGRAMA_FULL'].unique())
                prog_cod = prog_sel.split(" - ")[0]
                df_filtro_p = df_act[df_act['PROGRAMA_LIMPIO'] == prog_cod]
                
                prod_sel = st.selectbox("2. Seleccione Producto/Proyecto:", sorted(df_filtro_p['PROD_PROY'].unique()))
                df_filtro_prod = df_filtro_p[df_filtro_p['PROD_PROY'] == prod_sel]

            with col2:
                act_sel = st.selectbox("3. Seleccione Actividad (AI/OBR):", sorted(df_filtro_prod['ACT_AI_OBR'].unique()))
                df_filtro_act = df_filtro_prod[df_filtro_prod['ACT_AI_OBR'] == act_sel]

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
            st.table(styled_df_final)
            
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
    except Exception as e:
        st.error(f"Se detectó un problema: {e}")