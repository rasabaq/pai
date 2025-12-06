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
        """
        Consideramos cerrado si el cortafuego toca al menos dos paredes
        distintas (superior, inferior, izquierda, derecha). Contamos tanto
        celdas de cortafuego como la celda actual del bombero.
        """
        n = self.n
        walls: set[str] = set()
        for i, row in enumerate(self.matrix):
            for j, v in enumerate(row):
                if v not in (est_celda.c_fuego, est_celda.bomb):
                    continue
                if i == 0:
                    walls.add("top")
                if i == n - 1:
                    walls.add("bottom")
                if j == 0:
                    walls.add("left")
                if j == n - 1:
                    walls.add("right")
                if len(walls) >= 2:
                    return True
        return False


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
    
