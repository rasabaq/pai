import time

from comp_fuego import fuego
from comp_bombero import bombero
from iterated_local_search import IteratedLocalSearch
from variable_neighborhood_search import VariableNeighborhoodSearch
from loader import data_carga
from writer import guardar_salida_txt
from simulation import Simulation

INPUT_CHOICES = {str(i): f"input{i}.dat" for i in range(1, 21)}
SEEDS = list(range(10))  # 10 ejecuciones con 10 semillas distintas
SALIDAS = {"ils": "salidaA1.txt", "vns": "salidaA2.txt"}


def _seleccionar_inputs() -> list[str] | None:
    seleccion = input("Seleccione input [1-20] o 'todos': ").strip().lower()
    if seleccion in ("todos", "todo", "all", "*"):
        return [INPUT_CHOICES[k] for k in sorted(INPUT_CHOICES.keys(), key=int)]
    if seleccion.startswith("input"):
        seleccion = seleccion[5:]
    if seleccion in INPUT_CHOICES:
        return [INPUT_CHOICES[seleccion]]
    print("Opcion de input invalida. Ingrese un numero entre 1 y 20 o 'todos'.")
    return None


def _crear_estrategia(factory, seed: int):
    try:
        return factory(seed=seed)
    except TypeError:
        return factory()


def _correr_ejecucion(
    estrategia_factory,
    input_path: str,
    seed: int,
) -> tuple[int, float] | None:
    try:
        _, fuego_pos, bombero_pos, area = data_carga(input_path)
    except Exception as e:
        print(f"[ERROR] No se pudo cargar {input_path}: {e}")
        return None

    comp_bombero = bombero(bombero_pos[0], bombero_pos[1], estrategia=_crear_estrategia(estrategia_factory, seed))
    comp_fuego = fuego(tasa_crecimiento=1)
    sim = Simulation(area, comp_fuego, comp_bombero)

    start = time.perf_counter()
    sim.run_until_stable()
    elapsed = time.perf_counter() - start

    stats = comp_bombero.estrategia.resumen_global(area=area, wall_time=elapsed)
    costo = stats.get("quemadas")
    if costo is None:
        costo = area.counts()[1]

    return costo, elapsed


def _procesar_input(
    nombre_estrategia: str,
    estrategia_factory,
    input_path: str,
) -> list[str] | None:
    resultados: list[tuple[int, float]] = []
    for seed in SEEDS:
        ejec = _correr_ejecucion(estrategia_factory, input_path, seed)
        if ejec is None:
            return None
        resultados.append(ejec)

    costos = [c for c, _ in resultados]
    tiempos = [t for _, t in resultados]
    mejor_costo = min(costos)
    costo_prom = sum(costos) / len(costos)
    tiempo_prom = sum(tiempos) / len(tiempos)

    lineas: list[str] = []
    lineas.append(f"# {nombre_estrategia.upper()} - {input_path}")
    lineas.append("instancia,mejor_costo,error_relativa,costo_promedio,tiempo_promedio")
    for idx, (costo, _) in enumerate(resultados, start=1):
        error_rel = 0.0 if mejor_costo == 0 else (costo - mejor_costo) / mejor_costo
        lineas.append(f"{idx},{mejor_costo},{error_rel:.6f},{costo_prom:.6f},{tiempo_prom:.6f}")
    lineas.append("")

    print(
        f"[OK] {nombre_estrategia.upper()} - {input_path}: mejor_costo={mejor_costo}, "
        f"costo_prom={costo_prom:.4f}, tiempo_prom={tiempo_prom:.4f}s"
    )
    return lineas


def _ejecutar_metaheuristica(nombre: str, estrategia_factory) -> None:
    inputs = _seleccionar_inputs()
    if not inputs:
        return

    salida_path = SALIDAS[nombre]
    contenido: list[str] = []

    for input_path in inputs:
        seccion = _procesar_input(nombre, estrategia_factory, input_path)
        if seccion is None:
            continue
        contenido.extend(seccion)

    if not contenido:
        print("[ERROR] No se genero informacion para guardar.")
        return

    try:
        with open(salida_path, "w", encoding="utf-8") as f:
            f.write("\n".join(contenido))
        print(f"[OK] Reporte guardado en {salida_path}")
    except Exception as e:
        print(f"[ERROR] No se pudo guardar {salida_path}: {e}")


def main():
    while True:
        print("\n=== MENU METAHEURISTICAS ===")
        print("1) Ejecutar metaheuristica ILS")
        print("2) Ejecutar metaheuristica VNS")
        print("3) Salir")

        op = input("Opcion: ").strip().lower()

        if op == "1" or op in ("i", "ils"):
            _ejecutar_metaheuristica("ils", IteratedLocalSearch)
        elif op == "2" or op in ("v", "vns"):
            _ejecutar_metaheuristica("vns", VariableNeighborhoodSearch)
        elif op == "3" or op in ("s", "salir", "q", "quit"):
            print("Adios!")
            break
        else:
            print("Opcion invalida.")


if __name__ == "__main__":
    main()
