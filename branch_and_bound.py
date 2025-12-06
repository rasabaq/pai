from __future__ import annotations

import heapq
import time
from dataclasses import dataclass, field

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


@dataclass(order=True)
class SearchNode:
    """State inside the Branch & Bound tree.

    priority is the bound used in the priority queue (lower is better).
    bnb_cost is the monotone cost (number of burned cells) used for pruning.
    score is a heuristic value used only to compare leaves with the same cost.
    """

    priority: float
    depth: int
    bnb_cost: float
    score: float = field(compare=False)
    pos: tuple[int, int] = field(compare=False)
    area: Area = field(compare=False)
    forbidden: set[tuple[int, int]] = field(compare=False)
    path: list[tuple[int, int]] = field(compare=False, default_factory=list)
    counts: tuple[int, int, int] = field(compare=False, default=(0, 0, 0))


class BranchAndBound(strategy_bombero):
    """
    Estrategia de Branch & Bound con cola de prioridad y poda:
    - Cada nodo representa un estado simulado (posición, grilla, cortafuegos).
    - La cola está ordenada por una cota optimista (menos quemadas primero).
    - Se expande primero lo prometedor y se poda cuando la cota >= mejor solución.
    - En hojas o al agotar lookahead se usa un rollout pesimista (dejar quieto)
      para comparar soluciones por quemadas totales estimadas.
    """

    def __init__(
        self,
        lookahead: int = 5,
        node_limit: int = 2_000,
        time_limit: float = 5,
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
        # Copia ligera de la grilla para explorar una rama.
        return Area([row.copy() for row in area.matrix], tick=area.tick)

    def _bnb_cost(self, counts: tuple[int, int, int], depth: int) -> float:
        """Monotone cost used by Branch & Bound (minimised).

        We only count burned cells here, because that value can only increase
        as the simulation advances. This makes the pruning condition safe.
        """
        libres, quemadas, cortafuegos = counts
        return float(quemadas)

    def _score(self, counts: tuple[int, int, int], depth: int) -> float:
        """Heuristic score used to compare leaves with the same burned cells.

        Here we slightly reward having more firebreak cells and penalise
        going deeper, but this value is *not* used for pruning.
        """
        libres, quemadas, cortafuegos = counts
        return float(quemadas) - 0.05 * cortafuegos + 0.05 * depth

    def _bound(self, bnb_cost: float) -> float:
        # Cota optimista: reutiliza el costo monotono de quemadas.
        return bnb_cost

    def _rollout_stay_until_stable(self, area: Area) -> Area:
        """Simula expansion del fuego si el bombero se queda quieto.

        Es una estimacion pesimista del costo final desde un nodo hoja,
        que ayuda a comparar mejor las hojas que terminan antes del
        horizonte de lookahead.
        """
        area_copy = self._clone_area(area)
        while True:
            to_burn = self._fire.a_quemar(area_copy)
            if not to_burn:
                break
            self._fire.aplicar(area_copy, to_burn)
            area_copy.tick += 1
        return area_copy

    def _valid_moves(self, node: SearchNode) -> list[tuple[int, int]]:
        # Genera los movimientos legales desde un nodo de búsqueda.
        ci, cj = node.pos
        moves: list[tuple[int, int]] = []
        for di, dj in MOVES:
            ni, nj = ci + di, cj + dj
            if not node.area.dentro(ni, nj):
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
        # Aplica el movimiento, hace avanzar fuego y arma el siguiente nodo.
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
        depth = node.depth + 1
        bnb_cost = self._bnb_cost(counts, depth)
        bound = self._bound(bnb_cost)
        score = self._score(counts, depth)
        path = node.path + [(ni, nj)]

        return SearchNode(
            priority=bound,
            depth=depth,
            bnb_cost=bnb_cost,
            score=score,
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
        # Punto de entrada: calcula el mejor siguiente paso del bombero.
        start = time.perf_counter()

        root_area = self._clone_area(area)
        if root_area.matrix[i][j] == est_celda.bomb:
            root_area.matrix[i][j] = est_celda.c_fuego
        root_counts = root_area.counts()
        root_bnb_cost = self._bnb_cost(root_counts, depth=0)
        root_score = self._score(root_counts, depth=0)

        root = SearchNode(
            priority=self._bound(root_bnb_cost),
            depth=0,
            bnb_cost=root_bnb_cost,
            score=root_score,
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
            # bucle principal de B&B: saca el mejor nodo, poda y expande hijos
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
                # rollout: estimamos costo final si el bombero se queda quieto
                rollout_area = self._rollout_stay_until_stable(node.area)
                rollout_counts = rollout_area.counts()
                rollout_cost = self._bnb_cost(rollout_counts, node.depth)
                rollout_score = self._score(rollout_counts, node.depth)

                # evitamos elegir la raiz si aun hay movimientos posibles
                if not (node.depth == 0 and moves):
                    if (rollout_cost < best_cost or
                        (rollout_cost == best_cost and
                         best_node is not None and
                         rollout_score < best_node.score)):
                        best_cost = rollout_cost
                        best_node = SearchNode(
                            priority=rollout_cost,
                            depth=node.depth,
                            bnb_cost=rollout_cost,
                            score=rollout_score,
                            pos=node.pos,
                            area=rollout_area,
                            forbidden=node.forbidden,
                            path=node.path,
                            counts=rollout_counts,
                        )
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
            best_cost = root_bnb_cost

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
        # Estadísticas de la última búsqueda B&B ejecutada.
        return dict(self._last_report)

    def resumen_global(
        self,
        area: Area | None = None,
        wall_time: float | None = None,
    ) -> dict[str, object]:
        # Resumen acumulado para reportes o guardado.
        libres = quemadas = cortafuegos = None
        if area is not None:
            libres, quemadas, cortafuegos = area.counts()

        instantes = None
        cerrado = None
        if area is not None:
            instantes = area.tick
            cerrado = area.limite()

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


