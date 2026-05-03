import requests
import json
import os

# Los 30 Pokémon exactos de tu interfaz gráfica
POKEMON_NAMES = [
    "charizard", "venusaur", "blastoise", "gengar", "snorlax", "sceptile",
    "blaziken", "swampert", "gardevoir", "metagross", "lucario", "garchomp",
    "infernape", "togekiss", "electivire", "talonflame", "sylveon", "goodra",
    "hawlucha", "noivern", "decidueye", "incineroar", "primarina", "golisopod",
    "kommo-o", "cinderace", "dragapult", "corviknight", "grimmsnarl", "greninja-ash"
]

def get_stat(stats_array, stat_name):
    for stat in stats_array:
        if stat['stat']['name'] == stat_name:
            return stat['base_stat']
    return 0

def fetch_pokemon_and_moves():
    print("Iniciando descarga desde PokéAPI... Esto puede tomar unos segundos ⏳")
    
    os.makedirs('data', exist_ok=True)
    
    pokemon_pool = []
    moves_pool = {} # Usamos un diccionario para evitar duplicados
    
    for name in POKEMON_NAMES:
        print(f"Descargando datos de {name.capitalize()}...")
        try:
            req = requests.get(f"https://pokeapi.co/api/v2/pokemon/{name}")
            if req.status_code != 200:
                print(f"⚠️ Error encontrando a {name}")
                continue
                
            data = req.json()
            
            # --- EXTRAER ESTADÍSTICAS COMPLETAS ---
            hp = get_stat(data['stats'], 'hp')
            attack = get_stat(data['stats'], 'attack')
            defense = get_stat(data['stats'], 'defense')
            sp_attack = get_stat(data['stats'], 'special-attack') # NUEVO
            sp_defense = get_stat(data['stats'], 'special-defense') # NUEVO
            speed = get_stat(data['stats'], 'speed')
            
            types = [t['type']['name'].upper() for t in data['types']]
            
            # --- EXTRAER MOVIMIENTOS ---
            # Buscaremos 4 movimientos que hagan daño para simplificar tu motor
            chosen_moves_ids = []
            valid_moves_found = 0
            
            for move_info in data['moves']:
                if valid_moves_found >= 4:
                    break
                    
                move_url = move_info['move']['url']
                move_req = requests.get(move_url).json()
                
                # Solo queremos movimientos que hagan daño (power > 0)
                if move_req['power'] is not None and move_req['power'] > 0:
                    move_id = move_req['id']
                    
                    if move_id not in moves_pool:
                        moves_pool[move_id] = {
                            "id": move_id,
                            "name": move_req['name'],
                            "power": move_req['power'],
                            "accuracy": move_req['accuracy'] if move_req['accuracy'] else 100,
                            "move_type": move_req['type']['name'].upper(),
                            "category": move_req['damage_class']['name'].upper(), # PHYSICAL o SPECIAL
                            "max_pp": move_req['pp'],
                            "current_pp": move_req['pp'],
                            "drain": move_req['meta']['drain'] if move_req['meta'] else 0,
                            "healing": move_req['meta']['healing'] if move_req['meta'] else 0,
                            "ailment": move_req['meta']['ailment']['name'].upper() if move_req['meta'] else "NONE",
                            "ailment_chance": move_req['meta']['ailment_chance'] if move_req['meta'] else 0
                        }
                    
                    chosen_moves_ids.append(move_id)
                    valid_moves_found += 1

            # --- ARMAR EL OBJETO POKÉMON ---
            pkm_obj = {
                "poke_id": data['id'],
                "name": name,
                "types": types,
                "max_hp": hp,
                "attack": attack,
                "defense": defense,
                "special_attack": sp_attack,   # NUEVO
                "special_defense": sp_defense, # NUEVO
                "speed": speed,
                "moves": chosen_moves_ids
            }
            pokemon_pool.append(pkm_obj)
            
        except Exception as e:
            print(f"❌ Error procesando {name}: {e}")

    # --- GUARDAR EN ARCHIVOS JSON ---
    with open('data/pokemon_pool.json', 'w', encoding='utf-8') as f:
        json.dump(pokemon_pool, f, indent=4)
        
    # Convertir el diccionario de movimientos en una lista
    moves_list = list(moves_pool.values())
    with open('data/moves_pool.json', 'w', encoding='utf-8') as f:
        json.dump(moves_list, f, indent=4)

    print("\n✅ ¡Descarga completada con éxito!")
    print(f"-> data/pokemon_pool.json ({len(pokemon_pool)} Pokémon)")
    print(f"-> data/moves_pool.json ({len(moves_list)} Movimientos únicos)")

if __name__ == "__main__":
    fetch_pokemon_and_moves()