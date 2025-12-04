from area import Area
from celdas import est_celda

class fuego: #Clase que lleva todo el fuego maneja la expansion (cuadrada a tasa dada) con su limites en cortafuego
    def __init__(self, tasa_crecimiento: int = 1):
        self.tasa_crecimiento = tasa_crecimiento  

    def _neighbors8(self, i: int, j: int, n: int): #Movimiento o formas en que puede moverse el fuego
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                if di == 0 and dj == 0:
                    continue
                ni, nj = i + di, j + dj
                if 0 <= ni < n and 0 <= nj < n:
                    yield (ni, nj)

    def a_quemar(self, area: Area) -> set[tuple[int, int]]: #Escribe las siguientes zonas o ticks a quemar
        n = area.n
        frontier = set(area.positions(est_celda.fuego))
        if not frontier:
            return set()

        para_quemar: set[tuple[int, int]] = set()

        for _ in range(max(1, self.tasa_crecimiento)): #Que se quema y que no
            next_frontier: set[tuple[int, int]] = set()
            for (i, j) in frontier:
                for (ni, nj) in self._neighbors8(i, j, n):
                    cell = area.matrix[ni][nj]
                    if abs(ni - i) == 1 and abs(nj - j) == 1:
                        if (area.matrix[i][nj] == est_celda.c_fuego) or (area.matrix[ni][j] == est_celda.c_fuego): #no quemamos con cortafuegos
                            continue
                    if cell in (est_celda.c_fuego, est_celda.bomb): #No quemamos con bombero
                        continue
                    if cell == est_celda.sn_af: #ningun caso anterior se quema
                        if (ni, nj) not in para_quemar:
                            para_quemar.add((ni, nj))
                            next_frontier.add((ni, nj))
                    elif cell == est_celda.fuego: #se quema
                        next_frontier.add((ni, nj))
            frontier = next_frontier
            if not frontier:
                break

        return para_quemar

    def aplicar(self, area: Area, cells: set[tuple[int, int]]) -> None: #se aplica todo lo calculado antes
        for i, j in cells:
            if area.matrix[i][j] not in (est_celda.c_fuego, est_celda.bomb):
                area.matrix[i][j] = est_celda.fuego
