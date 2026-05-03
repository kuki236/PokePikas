from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
from src.entities.enums import AilmentType


class ActionType(Enum):
    MOVE = "MOVE"
    SWITCH = "SWITCH"


@dataclass
class Action:
    type: ActionType
    target_index: int


@dataclass
class MoveState:
    id: int
    name: str
    power: int
    category: str   
    move_type: str   
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
    special_attack: int   
    special_defense: int 
    speed: int
    types: List[str]      
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
    winner: Optional[int]