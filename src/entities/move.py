from dataclasses import dataclass
from .enums import PokemonType, AilmentType

@dataclass
class Move:
    """Representa un movimiento/ataque instanciado para un combate."""
    id: int
    name: str
    power: int
    accuracy: int
    move_type: PokemonType
    category: str    
    max_pp: int
    current_pp: int
    ailment: AilmentType
    ailment_chance: int
    drain: int
    healing: int

    def is_usable(self) -> bool:
        """Verifica si el ataque aún tiene puntos de poder."""
        return self.current_pp > 0

    def use(self) -> None:
        """Consume un PP al ejecutar el movimiento."""
        if not self.is_usable():
            raise ValueError(f"{self.name} no tiene PP disponibles.")
        self.current_pp -= 1