from area import Area


def guardar_salida(path: str, area: Area) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for line in area.to_lines():
            f.write(line + "\n")


def guardar_report(
    path: str,
    area: Area,
    finished: bool,
    cerrado: bool,
    stats: dict | None = None,
) -> None:
    a_salvo, quemado, corta_fuego = area.counts()
    estado = "Finalizada" if finished else "Parcial"
    ctext = "Si" if cerrado else "No"

    nodes = "-"
    status = "-"
    t_busqueda = "-"
    t_total = "-"
    instantes = area.tick
    if stats:
        nodes = stats.get("nodes", nodes)
        status = stats.get("estrategia", status)
        t_busqueda = stats.get("tiempo_busqueda_sec", t_busqueda)
        t_total = stats.get("tiempo_total_sec", t_total)
        instantes = stats.get("instantes", instantes)

    with open(path, "w", encoding="utf-8") as f:
        f.write(f"Instante actual : {instantes}\n")
        f.write(f"Estado : {estado}\n")
        f.write(f"Nodos explorados : {nodes}\n")
        f.write(f"Estrategia estado : {status}\n")
        f.write(f"Tiempo busqueda (s) : {t_busqueda}\n")
        f.write(f"Tiempo total (s) : {t_total}\n")
        f.write(f"Posiciones sin afectar : {a_salvo}\n")
        f.write(f"Posiciones quemadas : {quemado}\n")
        f.write(f"Posiciones con cortafuego : {corta_fuego}\n")
        f.write(f"El cortafuego esta cerrado? : {ctext}\n")


def guardar_salida_txt(
    path: str,
    stats: dict,
    cerrado: bool,
) -> None:
    """
    Genera un resumen breve con los datos clave de la estrategia.
    """
    nodes = stats.get("nodes", "-")
    estado_raw = stats.get("estrategia", "-")
    if estado_raw == "ok":
        estado = "Optima"
    elif estado_raw == "-":
        estado = "-"
    else:
        estado = f"Factible ({estado_raw})"

    tiempo = stats.get("tiempo_total_sec", "-")
    instantes = stats.get("instantes", "-")
    libres = stats.get("sin_afectar", "-")
    quemadas = stats.get("quemadas", "-")
    cortafuego = stats.get("cortafuegos", "-")
    cerrado_txt = "Si" if cerrado else "No"

    with open(path, "w", encoding="utf-8") as f:
        f.write(f"Nodos : {nodes}\n")
        f.write(f"Estado estrategia : {estado}\n")
        f.write(f"Tiempo (seg) : {tiempo}\n")
        f.write(f"Numero de instantes : {instantes}\n")
        f.write(f"Posiciones sin afectar : {libres}\n")
        f.write(f"Posiciones quemadas : {quemadas}\n")
        f.write(f"Posiciones con cortafuego : {cortafuego}\n")
        f.write(f"Cortafuego cerrado : {cerrado_txt}\n")
