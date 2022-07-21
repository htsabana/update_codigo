# -*- coding: utf-8 -*-
"""
Created on Tue Jul 19 17:40:13 2022

@author: groja
"""

import numpy as np
from scipy import signal
from scipy import stats
import matplotlib.pyplot as plt
import pandas as pd
import psycopg2 as pg
import streamlit as st
import pandas.io.sql as psql
from operator import add
import time

###########################################
###         Variables Globales          ###
###########################################
insig = 200 # Valor bajo el cual se consideran insignificantes

# Filter requirements.
T = 5.0         # Sample Period
fs = 50.0       # sample rate, Hz
cutoff = 0.8      # desired cutoff frequency of the filter, Hz ,      slightly higher than actual 1.2 Hz
nyq = 0.5 * fs  # Nyquist Frequency
order = 2       # sin wave can be approx represented as quadratic
n = int(T * fs) # total number of samples

clsr=['#d9ed92','#b5e48c','#99d98c','#76c893','#52b69a','#34a0a4',
      '#168aad','#1a759f','#1e6091','#184e77','#ffcdb2','#ffb4a2',
      '#e5989b','#b5838d','#757bc8','#8187dc','#8e94f2','#9fa0ff',
      '#bbadff','#cbb2fe','#ddbdfc','#06d6a0','#118ab2']#,'#cdb4db']
# La idea es estandarizar los colores para cada sensor pero aÃºn no estÃ¡ implementado

#connect to db
con = pg.connect(
    host = '152.74.29.160',
    user = 'postgres',
    password = 'somno2019',
    port = '9001',
    database = 'somno')

#cursor
cur = con.cursor()

info = st.empty()

def butter_lowpass_filter(data, cutoff, fs, order):
    normal_cutoff = cutoff / nyq
    # Get the filter coefficients
    b, a = signal.butter(order, normal_cutoff, btype='low', analog=False)
    y = signal.filtfilt(b, a, data)
    return y

while True:
    
    df_assigns = psql.read_sql('SELECT * FROM assign_table', con)

    df_mac = list(df_assigns['mac'].loc[df_assigns['fecha_termino'] == '-'])
    df_users = list(df_assigns['id_pct'].loc[df_assigns['fecha_termino'] == '-'])
    
    for mac,id_ in zip(df_mac,df_users):
        
        select_script = 'SELECT * FROM mac_' + str(mac) + ' ORDER BY time DESC LIMIT 3000'
        
        cur.execute(select_script)
        file = cur.fetchall()
        file = pd.DataFrame(file)
        len_a = file.shape[0]
        x_axis =  [i for i in range(len_a)] # Crea el vector de tiempo
        x_axis = np.multiply(x_axis,0.03333) # pasa a segundos
        file.columns = file.columns.astype(str)
        
        file.drop(['0'],axis = 1, inplace = True) # Elimina la columna de informaciÃ³n
        # file.drop(['Unnamed: 0'],axis = 1, inplace = True) # Elimina la columna de informaciÃ³n
        file.insert(loc = 0, column = 'Minutos', value= x_axis) # inserta la columna de tiempo
        file['Minutos'] = file['Minutos']/60
        
        
    
        
        fil_data_all = pd.DataFrame(file['Minutos']) # Nuevo DataFrame que contendrÃ¡ las seÃ±ales filtradas
        # Mediante un loop agregamos las columnas filtradas correspondientes a cada sensor
        for column in file:
            col_dat = file[str(column)]
            if column != 'Minutos':
                filtered_all = butter_lowpass_filter(col_dat, cutoff, fs, order)
                fil_data_all[column] = filtered_all
                
        
        for a in range(1,24):
            col = str(a)
            # Se reemplazan aquellos valores por NaN para que no distorsionen la grÃ¡fica
            fil_data_all[col].mask(fil_data_all[col] < insig, 0, inplace=True)
            # fil_data_all[col].mask(fil_data_all[col] > 3100, 3100, inplace=True)
            ### Elimino columnas que no poseen informaciÃ³n Ãºtil, es decir que todos sus componentes son cero
            total_col = fil_data_all[col].sum()
            if total_col == 0 :
                fil_data_all.drop([col],axis =1, inplace = True) # Elimino las columnas sin informaciÃ³n
                
                
        mpv = len(fil_data_all) # Cantidad de Muestras Por Ventana, idealmente 1000
        
        
        n_row, n_col = fil_data_all.shape #Dimensiones del dataframe resultante luego de eliminar columnas con ceros
        
        for col in fil_data_all:    # Recorro el DataFrame
            if str(col) != 'Minutos' :
                # Min y Max para calcular el promedio
                min_val = fil_data_all[str(col)].min(skipna=True)
                max_val = fil_data_all[str(col)].max(skipna=True)
                #NormalizaciÃ³n de la seÃ±al
                fil_data_all[str(col)] = fil_data_all[str(col)] - min_val
                fil_data_all[str(col)] = fil_data_all[str(col)]/(max_val - min_val)
        
        Prom = [0] * mpv
        
        for column in fil_data_all:
            col = str(column)
            if col != 'Minutos':
                datos = fil_data_all[col].tolist() # Transformo la columna de DataFrame a lista para encontrar los peaks
                antidatos = [x*-1 / (n_col -1) for x in datos]
                antipeak = signal.find_peaks(antidatos,distance = 50,prominence=0.01)[0] # Encuentra los peaks inversos
                len_in = antipeak.shape[0]
                #len_in = indices.shape[0]   # Calculo cuantos peaks hay
        
        
                if len_in > 0 :         # Si hay peaks
                    #del datos[0:indices[0]] # Recorto la seÃ±al para que inicie justo en el primer peak
                    del datos[0:antipeak[0]]
                    del datos[mpv-100:]         # Recorto para que tengan el mismo largo todas las listas
                    # Se quitan 100 muestras pensando que se recortan algunas del inicio para acomodar los peaks, asi no hay problemas
        
        
                    #Promedio
                    Prom = list(map(add, Prom, datos))  # Sumo las listas para calcular el promedio
        
        
        
        
        Prom = [x / (n_col -1) for x in Prom]
        antiprom = [x*-1 / (n_col -1) for x in Prom] # SeÃ±al invertida para encontrar los valores mas bajos (peaks inversos)
    
        ###################################
        ### Calculo numÃ©rico de la frec ###
        ###################################
        
        antipeak_prom = signal.find_peaks(antiprom,distance = 50)[0] # Encuentra los peaks inversos
        len_anti = len(antipeak_prom) # Cuenta la cantidad de peaks inversos
        
        if len_anti > 0: # Si hay al menos 2, entonces se considera que la ventana contiene info Ãºtil
            #Prom_fin = Prom[antipeak_prom[0]:antipeak_prom[len_anti-1]]
            # Corta la seÃ±al promedio para que queden ciclos de respiraciÃ³n completos y por lo tanto el cÃ¡lculo sea correcto
            peak_prom = signal.find_peaks(Prom,distance = 50,prominence=0.01)[0]
            # Encuentra los peaks y los cuenta
            num_peaks = peak_prom.shape[0] #Numero de peaks
            num_samp = len(Prom)    # Muestras
            frec_resp = num_peaks/(num_samp*0.03333/60) # Calculo en respiraciones/seg
            # select_script_users = 'SELECT * FROM'
            print(str(frec_resp) + ' ' + str(mac) + ' ' +  str(id_))
            # info.info('Frecuencia respiratoria  = ' + str(round(frec_resp,2)) + ' resp/min')
            insert_script = 'INSERT INTO frec_resp (id_pct,frec) VALUES (%s,%s)'
            values = (str(id_),round(frec_resp,2))
            cur.execute(insert_script,values)
            con.commit()
            
            # time.sleep(0.2)
    time.sleep(60)
    #     if frec_resp > 6: # Si hay mas de 3, se considera ventana con respiraciÃ³n
    #         num_peaks = peak_prom.shape[0] #Numero de peaks
    #         num_samp = len(Prom)    # Muestras
    #         frec_resp = num_peaks/(num_samp*0.03333/60) # Calculo en respiraciones/seg
    
    #         ## Plot SeÃ±al promedio
    #         plt.figure(10)
    #         plt.plot(Prom)
    #         plt.title('Señal promedio, Frec Resp = ' + str(frec_resp)+' resp/min')
    #         plt.figure(10)
    #         plt.scatter(x =peak_prom,y = [Prom[j] for j in peak_prom], marker ='P')
    #         plt.xlabel('Muestras')
    #         plt.show()
    #     else: # Si tiene menos de 3 peaks, se considera posible apnea
    #         #print('Ventana sin InformaciÃ³n suficiente, posible apnea')
    #         ## Plot SeÃ±al promedio
    #         plt.figure(10)
    #         plt.plot(Prom)
    #         plt.title('Posible apnea, Frec Resp = ' + str(frec_resp)+' resp/min')
    #         plt.figure(10)
    #         plt.scatter(x =peak_prom,y = [Prom[j] for j in peak_prom], marker ='P')
    #         plt.xlabel('Muestras')
    #         plt.show()
    # else: # si no tiene peaks inversos se considera sin info
    #     #print('Ventana sin InformaciÃ³n suficiente')
    #     ## Plot SeÃ±al promedio
    #     plt.figure(10)
    #     plt.plot(Prom)
    #     plt.title('Ventana sin información relevante')
    #     plt.figure(10)
    #     plt.xlabel('Muestras')
    #     plt.show()


#%%


cur.close()

con.close()







