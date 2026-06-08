from src.core.interfaces import BattleState
from src.core.damage_calc import get_type_multiplier
from src.entities.enums import PokemonType


def evaluate_level3_state(state: BattleState, player_id: int) -> float:

    """
    Evalúa el estado de batalla de nivel 3 y asigna una puntuación numérica basada en las condiciones actuales de los equipos.

    Args:
        state (BattleState): El estado actual de la batalla.
        player_id (int): El identificador del jugador (1 o 2).

    Returns:
        float: Una puntuación que indica la ventaja o desventaja del jugador en la batalla.

    Raises:
        No se lanzan excepciones explícitas, pero podría producirse un error si el objeto BattleState no contiene los atributos esperados o si el player_id no es válido.
    """
    if player_id == 1:
        my_team, opp_team = state.p1_team, state.p2_team
        my_idx = state.p1_active_index
    else:
        my_team, opp_team = state.p2_team, state.p1_team
        my_idx = state.p2_active_index

    my_active = (
        my_team[my_idx]
        if my_idx < len(my_team)
        else my_team[0]
    )

    my_current_hp = sum(max(0, p.current_hp) for p in my_team)
    my_max_hp = sum(max(1, p.max_hp) for p in my_team)

    opp_current_hp = sum(max(0, p.current_hp) for p in opp_team)
    opp_max_hp = sum(max(1, p.max_hp) for p in opp_team)

    hp_score = (
        (my_current_hp / my_max_hp)
        -
        (opp_current_hp / opp_max_hp)
    )

    ko_score = 0.0

    if my_active.current_hp <= 0:
        ko_score = -1.0

    HP_WEIGHT = 0.8
    KO_WEIGHT = 0.2

    return (
        (HP_WEIGHT * hp_score)
        +
        (KO_WEIGHT * ko_score)
    )


from src.core.interfaces import BattleState
from src.core.damage_calc import get_type_multiplier
from src.entities.enums import PokemonType

def evaluate_level4_state(state: BattleState, player_id: int) -> float:
    
    # BALANCEO 
    """
    Evaluación del estado de nivel 4 en una batalla de Pokémon.

    Args:
        state (BattleState): Estado actual de la batalla.
        player_id (int): Identificador del jugador (1 o 2).

    Returns:
        float: Puntuación que refleja la ventaja o desventaja del jugador en la batalla.

    Raises:
        No se lanzan excepciones explícitas, pero puede ocurrir un error si el estado de la batalla o el identificador del jugador son inválidos.
    """
    HP_WEIGHT = 0.50
    ALIVE_WEIGHT = 0.30
    TYPE_WEIGHT = 0.15
    SPEED_WEIGHT = 0.03
    STATUS_WEIGHT = 0.02
    if player_id == 1:
        my_team, opp_team = state.p1_team, state.p2_team
        my_idx, opp_idx = state.p1_active_index, state.p2_active_index
    else:
        my_team, opp_team = state.p2_team, state.p1_team
        my_idx, opp_idx = state.p2_active_index, state.p1_active_index

    my_alive_flag = any(p.current_hp > 0 for p in my_team)
    opp_alive_flag = any(p.current_hp > 0 for p in opp_team)

    if not opp_alive_flag: return 999999.0
    if not my_alive_flag: return -999999.0

    my_active = my_team[my_idx] if my_idx < len(my_team) else my_team[0]
    opp_active = opp_team[opp_idx] if opp_idx < len(opp_team) else opp_team[0]

    my_current_hp = sum(max(0, p.current_hp) for p in my_team)
    my_max_hp = sum(max(1, p.max_hp) for p in my_team)
    opp_current_hp = sum(max(0, p.current_hp) for p in opp_team)
    opp_max_hp = sum(max(1, p.max_hp) for p in opp_team)
    hp_score = (my_current_hp / my_max_hp) - (opp_current_hp / opp_max_hp)

    my_alive = sum(1 for p in my_team if p.current_hp > 0)
    opp_alive = sum(1 for p in opp_team if p.current_hp > 0)
    team_size = max(1, len(my_team)) 
    alive_score = (my_alive - opp_alive) / float(team_size)

    speed_score = 0.0
    type_score = 0.0
    status_score = 0.0

    if my_active.current_hp > 0:
        if my_active.speed > opp_active.speed: speed_score = 1.0
        elif my_active.speed < opp_active.speed: speed_score = -1.0

        opp_types = [PokemonType[t.upper()] for t in getattr(opp_active, 'types', []) if t.upper() in PokemonType.__members__]
        my_types = [PokemonType[t.upper()] for t in getattr(my_active, 'types', []) if t.upper() in PokemonType.__members__]
        
        max_mult_offense = 0.0
        for move in getattr(my_active, 'moves', []):
            if getattr(move, 'current_pp', 0) > 0 and getattr(move, 'power', 0) > 0:
                m_type_str = getattr(move, 'move_type', 'NORMAL').upper()
                m_enum = PokemonType[m_type_str] if m_type_str in PokemonType.__members__ else PokemonType.NORMAL
                mult = get_type_multiplier(m_enum, opp_types)
                if mult > max_mult_offense: max_mult_offense = mult

        max_mult_defense = 0.0
        for move in getattr(opp_active, 'moves', []):
            if getattr(move, 'current_pp', 0) > 0 and getattr(move, 'power', 0) > 0:
                m_type_str = getattr(move, 'move_type', 'NORMAL').upper()
                m_enum = PokemonType[m_type_str] if m_type_str in PokemonType.__members__ else PokemonType.NORMAL
                mult = get_type_multiplier(m_enum, my_types)
                if mult > max_mult_defense: max_mult_defense = mult
        
        type_score = ((max_mult_offense - 1.0) - (max_mult_defense - 1.0))/3

        bad_ailments = ["BURN", "POISON", "PARALYSIS", "FREEZE", "SLEEP"]
        my_ailment = getattr(my_active, 'status_ailment', "NONE")
        ailment_str = my_ailment.name if hasattr(my_ailment, 'name') else str(my_ailment).split('.')[-1].upper()
        if ailment_str in bad_ailments: status_score = -1.0

    return (HP_WEIGHT * hp_score) + (SPEED_WEIGHT * speed_score) + (TYPE_WEIGHT * type_score) + (STATUS_WEIGHT * status_score) + (ALIVE_WEIGHT * alive_score)