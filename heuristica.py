from strategy import strategy_bombero
from area import Area
from celdas import est_celda

NEIS8: list[tuple[int, int]] = [
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1),            (0, 1),
    (1, -1),  (1, 0),  (1, 1),
]
# La heuristica es bastante sencilla y tiene la logica de primero buscar el centro del fuego
# Luego busca la pared mas cercana y luego otra pared; la idea es ir cerrando el fuego con un cortafuegos
# cerrando el cortafuegos
# La heuristica va dando scores segun el movimiento, penalizando los no deseados para forzar paredes o el centro
# del fuego cuando lo necesite, y tras visitar dos paredes continua encadenando nuevas paredes para mantener el cortafuegos.
class paredes(strategy_bombero): # Clase de la heuristica

    def __init__(self,
                 dist_fuego_umbral: int = 2,
                 w_ir_fuego: float = 5.0,
                 w_ir_pared: float = 6.0,
                 inercia: float = 0.3):
        self.fase: str = "a_fuego"  # a_fuego -> a_pared -> a_otra_pared -> ciclo de paredes
        self.pared_objetivo: str | None = None  # 'arriba','abajo','izquierda','derecha'
        self.pared_previa: str | None = None
        self._prev_move: tuple[int, int] = (0, 0)
        self.dist_fuego_umbral = dist_fuego_umbral
        self.w_ir_fuego = w_ir_fuego
        self.w_ir_pared = w_ir_pared
        self.inercia = inercia

    def _dist_chebyshev_a_fuego(self, r: int, c: int, area: Area) -> int: #Establece el centro del fuego
        fuego = area.positions(est_celda.fuego)
        if not fuego:
            return 10**9
        best = 10**9
        for fr, fc in fuego:
            d = max(abs(fr - r), abs(fc - c))
            if d < best:
                best = d
        return best

    def _dist_a_pared(self, r: int, c: int, area: Area, pared: str) -> int: #Da las distancias a las 4 paredes posibles
        n = area.n
        if pared == 'arriba':
            return r
        if pared == 'abajo':
            return (n - 1) - r
        if pared == 'izquierda':
            return c
        if pared == 'derecha':
            return (n - 1) - c
        return 10**9

    def _paredes_por_cercania(self, r: int, c: int, area: Area) -> list[str]: # Ordenas las paredes segun su distancia previa
        items = [
            ('arriba', self._dist_a_pared(r, c, area, 'arriba')),
            ('abajo', self._dist_a_pared(r, c, area, 'abajo')),
            ('izquierda', self._dist_a_pared(r, c, area, 'izquierda')),
            ('derecha', self._dist_a_pared(r, c, area, 'derecha')),
        ]
        items.sort(key=lambda x: x[1])
        return [p for p, _ in items]

    def _elige_pared(self, r: int, c: int, area: Area, distinta: str | None) -> str: #Elige la pared a moverse
        for p in self._paredes_por_cercania(r, c, area):
            if p != distinta:
                return p
        return 'arriba'

    def _buildable(self, r: int, c: int, ci: int, cj: int, area: Area) -> bool: #Ve si es posible el mov
        if (r, c) == (ci, cj):
            return True
        return area.matrix[r][c] == est_celda.sn_af

    def siguiente_paso(self, i: int, j: int, area: Area, forbidden: set[tuple[int, int]]) -> tuple[int, int]: #Maneja el paso del bombero
        if not area.positions(est_celda.fuego):
            return i, j

        if self.fase in ("a_pared", "a_otra_pared") and self.pared_objetivo is None: #Vemos si la pared ya se elegio o no
            distinta = self.pared_previa if self.fase == "a_otra_pared" else None
            self.pared_objetivo = self._elige_pared(i, j, area, distinta)

        df0 = self._dist_chebyshev_a_fuego(i, j, area)

        def score(ni: int, nj: int) -> float: # Puntajes por movimientos
            if not area.dentro(ni, nj): # Para no salir del area o grilla
                return -1e18
            if (ni, nj) in forbidden: #Area a las que no se puede ir (quemadas)
                return -1e18
            if not self._buildable(ni, nj, i, j, area): #Ya pasadas por aqui
                return -1e18
            
            #No quedarse quieto
            s = 0.0
            if (ni, nj) == (i, j):
                s -= 0.2

            #Mantener inercia para evitar que se estanque
            mdi, mdj = ni - i, nj - j
            pdi, pdj = self._prev_move
            if (mdi, mdj) == (pdi, pdj):
                s += self.inercia
            elif (mdi, mdj) == (-pdi, -pdj):
                s -= 1.2 * self.inercia

            #Favorece ortogonales
            if abs(mdi) + abs(mdj) == 1:
                s += 0.15

            # Movere al fuego
            df = self._dist_chebyshev_a_fuego(ni, nj, area)
            mejora_fuego = df0 - df
            if self.fase == "a_fuego":
                s += self.w_ir_fuego * mejora_fuego - 0.05 * df
            else:
                s += 0.2 * mejora_fuego

            # Moverse a pared
            if self.fase in ("a_pared", "a_otra_pared") and self.pared_objetivo is not None:
                d0 = self._dist_a_pared(i, j, area, self.pared_objetivo)
                d1 = self._dist_a_pared(ni, nj, area, self.pared_objetivo)
                mejora_pared = d0 - d1
                s += self.w_ir_pared * mejora_pared - 0.02 * d1

                if self.fase == "a_otra_pared" and self.pared_previa is not None:
                    dprev0 = self._dist_a_pared(i, j, area, self.pared_previa)
                    dprev1 = self._dist_a_pared(ni, nj, area, self.pared_previa)
                    # Penaliza ir hacia la pared previa
                    s -= 0.5 * max(0, dprev0 - dprev1)

            return s

        #construir movimientos en base a los pesos generados
        moves = [(0, 0)] + NEIS8
        best = (i, j)
        best_s = -1e19
        for di, dj in moves:
            ni, nj = i + di, j + dj
            sc = score(ni, nj)
            if sc > best_s:
                best_s = sc
                best = (ni, nj)

        self._prev_move = (best[0] - i, best[1] - j)

        bi, bj = best
        df1 = self._dist_chebyshev_a_fuego(bi, bj, area)

        #Define fases de la heuristica
        if self.fase == "a_fuego":
            if df1 <= self.dist_fuego_umbral:
                self.fase = "a_pared"
                self.pared_objetivo = self._elige_pared(bi, bj, area, distinta=None)
        elif self.fase in ("a_pared", "a_otra_pared") and self.pared_objetivo is not None:
            if self._dist_a_pared(bi, bj, area, self.pared_objetivo) == 0:
                self.pared_previa = self.pared_objetivo
                if self.fase == "a_pared":
                    self.fase = "a_otra_pared"
                    self.pared_objetivo = self._elige_pared(bi, bj, area, distinta=self.pared_previa)
                else:
                    # Tras alcanzar la segunda pared continuamos encadenando paredes
                    self.fase = "a_pared"
                    self.pared_objetivo = self._elige_pared(bi, bj, area, distinta=self.pared_previa)

        return best
