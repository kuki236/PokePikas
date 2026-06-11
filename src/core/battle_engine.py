import random
from typing import List

from .interfaces import Action, ActionType, TurnResult, ActionOutcome
from src.entities.pokemon import Pokemon
from src.entities.enums import AilmentType
from .damage_calc import calculate_damage, get_type_multiplier

def _is_valid_switch(team: List[Pokemon], current_idx: int, target_idx: int) -> bool:
    """

    Determina si se puede realizar un intercambio válido en el equipo.

    Args:
        team (List[Pokemon]): El equipo de Pokémon.
        current_idx (int): El índice actual en el equipo.
        target_idx (int): El índice objetivo en el equipo.

    Returns:
        bool: True si el intercambio es válido, False en caso contrario.

    Raises:
        No se conocen excepciones.

    """
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
    """
    Descripción breve:
    Devuelve el índice del primer Pokémon vivo y disponible en el equipo, excluyendo el índice especificado.

    Args:
        team (List[Pokemon]): El equipo de Pokémon.
        exclude_idx (int | None, opcional): El índice del Pokémon a excluir. Defaults to None.

    Returns:
        int | None: El índice del primer Pokémon vivo y disponible, o None si no se encuentra ningún Pokémon vivo.

    Raises:
        No lanza excepciones.
    """
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
    Determina el orden de turno de los pokemon en base a sus acciones.

    Args:
        p1_pokemon (Pokemon): El pokemon del jugador 1.
        p1_action (Action): La acción del pokemon del jugador 1.
        p2_pokemon (Pokemon): El pokemon del jugador 2.
        p2_action (Action): La acción del pokemon del jugador 2.

    Returns:
        list[tuple[int, Pokemon, Action]]: Una lista de tuplas que contienen el orden de turno, el pokemon y la acción correspondientes.

    Raises:
        No se contempla explícitamente ninguna excepción en esta función, aunque puede generar errores si los parámetros no son del tipo esperado o si no se cumplen ciertas condiciones en la lógica de determinación del orden de turno.
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
    Procesa un turno en una batalla de Pokémon.

    Args:
        p1_team (List[Pokemon]): Equipo de Pokémon del jugador 1.
        p1_active_idx (int): Índice del Pokémon activo del jugador 1.
        p1_action (Action): Acción del jugador 1.
        p2_team (List[Pokemon]): Equipo de Pokémon del jugador 2.
        p2_active_idx (int): Índice del Pokémon activo del jugador 2.
        p2_action (Action): Acción del jugador 2.

    Returns:
        tuple[TurnResult, int, int]: Un objeto TurnResult que contiene los resultados del turno, y los nuevos índices de los Pokémon activos de ambos jugadores.

    Raises:
        Exception: Si se produce un error durante el procesamiento del turno.
    """
    outcomes: List[ActionOutcome] = []
    match_over = False
    winner = None

    new_p1_idx = max(0, min(p1_active_idx, len(p1_team) - 1))
    new_p2_idx = max(0, min(p2_active_idx, len(p2_team) - 1))

    turn_order = determine_turn_order(p1_team[new_p1_idx], p1_action, p2_team[new_p2_idx], p2_action)

    for actor_id, _, action in turn_order:
        
        if actor_id == 1:
            attacker_team, defender_team = p1_team, p2_team
            attacker_idx, defender_idx = new_p1_idx, new_p2_idx
        else:
            attacker_team, defender_team = p2_team, p1_team
            attacker_idx, defender_idx = new_p2_idx, new_p1_idx

        attacker = attacker_team[attacker_idx]
        defender = defender_team[defender_idx]

        if attacker.current_hp <= 0 or attacker.is_fainted():
            continue

        is_faster = (len(turn_order) > 0 and turn_order[0][0] == actor_id)

        if action.type == ActionType.SWITCH:
            if _is_valid_switch(attacker_team, attacker_idx, action.target_index):
                if actor_id == 1:
                    new_p1_idx = action.target_index
                else:
                    new_p2_idx = action.target_index
                
                active_pkmn = attacker_team[action.target_index]
                active_pkmn.reset_stages()
                
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
            
            if attacker.current_hp <= 0 or attacker.is_fainted() or defender.current_hp <= 0: 
                continue 

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
            
            if attacker.status_ailment in [AilmentType.SLEEP, AilmentType.FREEZE]:
                if random.randint(1, 100) <= 40:
                    attacker.status_ailment = AilmentType.NONE
                else:
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
                if move.category == "STATUS":
                    multi = get_type_multiplier(move.move_type, defender.types)
                    if move.name.lower() == "rest":
                        if not attacker.is_fainted():
                            attacker.heal(attacker.max_hp)
                            attacker.status_ailment = AilmentType.SLEEP
                            status_applied = AilmentType.SLEEP
                    elif move.healing > 0:
                        if not attacker.is_fainted():
                            attacker.heal(int(attacker.max_hp * (move.healing / 100.0)))
                    
                    is_fire_burn = move.ailment == AilmentType.BURN and "FIRE" in defender.types
                    if move.ailment != AilmentType.NONE and defender.status_ailment == AilmentType.NONE and multi > 0 and not is_fire_burn:
                        if not defender.is_fainted():
                            defender.status_ailment = move.ailment
                            status_applied = move.ailment
                else:
                    is_phys = move.category == "PHYSICAL"
                    atk_key = "attack" if is_phys else "special_attack"
                    def_key = "defense" if is_phys else "special_defense"
                    
                    atk_stage = attacker.stat_stages[atk_key]
                    def_stage = defender.stat_stages[def_key]

                    move_power = max(1, int(move.power * (attacker.current_hp / attacker.max_hp))) if move.id == 323 else (110 if move.id == 512 else move.power)

                    hits = random.randint(3, 5) if move.id == 594 else 1
                    total_damage_accumulator = 0
                    last_multi = 1.0
               
                    for _ in range(hits):
                        if defender.current_hp <= 0:
                            break

                        hit_damage, m = calculate_damage(
                            attacker.attack if is_phys else attacker.special_attack,
                            defender.defense if is_phys else defender.special_defense,
                            defender.speed, 
                            move_power, 
                            move.move_type, 
                            defender.types,
                            attacker_stage=atk_stage,
                            defender_stage=def_stage,
                            attacker_ailment=attacker.status_ailment
                        )
                        total_damage_accumulator += hit_damage
                        last_multi = m
                    
                    damage = total_damage_accumulator
                    multi = last_multi
                    defender.take_damage(damage)
               
                    if move.drain > 0 and damage > 0 and not attacker.is_fainted():
                        attacker.heal(int(damage * (move.drain / 100.0)))
                    
                    if move.id in [528, 413] and damage > 0:
                        recoil = max(1, damage // 4)
                        attacker.take_damage(recoil)
                    
                    is_fire_burn = move.ailment == AilmentType.BURN and "FIRE" in defender.types
                    if move.ailment != AilmentType.NONE and defender.status_ailment == AilmentType.NONE and multi > 0 and not is_fire_burn:
                        if not defender.is_fainted() and random.randint(1, 100) <= move.ailment_chance:
                            defender.status_ailment = move.ailment
                            status_applied = move.ailment

                    if attacker.id == 10117 and defender.current_hp <= 0:
                        for stat in ["attack", "special_attack", "speed"]:
                            if attacker.stat_stages[stat] < 6:
                                attacker.stat_stages[stat] += 1
                        DEBUG_BATTLE_ENGINE = False
                        if DEBUG_BATTLE_ENGINE:
                             print(f"  -> ¡El Vínculo Afectivo de {attacker.name} se fortalece! (Stats +1)")

            if move.id == 136 and not hit_success:
                attacker.take_damage(attacker.max_hp // 2)

            outcomes.append(ActionOutcome(
                actor=actor_id, action_type=ActionType.MOVE, action_id=move.id,
                is_faster=is_faster, hit_success=hit_success, damage_dealt=damage,
                type_multiplier=multi, target_hp_remaining=max(0, defender.current_hp),
                target_fainted=(defender.current_hp <= 0 or defender.is_fainted()), 
                attacker_hp_remaining=max(0, attacker.current_hp),
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
                if not opponent_team[opp_idx].is_fainted(): opponent_team[opp_idx].heal(residual)

    p1_lost = all(p.is_fainted() for p in p1_team)
    p2_lost = all(p.is_fainted() for p in p2_team)
    if p1_lost or p2_lost:
        match_over = True
        winner = 1 if p2_lost and not p1_lost else (2 if p1_lost and not p2_lost else None)
    
    if not match_over:
        for tid, team, idx in [(1, p1_team, new_p1_idx), (2, p2_team, new_p2_idx)]:
            if team[idx].is_fainted():
                c = _first_available_alive(team)
                if c is not None:
                    if tid == 1: new_p1_idx = c
                    else: new_p2_idx = c
                    team[c].reset_stages()
                    outcomes.append(ActionOutcome(tid, ActionType.SWITCH, team[c].id, False, True, 0, 1.0, 0, False, team[c].current_hp, None))

    return TurnResult(outcomes, match_over, winner), new_p1_idx, new_p2_idx