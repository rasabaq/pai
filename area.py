from celdas import est_celda
from errors import InputFormatError

class Area: #Clase que maneja toda el area o grid de * + - sirve para tener todas las caracteristicas de cada uno de los caracteres
    def __init__(self, matrix: list[list[est_celda]], tick: int = 0):
        self.matrix = matrix  # matrix
        self.tick = tick

    @property
    def n(self) -> int: #verificamos tamaño
        return len(self.matrix)
    
    def dentro(self, i:int, j:int) -> bool: #verifica que un punto este dentro del area
        return 0<= i < self.n and 0 <= j < self.n
    
    def positions(self, state: est_celda) -> set[tuple[int, int]]: #funcion para manejar el estado de cada celda
        coords: set[tuple[int, int]] = set()                       #esta conectada con la funcion de las celdas en celdas.py
        for i, row in enumerate(self.matrix):                     #recorre todo los puntos de la matriz y revisa su estado
            for j, v in enumerate(row):
                if v == state:
                    coords.add((i,j))
        return coords
    
    
    def counts(self) -> tuple[int, int, int]:   #funcion que maneja contadores de cuandos espacios hay en cada estado
        libre = quemado = corta_fuego = 0
        for row in self.matrix:
            for v in row:
                if v == est_celda.sn_af:
                    libre+= 1
                elif v == est_celda.fuego:
                    quemado+= 1
                elif v == est_celda.c_fuego:
                    corta_fuego+=1
        return libre, quemado, corta_fuego
    
    def limite(self) -> bool:
        fire_positions = self.positions(est_celda.fuego)
        if not fire_positions:
            return True  # sin fuegos, no se expandirá
        n = self.n
        queue = list(fire_positions)
        seen = set(fire_positions)
        reach_safe = False
        while queue:
            i, j = queue.pop(0)
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    if di == 0 and dj == 0:
                        continue
                    ni, nj = i + di, j + dj
                    if 0 <= ni < n and 0 <= nj < n:
                        if (ni, nj) in seen:
                            continue
                        # si encuentro SAFE, significa que podría expandirse
                        if self.matrix[ni][nj] == est_celda.sn_af:
                            reach_safe = True
                        # puedo seguir expandiendo la búsqueda por cualquier cosa que NO sea cortafuego
                        if self.matrix[ni][nj] != est_celda.c_fuego:
                            seen.add((ni, nj))
                            queue.append((ni, nj))
        return not reach_safe


    def to_lines(self) -> list[str]: #Funcion que ayuda a imprimir la matrix en el output
        return [" ".join(cell.value for cell in row) for row in self.matrix]
    
    @staticmethod
    def parse_from_lines(lines: list[str], expected_size: int | None = None) -> "Area":
        if expected_size is not None and expected_size <= 0:
            raise InputFormatError("El tamaño del area debe ser mayor que cero.")
        matrix: list[list[est_celda]] = []
        for row_idx, line in enumerate(lines):
            tokens = [t for t in line.strip().split() if t]
            if expected_size is not None and len(tokens) != expected_size:
                raise InputFormatError(
                    f"La fila {row_idx + 1} del area tiene {len(tokens)} columnas y se esperaban {expected_size}."
                )
            row: list[est_celda] = []
            for col_idx, token in enumerate(tokens):
                try:
                    row.append(est_celda(token))
                except ValueError as exc:
                    raise InputFormatError(
                        f"Caracter anormal '{token}' en la fila {row_idx + 1}, columna {col_idx + 1}."
                    ) from exc
            matrix.append(row)
        if expected_size is not None and len(matrix) != expected_size:
            raise InputFormatError(
                f"El archivo contiene {len(matrix)} filas de area y se esperaban {expected_size}."
            )
        n = len(matrix)
        if n == 0:
            raise InputFormatError("El area no puede estar vacia.")
        if not all(len(row) == n for row in matrix):
            raise InputFormatError("El area no es cuadrada.")
        return Area(matrix)
    
