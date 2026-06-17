from dataclasses import dataclass
from .enums import PokemonType, AilmentType

@dataclass
class Move:
    """Instancia de un movimiento de combate con PP y estado mutable.

    Attributes:
        id (int): Identificador del movimiento (catalogo de PokeAPI).
        name (str): Nombre legible.
        power (int): Poder base (0 para movimientos de estado).
        accuracy (int): Precision en porcentaje (0-100).
        move_type (PokemonType): Tipo elemental del movimiento.
        category (str): 'PHYSICAL', 'SPECIAL' o 'STATUS'.
        max_pp (int): PP maximos.
        current_pp (int): PP restantes (se reduce al usar).
        ailment (AilmentType): Estado alterado que puede infligir.
        ailment_chance (int): Probabilidad (0-100) de aplicar el estado.
        drain (int): Porcentaje de HP drenado/recuperado del dano causado
            (positivo cura al atacante, negativo causa recoil).
        healing (int): Porcentaje del HP maximo que cura al usuario.
    """
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
        """Indica si el movimiento puede ejecutarse (PP > 0).

        Returns:
            bool: True si current_pp > 0.
        """
        return self.current_pp > 0

    def use(self) -> None:
        """Consume un PP al ejecutar el movimiento.

        Raises:
            ValueError: Si el movimiento no tiene PP disponibles.
        """
        if not self.is_usable():
            raise ValueError(f"{self.name} no tiene PP disponibles.")
        self.current_pp -= 1