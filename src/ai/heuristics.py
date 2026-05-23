from src.core.interfaces import BattleState
from src.core.damage_calc import get_type_multiplier
from src.entities.enums import PokemonType


def evaluate_level3_state(state: BattleState, player_id: int) -> float:

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

    # =====================================================
    # HP GLOBAL NORMALIZADO [-1, 1]
    # =====================================================
    my_current_hp = sum(max(0, p.current_hp) for p in my_team)
    my_max_hp = sum(max(1, p.max_hp) for p in my_team)

    opp_current_hp = sum(max(0, p.current_hp) for p in opp_team)
    opp_max_hp = sum(max(1, p.max_hp) for p in opp_team)

    hp_score = (
        (my_current_hp / my_max_hp)
        -
        (opp_current_hp / opp_max_hp)
    )

    # =====================================================
    # KO SCORE
    # =====================================================
    ko_score = 0.0

    if my_active.current_hp <= 0:
        ko_score = -1.0

    # =====================================================
    # PESOS NORMALIZADOS
    # =====================================================
    HP_WEIGHT = 0.8
    KO_WEIGHT = 0.2

    return (
        (HP_WEIGHT * hp_score)
        +
        (KO_WEIGHT * ko_score)
    )


def evaluate_level4_state(state: BattleState, player_id: int) -> float:

    # =====================================================
    # TODOS LOS FACTORES NORMALIZADOS
    # =====================================================

    HP_WEIGHT = 0.40
    ALIVE_WEIGHT = 0.25
    TYPE_WEIGHT = 0.15
    SPEED_WEIGHT = 0.10
    STATUS_WEIGHT = 0.10

    # =====================================================
    # EQUIPOS
    # =====================================================
    if player_id == 1:
        my_team, opp_team = state.p1_team, state.p2_team
        my_idx, opp_idx = state.p1_active_index, state.p2_active_index
    else:
        my_team, opp_team = state.p2_team, state.p1_team
        my_idx, opp_idx = state.p2_active_index, state.p1_active_index

    my_active = (
        my_team[my_idx]
        if my_idx < len(my_team)
        else my_team[0]
    )

    opp_active = (
        opp_team[opp_idx]
        if opp_idx < len(opp_team)
        else opp_team[0]
    )

    # =====================================================
    # 1. HP SCORE [-1,1]
    # =====================================================
    my_current_hp = sum(max(0, p.current_hp) for p in my_team)
    my_max_hp = sum(max(1, p.max_hp) for p in my_team)

    opp_current_hp = sum(max(0, p.current_hp) for p in opp_team)
    opp_max_hp = sum(max(1, p.max_hp) for p in opp_team)

    hp_score = (
        (my_current_hp / my_max_hp)
        -
        (opp_current_hp / opp_max_hp)
    )

    # =====================================================
    # 2. POKEMON VIVOS [-1,1]
    # =====================================================
    my_alive = sum(1 for p in my_team if p.current_hp > 0)
    opp_alive = sum(1 for p in opp_team if p.current_hp > 0)

    alive_score = (
        (my_alive - opp_alive)
        /
        max(1, len(my_team))
    )

    # =====================================================
    # DEFAULTS
    # =====================================================
    speed_score = 0.0
    type_score = 0.0
    status_score = 0.0

    # =====================================================
    # SOLO SI EL ACTIVO SIGUE VIVO
    # =====================================================
    if my_active.current_hp > 0:

        # =================================================
        # 3. SPEED SCORE [-1,1]
        # =================================================
        if my_active.speed > opp_active.speed:
            speed_score = 1.0

        elif my_active.speed < opp_active.speed:
            speed_score = -1.0

        # =================================================
        # 4. TYPE SCORE [-1,1]
        # =================================================
        opp_types = [
            PokemonType[t.upper()]
            for t in getattr(opp_active, 'types', [])
            if t.upper() in PokemonType.__members__
        ]

        my_types = [
            PokemonType[t.upper()]
            for t in getattr(my_active, 'types', [])
            if t.upper() in PokemonType.__members__
        ]

        # =============================================
        # MEJOR MULTIPLICADOR OFENSIVO
        # =============================================
        max_mult_offense = 1.0

        for move in getattr(my_active, 'moves', []):

            if (
                getattr(move, 'current_pp', 0) > 0
                and
                getattr(move, 'power', 0) > 0
            ):

                m_type_str = getattr(
                    move,
                    'move_type',
                    'NORMAL'
                ).upper()

                m_enum = (
                    PokemonType[m_type_str]
                    if m_type_str in PokemonType.__members__
                    else PokemonType.NORMAL
                )

                mult = get_type_multiplier(
                    m_enum,
                    opp_types
                )

                max_mult_offense = max(
                    max_mult_offense,
                    mult
                )

        # =============================================
        # MEJOR MULTIPLICADOR DEFENSIVO ENEMIGO
        # =============================================
        max_mult_defense = 1.0

        for move in getattr(opp_active, 'moves', []):

            if (
                getattr(move, 'current_pp', 0) > 0
                and
                getattr(move, 'power', 0) > 0
            ):

                m_type_str = getattr(
                    move,
                    'move_type',
                    'NORMAL'
                ).upper()

                m_enum = (
                    PokemonType[m_type_str]
                    if m_type_str in PokemonType.__members__
                    else PokemonType.NORMAL
                )

                mult = get_type_multiplier(
                    m_enum,
                    my_types
                )

                max_mult_defense = max(
                    max_mult_defense,
                    mult
                )

        # =================================================
        # NORMALIZACIÓN REAL
        #
        # 0.0x -> -1
        # 1.0x -> 0
        # 2.0x -> +0.5
        # 4.0x -> +1
        # =================================================
        off_score = (max_mult_offense - 1.0) / 3.0
        def_score = (max_mult_defense - 1.0) / 3.0

        type_score = off_score - def_score

        # CLAMP
        type_score = max(-1.0, min(1.0, type_score))

        # =================================================
        # 5. STATUS SCORE [-1,1]
        # =================================================
        my_status_obj = getattr(
            my_active,
            'status_ailment',
            'NONE'
        )

        my_status = (
            my_status_obj.name
            if hasattr(my_status_obj, 'name')
            else str(my_status_obj).upper()
        )

        opp_status_obj = getattr(
            opp_active,
            'status_ailment',
            'NONE'
        )

        opp_status = (
            opp_status_obj.name
            if hasattr(opp_status_obj, 'name')
            else str(opp_status_obj).upper()
        )

        bad_status = [
            'BURN',
            'POISON',
            'PARALYSIS',
            'FREEZE',
            'SLEEP'
        ]

        if my_status in bad_status:
            status_score -= 1.0

        if opp_status in bad_status:
            status_score += 1.0

    # =====================================================
    # EVALUACIÓN FINAL NORMALIZADA
    # =====================================================
    final_score = (
        (HP_WEIGHT * hp_score)
        +
        (ALIVE_WEIGHT * alive_score)
        +
        (TYPE_WEIGHT * type_score)
        +
        (SPEED_WEIGHT * speed_score)
        +
        (STATUS_WEIGHT * status_score)
    )

    return final_score