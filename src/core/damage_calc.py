from src.entities.enums import PokemonType
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
    """Calcula el multiplicador total cruzando el ataque contra los tipos del defensor."""
    multiplier = 1.0
    
    if attack_type not in TYPE_CHART:
        return multiplier

    for def_type in defender_types:
        multiplier *= TYPE_CHART[attack_type].get(def_type, 1.0)
        
    return multiplier

import random



def calculate_damage(attacker_atk: int, defender_def: int, defender_spd: int, 
                     move_power: int, move_type: PokemonType, defender_types: list[PokemonType]) -> tuple[int, float]:
   
    
    type_multiplier = get_type_multiplier(move_type, defender_types)
    
    base_damage = (attacker_atk / max(1, defender_def)) * move_power
    
    speed_factor = defender_spd * FACTOR_K
    
    raw_damage = base_damage - speed_factor
    
    final_damage = int(max(1, raw_damage * type_multiplier))
    
    if type_multiplier == 0.0:
        final_damage = 0
        
    return final_damage, type_multiplier
