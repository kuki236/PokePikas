import random
from typing import List, Optional
from .interfaces import Action, ActionType, TurnResult, ActionOutcome
from src.entities.pokemon import Pokemon
from src.entities.move import Move
from src.entities.enums import PokemonType, AilmentType

from .damage_calc import calculate_damage

def determine_turn_order(p1_pokemon: Pokemon, p1_action: Action, p2_pokemon: Pokemon, p2_action: Action) -> list[tuple[int, Pokemon, Action]]:
    """
    Determina el orden de ejecución basado en el tipo de acción y la velocidad.
    Retorna una lista con el orden: [(actor_id, pokemon, action), ...]
    """
    order = []
    
    if p1_action.type == ActionType.SWITCH:
        order.append((1, p1_pokemon, p1_action))
    if p2_action.type == ActionType.SWITCH:
        order.append((2, p2_pokemon, p2_action))
        
    moves_to_order = []
    if p1_action.type == ActionType.MOVE:
        moves_to_order.append((1, p1_pokemon, p1_action))
    if p2_action.type == ActionType.MOVE:
        moves_to_order.append((2, p2_pokemon, p2_action))
        
    if len(moves_to_order) == 2:
        if p1_pokemon.speed > p2_pokemon.speed:
            order.extend([(1, p1_pokemon, p1_action), (2, p2_pokemon, p2_action)])
        elif p2_pokemon.speed > p1_pokemon.speed:
            order.extend([(2, p2_pokemon, p2_action), (1, p1_pokemon, p1_action)])
        else:
            if random.choice([True, False]):
                order.extend([(1, p1_pokemon, p1_action), (2, p2_pokemon, p2_action)])
            else:
                order.extend([(2, p2_pokemon, p2_action), (1, p1_pokemon, p1_action)])
    elif len(moves_to_order) == 1:
         order.append(moves_to_order[0])

    return order