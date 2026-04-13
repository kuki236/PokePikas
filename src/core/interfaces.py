# src/core/interfaces.py

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
from src.entities.enums import AilmentType

class ActionType(Enum):
    MOVE = "MOVE"
    SWITCH = "SWITCH"

@dataclass
class Action:
    """
    Representa la decisión de un jugador o de la IA en su turno.
    """
    type: ActionType
    target_index: int
    # Si es MOVE: índice del ataque en la lista del Pokémon activo (0 a 3).
    # Si es SWITCH: índice del Pokémon en la lista del equipo (0 a 2, o 0 a 3).

@dataclass
class PokemonState:
    id: int
    max_hp: int
    current_hp: int
    attack: int
    defense: int
    speed: int
    move_ids: List[int]

@dataclass
class BattleState:
    p1_team: List[PokemonState]
    p2_team: List[PokemonState]
    p1_active_index: int
    p2_active_index: int
    turn_number: int


@dataclass
class ActionOutcome:
    actor: int
    action_type: ActionType
    action_id: int
    is_faster: bool
    hit_success: bool
    damage_dealt: int
    type_multiplier: float
    target_hp_remaining: int
    target_fainted: bool
    attacker_hp_remaining: int           
    status_applied: Optional[AilmentType] 

@dataclass
class TurnResult:

    outcomes: List[ActionOutcome]
    match_over: bool
    winner: Optional[int]  # 1, 2, o None si la partida aún no termina