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
    return move is not None


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
    """
    Ejecuta un turno completo.
    Retorna: (TurnResult para la interfaz, nuevo_idx_activo_p1, nuevo_idx_activo_p2)

    Convención de Action.target_index:
    - MOVE: índice del movimiento dentro de attacker.moves
    - SWITCH: índice del pokémon dentro del equipo
    """
    outcomes: List[ActionOutcome] = []
    match_over = False
    winner = None

    new_p1_idx = p1_active_idx
    new_p2_idx = p2_active_idx

    if not (0 <= new_p1_idx < len(p1_team)):
        new_p1_idx = 0
    if not (0 <= new_p2_idx < len(p2_team)):
        new_p2_idx = 0

    p1_active = p1_team[new_p1_idx]
    p2_active = p2_team[new_p2_idx]

    turn_order = determine_turn_order(p1_active, p1_action, p2_active, p2_action)

    for actor_id, _current_pokemon, action in turn_order:
        if actor_id == 1:
            attacker_team = p1_team
            defender_team = p2_team
            attacker_idx = new_p1_idx
            defender_idx = new_p2_idx
        else:
            attacker_team = p2_team
            defender_team = p1_team
            attacker_idx = new_p2_idx
            defender_idx = new_p1_idx

        attacker = attacker_team[attacker_idx]
        defender = defender_team[defender_idx]

        if attacker.is_fainted():
            continue

        is_faster = (len(turn_order) > 0 and turn_order[0][0] == actor_id)

        if action.type == ActionType.SWITCH:
            if _is_valid_switch(attacker_team, attacker_idx, action.target_index):
                if actor_id == 1:
                    new_p1_idx = action.target_index
                    switched_pokemon = p1_team[new_p1_idx]
                else:
                    new_p2_idx = action.target_index
                    switched_pokemon = p2_team[new_p2_idx]
            else:
                switched_pokemon = attacker_team[attacker_idx]

            outcomes.append(ActionOutcome(
                actor=actor_id,
                action_type=ActionType.SWITCH,
                action_id=switched_pokemon.id,
                is_faster=is_faster,
                hit_success=True,
                damage_dealt=0,
                type_multiplier=1.0,
                target_hp_remaining=0,
                target_fainted=False,
                attacker_hp_remaining=switched_pokemon.current_hp,
                status_applied=None
            ))
            continue

        if action.type != ActionType.MOVE:
            continue

        if actor_id == 1:
            attacker = p1_team[new_p1_idx]
            defender = p2_team[new_p2_idx]
        else:
            attacker = p2_team[new_p2_idx]
            defender = p1_team[new_p1_idx]

        if attacker.is_fainted():
            continue

        if defender.is_fainted():
            continue

        if not _is_valid_move(attacker, action.target_index):
            outcomes.append(ActionOutcome(
                actor=actor_id,
                action_type=ActionType.MOVE,
                action_id=-1,
                is_faster=is_faster,
                hit_success=False,
                damage_dealt=0,
                type_multiplier=0.0,
                target_hp_remaining=defender.current_hp,
                target_fainted=defender.is_fainted(),
                attacker_hp_remaining=attacker.current_hp,
                status_applied=None
            ))
            continue

        move = attacker.moves[action.target_index]

        can_attack = True
        if attacker.status_ailment == AilmentType.SLEEP:
            can_attack = False
        elif attacker.status_ailment == AilmentType.PARALYSIS:
            if random.randint(1, 100) <= 25:
                can_attack = False

        if not move.is_usable() or not can_attack:
            outcomes.append(ActionOutcome(
                actor=actor_id,
                action_type=ActionType.MOVE,
                action_id=move.id,
                is_faster=is_faster,
                hit_success=False,
                damage_dealt=0,
                type_multiplier=0.0,
                target_hp_remaining=defender.current_hp,
                target_fainted=defender.is_fainted(),
                attacker_hp_remaining=attacker.current_hp,
                status_applied=None
            ))
            continue

        move.current_pp -= 1

        hit_success = random.randint(1, 100) <= move.accuracy

        damage = 0
        multi = 1.0
        status_applied = None

        if hit_success:
            damage, multi = calculate_damage(
                attacker.attack,
                defender.defense,
                defender.speed,
                move.power,
                move.move_type,
                defender.types
            )

            defender.take_damage(damage)

            if move.drain > 0 and damage > 0:
                drained_hp = int(damage * (move.drain / 100.0))
                attacker.heal(drained_hp)

            if move.healing > 0:
                healed_hp = int(attacker.max_hp * (move.healing / 100.0))
                attacker.heal(healed_hp)

            if (
                move.ailment != AilmentType.NONE
                and defender.status_ailment == AilmentType.NONE
                and not defender.is_fainted()
            ):
                if random.randint(1, 100) <= move.ailment_chance:
                    defender.status_ailment = move.ailment
                    status_applied = move.ailment

        outcomes.append(ActionOutcome(
            actor=actor_id,
            action_type=ActionType.MOVE,
            action_id=move.id,
            is_faster=is_faster,
            hit_success=hit_success,
            damage_dealt=damage,
            type_multiplier=multi,
            target_hp_remaining=defender.current_hp,
            target_fainted=defender.is_fainted(),
            attacker_hp_remaining=attacker.current_hp,
            status_applied=status_applied
        ))

    active_pokemons = [
        (1, p1_team[new_p1_idx]),
        (2, p2_team[new_p2_idx]),
    ]

    for owner_id, pkmn in active_pokemons:
        if pkmn.is_fainted():
            continue

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

    if p1_lost and p2_lost:
        match_over = True
        winner = None
    elif p1_lost:
        match_over = True
        winner = 2
    elif p2_lost:
        match_over = True
        winner = 1

    if not match_over:
        if p1_team[new_p1_idx].is_fainted():
            candidate = _first_available_alive(p1_team, exclude_idx=new_p1_idx)
            if candidate is not None:
                new_p1_idx = candidate
                switched_pokemon = p1_team[new_p1_idx]
                outcomes.append(ActionOutcome(
                    actor=1,
                    action_type=ActionType.SWITCH,
                    action_id=switched_pokemon.id,
                    is_faster=False,
                    hit_success=True,
                    damage_dealt=0,
                    type_multiplier=1.0,
                    target_hp_remaining=0,
                    target_fainted=False,
                    attacker_hp_remaining=switched_pokemon.current_hp,
                    status_applied=None
                ))

        if p2_team[new_p2_idx].is_fainted():
            candidate = _first_available_alive(p2_team, exclude_idx=new_p2_idx)
            if candidate is not None:
                new_p2_idx = candidate
                switched_pokemon = p2_team[new_p2_idx]
                outcomes.append(ActionOutcome(
                    actor=2,
                    action_type=ActionType.SWITCH,
                    action_id=switched_pokemon.id,
                    is_faster=False,
                    hit_success=True,
                    damage_dealt=0,
                    type_multiplier=1.0,
                    target_hp_remaining=0,
                    target_fainted=False,
                    attacker_hp_remaining=switched_pokemon.current_hp,
                    status_applied=None
                ))

    turn_result = TurnResult(
        outcomes=outcomes,
        match_over=match_over,
        winner=winner
    )

    return turn_result, new_p1_idx, new_p2_idx