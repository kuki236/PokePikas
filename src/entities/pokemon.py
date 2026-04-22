from dataclasses import replace
from typing import List
from .enums import PokemonType, AilmentType
from .move import Move
from src.core.interfaces import PokemonState

class Pokemon:
    """Molde base de las criaturas en el motor lógico."""

    def __init__(
        self,
        poke_id: int,
        name: str,
        max_hp: int,
        attack: int,
        defense: int,
        speed: int,
        types: List[PokemonType],
        moves: List[Move]
    ):
        self.id       = poke_id
        self.name     = name
        self.max_hp   = max_hp
        self.current_hp = max_hp
        self.attack   = attack
        self.defense  = defense
        self.speed    = speed
        self.types    = types
        self.moves    = moves
        self.status_ailment: AilmentType = AilmentType.NONE

    def take_damage(self, amount: int) -> None:
        self.current_hp = max(0, self.current_hp - amount)

    def heal(self, amount: int) -> None:
        self.current_hp = min(self.max_hp, self.current_hp + amount)

    def is_fainted(self) -> bool:
        return self.current_hp == 0

    def clone(self) -> "Pokemon":
        cloned = Pokemon(
            poke_id  = self.id,
            name     = self.name,
            max_hp   = self.max_hp,
            attack   = self.attack,
            defense  = self.defense,
            speed    = self.speed,
            types    = self.types,
            moves    = [replace(m) for m in self.moves]
        )
        cloned.current_hp     = self.current_hp
        cloned.status_ailment = self.status_ailment
        return cloned

    def to_state(self) -> PokemonState:
        return PokemonState(
            id=self.id,
            max_hp=self.max_hp,
            current_hp=self.current_hp,
            attack=self.attack,
            defense=self.defense,
            speed=self.speed,
            move_ids=[m.id for m in self.moves if m.current_pp > 0] 
        )