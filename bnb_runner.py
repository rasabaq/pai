import time

from comp_bombero import bombero as Bombero
from comp_fuego import fuego
from heuristica import BranchAndBound
from loader import data_carga
from simulation import Simulation


INPUT_PATH = "input.dat"


def main() -> None:
    start = time.perf_counter()

    _, _, (bi, bj), area = data_carga(INPUT_PATH)
    fire = fuego(tasa_crecimiento=1)
    estrategia = BranchAndBound()
    bomber = Bombero(bi, bj, estrategia=estrategia)
    sim = Simulation(area, fire, bomber)

    max_steps = 10_000
    steps = 0

    while steps < max_steps:
        if sim._no_more_expansion_after_bomber():
            break
        sim.step()
        steps += 1

    wall_time = time.perf_counter() - start
    report = estrategia.resumen_global(area=area, wall_time=wall_time)

    print("[Branch & Bound] Reporte")
    print(f"Nodos explorados: {report['nodes']}")
    print(f"Estado de la estrategia: {report['estrategia']}")
    print(f"Tiempo de busqueda (s): {report['tiempo_busqueda_sec']:.4f}")
    print(f"Tiempo total (s): {report['tiempo_total_sec']:.4f}")
    print(f"Instantes simulados: {report['instantes']}")
    print(f"Posiciones sin afectar: {report['sin_afectar']}")
    print(f"Posiciones quemadas: {report['quemadas']}")
    print(f"Posiciones con cortafuego: {report['cortafuegos']}")
    print(f"Cerrado: {'Si' if report['cerrado'] else 'No'}")


if __name__ == "__main__":
    main()
