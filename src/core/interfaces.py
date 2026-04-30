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
    - MOVE:   target_index = índice del movimiento en la lista del Pokémon activo (0-3)
    - SWITCH: target_index = índice del Pokémon en el equipo (0-2)
    """
    type: ActionType
    target_index: int


@dataclass
class MoveState:
    id: int
    name: str
    power: int
    move_type: str   # nombre del enum como string, ej: "FIRE"
    current_pp: int
    max_pp: int


@dataclass
class PokemonState:
    id: int
    name: str
    max_hp: int
    current_hp: int
    attack: int
    defense: int
    speed: int
    types: List[str]       # nombres del enum como strings, ej: ["WATER", "FLYING"]
    moves: List[MoveState]


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
    action_id: int         # MOVE → move.id  |  SWITCH → pokemon.id del que entró
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
    winner: Optional[int]   # 1, 2, o None (empate / en curso)