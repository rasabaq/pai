from celdas import est_celda
from area import Area
from comp_fuego import fuego
from comp_bombero import bombero
from heuristica import paredes
from loader import data_carga
from writer import guardar_report, guardar_salida
from simulation import Simulation

INPUT_PATH = "input.dat"
OUTPUT_PATH = "output.dat"
REPORT_PATH = "reporte.dat"

def main():
    area1 = None
    Fuego = fuego(tasa_crecimiento=1)  # puede ajustar la tasa aquí
    Bombero = None

    while True:
        print("\n=== MENU ===")
        print("1) Lectura: cargar input.dat")
        print("2) Salida: ejecutar (final)")
        print("3) Salida: ejecutar hasta instante k")
        print("4) Guardar: output.dat y reporte.dat")
        print("5) Salir")

        op = input("Opción: ").strip()

        if op == "1":
            try:
                n, (x, y), (a, b), area1 = data_carga(INPUT_PATH)
                Bombero = bombero(a, b, estrategia=paredes())
                print(f"[OK] Cargado input.dat (n={n}, fuego=({x},{y}), bombero=({a},{b}))")
            except Exception as e:
                print(f"[ERROR] Lectura: {e}")

        elif op == "2":
            if area1 is None or Bombero is None:
                print("Primero cargue el input (opción 1).")
                continue 
            sim = Simulation(area1, Fuego, Bombero)
            steps = sim.run_until_stable()
            print(f"[OK] Simulación finalizada en t={area1.tick} (pasos={steps}).")
            
        elif op == "3":
            if area1 is None or Bombero is None:
                print("Primero cargue el input (opción 1).")
                continue
            try:
                k = int(input("Ingrese instante k: "))
            except ValueError:
                print("Instante inválido.")
                continue
            sim = Simulation(area1, Fuego, Bombero)
            steps = sim.run_until_tick(k)
            print(f"[OK] Simulación ejecutada hasta t={area1.tick} (pasos={steps}).")

        elif op == "4":
            if area1 is None:
                print("Nada que guardar (cargue y ejecute primero).")
                continue
            # 'finished': no hay próxima expansión posible
            finished = (len(Fuego.a_quemar(area1)) == 0)
            # 'cerrado': el fuego ya no puede alcanzar ninguna SAFE
            cerrado = area1.limite()
            try:
                guardar_salida(OUTPUT_PATH, area1)
                guardar_report(REPORT_PATH, area1, finished=finished, cerrado=cerrado)
                print(f"[OK] Guardados: {OUTPUT_PATH}, {REPORT_PATH}")
            except Exception as e:
                print(f"[ERROR] Guardado: {e}")

        elif op == "5":
            print("Adiós!")
            break

        else:
            print("Opción inválida.")

if __name__ == "__main__":
    main()

