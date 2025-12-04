from area import Area
from celdas import est_celda
from strategy import strategy_bombero

class bombero: #Clase encargada de manejar los movimiento del bombero, manejando los cortafuegos y movimientos
    def __init__(self, i: int, j: int, estrategia: strategy_bombero):
        self.i = i
        self.j = j
        self.estrategia = estrategia

    def u_cortafuego(self, area: Area) -> None: #Modifica las areas que seran cortafuegos
        if area.matrix[self.i][self.j] in (est_celda.sn_af, est_celda.bomb): #Debe estar sin fuego y con el bombero en la posicion
            area.matrix[self.i][self.j] = est_celda.c_fuego #Cambia a cortafuego

    def move(self, area: Area, forbidden: set[tuple[int, int]]) -> None: #Maneja los movimiento en base a strategy.py
        ni,nj = self.estrategia.siguiente_paso(self.i, self.j, area, forbidden)
        if area.dentro(ni,nj) and (ni,nj) not in forbidden and area.matrix[ni][nj] == est_celda.sn_af:
            self.i, self.j = ni,nj

        area.matrix[self.i][self.j] = est_celda.bomb
            
