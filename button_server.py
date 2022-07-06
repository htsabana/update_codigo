# -*- coding: utf-8 -*-
"""
Created on Wed Jul  6 16:20:40 2022

@author: groja
"""

import socket

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
s.bind(('0.0.0.0',9002))
s.listen(0)

Fs = 50

while True:
    client, addr = s.accept()
    
    while True:
        
        content = client.recv(164*Fs)
        
        if len(content) == 0:
            break
        else:
            print(content)
    print('closing connection')
    client.close()






