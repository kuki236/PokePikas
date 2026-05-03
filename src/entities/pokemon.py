from dataclasses import replace
from typing import List
from .enums import PokemonType, AilmentType
from .move import Move


class Pokemon:
    """Molde base de las criaturas en el motor lógico con soporte para stats especiales."""

    def __init__(
        self,
        poke_id: int,
        name: str,
        max_hp: int,
        attack: int,
        defense: int,
        special_attack: int,  
        special_defense: int, 
        speed: int,
        types: List[PokemonType],
        moves: List[Move]
    ):
        self.id              = poke_id
        self.name            = name
        self.max_hp          = max_hp
        self.current_hp      = max_hp
        self.attack          = attack
        self.defense         = defense
        self.special_attack  = special_attack  
        self.special_defense = special_defense 
        self.speed           = speed
        self.types           = types
        self.moves           = moves
        self.status_ailment: AilmentType = AilmentType.NONE

    def take_damage(self, amount: int) -> None:
        self.current_hp = max(0, self.current_hp - amount)

    def heal(self, amount: int) -> None:
        self.current_hp = min(self.max_hp, self.current_hp + amount)

    def is_fainted(self) -> bool:
        return self.current_hp <= 0

    def clone(self) -> "Pokemon":
        cloned = Pokemon(
            poke_id         = self.id,
            name            = self.name,
            max_hp          = self.max_hp,
            attack          = self.attack,
            defense         = self.defense,
            special_attack  = self.special_attack,  
            special_defense = self.special_defense, 
            speed           = self.speed,
            types           = list(self.types),
            moves           = [replace(m) for m in self.moves]
        )
        cloned.current_hp     = self.current_hp
        cloned.status_ailment = self.status_ailment
        return cloned

    def to_state(self):
        from src.core.interfaces import PokemonState, MoveState

        move_states = []
        for m in self.moves:
            move_states.append(MoveState(
                id         = getattr(m, 'id', 0),
                name       = getattr(m, 'name', ''),
                power      = getattr(m, 'power', 0),
                category   = getattr(m, 'category', 'PHYSICAL'), 
                move_type  = m.move_type.name if hasattr(m, 'move_type') and m.move_type else 'NORMAL',
                current_pp = getattr(m, 'current_pp', 0),
                max_pp     = getattr(m, 'max_pp', 1),
            ))

        return PokemonState(
            id              = self.id,
            name            = self.name,
            max_hp          = self.max_hp,
            current_hp      = self.current_hp,
            attack          = self.attack,
            defense         = self.defense,
            special_attack  = self.special_attack,  
            special_defense = self.special_defense, 
            speed           = self.speed,
            types           = [t.name for t in self.types],
            moves           = move_states
        )