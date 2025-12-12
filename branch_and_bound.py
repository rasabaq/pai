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
class SearchNode:        #Clase para buscar en los arboles, la idea central es que el uso de clases permite comparar atributos entre ramas
    priority: float    #Prioridad para la cola
    depth: int         #Profundidad de la busqueda
    bnb_cost: float    #costo (celdas quemadas)
    score: float = field(compare=False)  #puntaje para resolver empates
    pos: tuple[int, int] = field(compare=False)  #posicion bombero
    area: Area = field(compare=False) 
    forbidden: set[tuple[int, int]] = field(compare=False) #celdas a quemar
    path: list[tuple[int, int]] = field(compare=False, default_factory=list) #registro de ramas recorrida
    counts: tuple[int, int, int] = field(compare=False, default=(0, 0, 0)) 


class BranchAndBound(strategy_bombero):
    """
    Estrategia de Branch & Bound con cola  y poda:
    - Cada nodo representa un estado simulado (posición, area, cortafuegos)
    - La cola está ordenada por una cota optimista (menos quemadas primero)
    - Se expande primero lo prometedor y se poda cuando la cota >= mejor sol
    - En hojas o al agotar lookahead se usa un rollout pesimista (dejar quieto)
      para comparar soluciones por quemadas totales estimadas.
    """

    def __init__(
        self,
        lookahead: int = 5,
        node_limit: int = 2_000,
        time_limit: float = 5,
        trace_enabled: bool = False,
        trace_limit: int | None = None,
    ):
        self.lookahead = lookahead #lookhead son los avances hacia el futuro que hace
        self.node_limit = node_limit
        self.time_limit = time_limit
        self._fire = fuego(tasa_crecimiento=1)
        self.total_nodes = 0
        self.total_time = 0.0
        self._last_report: dict[str, object] = {}
        self.trace_enabled = trace_enabled
        self.trace_limit = trace_limit
        self._last_trace: list[dict[str, object]] = []
        self._trace_truncated = False
        self._trace_history: list[tuple[list[dict[str, object]], bool]] = []


    def _clone_area(self, area: Area) -> Area: #copia de area solamente
        return Area([row.copy() for row in area.matrix], tick=area.tick)

    def _trace_event(self, kind: str, node: SearchNode, **extra: object) -> None:
        # Guarda una linea de traza si la opcion esta activada.
        if not self.trace_enabled:
            return
        if self.trace_limit is not None and len(self._last_trace) >= self.trace_limit:
            self._trace_truncated = True
            return
        entry: dict[str, object] = {
            "type": kind,
            "depth": node.depth,
            "pos": node.pos,
            "bound": node.priority,
            "bnb_cost": node.bnb_cost,
            "score": node.score,
            "path": list(node.path),
        }
        if extra:
            entry.update(extra)
        self._last_trace.append(entry)

    def _bnb_cost(self, counts: tuple[int, int, int], depth: int) -> float: #costo = celdas quemadas
        libres, quemadas, cortafuegos = counts
        return float(quemadas)

    def _score(self, counts: tuple[int, int, int], depth: int) -> float: #empates se deseempatan con cortafuegos y la profundidad
        libres, quemadas, cortafuegos = counts
        return float(quemadas) - 0.05 * cortafuegos + 0.05 * depth

    def _bound(self, bnb_cost: float) -> float: 
        return bnb_cost

    def _rollout_stay_until_stable(self, area: Area) -> Area: #analiza el costo de no hacer nada
        area_copy = self._clone_area(area)
        while True:
            to_burn = self._fire.a_quemar(area_copy)
            if not to_burn:
                break
            self._fire.aplicar(area_copy, to_burn)
            area_copy.tick += 1
        return area_copy

    def _valid_moves(self, node: SearchNode) -> list[tuple[int, int]]: #maneja los movimientos validos
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
        # Aplica el movimiento
        ci, cj = node.pos
        ni, nj = move

        area_copy = self._clone_area(node.area)

        #Mantenemos el cortafuego en la celda anterior
        if area_copy.matrix[ci][cj] == est_celda.bomb:
            area_copy.matrix[ci][cj] = est_celda.c_fuego

        #Fin del tick actual: el bombero se mueve.
        area_copy.matrix[ni][nj] = est_celda.bomb

        #Inicio del siguiente tick coloca cortafuego y avanza fuego
        area_copy.matrix[ni][nj] = est_celda.c_fuego
        area_copy.tick = node.area.tick + 1

        to_burn = self._fire.a_quemar(area_copy)
        self._fire.aplicar(area_copy, to_burn)

        forbidden_next = self._fire.a_quemar(area_copy) #celdas a quemar
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


    def siguiente_paso( #funcion que maneja el movimiento, primero establece el punto de raiz
        self,
        i: int,
        j: int,
        area: Area,
        forbidden: set[tuple[int, int]],
    ) -> tuple[int, int]:
        start = time.perf_counter()
        self._last_trace = []
        self._trace_truncated = False

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
        self._trace_event("root", root)

        while queue:
            # bucle principal de B&B saca el mejor nodo, poda y expande 
            now = time.perf_counter()
            if (now - start) >= self.time_limit:
                status = "time_limit"
                break
            if nodes_expanded >= self.node_limit:
                status = "node_limit"
                break

            node = heapq.heappop(queue)
            self._trace_event("expand", node, queue_size=len(queue) + 1, best_cost=best_cost)
            if node.priority >= best_cost:
                # poda por cota
                self._trace_event("prune", node, reason="bound", best_cost=best_cost)
                continue

            moves = self._valid_moves(node)

            if node.depth >= self.lookahead or not moves:
                # rollout estimamos costo final si el bombero se queda quieto, esto para cuando no se pudiera mover mas
                rollout_area = self._rollout_stay_until_stable(node.area)
                rollout_counts = rollout_area.counts()
                rollout_cost = self._bnb_cost(rollout_counts, node.depth)
                rollout_score = self._score(rollout_counts, node.depth)
                self._trace_event(
                    "leaf",
                    node,
                    rollout_cost=rollout_cost,
                    rollout_score=rollout_score,
                    best_cost=best_cost,
                    moves=len(moves),
                )

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
                        self._trace_event("best", best_node, best_cost=best_cost, status=status)
                continue

            for mv in moves: #Continua simulando los pasos futuros para logra establecer nuevamente la cola de prioridad
                child = self._simulate_transition(node, mv)
                if child is None:
                    continue
                nodes_expanded += 1
                if child.priority >= best_cost:
                    self._trace_event(
                        "prune_child",
                        child,
                        reason="bound",
                        best_cost=best_cost,
                        parent=node.pos,
                    )
                    continue
                heapq.heappush(queue, child)
                self._trace_event("enqueue", child, parent=node.pos)

        elapsed = time.perf_counter() - start #Finaliza el conteo de tiempo
        self.total_nodes += nodes_expanded
        self.total_time += elapsed

        if best_node is None:
            best_node = root
            best_cost = root_bnb_cost

        self._last_report = { #guardar datos para el report
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

        if self.trace_enabled:
            # Guardamos una copia para no perder el historial al limpiar _last_trace.
            self._trace_history.append((
                [dict(ev) for ev in self._last_trace],
                self._trace_truncated,
            ))

        if best_node.path:
            return best_node.path[0]

        # Fallback: elegir algun movimiento valido para no quedarse quieto.
        fallback_moves = self._valid_moves(root)
        if fallback_moves:
            return fallback_moves[0]

        return i, j

    def _format_trace(self, trace: list[dict[str, object]], truncated: bool, max_eventos: int | None) -> str:
        markers = {
            "root": "R",
            "expand": ">",
            "enqueue": "+",
            "leaf": "*",
            "best": "!",
            "prune": "x",
            "prune_child": "x",
        }
        lines: list[str] = []
        to_show = trace
        was_truncated = truncated
        if max_eventos is not None:
            was_truncated = was_truncated or len(to_show) > max_eventos
            to_show = to_show[:max_eventos]

        for ev in to_show:
            ev_type = ev.get("type", "-")
            depth = int(ev.get("depth", 0))
            indent = "  " * depth
            marker = markers.get(ev_type, "-")
            pos = ev.get("pos", ("?", "?"))
            bound = ev.get("bound")
            bnb_cost = ev.get("bnb_cost")
            bound_txt = f"{float(bound):.2f}" if isinstance(bound, (int, float)) else str(bound)
            cost_txt = f"{float(bnb_cost):.2f}" if isinstance(bnb_cost, (int, float)) else str(bnb_cost)
            path = ev.get("path") or []
            path_txt = " -> ".join(f"({pi},{pj})" for pi, pj in path) if path else "-"
            extra = ""
            if ev_type == "leaf":
                rc = ev.get("rollout_cost")
                if rc is not None:
                    extra += f" rollout={rc:.2f}" if isinstance(rc, (int, float)) else f" rollout={rc}"
            if ev_type in ("prune", "prune_child"):
                bc = ev.get("best_cost")
                if bc is not None:
                    extra += f" poda>=best({bc:.2f})" if isinstance(bc, (int, float)) else f" poda>=best({bc})"
            parent = ev.get("parent")
            if parent is not None:
                extra += f" padre=({parent[0]},{parent[1]})"
            lines.append(
                f"{indent}{marker} {ev_type} pos=({pos[0]},{pos[1]}) "
                f"cota={bound_txt} quemadas={cost_txt} prof={depth} path={path_txt}{extra}"
            )

        if was_truncated:
            lines.append(f"... traza truncada a {len(to_show)} eventos (trace_limit={self.trace_limit})")
        return "\n".join(lines)

    def arbol_ultima_busqueda(self, max_eventos: int | None = None) -> str:
        """
        Representacion lineal del arbol explorado en la ultima llamada a siguiente_paso.
        Usa indentacion por profundidad y marca podas, hojas y el mejor nodo encontrado.
        """
        if not self.trace_enabled:
            return "Traza desactivada. Active trace_enabled en BranchAndBound para registrar el arbol."
        if not self._last_trace:
            return "Sin traza disponible: ejecute una busqueda con trace_enabled=True."

        return self._format_trace(self._last_trace, self._trace_truncated, max_eventos)

    def arbol_historial(
        self,
        max_busquedas: int | None = None,
        max_eventos: int | None = None,
    ) -> str:
        """
        Devuelve el arbol de todas las busquedas registradas (o las ultimas N).
        max_eventos limita los eventos por busqueda; max_busquedas limita cuantas
        busquedas se muestran (None = todas).
        """
        if not self.trace_enabled:
            return "Traza desactivada. Active trace_enabled en BranchAndBound para registrar el arbol."
        if not self._trace_history:
            return "Sin traza disponible: ejecute una busqueda con trace_enabled=True."

        traces = self._trace_history
        truncated_hist = False
        if max_busquedas is not None and max_busquedas > 0 and len(traces) > max_busquedas:
            traces = traces[-max_busquedas:]
            truncated_hist = True

        start_idx = len(self._trace_history) - len(traces) + 1
        lines: list[str] = []
        for offset, (trace, was_truncated) in enumerate(traces):
            num = start_idx + offset
            lines.append(f"=== Busqueda #{num} ===")
            lines.append(self._format_trace(trace, was_truncated, max_eventos))
        if truncated_hist:
            lines.append(f"... historial truncado a ultimas {max_busquedas} busquedas")
        return "\n".join(lines)


    def ultima_busqueda(self) -> dict[str, object]:
        #stats
        return dict(self._last_report)

    def resumen_global(
        self,
        area: Area | None = None,
        wall_time: float | None = None,
    ) -> dict[str, object]:
        #resumen acumulado para reportes o guardado
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


