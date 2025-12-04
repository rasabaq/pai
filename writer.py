from area import Area

def guardar_salida(path: str, area:Area) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for line in area.to_lines():
            f.write(line + "\n")

def guardar_report(path: str, area: Area, finished: bool, cerrado: bool):
    a_salvo, quemado, corta_fuego = area.counts()
    estado = "Finalizada" if finished else "Parcial"
    ctext = "Si" if cerrado else "No"

    with open(path, "w", encoding="utf-8") as f:
        f.write(f"Instante actual : {area.tick}\n")
        f.write(f"Estado : {estado}\n")
        f.write(f"Posiciones sin afectar : {a_salvo}\n")
        f.write(f"Posiciones quemadas : {quemado}\n")
        f.write(f"Posiciones con cortafuego : {corta_fuego}\n")
        f.write(f"¿El corta fuego esta cerrado?: {ctext}\n")
    