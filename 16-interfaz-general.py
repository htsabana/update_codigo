# -*- coding: utf-8 -*-
"""
Created on Sat May 28 19:30:33 2022

@author: groja
"""

#%%
import datetime
import base64
import pickle
import time
import asyncio
import seaborn as sns
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import psycopg2 as pg
import psycopg2.extras as pg2
from PIL import Image
from sklearn import svm
from scipy import stats
from datetime import timedelta
from streamlit_autorefresh import st_autorefresh
pd.options.mode.chained_assignment = None  # default='warn'
#%% FUNCIONES

def filedownload(df):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()  # strings <-> bytes conversions
    href = f'<a href="data:file/csv;base64,{b64}" download="sensor_file.csv">Descargar archivo CSV</a>'
    return href

@st.cache
def convert_df(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_csv().encode('utf-8')

def posiciones_sabana(input_parameter,img_box):
    if input_parameter == 0:
        input_parameter = 'Paciente acostado apoyado en hombro derecho'
        img_box.image(st.session_state.h_der,width=200)
    elif input_parameter == 1:
        input_parameter = 'Paciente acostado apoyado en hombro izquierdo'
        img_box.image(st.session_state.h_izq,width=200)
    elif input_parameter == 2:
        input_parameter = 'Paciente acostado de espalda'
        img_box.image(st.session_state.boca_arriba,width=200)
    elif input_parameter == 3:
        input_parameter = 'Paciente acostado boca abajo'
        img_box.image(st.session_state.boca_abajo,width=200)
    elif input_parameter == 4:
        input_parameter = 'Paciente no se encuentra acostado'
        img_box.image(st.session_state.bed,width=200)
    return input_parameter

#%% start program
if "start_program" not in st.session_state:
    st.session_state.start_program = True
#%% IMAGENES
if "ht_2" not in st.session_state:
    st.session_state.ht_2 = Image.open('ht2.jfif')
if "boca_abajo" not in st.session_state:
    st.session_state.boca_abajo = Image.open('boca_abajo.png')
if "boca_arriba" not in st.session_state:
    st.session_state.boca_arriba = Image.open('boca_arriba.png') 
if "h_izq" not in st.session_state:
    st.session_state.h_izq = Image.open('hombro_izquierdo.png')
if "h_der" not in st.session_state:
    st.session_state.h_der = Image.open('hombro_derecho.png')
if "bed" not in st.session_state:
    st.session_state.bed = Image.open('bed_alone.png')

#%% BASE DE DATOS PACIENTES CON SÁBANA

filename = 'datos_pos.pickle'
if "infile" not in st.session_state:
    st.session_state.infile = open(filename,'rb')
if "df_datos" not in st.session_state:
    st.session_state.df_datos = pickle.load(st.session_state.infile)
st.session_state.infile.close()

#%% VARIABLES PARA ENTRENAMIENTO CLASIFICADOR
y = np.array(list(st.session_state.df_datos['Etiqueta']))
X = np.array(st.session_state.df_datos.iloc[:, 1:25])

#%% CLASIFICADOR SVM

if "clf" not in st.session_state:
    st.session_state.clf = svm.SVC()
    st.session_state.clf.fit(X,y)

db_pctes = "database_pctes.xlsx"

if "db_pctes_df" not in st.session_state:
    st.session_state.db_pctes_df = pd.read_excel(db_pctes,index_col=[0])
    st.session_state.db_pctes_df = st.session_state.db_pctes_df.sort_values(by=['estado'],ascending=False)
    st.session_state.db_pctes_df = st.session_state.db_pctes_df.reset_index(drop=True)

pct_tup = list(st.session_state.db_pctes_df['Paciente'])
pct_tup = tuple(pct_tup)

#%% BASE DE DATOS POSTGRESQL (ENVÍO DATOS SENSORES)
#connect to db
con = pg.connect(
    host = '152.74.29.160',
    user = 'postgres',
    password = 'somno2019',
    port = '9001',
    database = 'somno')

#cursor
cur = con.cursor()

#%% ACTUALIZA LISTADO DE SÁBANAS
if "sabanas" not in st.session_state:
    st.session_state.sabanas = 0
    
if st.session_state.sabanas == 0:
    create_script = """ CREATE TABLE IF NOT EXISTS sabanas_table(
                            mac      varchar(40) PRIMARY KEY,
                            id_sabana    varchar(40)
                                                                                                                       
                          )
            
    """
    cur.execute(create_script)
    # con.commit()
    
    
    s = ""
    s += "SELECT"
    s += " table_schema"
    s += ", table_name"
    s += " FROM information_schema.tables"
    s += " WHERE"
    s += " ("
    s += " table_schema = 'public'"
    s += " )"
    s += " ORDER BY table_schema, table_name;"
    
    
    cur.execute(s)
    list_tables = cur.fetchall()
    
    output_table = [item for t in list_tables for item in t]
    mac_list = []
    ids = []
    # k = 1
    for t_name_table in output_table:
        if t_name_table.startswith('mac'):
            # print(t_name_table + "\n")
            mac_list.append(t_name_table.replace('mac_',''))
            # ids.append('000' + str(k))
            # k+=1
    
    
    psql_table2 = 'SELECT mac FROM sabanas_table'
    
    cur.execute(psql_table2)
    macs = cur.fetchall()
    macs = [item for t in macs for item in t]
    
    
    insert_script = 'INSERT INTO sabanas_table (mac, id_sabana) VALUES (%s,%s)'
    n = 1
    for mac in mac_list:
        if mac not in macs:
            print(mac)
            insert_values = (mac,'000' + str(len(macs) + n))
            
            cur.execute(insert_script,insert_values)
            n+=1
    con.commit()
    st.session_state.sabanas = 1
#%% INTERFACES

def parameter_interface():
    
    col1, mid, col2 = st.columns([1,10,1])
    with col1:
        st.image('logo.png', width=90)
    
    with mid:
        st.markdown("<h1 style='text-align: center; color: black;'>Selección de parámetros</h1>", unsafe_allow_html=True)
    st.write('Interfaz destinada a designar parámetros a los pacientes. (en desarrollo)')
        
    pct = st.selectbox(
        'Seleccionar paciente',
        pct_tup)

    pos_parameter = st.text_input('Advertencia tiempo en misma posición (hrs) (default= 2 hrs)', st.session_state.db_pctes_df['pos_p'][st.session_state.db_pctes_df.index[st.session_state.db_pctes_df['Paciente'] == pct][0]],key=1)#key=random.randint(0, 9999))
    bed_parameter = st.text_input('Advertencia tiempo en cama (hrs) (default= 20 hrs)', st.session_state.db_pctes_df['bed_p'][st.session_state.db_pctes_df.index[st.session_state.db_pctes_df['Paciente'] == pct][0]],key=2)#random.randint(0, 9999))
    # resp_parameter = st.text_input('Advertencia frecuencia respiratoria (RPM) (default= 30 rpm)', st.session_state.db_pctes_df['resp_p'][st.session_state.db_pctes_df.index[st.session_state.db_pctes_df['Paciente'] == pct][0]],key=3)#random.randint(0, 9999))
    st.session_state.db_pctes_df['pos_p'][st.session_state.db_pctes_df.index[st.session_state.db_pctes_df['Paciente'] == pct][0]] = pos_parameter
    # st.session_state.db_pctes_df['resp_p'][st.session_state.db_pctes_df.index[st.session_state.db_pctes_df['Paciente'] == pct][0]] = resp_parameter
    st.session_state.db_pctes_df['bed_p'][st.session_state.db_pctes_df.index[st.session_state.db_pctes_df['Paciente'] == pct][0]] = bed_parameter
    st.session_state.db_pctes_df.to_excel("database_pctes.xlsx")

#%%

def visualize_report(postgreSQL_select_Query):#,count):

    prev_time = 0
    fig, ax = plt.subplots()
    start = time.perf_counter()

    heat_map = st.empty() ## mapa de calor
    time_box = st.empty() ## tiempo transcurrido
    warning_box = st.empty() ## alerta de tiempo
    pos_box = st.empty() ## posición del paciente
    pos_img_box = st.empty() ##imagen de la posicion del pcte

    while True:

        time_ = time.perf_counter()
        pred_list = []
        plt.close(fig)

        fig, ax = plt.subplots()

        cur.execute(postgreSQL_select_Query)
        mobile_records = cur.fetchall()
        mobile_records = [list(elem[1:]) for elem in mobile_records]
        mobile_records_2 = []
        max_val = np.int32(4068)
        min_val = np.int32(0)
        for i in range(len(mobile_records)):
            data_norm = (mobile_records[i] - min_val)/(max_val - min_val)
            mobile_records_2.append(data_norm)


        sens = mobile_records_2[0]

        if time_ - prev_time >= 5: ## se actualiza cada 5 segundos
            for record in mobile_records:
                y_preds = st.session_state.clf.predict([record])[0]
                pred_list.append(y_preds)
            final_mode = stats.mode(pred_list)[0][0]
            pos_box.write(posiciones_sabana(final_mode,pos_img_box))
            prev_time = time_

        df_data = {
            'col1': [sens[19],sens[16],sens[13]],
            'col2': [sens[5],sens[2],sens[22]],
            'col3': [sens[9],sens[6],sens[3]],
            'col4': [sens[18],sens[15],sens[12]],
            'col5': [sens[4],sens[1],sens[21]],
            'col6': [sens[0],sens[10],sens[7]],
            'col7': [sens[14],sens[11],sens[8]],
            'col8': [sens[23],sens[20],sens[17]]
        }

        # time_box.write('Minutos transcurridos: ' + str(count))
        
        hm_df = pd.DataFrame.from_dict(df_data)
        
        sns.heatmap(hm_df,vmin=0,vmax=1,annot=True,ax=ax,square=True)
        heat_map.write(fig)

        time.sleep(0.2)

#%%

async def health_team_interface():
    
    # count = st_autorefresh(interval=60000*1, key="refresco_equipo_salud")

    # async def update():

    #     if "prev_pos" not in st.session_state:
    #         st.session_state.prev_pos = {}
    #         for i in range(len(st.session_state.db_pctes_df)):
    #             st.session_state.prev_pos[str(st.session_state.db_pctes_df['Paciente'][i])] = st.session_state.db_pctes_df['pos'][i]

    #     for i in range(len(st.session_state.db_pctes_df)):
    #         postgreSQL_select_Query = "select * from " + str(st.session_state.db_pctes_df['MAC'][i]) + " order by time desc limit 30"

    #         pred_list = []
    #         cur.execute(postgreSQL_select_Query)
    #         mobile_records = cur.fetchall()
    #         mobile_records = [list(elem[1:]) for elem in mobile_records]

    #         for record in mobile_records:
    #             y_preds = st.session_state.clf.predict([record])[0]
    #             pred_list.append(y_preds)
    #         final_pos = stats.mode(pred_list)[0][0]

    #         st.session_state.db_pctes_df['pos'][i] = final_pos

    #         if final_pos == st.session_state.prev_pos[str(st.session_state.db_pctes_df['Paciente'][i])] and count >= 3 and final_pos != 4:
    #             st.write('Paciente ' + str(st.session_state.db_pctes_df['Paciente'][i]) + ' se encuentra en la misma posición que la anterior')
    #             if st.session_state.db_pctes_df['estado'][i] == 0:
    #                 print(st.session_state.db_pctes_df['Paciente'][i])
    #                 st.session_state.db_pctes_df['estado'][i] = 1

    #         st.session_state.prev_pos[str(st.session_state.db_pctes_df['Paciente'][i])] = final_pos

    #     st.session_state.db_pctes_df.to_excel('database_pctes.xlsx')
    #     st.write('Actualizado')

    col1, mid, col2 = st.columns([1,10,1])
    with col1:
        st.image('logo.png', width=90)
    with mid:
        st.markdown("<h1 style='text-align: center; color: black;'>Interfaz de pacientes</h1>", unsafe_allow_html=True)

    st.write('Interfaz destinada al monitoreo en tiempo real de pacientes.')
 
    st.sidebar.image(st.session_state.ht_2,width=200)
    st.sidebar.subheader('**Proximamente...**')
    st.sidebar.title('Estados del paciente')

    # if count%2 == 0:
    #     task_2 = asyncio.create_task(update())
    #     r = await asyncio.sleep(0.5)
    
    
    col1,mid,col2 = st.sidebar.columns([1,1,1])
    
    with col1:
        st.image('c_verde.png',width=50)
        st.write('Buen estado')
    with mid:
        st.image('c_amarillo.png',width=50)
        st.write('Estado regular')
    with col2:
        st.image('c_rojo.png',width=50)
        st.write('Estado crítico')
        
    psql_table = 'SELECT * FROM pct_table'
    
    cur.execute(psql_table)
    pcts = cur.fetchall()
    # num_fields = len(cur.description)
    field_names = [i[0] for i in cur.description]
    
    df_pcts = pd.DataFrame(pcts,columns=field_names)
    
    psql_table3 = 'SELECT * FROM assign_table'
    
    cur.execute(psql_table3)
    pcts3 = cur.fetchall()
    field_names = [i[0] for i in cur.description]
    
    df_pcts3 = pd.DataFrame(pcts3,columns=field_names)
    
    # ids_list = list(df_pcts3['id_pct'].loc[df_pcts3['fecha_termino'] == '-'])
    # ids_list = list(dict.fromkeys(ids_list))
    
    df_pcts3 = df_pcts3.loc[df_pcts3['fecha_termino'] == '-']
    
    df_general = pd.merge(df_pcts3,df_pcts,how='left',on='id_pct')
    
    
    
    for i in range(len(df_general)):

        col1, mid, col2 = st.columns([1,5,1])
        with col1:
            st.image('bed_sheet_logo.png', width=90)
        with mid:
            st.write('Identificador: ' + str(df_general['mac'][i]))
            st.write('Nombre: ' + str(df_general['nombre'][i]))
            st.write('ID Paciente: ' + str(df_general['id_pct'][i]))
            st.write('ID sábana ocupada: S' + str(df_general['id_sabana'][i]))
            if st.checkbox('Visualizar en tiempo real paciente: ' + str(df_general['id_pct'][i]),key=i):
                postgreSQL_select_Query = "select * from mac_" + str(df_general['mac'][i]) + " order by time desc limit 30"

                visualize_report(postgreSQL_select_Query)#,count)
 
        # with col2:
        #     if st.session_state.db_pctes_df['estado'][i] == 0:
        #         st.image('c_verde.png', width=50)
        #     elif st.session_state.db_pctes_df['estado'][i] == 1:
        #         st.image('c_amarillo.png', width=50)
        #         st.warning('ALERTA')
        #     elif st.session_state.db_pctes_df['estado'][i] == 2:
        #         st.image('c_rojo.png', width=50)
        #         st.error('CRÍTICO')
    r = await asyncio.sleep(0.5)
    return ''

#%%

def download_csv_file_interface():
    if "state_csv" not in st.session_state:
        st.session_state.state_csv = 0
    col1, mid, col2 = st.columns([1,5,1])
    with col1:
        st.image('logo.png', width=90)
    with mid:
        st.markdown("<h1 style='text-align: center; color: black;'>Interfaz de descarga archivo de datos</h1>", unsafe_allow_html=True)
    
    st.write('Interfaz destinada a la descarga del archivo tipo .csv con información de sensores.')
    
    psql_table = 'SELECT * FROM pct_table'

    cur.execute(psql_table)
    info = cur.fetchall()
    # num_fields = len(cur.description)
    field_names = [i[0] for i in cur.description]
    info_list = [list(x) for x in info]



    df_pcts = pd.DataFrame(info_list,columns=field_names)
    
    option = st.selectbox(
        'Seleccionar paciente',
        list(df_pcts['id_pct']),key=25)
    
    psql_table2 = 'SELECT * FROM assign_table'
    
    cur.execute(psql_table2)
    info_sb = cur.fetchall()
    # num_fields = len(cur.description)
    field_names = [i[0] for i in cur.description]
    info_list_sb = [list(x) for x in info_sb]
    
    
    df_pcts_sb = pd.DataFrame(info_list_sb,columns=field_names)
    df_pcts3 = df_pcts_sb.drop_duplicates(subset=['id_pct'],keep='last')
    ids_list = list(df_pcts3['id_pct'])
    
    try:
        
        ind = max(df_pcts3['fecha_termino'].loc[df_pcts_sb['id_pct'] == option].index)
        if option in ids_list:
            st.success('Usuario asignado a sábana')
            st.session_state.state_csv = 1
        
        # ind = max(df_pcts_sb['fecha_termino'].loc[df_pcts_sb['id_pct'] == option].index)
        # if df_pcts_sb['fecha_termino'].loc[df_pcts_sb['id_pct'] == option][ind] == '-':
        #     st.success('Usuario asignado a sábana')
        #     st.session_state.state_csv = 1
        else:
            st.info('Usuario no asignado a sábana, favor asignar o seleccionar otro usuario')
            st.session_state.state_csv = 0
    except:
        st.info('Usuario no asignado a sábana, favor asignar o seleccionar otro usuario')
        st.session_state.state_csv = 0


    if st.session_state.state_csv == 1:
        #% SIDEBAR
        # st.sidebar.image(st.session_state.ht_2, width=200)
        st.sidebar.header('Información de paciente')
        st.sidebar.write('Nombre paciente:', str(df_pcts['nombre'].loc[df_pcts['id_pct'] == option][df_pcts.index[df_pcts['id_pct'] == option][0]]))
        st.sidebar.write('Rut paciente:', str(df_pcts['id_pct'].loc[df_pcts['id_pct'] == option][df_pcts.index[df_pcts['id_pct'] == option][0]]))
        st.sidebar.write('N° Sabana en uso (o última en ser utilizada):', str(df_pcts_sb['id_sabana'].loc[df_pcts_sb['id_pct'] == option][ind]))
        st.sidebar.write('MAC address:', str(df_pcts_sb['mac'].loc[df_pcts_sb['id_pct'] == option][ind]))
    
        #%
        time_stamp_2 = ('1 hour','5 hours','12 hours','1 day','2 days')
        time_stamp = ('1 hora','5 horas','12 horas','1 día','2 días')
        #%
    
        st.header("""
            Descargar archivo con datos de sábana de acuerdo a rango de fechas: 
                """)
    
        d1 = datetime.date.today()
        d2 = d1 + datetime.timedelta(days=1)
        st.write("""
            **Seleccionar fecha:**
                """)
    
        start_date = st.date_input('Desde:', d1)
        t1 = st.time_input('Hora:', datetime.time(00, 00),key=0)
        end_date = st.date_input('Hasta:', d2)
        t2 = st.time_input('Hora:', datetime.time(00, 15),key=1)
    
        if start_date <= end_date and t1 < t2:
            # print(datetime.datetime.combine(start_date, t1) + timedelta(hours=4))
            # temp_date = datetime.datetime.combine(start_date, t1) + timedelta(hours=4)
            # temp_date_str = temp_date.strftime("%m-%d-%Y %H:%M:%S")
            # temp_date2 = datetime.datetime.combine(end_date, t2) + timedelta(hours=4)
            # temp_date_str2 = temp_date2.strftime("%m-%d-%Y %H:%M:%S")
            
            # print(temp_date_str)
            # print(temp_date_str2)
            
            start_date = str(start_date) + ' ' + str(t1)
            end_date = str(end_date) + ' ' + str(t2)
            # print(start_date)
            
            st.success('Desde: `%s`\n\nHasta: `%s`' % (start_date[:-3], end_date[:-3]))
            postgreSQL_select_Query_2 = "select * from mac_" + str(df_pcts_sb['mac'].loc[df_pcts_sb['id_pct'] == option][ind]) + " where time between " + "'" + start_date + "'" + " and " + "'" + end_date + "'"
            # postgreSQL_select_Query_2 = "select * from " + str(db_mac) + " where time between " + "'" + temp_date_str + "'" + " and " + "'" + temp_date_str2 + "'"
            cur.execute(postgreSQL_select_Query_2)
            mobile_records_2 = cur.fetchall()
            log_df = pd.DataFrame(mobile_records_2)
            log_df = convert_df(log_df)
            
            st.download_button(
                 label="Descargar archivo con info. de sensores",
                 data=log_df,
                 file_name='info_sensores.csv',
                 mime='text/csv',
                 key = 1,
             )

            # st.markdown(filedownload(log_df), unsafe_allow_html=True)
        
        else:
            st.error('Error: Rango de fechas inválido.')
            pass
    
        st.header("""
            Descargar archivo con datos de sábana en las últimas: 
                """)
        time_checkbox = st.checkbox('Selección de horas',key=1)
        
        if time_checkbox:
            select_time = st.radio(
                'Seleccionar tiempo a descargar:',
                time_stamp)
            time_stamp = list(time_stamp)
            time_stamp_2 = list(time_stamp_2)
        
            for i in range(len(time_stamp)):
                if str(select_time) == time_stamp[i]:
                    select_time = time_stamp_2[i]
        
            postgreSQL_select_Query_2 = "select * from mac_" + str(df_pcts_sb['mac'].loc[df_pcts_sb['id_pct'] == option][ind]) + " where time >= NOW() - " + "'" + str(select_time) + "'" + "::INTERVAL"
            print(postgreSQL_select_Query_2)
            cur.execute(postgreSQL_select_Query_2)
            mobile_records_2 = cur.fetchall()
        
            log_df = pd.DataFrame(mobile_records_2)
            log_df = convert_df(log_df)
            
            st.download_button(
                 label="Descargar archivo con info. de sensores",
                 data=log_df,
                 file_name='info_sensores.csv',
                 mime='text/csv',
                 key = 2,
             )
            # st.markdown(filedownload(log_df), unsafe_allow_html=True)

#%%

def active_users_int():
    
    col1, mid, col2 = st.columns([1,5,1])
    with col1:
        st.image('logo.png', width=90)
    with mid:
        st.markdown("<h1 style='text-align: center; color: black;'>Interfaz de sábanas activas</h1>", unsafe_allow_html=True)
    st.header('Interfaz para verificar que las sábanas estén enviando información al servidor.')
    
    s = ""
    s += "SELECT"
    s += " table_schema"
    s += ", table_name"
    s += " FROM information_schema.tables"
    s += " WHERE"
    s += " ("
    s += " table_schema = 'public'"
    s += " )"
    s += " ORDER BY table_schema, table_name;"


    cur.execute(s)
    list_tables = cur.fetchall()

    output_table = [item for t in list_tables for item in t]
    mac_list_us = []

    for t_name_table in output_table:
        if t_name_table.startswith('mac'):
            # print(t_name_table + "\n")
            mac_list_us.append(t_name_table)
    # active_users = st.empty()
    n = 0
    count2 = st_autorefresh(interval=60000*1, key="refresco_equipo_salud_2")
    # while True:
    for i in range(2):
        active = []
        if n == 0:
            data_list = []
        for i in range(len(mac_list_us)):
            
            postgreSQL_select_Query = "select * from " + str(mac_list_us[i]) + " order by time desc limit 30"
            cur.execute(postgreSQL_select_Query)
            mobile_records = cur.fetchall()
            data_date = mobile_records[0][0]
            if n > 0:
                if data_date == data_list[i]:
                    print('No actualizado')
                else:
                    active.append(mac_list_us[i])
                    print('Actualizado')
            # print(data_date)
            if n == 0:
                data_list.append(data_date)
            if i == (len(mac_list_us)-1) and n > 0:
                print('Lista actualizada')
                # n = 0
            time.sleep(1)
            # print(n)
        # print(active)
        # print(data_list)
        if n == 0:
            n+=1
        else:
            n = 0
            
        # for users in active:
        #     active_users.write(str(users) + ' Activo')
    col1,mid,col2 = st.columns([1,5,2])
    
    for active_users in active:
        with col1:
            st.image('c_verde.png',width=50)
        with mid:
            st.subheader(active_users + ' Activa')

    #close cursor
    # cur.close()
    
    # #close connection
    # con.close()

#%%

def user_control():
    
    # if "count" not in st.session_state:
    #     st.session_state.count = 0
        
    col1, mid, col2 = st.columns([1,5,1])
    with col1:
        st.image('logo.png', width=90)
    with mid:
        st.markdown("<h1 style='text-align: center; color: black;'>Interfaz para gestionar pacientes</h1>", unsafe_allow_html=True)
    # st.write('Desarrollado por ***Healthtracker***')
    users = st.radio(
     " ",
     ('Ingresar paciente', 'Eliminar paciente','Pacientes ingresados'))

    create_script = """ CREATE TABLE IF NOT EXISTS pct_table(
                            id_pct      varchar(30) PRIMARY KEY,
                            nombre    varchar(40) NOT NULL,
                            domicilio  varchar(100) NOT NULL,
                            fecha_nacimiento varchar(100),
                            fecha_derivacion varchar(100)
                                                  
                          )
            
    """ ## fecha_nacimiento, fecha_derivacion
    cur.execute(create_script)

    rut_query = 'SELECT id_pct FROM pct_table'
    
    cur.execute(rut_query)
    pcts = cur.fetchall()
    out_ruts = [item for t in pcts for item in t]
    # print(out_macs)
    
    if users == 'Ingresar paciente':
        st.subheader('Ingresar paciente')
        info_lab = st.empty()
        ingresado = st.empty()
        
        form_2 = st.empty()
        form2 = form_2.form(key='my_form_3')
        rut = form2.text_input('Ingrese rut o ID de nuevo paciente: ')
        nombre = form2.text_input('Ingrese nombre de nuevo paciente: ')
        dom = form2.text_input('Ingrese domicilio de nuevo paciente: ')
        d = form2.date_input(
         "Ingrese fecha de nacimiento de nuevo paciente: ",
         datetime.date(2000, 1, 1))
        # print(type(d.strftime('%Y-%m-%d')))
        d2 = form2.date_input(
         "Ingrese fecha de derivación de nuevo paciente: ",
         datetime.date(2020, 1, 1))
        submit_button_2 = form2.form_submit_button(label='Ingresar')
        
        
        try:
            
            if rut != '':
                rut = rut.replace('.','').replace('-','')
                insert_script = 'INSERT INTO pct_table (id_pct, nombre, domicilio, fecha_nacimiento, fecha_derivacion) VALUES (%s,%s,%s,%s,%s)'
                # id_s = '000' + str(st.session_state.count)
                
                insert_values = (rut,nombre,dom,d.strftime('%Y-%m-%d'),d2.strftime('%Y-%m-%d'))
                
                cur.execute(insert_script,insert_values)
                
                ingresado.success('Paciente ingresado correctamente')
                # st.session_state.count+=1
    
        except pg.errors.UniqueViolation:
            
            info_lab.info('Paciente ya ingresado')
        
        except pg.errors.InvalidTextRepresentation:
            
            info_lab.info('Favor ingresar datos válidos')
    
    
    # delete_checkbox = st.checkbox('Eliminar usuario',key=0) 
    
    elif users == 'Eliminar paciente':
        st.subheader('Eliminar paciente')
        
        info_lab2 = st.empty()
        eliminado = st.empty()
        
        form_3 = st.empty()
        form3 = form_3.form(key='my_form_2')
        rut2 = form3.selectbox(
            'Seleccionar paciente a eliminar:',
            out_ruts,key=1)
        submit_button_2 = form3.form_submit_button(label='Eliminar')
        
        try:
            
            if submit_button_2:
                
                deleteStatement   = "DELETE FROM pct_table WHERE id_pct = %s"
                delete_record = (str(rut2),)
                cur.execute(deleteStatement,delete_record)
                
                eliminado.success('Paciente eliminado')
                
        except:
            
            info_lab2.info('Favor ingresar datos válidos')
    
    elif users == 'Pacientes ingresados':
        psql_table = 'SELECT * FROM pct_table'

        cur.execute(psql_table)
        df_pcts = cur.fetchall()
        # num_fields = len(cur.description)
        field_names = [i[0] for i in cur.description]

        df_pcts = pd.DataFrame(df_pcts,columns=field_names)
        st.dataframe(df_pcts)
        
    
    con.commit()
    
    #close cursor
    # cur.close()
    
    # #close connection
    # con.close()



#%%

def assign_control():

    col1, mid, col2 = st.columns([1,5,1])
    with col1:
        st.image('logo.png', width=90)
    with mid:
        st.markdown("<h1 style='text-align: center; color: black;'>Interfaz para gestionar asignaciones</h1>", unsafe_allow_html=True)
    # st.write('Desarrollado por ***Healthtracker***')

    assigns = st.radio(
     " ",
     ('Asignar sábana a paciente', 'Desasignar sábana a paciente','Pacientes asignados'))

    create_script = """ CREATE TABLE IF NOT EXISTS assign_table(
                            id_pct      varchar(30),
                            id_sabana    varchar(40) NOT NULL,
                            fecha_inicio  varchar(40) NOT NULL,
                            fecha_termino  varchar(40),
                            mac     varchar(40) NOT NULL
                                                    
                          )
            
    """
    
    cur.execute(create_script)
    
    today = datetime.date.today().strftime('%Y-%m-%d')
    hora = time.localtime().tm_hour
    minu = time.localtime().tm_min
    sec = time.localtime().tm_sec
    hour = str(hora) + ':' + str(minu) + ':' + str(sec)
    date_today = today + ' ' + hour
    
####################################################################################    

    psql_table = 'SELECT * FROM pct_table'

    cur.execute(psql_table)
    df_pcts = cur.fetchall()
    # num_fields = len(cur.description)
    field_names = [i[0] for i in cur.description]

    df_pcts = pd.DataFrame(df_pcts,columns=field_names)
    
############################################################################
    
    psql_table2 = 'SELECT * FROM sabanas_table'

    cur.execute(psql_table2)
    df_pcts2 = cur.fetchall()
    # num_fields = len(cur.description)
    field_names = [i[0] for i in cur.description]

    df_pcts2 = pd.DataFrame(df_pcts2,columns=field_names)
    
####################################################################################

    psql_table3 = 'SELECT * FROM assign_table'

    cur.execute(psql_table3)
    df_pcts3 = cur.fetchall()
    field_names = [i[0] for i in cur.description]

    df_pcts3 = pd.DataFrame(df_pcts3,columns=field_names)

############################################################################################

    query = 'SELECT id_pct FROM pct_table'

    cur.execute(query)
    pcts = cur.fetchall()
    out_pct = [item for t in pcts for item in t]

###################################################################################################

    query2 = 'SELECT id_sabana FROM sabanas_table'

    cur.execute(query2)
    sb = cur.fetchall()
    out_sabana = [item for t in sb for item in t]
    # print(out)
    
###################################################################################################
    
    query = 'SELECT id_pct FROM assign_table'

    cur.execute(query)
    pcts = cur.fetchall()
    out_ids = [item for t in pcts for item in t]
    
        
    for ids_ in out_ids:
        try:
            index = df_pcts.loc[df_pcts['id_pct'] == ids_].index[0]
            list_as = list(df_pcts3['id_pct'].loc[df_pcts3['fecha_termino'] == '-'])
            if ids_ in list_as:
                df_pcts = df_pcts.drop(labels=index)
        except:
            # print('df_vacio')
            pass
    
####################################################################################################        

    query = 'SELECT id_sabana FROM assign_table'

    cur.execute(query)
    pcts = cur.fetchall()
    out_idsabana = [item for t in pcts for item in t]
    last_updated = []

    for pct in out_pct:
        postgreSQL_select_Query = "select id_pct,id_sabana,fecha_inicio,fecha_termino from assign_table where id_pct = %s order by fecha_inicio desc limit 1"
        query_value = (pct,)
        cur.execute(postgreSQL_select_Query,query_value)
        termino = cur.fetchall()
        last_updated.append(termino)

    out_pct_ = [item for t in last_updated for item in t]

    pcts_na = []
    sbs = []

    for i in range(len(out_pct_)):
        if out_pct_[i][3] == '-':
            pcts_na.append(out_pct_[i][0])
            sbs.append(out_pct_[i][1])
            
    for pct in pcts_na:
        out_pct.remove(pct)
    for sb in sbs:
        out_sabana.remove(sb)

        
    for ids_s in out_idsabana:
        try:
            index = df_pcts2.loc[df_pcts2['id_sabana'] == ids_s].index[0]
            list_as2 = list(df_pcts3['id_sabana'].loc[df_pcts3['fecha_termino'] == '-'])
            # print(list_as2)
            if ids_s in list_as2:
                df_pcts2 = df_pcts2.drop(labels=index)
        except:
            # print('df_vacio')
            pass
        # df_pcts2 = df_pcts2.drop(labels=index)
##################################################################################################
    
    if assigns == 'Asignar sábana a paciente':
        
        st.subheader('Asignar paciente')
        st.dataframe(df_pcts)
        st.subheader('Sábanas disponibles para asignar')
        st.dataframe(df_pcts2)
        info_lab3 = st.empty()
        asignado = st.empty()
        
        form_3 = st.empty()
        form3 = form_3.form(key='my_form_9')
        rut3 = form3.selectbox(
            'Seleccionar paciente (id_pct)',
            out_pct,key=1)
        sabana = form3.selectbox(
            'Seleccionar ID de sábana (id_sabana)',
            out_sabana,key=1)

        submit_button_2 = form3.form_submit_button(label='Asignar')

        try:
            
            if submit_button_2:
                
                
                # if rut3 in out_pct:
                df2 = df_pcts2['mac'].loc[df_pcts2['id_sabana'] == sabana]
                # print(df2)
                insert_script = 'INSERT INTO assign_table (id_pct, id_sabana, fecha_inicio, fecha_termino, mac) VALUES (%s,%s,%s,%s,%s)'
                insert_values = (rut3,sabana,date_today,'-',df2[df2.index[0]])
                cur.execute(insert_script,insert_values)
                asignado.success('Paciente asignado correctamente')
                # else:
                    
                    # asignado.error('Paciente no en listado')

        except pg.errors.UniqueViolation:
            
            info_lab3.info('Paciente en tabla')
        
        except pg.errors.InvalidTextRepresentation:
            
            info_lab3.info('Favor ingresar datos válidos')
        
    elif assigns == 'Desasignar sábana a paciente':
        
        query = 'SELECT id_pct FROM assign_table WHERE fecha_termino = %s'
        
        query_value = ('-')
        cur.execute(query,query_value)
        termino = cur.fetchall()
        out_fecha = [item for t in termino for item in t]
        
        st.subheader('Desasignar paciente')
        
        info_lab = st.empty()
        eliminado = st.empty()
        
        form_3 = st.empty()
        form3 = form_3.form(key='my_form_5')
        rut2 = form3.selectbox(
            'Seleccionar paciente a desasignar:',
            out_fecha,key=1)
        submit_button = form3.form_submit_button(label='Desasignar')
        
        query = 'SELECT fecha_inicio FROM assign_table WHERE id_pct = %s AND fecha_termino = %s ORDER BY fecha_inicio DESC LIMIT 1'
        value = (rut2,'-')
        cur.execute(query,value)
        pcts = cur.fetchall()
        out_inicio = [item for t in pcts for item in t]
        
        try:
            
            if submit_button:
                
                update_script =  """ UPDATE assign_table
                SET fecha_termino = %s
                WHERE fecha_inicio = %s"""
                # id_s = '000' + str(st.session_state.count)
                
                update_values = (date_today,out_inicio[0])
                # deleteStatement   = "DELETE FROM assign_table WHERE id_pct = %s"
                # delete_record = (str(rut2),)
                cur.execute(update_script,update_values)
                
                eliminado.success('Usuario desasignado')
                
        except:
            
            info_lab.info('Favor ingresar datos válidos')

    elif assigns == 'Pacientes asignados':
        
        
        psql_table = 'SELECT * FROM pct_table'
        
        cur.execute(psql_table)
        pcts = cur.fetchall()
        # num_fields = len(cur.description)
        field_names = [i[0] for i in cur.description]
        
        df_pcts = pd.DataFrame(pcts,columns=field_names)
        
        df_general = df_pcts3.loc[df_pcts3['fecha_termino'] == '-']
        
        df_general = pd.merge(df_general,df_pcts,how='left',on='id_pct')
        
        st.subheader('Pacientes asignados')
        st.dataframe(df_general)
        st.subheader('Historial de asignaciones')
        st.dataframe(df_pcts3)

    con.commit()
    
    #close cursor
    # cur.close()
    
    # #close connection
    # con.close()



#%%

## MAIN
async def main():
    # --- Initialising SessionState ---
    if "state1" not in st.session_state:
        st.session_state.state1 = 0
    if "state_but" not in st.session_state:
        st.session_state.state_but = 0

    if st.session_state.state1 == 0:

        col1, mid, col2 = st.columns([1,5,1])
        with col1:
            image = st.image('logo.png', width=90)
        with mid:
            title = st.markdown("<h1 style='text-align: center; color: black;'>Interfaz general</h1>", unsafe_allow_html=True)

        head = st.header("""
            **Seleccionar interfaz que se desee visualizar**:
        """)
        text_ = st.write('Desarrollado por ***Healthtracker***')

        form_ = st.empty()
        form_ = form_.form(key='my_form_4')
        menu = form_.selectbox(
            'Seleccionar paciente a eliminar:',
            ('Control de pacientes','Control de asignaciones','Parámetros pacientes (en desarrollo)',
            'Visualizar pacientes','Descargar archivo con información de sensores',
            'Sábanas activas'),key=13)
        
        submit_button = form_.form_submit_button(label='Ingresar a interfaz')
        if submit_button or st.session_state.state_but == 1:
            st.session_state.state_but = 1
            if menu == 'Control de pacientes':
                # st.session_state.state_but = 1
                user_control()
                
            if menu == 'Control de asignaciones':
                # st.session_state.state_but = 2
                assign_control()
                
            if menu == 'Parámetros pacientes (en desarrollo)':
                parameter_interface()
                
            if menu == 'Visualizar pacientes':
                task = asyncio.create_task(health_team_interface())
                await task
    
            if menu == 'Descargar archivo con información de sensores':
                download_csv_file_interface()
                
            if menu == 'Sábanas activas':
                active_users_int()
            
        # if menu == 'Cerrar sesión':
        #     st.session_state.state2 = 0
        #     login()
        #     count = st_autorefresh()
            
        
            
            
            

            
    

#%%

def login():

    # --- Initialising SessionState ---
    if "state2" not in st.session_state:
        st.session_state.state2 = 0
    
    if st.session_state.state2 == 1:
        asyncio.run(main())
    
    if st.session_state.state2 == 0:

        cols = st.empty()
        text = st.empty()
        
        connected = st.empty()
        n_connected = st.empty()
        in_ = st.empty()
        col1, mid, col2 = cols.columns([1,5,1])
        with mid:
            st.markdown("<h1 style='text-align: center; color: black;'>Bienvenido</h1>", unsafe_allow_html=True)

        text.write('Favor ingresar *usuario* y *contraseña* para ingresar al sistema de monitoreo en tiempo real desarrollado por ***Healthtracker***.')
        user = 'healthtracker'
        pass_ = 'ht2022'
        form_ = st.empty()
        form = form_.form(key='my_form')
        u_ = ''
        p_ = ''
        u = st.empty()
        p = st.empty()
        u_ = form.text_input('Usuario')
        p_ = form.text_input('Contraseña',type='password')
        submit_button = form.form_submit_button(label='Ingresar')
        # print(u_)
        if u_ == user and p_ == pass_:
            with st.spinner('Revisando credenciales...'):
                cols.empty()
                text.empty()
                form_.empty()
                st.session_state.state2 = 1
                
                n_connected.empty()
                in_.empty()
                connected.success('Usuario y contraseña correctos, conectando a interfaz general...')
                time.sleep(1)
                connected.empty()

                asyncio.run(main())
        elif (u_ != user and p_ != pass_) or (u_ == user and p_ != pass_) or (u_ != user and p_ == pass_):
            if u_ == '' and p_ == '':
                in_.info('Favor ingresar usuario y contraseña')
            else:
                n_connected.error('Usuario o contraseña incorrecto')
        
        if u_ != "" and p_ != "" and st.session_state.state2 == 1:
            u.empty()
            p.empty()
            form_.empty()

#%% LLAMAR A FUNCIÓN LOGIN

if __name__ == '__main__':
    login()
    # asyncio.run(main())