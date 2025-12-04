from area import Area
from celdas import est_celda
from comp_fuego import fuego
from comp_bombero import bombero

class Simulation:
    def __init__(self, area: Area, comp_fuego: fuego, comp_bombero: bombero):
        self.area = area
        self.comp_fuego = comp_fuego
        self.comp_bombero = comp_bombero
        # marcar visualmente dónde está el bombero al inicio
        self.area.matrix[self.comp_bombero.i][self.comp_bombero.j] = est_celda.bomb

    def step(self) -> None:
        #1 el bombero construye cortafuego en su celda actual
        self.comp_bombero.u_cortafuego(self.area)
        #2 predecimos y aplicamos expansión del fuego
        para_quemar = self.comp_fuego.a_quemar(self.area)
        self.comp_fuego.aplicar(self.area, para_quemar)

        #3 predecimos la próxima expansión y nos movemos evitando esas celdas
        forbidden_next = self.comp_fuego.a_quemar(self.area)
        self.comp_bombero.move(self.area, forbidden=forbidden_next)

        #4 avanzar tiempo
        self.area.tick += 1

    def run_until_end(self, max_steps: int = 10_000) -> int:
        steps = 0
        while steps < max_steps:
            # si ya no hay más expansión posible, paramos
            if not self.comp_fuego.a_quemar(self.area):
                break
            self.step()
            steps += 1
        return steps

    def _no_more_expansion_after_bomber(self) -> bool:
        """
        Devuelve True si, considerando que el bombero construye el cortafuego
        en su celda actual (tal como ocurre al inicio de cada step), el fuego
        ya no puede expandirse en el siguiente tick.
        """
        bi, bj = self.comp_bombero.i, self.comp_bombero.j
        original = self.area.matrix[bi][bj]
        if original in (est_celda.sn_af, est_celda.bomb):
            self.area.matrix[bi][bj] = est_celda.c_fuego
        try:
            return len(self.comp_fuego.a_quemar(self.area)) == 0
        finally:
            self.area.matrix[bi][bj] = original

    def run_until_stable(self, max_steps: int = 10_000) -> int:
        """
        Igual que run_until_end, pero chequeando la condición de paro
        tras simular el cortafuego del bombero del siguiente tick.
        """
        steps = 0
        while steps < max_steps:
            if self._no_more_expansion_after_bomber():
                break
            self.step()
            steps += 1
        return steps

    def run_until_tick(self, target_tick: int) -> int:
        steps = 0
        while self.area.tick < target_tick:
            if not self.comp_fuego.a_quemar(self.area):
                break
            self.step()
            steps += 1
        return steps
