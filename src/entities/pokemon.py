from typing import List
from .enums import PokemonType, AilmentType
from .move import Move

class Pokemon:
    """Molde base de las criaturas en el motor lógico con soporte para stats especiales y stages."""

    def __init__(
        self,
        poke_id: int,
        name: str,
        max_hp: int,
        attack: int,
        defense: int,
        special_attack: int,  
        special_defense: int, 
        speed: int,
        types: List[PokemonType],
        moves: List[Move]
    ):
        """
        Inicializa un objeto Pokémon con sus estadísticas y propiedades.

        Args:
            poke_id (int): El ID único del Pokémon.
            name (str): El nombre del Pokémon.
            max_hp (int): Los puntos de salud máximos del Pokémon.
            attack (int): El valor de ataque del Pokémon.
            defense (int): El valor de defensa del Pokémon.
            special_attack (int): El valor de ataque especial del Pokémon.
            special_defense (int): El valor de defensa especial del Pokémon.
            speed (int): La velocidad del Pokémon.
            types (List[PokemonType]): Los tipos de Pokémon.
            moves (List[Move]): Las movidas que conoce el Pokémon.

        Returns:
            None

        Raises:
            None
        """
        self.id              = poke_id
        self.name            = name
        self.max_hp          = max_hp
        self.current_hp      = max_hp
        self.attack          = attack
        self.defense         = defense
        self.special_attack  = special_attack  
        self.special_defense = special_defense 
        self.speed           = speed
        self.types           = types
        self.moves           = moves
        self.status_ailment: AilmentType = AilmentType.NONE
        
        self.stat_stages = {
            "attack": 0,
            "defense": 0,
            "special_attack": 0,
            "special_defense": 0,
            "speed": 0
        }

    def reset_stages(self):
        """Reinicia las estadísticas al cambiar de Pokémon"""
        for stat in self.stat_stages:
            self.stat_stages[stat] = 0

    def take_damage(self, amount: int) -> None:
        if amount <= 0:
            return
        self.current_hp = max(0, self.current_hp - amount)

    def heal(self, amount: int) -> None:
        if self.is_fainted() or amount <= 0:
            return
        self.current_hp = min(self.max_hp, self.current_hp + amount)

    def is_fainted(self) -> bool:
        return self.current_hp <= 0

    def to_state(self):
        """Convierte el objeto a una estructura de datos plana para la IA."""
        from src.core.interfaces import PokemonState, MoveState

        move_states = []
        for m in self.moves:
            move_states.append(MoveState(
                id         = getattr(m, 'id', 0),
                name       = getattr(m, 'name', ''),
                power      = getattr(m, 'power', 0),
                category   = getattr(m, 'category', 'PHYSICAL'), 
                move_type  = m.move_type.name if hasattr(m, 'move_type') and m.move_type else 'NORMAL',
                current_pp = getattr(m, 'current_pp', 0),
                max_pp     = getattr(m, 'max_pp', 1),
                accuracy=getattr(m, 'accuracy', 100),
                drain=getattr(m, 'drain', 0),
                healing=getattr(m, 'healing', 0),
                ailment=m.ailment.name if hasattr(m, 'ailment') and m.ailment else 'NONE',
                ailment_chance=getattr(m, 'ailment_chance', 0),
            ))

        return PokemonState(
            id              = self.id,
            name            = self.name,
            max_hp          = self.max_hp,
            current_hp      = self.current_hp,
            attack          = self.attack,
            defense         = self.defense,
            special_attack  = self.special_attack,  
            special_defense = self.special_defense, 
            speed           = self.speed,
            types           = [t.name for t in self.types],
            moves           = move_states,
            stat_stages     = dict(self.stat_stages),
            status_ailment = self.status_ailment.name
        )
    @staticmethod
    def from_state(state):
        """
        Reconstruye un Pokemon real desde PokemonState
        para simulaciones reales del minimax.
        """

        import copy

        from src.entities.enums import PokemonType, AilmentType
        from src.utils.move_registry import MOVE_TEMPLATES

        # =========================================
        # RECONSTRUIR MOVES REALES
        # =========================================
        real_moves = []

        for move_state in state.moves:

            if move_state.id not in MOVE_TEMPLATES:
                continue

            move_obj = copy.deepcopy(
                MOVE_TEMPLATES[move_state.id]
            )

            # restaurar PP actual
            move_obj.current_pp = move_state.current_pp

            real_moves.append(move_obj)

        # =========================================
        # RECONSTRUIR TYPES
        # =========================================
        real_types = []

        for t in state.types:

            t_upper = str(t).upper()

            if t_upper in PokemonType.__members__:
                real_types.append(
                    PokemonType[t_upper]
                )

        # =========================================
        # CREAR POKEMON REAL
        # =========================================
        pkmn = Pokemon(
            poke_id=state.id,
            name=state.name,

            max_hp=state.max_hp,

            attack=state.attack,
            defense=state.defense,

            special_attack=state.special_attack,
            special_defense=state.special_defense,

            speed=state.speed,

            types=real_types,

            moves=real_moves
        )

        # =========================================
        # RESTAURAR ESTADO ACTUAL
        # =========================================
        pkmn.current_hp = state.current_hp

        # =========================================
        # STATUS
        # =========================================
        ailment_str = str(
            getattr(state, 'status_ailment', 'NONE')
        ).upper()

        if ailment_str in AilmentType.__members__:
            pkmn.status_ailment = AilmentType[ailment_str]
        else:
            pkmn.status_ailment = AilmentType.NONE

        # =========================================
        # STAT STAGES
        # =========================================
        pkmn.stat_stages = dict(
            getattr(state, 'stat_stages', {})
        )

        return pkmn
