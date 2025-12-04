from area import Area

class strategy_bombero:
    def siguiente_paso(self, i: int, j: int, area: Area, forbidden: set[tuple[int, int]]) -> tuple[int, int]:
        raise NotImplementedError
