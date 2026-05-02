# src/core/battle_engine.py

import random
from typing import List

from .interfaces import Action, ActionType, TurnResult, ActionOutcome
from src.entities.pokemon import Pokemon
from src.entities.enums import AilmentType
from .damage_calc import calculate_damage


def _is_valid_switch(team: List[Pokemon], current_idx: int, target_idx: int) -> bool:
    if target_idx < 0 or target_idx >= len(team):
        return False
    if target_idx == current_idx:
        return False
    candidate = team[target_idx]
    return not candidate.is_fainted()


def _is_valid_move(pokemon: Pokemon, move_idx: int) -> bool:
    if move_idx < 0 or move_idx >= len(getattr(pokemon, "moves", [])):
        return False
    move = pokemon.moves[move_idx]
    return move is not None and move.current_pp > 0

def _first_available_alive(team: List[Pokemon], exclude_idx: int | None = None) -> int | None:
    for i, p in enumerate(team):
        if i == exclude_idx:
            continue
        if not p.is_fainted():
            return i
    return None


def determine_turn_order(
    p1_pokemon: Pokemon,
    p1_action: Action,
    p2_pokemon: Pokemon,
    p2_action: Action
) -> list[tuple[int, Pokemon, Action]]:
    """
    Determina el orden de ejecución basado en el tipo de acción y la velocidad.
    Retorna una lista con el orden: [(actor_id, pokemon, action), ...]
    Reglas:
    - SWITCH ocurre antes que MOVE.
    - Si ambos usan MOVE, decide por speed.
    - En empate de speed, orden aleatorio.
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


def process_turn(
    p1_team: List[Pokemon],
    p1_active_idx: int,
    p1_action: Action,
    p2_team: List[Pokemon],
    p2_active_idx: int,
    p2_action: Action
) -> tuple[TurnResult, int, int]:
    outcomes: List[ActionOutcome] = []
    match_over = False
    winner = None

    new_p1_idx = max(0, min(p1_active_idx, len(p1_team) - 1))
    new_p2_idx = max(0, min(p2_active_idx, len(p2_team) - 1))

    turn_order = determine_turn_order(p1_team[new_p1_idx], p1_action, p2_team[new_p2_idx], p2_action)

    for actor_id, _current_pokemon, action in turn_order:
        if actor_id == 1:
            attacker_team, defender_team = p1_team, p2_team
            attacker_idx, defender_idx = new_p1_idx, new_p2_idx
        else:
            attacker_team, defender_team = p2_team, p1_team
            attacker_idx, defender_idx = new_p2_idx, new_p1_idx

        attacker = attacker_team[attacker_idx]
        defender = defender_team[defender_idx]

        if attacker.is_fainted():
            continue

        is_faster = (len(turn_order) > 0 and turn_order[0][0] == actor_id)

        if action.type == ActionType.SWITCH:
            if _is_valid_switch(attacker_team, attacker_idx, action.target_index):
                if actor_id == 1:
                    new_p1_idx = action.target_index
                else:
                    new_p2_idx = action.target_index
                
                active_pkmn = attacker_team[action.target_index]
                outcomes.append(ActionOutcome(
                    actor=actor_id, action_type=ActionType.SWITCH, action_id=active_pkmn.id,
                    is_faster=is_faster, hit_success=True, damage_dealt=0, type_multiplier=1.0,
                    target_hp_remaining=defender.current_hp, target_fainted=False,
                    attacker_hp_remaining=active_pkmn.current_hp, status_applied=None
                ))
            continue

        if action.type == ActionType.MOVE:
            if actor_id == 1:
                attacker, defender = p1_team[new_p1_idx], p2_team[new_p2_idx]
            else:
                attacker, defender = p2_team[new_p2_idx], p1_team[new_p1_idx]

            if not _is_valid_move(attacker, action.target_index):
                outcomes.append(ActionOutcome(
                    actor=actor_id, action_type=ActionType.MOVE, action_id=-1,
                    is_faster=is_faster, hit_success=False, damage_dealt=0, type_multiplier=0.0,
                    target_hp_remaining=defender.current_hp, target_fainted=False,
                    attacker_hp_remaining=attacker.current_hp, status_applied=None
                ))
                continue

            move = attacker.moves[action.target_index]
            can_attack = True
            if attacker.status_ailment == AilmentType.SLEEP:
                can_attack = False
            elif attacker.status_ailment == AilmentType.PARALYSIS:
                if random.randint(1, 100) <= 25:
                    can_attack = False

            if not can_attack:
                outcomes.append(ActionOutcome(
                    actor=actor_id, action_type=ActionType.MOVE, action_id=move.id,
                    is_faster=is_faster, hit_success=False, damage_dealt=0, type_multiplier=0.0,
                    target_hp_remaining=defender.current_hp, target_fainted=False,
                    attacker_hp_remaining=attacker.current_hp, status_applied=None
                ))
                continue

            move.current_pp -= 1
            hit_success = random.randint(1, 100) <= move.accuracy
            damage, multi, status_applied = 0, 1.0, None

            if hit_success:
                damage, multi = calculate_damage(
                    attacker.attack, defender.defense, defender.speed,
                    move.power, move.move_type, defender.types
                )
                defender.take_damage(damage)

                if move.drain > 0 and damage > 0:
                    attacker.heal(int(damage * (move.drain / 100.0)))
                if move.healing > 0:
                    attacker.heal(int(attacker.max_hp * (move.healing / 100.0)))

                if move.ailment != AilmentType.NONE and defender.status_ailment == AilmentType.NONE:
                    if not defender.is_fainted() and random.randint(1, 100) <= move.ailment_chance:
                        defender.status_ailment = move.ailment
                        status_applied = move.ailment

            outcomes.append(ActionOutcome(
                actor=actor_id, action_type=ActionType.MOVE, action_id=move.id,
                is_faster=is_faster, hit_success=hit_success, damage_dealt=damage,
                type_multiplier=multi, target_hp_remaining=defender.current_hp,
                target_fainted=defender.is_fainted(), attacker_hp_remaining=attacker.current_hp,
                status_applied=status_applied
            ))

    for owner_id, team, active_idx in [(1, p1_team, new_p1_idx), (2, p2_team, new_p2_idx)]:
        pkmn = team[active_idx]
        if not pkmn.is_fainted() and pkmn.status_ailment in [AilmentType.BURN, AilmentType.POISON, AilmentType.LEECH_SEED]:
            residual = max(1, pkmn.max_hp // 8)
            pkmn.take_damage(residual)
            if pkmn.status_ailment == AilmentType.LEECH_SEED:
                opponent_team = p2_team if owner_id == 1 else p1_team
                opp_idx = new_p2_idx if owner_id == 1 else new_p1_idx
                if not opponent_team[opp_idx].is_fainted():
                    opponent_team[opp_idx].heal(residual)

    p1_lost = all(p.is_fainted() for p in p1_team)
    p2_lost = all(p.is_fainted() for p in p2_team)

    if p1_lost or p2_lost:
        match_over = True
        winner = 1 if p2_lost and not p1_lost else (2 if p1_lost and not p2_lost else None)
    
    if not match_over:
        if p1_team[new_p1_idx].is_fainted():
            candidate = _first_available_alive(p1_team)
            if candidate is not None:
                new_p1_idx = candidate
                outcomes.append(ActionOutcome(
                    actor=1, action_type=ActionType.SWITCH, action_id=p1_team[new_p1_idx].id,
                    is_faster=False, hit_success=True, damage_dealt=0, type_multiplier=1.0,
                    target_hp_remaining=0, target_fainted=False,
                    attacker_hp_remaining=p1_team[new_p1_idx].current_hp, status_applied=None
                ))
        if p2_team[new_p2_idx].is_fainted():
            candidate = _first_available_alive(p2_team)
            if candidate is not None:
                new_p2_idx = candidate
                outcomes.append(ActionOutcome(
                    actor=2, action_type=ActionType.SWITCH, action_id=p2_team[new_p2_idx].id,
                    is_faster=False, hit_success=True, damage_dealt=0, type_multiplier=1.0,
                    target_hp_remaining=0, target_fainted=False,
                    attacker_hp_remaining=p2_team[new_p2_idx].current_hp, status_applied=None
                ))

    return TurnResult(outcomes, match_over, winner), new_p1_idx, new_p2_idx