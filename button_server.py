# -*- coding: utf-8 -*-
"""
Created on Wed Jul  6 16:20:40 2022

@author: groja
"""

import socket
import psycopg2 as pg

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
s.bind(('0.0.0.0',9002))
s.listen(0)

Fs = 50

def database_sending(id_,data):
    #connect to db
    con = pg.connect(
        host = '152.74.29.160',
        user = 'postgres',
        password = 'somno2019',
        port = '9001',
        database = 'somno')

    #cursor
    cur = con.cursor()
    
    create_script = """ CREATE TABLE IF NOT EXISTS button_data(
                            id_button     varchar(10) PRIMARY KEY,
                            info    varchar(15)
                                                                                                                       
                          )
            
    """

    cur.execute(create_script)
    con.commit()
    
    
    
    insert_script = 'INSERT INTO button_data (id_button,info) VALUES (%s,%s)'
    insert_values = (id_,data)
    cur.execute(insert_script,insert_values)
    



while True:
    client, addr = s.accept()
    
    while True:
        
        content = client.recv(164*Fs)
        
        if len(content) == 0:
            break
        else:
            print(str(content).replace('b',''))
            database_sending('1', str(content).replace('b',''))
    print('closing connection')
    client.close()






