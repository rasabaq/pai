from __future__ import annotations

import heapq
import time
from dataclasses import dataclass, field

from strategy import strategy_bombero
from area import Area
from celdas import est_celda
from comp_fuego import fuego

# Movements in 8 directions plus stay still (used for branching).
NEIS8: list[tuple[int, int]] = [
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1),            (0, 1),
    (1, -1),  (1, 0),  (1, 1),
]
MOVES: list[tuple[int, int]] = [(0, 0)] + NEIS8


@dataclass(order=True)
class SearchNode:
    """State inside the Branch & Bound tree."""

    priority: float
    depth: int
    cost: float
    pos: tuple[int, int] = field(compare=False)
    area: Area = field(compare=False)
    forbidden: set[tuple[int, int]] = field(compare=False)
    path: list[tuple[int, int]] = field(compare=False, default_factory=list)
    counts: tuple[int, int, int] = field(compare=False, default=(0, 0, 0))


class BranchAndBound(strategy_bombero):
    """
    Estrategia de Branch & Bound con cola de prioridad y poda.
    Explora un arbol de movimientos para los siguientes ticks y
    elige el siguiente paso minimizando la cantidad de celdas quemadas.
    """

    def __init__(
        self,
        lookahead: int = 3,
        node_limit: int = 2_000,
        time_limit: float = 0.25,
    ):
        self.lookahead = lookahead
        self.node_limit = node_limit
        self.time_limit = time_limit
        self._fire = fuego(tasa_crecimiento=1)
        self.total_nodes = 0
        self.total_time = 0.0
        self._last_report: dict[str, object] = {}

    # -------- utilidades internas --------
    def _clone_area(self, area: Area) -> Area:
        return Area([row.copy() for row in area.matrix], tick=area.tick)

    def _cost(self, counts: tuple[int, int, int], depth: int) -> float:
        libres, quemadas, cortafuegos = counts
        return float(quemadas) - 0.05 * cortafuegos + 0.15 * depth

    def _bound(self, cost: float) -> float:
        # cost es ya una cota optimista: no anticipamos quemados extra.
        return cost

    def _valid_moves(self, node: SearchNode) -> list[tuple[int, int]]:
        ci, cj = node.pos
        moves: list[tuple[int, int]] = []
        for di, dj in MOVES:
            ni, nj = ci + di, cj + dj
            if not node.area.dentro(ni, nj):
                continue
            if (ni, nj) in node.forbidden:
                continue
            if node.area.matrix[ni][nj] != est_celda.sn_af:
                continue
            moves.append((ni, nj))
        return moves

    def _simulate_transition(
        self,
        node: SearchNode,
        move: tuple[int, int],
    ) -> SearchNode | None:
        ci, cj = node.pos
        ni, nj = move

        area_copy = self._clone_area(node.area)

        # Mantenemos el cortafuego en la celda anterior.
        if area_copy.matrix[ci][cj] == est_celda.bomb:
            area_copy.matrix[ci][cj] = est_celda.c_fuego

        # Fin del tick actual: el bombero se mueve.
        area_copy.matrix[ni][nj] = est_celda.bomb

        # Inicio del siguiente tick: coloca cortafuego y avanza fuego.
        area_copy.matrix[ni][nj] = est_celda.c_fuego
        area_copy.tick = node.area.tick + 1

        to_burn = self._fire.a_quemar(area_copy)
        self._fire.aplicar(area_copy, to_burn)

        forbidden_next = self._fire.a_quemar(area_copy)
        counts = area_copy.counts()
        cost = self._cost(counts, node.depth + 1)
        bound = self._bound(cost)
        path = node.path + [(ni, nj)]

        return SearchNode(
            priority=bound,
            depth=node.depth + 1,
            cost=cost,
            pos=(ni, nj),
            area=area_copy,
            forbidden=forbidden_next,
            path=path,
            counts=counts,
        )

    # -------- API principal --------
    def siguiente_paso(
        self,
        i: int,
        j: int,
        area: Area,
        forbidden: set[tuple[int, int]],
    ) -> tuple[int, int]:
        start = time.perf_counter()

        root_area = self._clone_area(area)
        if root_area.matrix[i][j] == est_celda.bomb:
            root_area.matrix[i][j] = est_celda.c_fuego
        root_counts = root_area.counts()
        root_cost = self._cost(root_counts, depth=0)

        root = SearchNode(
            priority=self._bound(root_cost),
            depth=0,
            cost=root_cost,
            pos=(i, j),
            area=root_area,
            forbidden=set(forbidden),
            path=[],
            counts=root_counts,
        )

        queue: list[SearchNode] = [root]
        best_node: SearchNode | None = None
        best_cost = float("inf")
        nodes_expanded = 0
        status = "no_move"

        while queue:
            now = time.perf_counter()
            if (now - start) >= self.time_limit:
                status = "time_limit"
                break
            if nodes_expanded >= self.node_limit:
                status = "node_limit"
                break

            node = heapq.heappop(queue)
            if node.priority >= best_cost:
                # poda por cota
                continue

            moves = self._valid_moves(node)

            if node.depth >= self.lookahead or not moves:
                # evitamos elegir la raiz si aun hay movimientos posibles
                if not (node.depth == 0 and moves):
                    if node.cost < best_cost:
                        best_cost = node.cost
                        best_node = node
                        status = "ok"
                continue

            for mv in moves:
                child = self._simulate_transition(node, mv)
                if child is None:
                    continue
                nodes_expanded += 1
                if child.priority >= best_cost:
                    continue
                heapq.heappush(queue, child)

        elapsed = time.perf_counter() - start
        self.total_nodes += nodes_expanded
        self.total_time += elapsed

        if best_node is None:
            best_node = root
            best_cost = root_cost

        self._last_report = {
            "nodes": nodes_expanded,
            "status": status,
            "elapsed_sec": elapsed,
            "instants": best_node.depth,
            "counts": {
                "sin_afectar": best_node.counts[0],
                "quemadas": best_node.counts[1],
                "cortafuegos": best_node.counts[2],
            },
            "cerrado": best_node.area.limite(),
        }

        if best_node.path:
            return best_node.path[0]

        # Fallback: elegir algun movimiento valido para no quedarse quieto.
        fallback_moves = self._valid_moves(root)
        if fallback_moves:
            return fallback_moves[0]

        return i, j

    # -------- reportes --------
    def ultima_busqueda(self) -> dict[str, object]:
        return dict(self._last_report)

    def resumen_global(
        self,
        area: Area | None = None,
        wall_time: float | None = None,
    ) -> dict[str, object]:
        libres = quemadas = cortafuegos = None
        cerrado = None
        instantes = None
        if area is not None:
            libres, quemadas, cortafuegos = area.counts()
            cerrado = area.limite()
            instantes = area.tick
        return {
            "nodes": self.total_nodes,
            "estrategia": self._last_report.get("status", "sin_busqueda"),
            "tiempo_busqueda_sec": self.total_time,
            "tiempo_total_sec": wall_time,
            "instantes": instantes,
            "sin_afectar": libres,
            "quemadas": quemadas,
            "cortafuegos": cortafuegos,
            "cerrado": cerrado,
        }


# Alias para mantener compatibilidad con el nombre previo.
paredes = BranchAndBound
