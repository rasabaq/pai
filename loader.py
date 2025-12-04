from area import Area
from celdas import est_celda
from errors import InputFormatError

def data_carga(path: str) -> tuple[int, tuple[int, int], tuple[int, int], Area]: #Funcion para cargar las primeras 3 lineas + toda el area a quemar
    with open(path, "r", encoding="utf-8") as f:
        lines = [ln.strip() for ln in f if ln.strip()]

    if not lines:
        raise InputFormatError("Falta la linea con el valor de n.")
    if len(lines) < 2:
        raise InputFormatError("Falta la linea con las coordenadas iniciales del fuego.")
    if len(lines) < 3:
        raise InputFormatError("Falta la linea con las coordenadas del bombero.")

    n = _parse_int(lines[0], "n")
    if n <= 0:
        raise InputFormatError("El valor de n debe ser mayor que cero.")

    if len(lines) < 3 + n:
        raise InputFormatError(
            f"El area esta incompleta: se esperaban {n} filas y solo hay {len(lines) - 3}."
        )

    fuego_coord = _parse_pair(lines[1], "fuego")
    bombero_coord = _parse_pair(lines[2], "bombero")

    area_lines = lines[3:3+n]
    grid = Area.parse_from_lines(area_lines, expected_size=n)

    _validate_inside(fuego_coord, n, "fuego")
    _validate_inside(bombero_coord, n, "bombero")

    x, y = fuego_coord
    a, b = bombero_coord

    grid.matrix[x][y] = est_celda.fuego
    grid.matrix[a][b] = est_celda.bomb

    return n, (x, y), (a, b), grid


def _parse_int(text: str, label: str) -> int:
    try:
        return int(text)
    except ValueError as exc:
        raise InputFormatError(f"El valor de {label} debe ser un entero: '{text}'.") from exc


def _parse_pair(text: str, label: str) -> tuple[int, int]:
    parts = text.split()
    if len(parts) != 2:
        raise InputFormatError(f"La linea de {label} debe contener exactamente dos enteros.")
    try:
        return int(parts[0]), int(parts[1])
    except ValueError as exc:
        raise InputFormatError(f"Las coordenadas de {label} deben ser enteros: '{text}'.") from exc


def _validate_inside(coord: tuple[int, int], n: int, label: str) -> None:
    i, j = coord
    if not (0 <= i < n and 0 <= j < n):
        raise InputFormatError(
            f"La posicion del {label} ({i},{j}) esta fuera del area de tamanio {n}."
        )
