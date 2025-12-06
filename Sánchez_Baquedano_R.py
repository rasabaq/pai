import time

from celdas import est_celda
from area import Area
from comp_fuego import fuego
from comp_bombero import bombero
from branch_and_bound import BranchAndBound
from loader import data_carga
from writer import guardar_salida, guardar_salida_txt
from simulation import Simulation

DEFAULT_INPUT_PATH = "input.dat"
INPUT_CHOICES = {
    "1": "input1.dat",
    "2": "input2.dat",
    "3": "input3.dat",
    "4": "input4.dat",
    "5": "input5.dat",
    "6": "input6.dat",
    "7": "input7.dat",
    "8": "input8.dat",
    "9": "input9.dat",
    "10": "input10.dat",
}
OUTPUT_PATH = "output.dat"
SALIDA_PATH = "salida.txt"


def main():
    area1 = None
    Fuego = fuego(tasa_crecimiento=1)  # puede ajustar la tasa aqui
    Bombero = None
    last_stats = None
    last_finished = None
    last_cerrado = None

    while True:
        print("\n=== MENU ===")
        print("1) Lectura: cargar input (1-10=inputX.dat, enter=input.dat)")
        print("2) Salida: ejecutar (final)")
        print("3) Salida: ejecutar hasta instante k")
        print("4) Guardar: output.dat y salida.txt")
        print("5) Salir")

        op = input("Opcion: ").strip()

        if op == "1":
            selected = input("Seleccione input [1-10] o Enter para input.dat: ").strip()
            input_path = INPUT_CHOICES.get(selected, DEFAULT_INPUT_PATH if selected == "" else None)

            if input_path is None:
                print("Opcion de input invalida.")
                continue

            try:
                n, (x, y), (a, b), area1 = data_carga(input_path)
                Bombero = bombero(a, b, estrategia=BranchAndBound())
                last_stats = None
                last_finished = None
                last_cerrado = None
                print(
                    f"[OK] Cargado {input_path} (n={n}, fuego=({x},{y}), bombero=({a},{b}))"
                )
            except Exception as e:
                print(f"[ERROR] Lectura: {e}")

        elif op == "2":
            if area1 is None or Bombero is None:
                print("Primero cargue el input (opcion 1).")
                continue
            start = time.perf_counter()
            sim = Simulation(area1, Fuego, Bombero)
            steps = sim.run_until_stable()
            wall_time = time.perf_counter() - start
            last_finished = (len(Fuego.a_quemar(area1)) == 0)
            last_cerrado = area1.limite()
            last_stats = Bombero.estrategia.resumen_global(area=area1, wall_time=wall_time)
            print(f"[OK] Simulacion finalizada en t={area1.tick} (pasos={steps}).")
            print(
                f"    Nodos explorados: {last_stats['nodes']}, "
                f"estado estrategia: {last_stats['estrategia']}, "
                f"tiempo (s): {last_stats['tiempo_total_sec']:.4f}"
            )
            try:
                guardar_salida_txt(SALIDA_PATH, last_stats, cerrado=last_cerrado)
                print(f"    Resumen guardado en {SALIDA_PATH}")
            except Exception as e:
                print(f"[ERROR] Guardar salida.txt: {e}")

        elif op == "3":
            if area1 is None or Bombero is None:
                print("Primero cargue el input (opcion 1).")
                continue
            try:
                k = int(input("Ingrese instante k: "))
            except ValueError:
                print("Instante invalido.")
                continue
            start = time.perf_counter()
            sim = Simulation(area1, Fuego, Bombero)
            steps = sim.run_until_tick(k)
            wall_time = time.perf_counter() - start
            last_finished = (len(Fuego.a_quemar(area1)) == 0)
            last_cerrado = area1.limite()
            last_stats = Bombero.estrategia.resumen_global(area=area1, wall_time=wall_time)
            print(f"[OK] Simulacion ejecutada hasta t={area1.tick} (pasos={steps}).")
            print(
                f"    Nodos explorados: {last_stats['nodes']}, "
                f"estado estrategia: {last_stats['estrategia']}, "
                f"tiempo (s): {last_stats['tiempo_total_sec']:.4f}"
            )
            try:
                guardar_salida_txt(SALIDA_PATH, last_stats, cerrado=last_cerrado)
                print(f"    Resumen guardado en {SALIDA_PATH}")
            except Exception as e:
                print(f"[ERROR] Guardar salida.txt: {e}")

        elif op == "4":
            if area1 is None:
                print("Nada que guardar (cargue y ejecute primero).")
                continue
            finished = (len(Fuego.a_quemar(area1)) == 0) if last_finished is None else last_finished
            cerrado = area1.limite() if last_cerrado is None else last_cerrado
            stats_to_save = last_stats or Bombero.estrategia.resumen_global(area=area1, wall_time=None)
            try:
                guardar_salida(OUTPUT_PATH, area1)
                guardar_salida_txt(SALIDA_PATH, stats_to_save, cerrado=cerrado)
                print(f"[OK] Guardados: {OUTPUT_PATH}, {SALIDA_PATH}")
            except Exception as e:
                print(f"[ERROR] Guardado: {e}")

        elif op == "5":
            print("Adios!")
            break

        else:
            print("Opcion invalida.")


if __name__ == "__main__":
    main()
