from enum import Enum

class est_celda(str, Enum): #Clase sencilla que maneja los estados de cada caracter del area 
    sn_af = "*"  # Sin afectar
    fuego = "-"  # Quemandose
    c_fuego = "+"  # Corta fuego
    bomb = "x"  # Bombero
