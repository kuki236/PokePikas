import json
import random
import copy
from src.entities.pokemon import Pokemon
from src.entities.move import Move
from src.entities.enums import PokemonType, AilmentType

class DataLoader:
    def __init__(self, pokemon_file_path: str, moves_file_path: str):
        with open(pokemon_file_path, 'r', encoding='utf-8') as f:
            self.pokemon_data = json.load(f)
            
        with open(moves_file_path, 'r', encoding='utf-8') as f:
            self.moves_data = json.load(f)

        self.move_templates = {}
        for m in self.moves_data:
            self.move_templates[m["id"]] = Move(
                id=m["id"],
                name=m["name"],
                power=m["power"],
                accuracy=m["accuracy"],
                move_type=PokemonType[m["move_type"]], 
                max_pp=m["max_pp"],
                current_pp=m["current_pp"],
                ailment=AilmentType[m["ailment"].replace("-", "_").upper()],
                ailment_chance=m["ailment_chance"],
                drain=m["drain"],
                healing=m["healing"]
            )

    def create_battle_pokemon(self, target_poke_id: int) -> Pokemon:
        """Busca el Pokémon, le asigna 4 ataques aleatorios y lo instancia."""
        p_data = next((p for p in self.pokemon_data if p["poke_id"] == target_poke_id), None)
        if not p_data:
            raise ValueError(f"No se encontró el Pokémon con ID {target_poke_id}")

        selected_move_ids = random.sample(p_data["move_ids"], 4)

        battle_moves = [copy.deepcopy(self.move_templates[m_id]) for m_id in selected_move_ids]

        poke_types = [PokemonType[t] for t in p_data["types"]]

        return Pokemon(
            poke_id=p_data["poke_id"],
            name=p_data["name"],
            max_hp=p_data["max_hp"],
            attack=p_data["attack"],
            defense=p_data["defense"],
            speed=p_data["speed"],
            types=poke_types,
            moves=battle_moves
        )