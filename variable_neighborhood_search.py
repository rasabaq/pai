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
# Permite quedarse quieto (primer elemento) o moverse en las 8 direcciones.
MOVES: list[tuple[int, int]] = [(0, 0)] + NEIS8


class VariableNeighborhoodSearch(strategy_bombero):
    """
    Estrategia basada en Variable Neighborhood Search (VNS).
    - Construye un plan corto de movimientos (horizon) y lo evalua con rollout.
    - Aplica etapas de shaking con distintos tamanos de vecindad (k) y luego
      mejora local por primer mejor.
    - Reinicia k cuando hay mejora; recorre vecindades mas amplias si no la hay.
    """

    def __init__(
        self,
        horizon: int = 6,
        k_max: int = 3,
        max_iterations: int = 60,
        max_evaluations: int = 180,
        local_search_steps: int = 6,
        time_limit: float = 1.0,
        seed: int | None = None,
    ):
        self.horizon = horizon
        self.k_max = k_max
        self.max_iterations = max_iterations
        self.max_evaluations = max_evaluations
        self.local_search_steps = local_search_steps
        self.time_limit = time_limit
        self._rng = random.Random(seed)

        self._fire = fuego(tasa_crecimiento=1)
        self.total_evaluations = 0
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
        para permitir quedarse quieto.
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

        if working.matrix[ci][cj] in (est_celda.sn_af, est_celda.bomb):
            working.matrix[ci][cj] = est_celda.c_fuego

        if (not working.dentro(ni, nj)) or (working.matrix[ni][nj] != est_celda.sn_af):
            ni, nj = ci, cj

        working.matrix[ni][nj] = est_celda.c_fuego
        working.tick = area.tick + 1

        to_burn = self._fire.a_quemar(working)
        self._fire.aplicar(working, to_burn)

        return working, (ni, nj), working.counts()

    def _move_score(self, area: Area, pos: tuple[int, int], move: tuple[int, int]) -> float:
        """
        Heuristica rapida para seleccionar movimientos en el plan inicial.
        """
        sim_area, _, counts = self._apply_move(area, pos, move, clone=True)
        quemadas = counts[1]
        next_burn = len(self._fire.a_quemar(sim_area))
        return float(quemadas) + 0.35 * next_burn

    def _initial_plan(self, area: Area, pos: tuple[int, int]) -> list[tuple[int, int]]:
        """
        Construye un plan base combinando decisiones greedy y un poco de ruido.
        """
        plan: list[tuple[int, int]] = []
        work_area = self._clone_area(area)
        cur_pos = pos
        for _ in range(self.horizon):
            moves = self._valid_moves(work_area, cur_pos)
            if not moves:
                plan.append((0, 0))
                continue

            scored = [(self._move_score(work_area, cur_pos, mv), mv) for mv in moves]
            scored.sort(key=lambda x: x[0])
            top = scored[: min(3, len(scored))]
            choice = self._rng.choice(top) if len(top) > 1 else top[0]
            chosen = choice[1]

            plan.append(chosen)
            work_area, cur_pos, _ = self._apply_move(work_area, cur_pos, chosen, clone=False)
            if not self._fire.a_quemar(work_area):
                break

        while len(plan) < self.horizon:
            plan.append((0, 0))
        return plan

    def _score(self, counts: tuple[int, int, int], steps_taken: int) -> float:
        libres, quemadas, cortafuegos = counts
        return float(quemadas) - 0.05 * cortafuegos + 0.02 * steps_taken

    def _evaluate_plan(
        self,
        area: Area,
        pos: tuple[int, int],
        plan: list[tuple[int, int]],
    ) -> tuple[float, float, Area, tuple[int, int], int]:
        """
        Ejecuta el plan y devuelve (costo, score, area_final, pos_final, pasos).
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
            area_copy, cur_pos, counts = self._apply_move(area_copy, cur_pos, chosen, clone=False)
            steps_taken += 1
            if not self._fire.a_quemar(area_copy):
                break

        rollout_area = self._rollout_stay_until_stable(area_copy)
        counts = rollout_area.counts()
        costo = float(counts[1])
        score = self._score(counts, steps_taken)
        return costo, score, rollout_area, cur_pos, steps_taken

    def _shake_plan(self, plan: list[tuple[int, int]], k: int) -> list[tuple[int, int]]:
        shaken = list(plan)
        if not shaken:
            return shaken
        changes = min(k, len(shaken))
        indices = self._rng.sample(range(len(shaken)), changes)
        for idx in indices:
            shaken[idx] = self._rng.choice(MOVES)
        return shaken

    def _local_search(
        self,
        area: Area,
        pos: tuple[int, int],
        plan: list[tuple[int, int]],
        start: float,
        evaluations_done: int,
    ) -> tuple[list[tuple[int, int]], float, float, Area, int]:
        """
        Mejora local por primer mejor sobre el plan dado.
        """
        best_cost, best_score, best_area, _, _ = self._evaluate_plan(area, pos, plan)
        evals_used = 1
        steps = 0
        improved = True
        while improved and steps < self.local_search_steps:
            if evaluations_done + evals_used >= self.max_evaluations:
                break
            if (time.perf_counter() - start) >= self.time_limit:
                break
            improved = False
            indices = list(range(len(plan)))
            self._rng.shuffle(indices)
            for idx in indices:
                base_move = plan[idx]
                for mv in MOVES:
                    if mv == base_move:
                        continue
                    candidate = list(plan)
                    candidate[idx] = mv
                    cost, score, cand_area, _, _ = self._evaluate_plan(area, pos, candidate)
                    evals_used += 1
                    if cost < best_cost or (cost == best_cost and score < best_score):
                        plan = candidate
                        best_cost = cost
                        best_score = score
                        best_area = cand_area
                        improved = True
                        break
                if improved or evaluations_done + evals_used >= self.max_evaluations:
                    break
                if (time.perf_counter() - start) >= self.time_limit:
                    break
            steps += 1
        return plan, best_cost, best_score, best_area, evals_used

    def siguiente_paso(
        self,
        i: int,
        j: int,
        area: Area,
        forbidden: set[tuple[int, int]],
    ) -> tuple[int, int]:
        start = time.perf_counter()
        status = "ok"

        base_plan = self._initial_plan(area, (i, j))
        base_plan, best_cost, best_score, best_area, evaluations = self._local_search(
            area,
            (i, j),
            base_plan,
            start,
            evaluations_done=0,
        )

        k = 1
        iterations = 0
        while iterations < self.max_iterations:
            if (time.perf_counter() - start) >= self.time_limit:
                status = "time_limit"
                break
            if evaluations >= self.max_evaluations:
                status = "eval_limit"
                break

            shaken = self._shake_plan(base_plan, k)
            shaken, cost, score, cand_area, used = self._local_search(
                area,
                (i, j),
                shaken,
                start,
                evaluations,
            )
            evaluations += used
            iterations += 1

            if cost < best_cost or (cost == best_cost and score < best_score):
                base_plan = shaken
                best_cost = cost
                best_score = score
                best_area = cand_area
                k = 1
            else:
                k += 1
                if k > self.k_max:
                    k = 1

        elapsed = time.perf_counter() - start
        self.total_evaluations += evaluations
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

        mv = base_plan[0] if base_plan else (0, 0)
        ni, nj = i + mv[0], j + mv[1]
        if not area.dentro(ni, nj) or area.matrix[ni][nj] != est_celda.sn_af:
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
            "nodes": self.total_evaluations,
            "estrategia": self._last_report.get("status", "sin_busqueda"),
            "tiempo_busqueda_sec": self.total_time,
            "tiempo_total_sec": wall_time,
            "instantes": instantes,
            "sin_afectar": libres,
            "quemadas": quemadas,
            "cortafuegos": cortafuegos,
            "cerrado": cerrado,
        }
