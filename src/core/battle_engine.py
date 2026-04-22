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

def process_turn(p1_team: List[Pokemon], p1_active_idx: int, p1_action: Action, 
                 p2_team: List[Pokemon], p2_active_idx: int, p2_action: Action) -> tuple[TurnResult, int, int]:
    """
    Ejecuta un turno completo.
    Retorna: (TurnResult para la interfaz, nuevo_idx_activo_p1, nuevo_idx_activo_p2)
    """
    outcomes = []
    match_over = False
    winner = None

    p1_active = p1_team[p1_active_idx]
    p2_active = p2_team[p2_active_idx]

    turn_order = determine_turn_order(p1_active, p1_action, p2_active, p2_action)
    
    new_p1_idx = p1_active_idx
    new_p2_idx = p2_active_idx

    for actor_id, current_pokemon, action in turn_order:
        
        if actor_id == 1 and p1_team[new_p1_idx].is_fainted():
            continue
        if actor_id == 2 and p2_team[new_p2_idx].is_fainted():
             continue

        is_faster = (turn_order[0][0] == actor_id)
        
        if action.type == ActionType.SWITCH:
            if actor_id == 1:
                new_p1_idx = action.target_index
                switched_pokemon = p1_team[new_p1_idx]
            else:
                new_p2_idx = action.target_index
                switched_pokemon = p2_team[new_p2_idx]
                
            outcomes.append(ActionOutcome(
                actor=actor_id, action_type=ActionType.SWITCH, action_id=switched_pokemon.id,
                is_faster=is_faster, hit_success=True, damage_dealt=0, type_multiplier=1.0,
                target_hp_remaining=0, target_fainted=False, attacker_hp_remaining=switched_pokemon.current_hp,
                status_applied=None
            ))
            
        elif action.type == ActionType.MOVE:
            if actor_id == 1:
                attacker = p1_team[new_p1_idx]
                defender = p2_team[new_p2_idx]
            else:
                attacker = p2_team[new_p2_idx]
                defender = p1_team[new_p1_idx]
            
            move = attacker.moves[action.target_index]
            
            can_attack = True
            if attacker.status_ailment == AilmentType.SLEEP:
                can_attack = False 
            elif attacker.status_ailment == AilmentType.PARALYSIS:
                if random.randint(1, 100) <= 25:
                    can_attack = False
                    
            if not move.is_usable() or not can_attack:
                 outcomes.append(ActionOutcome(
                     actor=actor_id, action_type=ActionType.MOVE, action_id=move.id, 
                     is_faster=is_faster, hit_success=False, damage_dealt=0, type_multiplier=0.0, 
                     target_hp_remaining=defender.current_hp, target_fainted=defender.is_fainted(), 
                     attacker_hp_remaining=attacker.current_hp, status_applied=None
                 ))
                 continue

            move.current_pp -= 1
            
            hit_success = random.randint(1, 100) <= move.accuracy
            
            damage = 0
            multi = 1.0
            status_applied = None
            
            if hit_success:
                 damage, multi = calculate_damage(attacker.attack, defender.defense, defender.speed, move.power, move.move_type, defender.types)
                 defender.take_damage(damage)
                 
                 if move.drain > 0:
                     drained_hp = int(damage * (move.drain / 100.0))
                     attacker.heal(drained_hp)

                 if move.healing > 0:
                     healed_hp = int(attacker.max_hp * (move.healing / 100.0))
                     attacker.heal(healed_hp)

                 if move.ailment != AilmentType.NONE and defender.status_ailment == AilmentType.NONE:
                     if random.randint(1, 100) <= move.ailment_chance:
                         defender.status_ailment = move.ailment
                         status_applied = move.ailment
                 
            outcomes.append(ActionOutcome(
                actor=actor_id, action_type=ActionType.MOVE, action_id=move.id,
                is_faster=is_faster, hit_success=hit_success, damage_dealt=damage, type_multiplier=multi,
                target_hp_remaining=defender.current_hp, target_fainted=defender.is_fainted(),
                attacker_hp_remaining=attacker.current_hp, status_applied=status_applied
            ))

    active_pokemons = [
        (1, p1_team[new_p1_idx]),
        (2, p2_team[new_p2_idx])
    ]

    for owner_id, pkmn in active_pokemons:
        if not pkmn.is_fainted():
            if pkmn.status_ailment in [AilmentType.BURN, AilmentType.POISON, AilmentType.LEECH_SEED]:
                
                residual_damage = max(1, pkmn.max_hp // 8)
                pkmn.take_damage(residual_damage)

                if pkmn.status_ailment == AilmentType.LEECH_SEED:
                    if owner_id == 1 and not p2_team[new_p2_idx].is_fainted():
                        p2_team[new_p2_idx].heal(residual_damage)
                    elif owner_id == 2 and not p1_team[new_p1_idx].is_fainted():
                        p1_team[new_p1_idx].heal(residual_damage)

    p1_lost = all(p.is_fainted() for p in p1_team)
    p2_lost = all(p.is_fainted() for p in p2_team)
    
    if p1_lost:
         match_over = True
         winner = 2
    elif p2_lost:
         match_over = True
         winner = 1
         
    turn_result = TurnResult(outcomes=outcomes, match_over=match_over, winner=winner)

    return turn_result, new_p1_idx, new_p2_idx
