from __future__ import annotations

import random
import time

from strategy import strategy_bombero
from area import Area
from celdas import est_celda
from comp_fuego import fuego

# Movimientos en 8 direcciones.
NEIS8: list[tuple[int, int]] = [
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1),            (0, 1),
    (1, -1),  (1, 0),  (1, 1),
]
# Permitimos quedarse quieto (primer elemento) o moverse en las 8 direcciones.
MOVES: list[tuple[int, int]] = [(0, 0)] + NEIS8


class IteratedLocalSearch(strategy_bombero):
    """
    Estrategia basada en Iterated Local Search (ILS).
    - Planifica una secuencia de movimientos corta (horizon) evaluando
      cuantas celdas terminan quemadas tras dejar quieto al bombero.
    - Genera un plan inicial simple, luego aplica perturbaciones y
      mejoras locales (hill-climbing de primer mejor) para refinarlo.
    - El mejor plan encontrado define el siguiente movimiento.
    """

    def __init__(
        self,
        horizon: int = 6,
        max_evaluations: int = 120,
        local_search_steps: int = 15,
        perturbation_strength: int = 2,
        time_limit: float = 1.0,
        greedy_bias: float = 0.45,
        seed: int | None = None,
    ):
        self.horizon = horizon
        self.max_evaluations = max_evaluations
        self.local_search_steps = local_search_steps
        self.perturbation_strength = perturbation_strength
        self.time_limit = time_limit
        self.greedy_bias = greedy_bias
        self._rng = random.Random(seed)

        self._fire = fuego(tasa_crecimiento=1)
        self.total_plans = 0
        self.total_time = 0.0
        self._last_report: dict[str, object] = {}

    def _clone_area(self, area: Area) -> Area:
        return Area([row.copy() for row in area.matrix], tick=area.tick)

    def _rollout_stay_until_stable(self, area: Area) -> Area:
        """
        Deja al bombero quieto hasta que no haya mas expansion posible.
        Sirve para estimar el costo final de una trayectoria parcial.
        """
        area_copy = self._clone_area(area)
        while True:
            to_burn = self._fire.a_quemar(area_copy)
            if not to_burn:
                break
            self._fire.aplicar(area_copy, to_burn)
            area_copy.tick += 1
        return area_copy

    def _valid_moves(self, area: Area, pos: tuple[int, int]) -> list[tuple[int, int]]:
        """
        Devuelve movimientos relativos validos desde pos. Siempre incluye (0,0)
        para permitir quedarse quieto aunque la celda actual no sea sn_af.
        """
        ci, cj = pos
        moves: list[tuple[int, int]] = [(0, 0)]
        for di, dj in NEIS8:
            ni, nj = ci + di, cj + dj
            if not area.dentro(ni, nj):
                continue
            if area.matrix[ni][nj] != est_celda.sn_af:
                continue
            moves.append((di, dj))
        return moves

    def _apply_move(
        self,
        area: Area,
        pos: tuple[int, int],
        move: tuple[int, int],
        clone: bool = True,
    ) -> tuple[Area, tuple[int, int], tuple[int, int, int]]:
        """
        Simula un paso con el movimiento indicado. Si clone=True no modifica
        el area recibida.
        """
        working = self._clone_area(area) if clone else area
        ci, cj = pos
        di, dj = move
        ni, nj = ci + di, cj + dj

        # Cortafuego en la posicion actual.
        if working.matrix[ci][cj] in (est_celda.sn_af, est_celda.bomb):
            working.matrix[ci][cj] = est_celda.c_fuego

        # Si el movimiento no es valido, el bombero permanece.
        if (not working.dentro(ni, nj)) or (working.matrix[ni][nj] != est_celda.sn_af):
            ni, nj = ci, cj

        # Marcamos la nueva celda como cortafuego (proteccion inmediata).
        working.matrix[ni][nj] = est_celda.c_fuego
        working.tick = area.tick + 1

        to_burn = self._fire.a_quemar(working)
        self._fire.aplicar(working, to_burn)

        return working, (ni, nj), working.counts()

    def _move_score(self, area: Area, pos: tuple[int, int], move: tuple[int, int]) -> float:
        """
        Heuristica rapida para seleccionar movimientos en el plan inicial:
        prioriza menos quemadas y menor expansion esperada.
        """
        sim_area, _, counts = self._apply_move(area, pos, move, clone=True)
        quemadas = counts[1]
        proxima_expansion = len(self._fire.a_quemar(sim_area))
        return float(quemadas) + 0.3 * proxima_expansion

    def _initial_plan(self, area: Area, pos: tuple[int, int]) -> list[tuple[int, int]]:
        """
        Construye un plan base sencillo combinando decisiones greedy y aleatorias.
        """
        plan: list[tuple[int, int]] = []
        work_area = self._clone_area(area)
        cur_pos = pos
        for _ in range(self.horizon):
            moves = self._valid_moves(work_area, cur_pos)
            if not moves:
                plan.append((0, 0))
                continue

            if self._rng.random() < self.greedy_bias:
                scored = [(self._move_score(work_area, cur_pos, mv), mv) for mv in moves]
                scored.sort(key=lambda x: x[0])
                chosen = scored[0][1]
            else:
                chosen = self._rng.choice(moves)

            plan.append(chosen)
            work_area, cur_pos, _ = self._apply_move(work_area, cur_pos, chosen, clone=False)
            if not self._fire.a_quemar(work_area):
                # Ya no hay expansion: completamos con quedarse quieto.
                while len(plan) < self.horizon:
                    plan.append((0, 0))
                break

        while len(plan) < self.horizon:
            plan.append((0, 0))
        return plan

    def _evaluate_plan(
        self,
        area: Area,
        pos: tuple[int, int],
        plan: list[tuple[int, int]],
    ) -> tuple[float, float, Area, tuple[int, int]]:
        """
        Ejecuta el plan y devuelve (costo, score, area_final, pos_final).
        Costo = celdas quemadas tras un rollout pasivo.
        """
        area_copy = self._clone_area(area)
        ci, cj = pos
        if area_copy.matrix[ci][cj] == est_celda.bomb:
            area_copy.matrix[ci][cj] = est_celda.c_fuego

        cur_pos = (ci, cj)
        steps_taken = 0

        for mv in plan:
            moves = self._valid_moves(area_copy, cur_pos)
            if not moves:
                break
            chosen = mv if mv in moves else moves[0]
            area_copy, cur_pos, _ = self._apply_move(area_copy, cur_pos, chosen, clone=False)
            steps_taken += 1
            if not self._fire.a_quemar(area_copy):
                break

        rollout_area = self._rollout_stay_until_stable(area_copy)
        libres, quemadas, cortafuegos = rollout_area.counts()
        costo = float(quemadas)
        score = costo - 0.05 * cortafuegos + 0.02 * steps_taken
        return costo, score, rollout_area, cur_pos

    def _perturb_plan(self, plan: list[tuple[int, int]]) -> list[tuple[int, int]]:
        mutated = list(plan)
        for _ in range(self.perturbation_strength):
            idx = self._rng.randrange(len(mutated))
            mutated[idx] = self._rng.choice(MOVES)
        return mutated

    def _local_improve(
        self,
        area: Area,
        pos: tuple[int, int],
        plan: list[tuple[int, int]],
        start: float,
        evaluations_done: int,
    ) -> tuple[list[tuple[int, int]], float, float, Area, int]:
        """
        Mejora local del plan (primer mejor). Retorna el plan refinado y
        evaluaciones adicionales consumidas.
        """
        current_cost, current_score, current_area, _ = self._evaluate_plan(area, pos, plan)
        evals_used = 1
        steps = 0
        improved = True
        while improved and steps < self.local_search_steps:
            if evaluations_done + evals_used >= self.max_evaluations:
                break
            if (time.perf_counter() - start) >= self.time_limit:
                break
            improved = False
            idx = self._rng.randrange(len(plan))
            base_move = plan[idx]
            for mv in MOVES:
                if mv == base_move:
                    continue
                candidate = list(plan)
                candidate[idx] = mv
                cost, score, cand_area, _ = self._evaluate_plan(area, pos, candidate)
                evals_used += 1
                if cost < current_cost or (cost == current_cost and score < current_score):
                    plan = candidate
                    current_cost = cost
                    current_score = score
                    current_area = cand_area
                    improved = True
                    break
            steps += 1
        return plan, current_cost, current_score, current_area, evals_used

    def siguiente_paso(
        self,
        i: int,
        j: int,
        area: Area,
        forbidden: set[tuple[int, int]],
    ) -> tuple[int, int]:
        start = time.perf_counter()
        status = "ok"

        best_plan = self._initial_plan(area, (i, j))
        best_cost, best_score, best_area, _ = self._evaluate_plan(area, (i, j), best_plan)
        evaluations = 1

        while evaluations < self.max_evaluations:
            if (time.perf_counter() - start) >= self.time_limit:
                status = "time_limit"
                break

            perturbed = self._perturb_plan(best_plan)
            perturbed, cost, score, cand_area, used = self._local_improve(
                area,
                (i, j),
                perturbed,
                start,
                evaluations,
            )
            evaluations += used

            if cost < best_cost or (cost == best_cost and score < best_score):
                best_plan = perturbed
                best_cost = cost
                best_score = score
                best_area = cand_area
            elif self._rng.random() < 0.1:
                # Aceptacion ocasional para diversificar.
                best_plan = perturbed
                best_cost = cost
                best_score = score
                best_area = cand_area

        elapsed = time.perf_counter() - start
        self.total_plans += evaluations
        self.total_time += elapsed

        cerrada = best_area.limite()
        self._last_report = {
            "nodes": evaluations,
            "status": status,
            "elapsed_sec": elapsed,
            "instants": best_area.tick,
            "counts": {
                "sin_afectar": best_area.counts()[0],
                "quemadas": best_area.counts()[1],
                "cortafuegos": best_area.counts()[2],
            },
            "cerrado": cerrada,
        }

        # Devolvemos solo el primer movimiento del mejor plan.
        mv = best_plan[0] if best_plan else (0, 0)
        ni, nj = i + mv[0], j + mv[1]
        if not area.dentro(ni, nj) or area.matrix[ni][nj] != est_celda.sn_af:
            # Fallback a cualquier movimiento valido.
            valid = self._valid_moves(area, (i, j))
            if valid:
                mv = valid[0]
                ni, nj = i + mv[0], j + mv[1]
            else:
                return i, j
        return ni, nj

    def ultima_busqueda(self) -> dict[str, object]:
        return dict(self._last_report)

    def resumen_global(
        self,
        area: Area | None = None,
        wall_time: float | None = None,
    ) -> dict[str, object]:
        libres = quemadas = cortafuegos = None
        instantes = None
        cerrado = None
        if area is not None:
            libres, quemadas, cortafuegos = area.counts()
            instantes = area.tick
            cerrado = area.limite()

        return {
            "nodes": self.total_plans,
            "estrategia": self._last_report.get("status", "sin_busqueda"),
            "tiempo_busqueda_sec": self.total_time,
            "tiempo_total_sec": wall_time,
            "instantes": instantes,
            "sin_afectar": libres,
            "quemadas": quemadas,
            "cortafuegos": cortafuegos,
            "cerrado": cerrado,
        }
