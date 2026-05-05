from src.entities.enums import PokemonType, AilmentType
from config import FACTOR_K
TYPE_CHART: dict[PokemonType, dict[PokemonType, float]] = {
    PokemonType.NORMAL: {
        PokemonType.ROCK:   0.5,
        PokemonType.GHOST:  0.0,
        PokemonType.STEEL:  0.5,
    },
    PokemonType.FIRE: {
        PokemonType.FIRE:   0.5,
        PokemonType.WATER:  0.5,
        PokemonType.GRASS:  2.0,
        PokemonType.ICE:    2.0,
        PokemonType.BUG:    2.0,
        PokemonType.ROCK:   0.5,
        PokemonType.DRAGON: 0.5,
        PokemonType.STEEL:  2.0,
    },
    PokemonType.WATER: {
        PokemonType.FIRE:   2.0,
        PokemonType.WATER:  0.5,
        PokemonType.GRASS:  0.5,
        PokemonType.GROUND: 2.0,
        PokemonType.ROCK:   2.0,
        PokemonType.DRAGON: 0.5,
    },
    PokemonType.ELECTRIC: {
        PokemonType.WATER:    2.0,
        PokemonType.ELECTRIC: 0.5,
        PokemonType.GRASS:    0.5,
        PokemonType.GROUND:   0.0,
        PokemonType.FLYING:   2.0,
        PokemonType.DRAGON:   0.5,
    },
    PokemonType.GRASS: {
        PokemonType.FIRE:    0.5,
        PokemonType.WATER:   2.0,
        PokemonType.GRASS:   0.5,
        PokemonType.POISON:  0.5,
        PokemonType.GROUND:  2.0,
        PokemonType.FLYING:  0.5,
        PokemonType.BUG:     0.5,
        PokemonType.ROCK:    2.0,
        PokemonType.DRAGON:  0.5,
        PokemonType.STEEL:   0.5,
    },
    PokemonType.ICE: {
        PokemonType.FIRE:    0.5,
        PokemonType.WATER:   0.5,
        PokemonType.GRASS:   2.0,
        PokemonType.ICE:     0.5,
        PokemonType.GROUND:  2.0,
        PokemonType.FLYING:  2.0,
        PokemonType.DRAGON:  2.0,
        PokemonType.STEEL:   0.5,
    },
    PokemonType.FIGHTING: {
        PokemonType.NORMAL:  2.0,
        PokemonType.ICE:     2.0,
        PokemonType.POISON:  0.5,
        PokemonType.FLYING:  0.5,
        PokemonType.PSYCHIC: 0.5,
        PokemonType.BUG:     0.5,
        PokemonType.ROCK:    2.0,
        PokemonType.GHOST:   0.0,
        PokemonType.DARK:    2.0,
        PokemonType.STEEL:   2.0,
        PokemonType.FAIRY:   0.5,
    },
    PokemonType.POISON: {
        PokemonType.GRASS:   2.0,
        PokemonType.POISON:  0.5,
        PokemonType.GROUND:  0.5,
        PokemonType.ROCK:    0.5,
        PokemonType.GHOST:   0.5,
        PokemonType.STEEL:   0.0,
        PokemonType.FAIRY:   2.0,
    },
    PokemonType.GROUND: {
        PokemonType.FIRE:     2.0,
        PokemonType.ELECTRIC: 2.0,
        PokemonType.GRASS:    0.5,
        PokemonType.POISON:   2.0,
        PokemonType.FLYING:   0.0,
        PokemonType.BUG:      0.5,
        PokemonType.ROCK:     2.0,
        PokemonType.STEEL:    2.0,
    },
    PokemonType.FLYING: {
        PokemonType.ELECTRIC: 0.5,
        PokemonType.GRASS:    2.0,
        PokemonType.FIGHTING: 2.0,
        PokemonType.BUG:      2.0,
        PokemonType.ROCK:     0.5,
        PokemonType.STEEL:    0.5,
    },
    PokemonType.PSYCHIC: {
        PokemonType.FIGHTING: 2.0,
        PokemonType.POISON:   2.0,
        PokemonType.PSYCHIC:  0.5,
        PokemonType.DARK:     0.0,
        PokemonType.STEEL:    0.5,
    },
    PokemonType.BUG: {
        PokemonType.FIRE:     0.5,
        PokemonType.GRASS:    2.0,
        PokemonType.FIGHTING: 0.5,
        PokemonType.POISON:   0.5,
        PokemonType.FLYING:   0.5,
        PokemonType.PSYCHIC:  2.0,
        PokemonType.GHOST:    0.5,
        PokemonType.DARK:     2.0,
        PokemonType.STEEL:    0.5,
        PokemonType.FAIRY:    0.5,
    },
    PokemonType.ROCK: {
        PokemonType.FIRE:     2.0,
        PokemonType.ICE:      2.0,
        PokemonType.FIGHTING: 0.5,
        PokemonType.GROUND:   0.5,
        PokemonType.FLYING:   2.0,
        PokemonType.BUG:      2.0,
        PokemonType.STEEL:    0.5,
    },
    PokemonType.GHOST: {
        PokemonType.NORMAL:   0.0,
        PokemonType.PSYCHIC:  2.0,
        PokemonType.GHOST:    2.0,
        PokemonType.DARK:     0.5,
    },
    PokemonType.DRAGON: {
        PokemonType.DRAGON:   2.0,
        PokemonType.STEEL:    0.5,
        PokemonType.FAIRY:    0.0,
    },
    PokemonType.DARK: {
        PokemonType.FIGHTING: 0.5,
        PokemonType.PSYCHIC:  2.0,
        PokemonType.GHOST:    2.0,
        PokemonType.DARK:     0.5,
        PokemonType.FAIRY:    0.5,
    },
    PokemonType.STEEL: {
        PokemonType.FIRE:     0.5,
        PokemonType.WATER:    0.5,
        PokemonType.ELECTRIC: 0.5,
        PokemonType.ICE:      2.0,
        PokemonType.ROCK:     2.0,
        PokemonType.STEEL:    0.5,
        PokemonType.FAIRY:    2.0,
    },
    PokemonType.FAIRY: {
        PokemonType.FIRE:     0.5,
        PokemonType.FIGHTING: 2.0,
        PokemonType.POISON:   0.5,
        PokemonType.DRAGON:   2.0,
        PokemonType.DARK:     2.0,
        PokemonType.STEEL:    0.5,
    },
}


def get_type_multiplier(attack_type: PokemonType, defender_types: list[PokemonType]) -> float:
    multiplier = 1.0
    if attack_type not in TYPE_CHART:
        return multiplier
    for def_type in defender_types:
        multiplier *= TYPE_CHART[attack_type].get(def_type, 1.0)
    return multiplier

def get_modified_stat(base_value: int, stage: int, ailment: AilmentType = AilmentType.NONE, is_speed: bool = False) -> int:
    if stage >= 0:
        multiplier = (2 + stage) / 2
    else:
        multiplier = 2 / (2 + abs(stage))
    
    final_stat = int(base_value * multiplier)
    
    if is_speed and ailment == AilmentType.PARALYSIS:
        final_stat = int(final_stat * 0.5)
    
    if not is_speed and ailment == AilmentType.BURN:
        final_stat = int(final_stat * 0.5)
        
    return final_stat

def calculate_damage(
    attacker_base_stat: int,      
    defender_base_stat: int,     
    defender_spd: int, 
    move_power: int, 
    move_type: PokemonType, 
    defender_types: list[PokemonType],
    attacker_stage: int = 0,    
    defender_stage: int = 0,   
    attacker_ailment: AilmentType = AilmentType.NONE
) -> tuple[int, float]:
    
    if move_power == 0:
        return 0, 1.0 
    
    type_multiplier = get_type_multiplier(move_type, defender_types)
    
    if type_multiplier == 0.0:
        return 0, 0.0

    atk = get_modified_stat(attacker_base_stat, attacker_stage, attacker_ailment)
    dfe = get_modified_stat(defender_base_stat, defender_stage)

    base_damage = ((atk / max(1, dfe)) * move_power) / 2.75     
    speed_factor = defender_spd * FACTOR_K
    
    raw_damage = base_damage - speed_factor
    
    final_damage = int(max(1, raw_damage * type_multiplier))
        
    return final_damage, type_multiplier