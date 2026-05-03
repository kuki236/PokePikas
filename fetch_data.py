import requests
import json
import os

# Mapeo exacto de los movimientos que pediste según el JSON de referencia
POKEMON_MOVES = {
    "charizard": [53, 126, 337, 403, 355, 412, 89, 394],
    "venusaur": [188, 412, 235, 73, 89, 79, 202, 92],
    "blastoise": [56, 57, 58, 430, 396, 323, 229, 89],
    "gengar": [247, 188, 411, 85, 506, 261, 399], 
    "snorlax": [34, 89, 242, 484, 156, 94, 428, 667],
    "sceptile": [348, 406, 411, 202, 412, 89, 404, 437],
    "blaziken": [394, 136, 413, 89, 444, 421, 299, 370],
    "swampert": [127, 89, 8, 444, 57, 330, 276, 56],
    "gardevoir": [585, 94, 473, 247, 85, 412, 595, 411],
    "metagross": [309, 428, 89, 418, 8, 9, 359, 94],
    "lucario": [396, 430, 370, 309, 245, 399, 406, 94],
    "garchomp": [89, 337, 200, 444, 424, 242, 442, 398],
    "infernape": [394, 370, 183, 9, 89, 404, 126, 411],
    "togekiss": [403, 605, 396, 53, 355, 304, 247, 94],
    "electivire": [85, 528, 8, 7, 89, 238, 53, 9],
    "talonflame": [413, 394, 355, 404, 211, 261, 512, 488],
    "sylveon": [585, 304, 473, 247, 595, 98, 577, 156],
    "goodra": [406, 434, 53, 85, 58, 188, 330, 438],
    "hawlucha": [560, 136, 512, 398, 404, 444, 428, 413],
    "noivern": [406, 542, 53, 586, 355, 404, 399, 247],
    "decidueye": [662, 348, 413, 389, 404, 421, 355, 412],
    "incineroar": [394, 663, 89, 404, 370, 126, 7, 9],
    "primarina": [664, 585, 56, 58, 412, 94, 247, 57],
    "golisopod": [404, 710, 141, 389, 398, 529, 370, 404],
    "kommo-o": [691, 370, 53, 398, 337, 430, 396, 89],
    "cinderace": [780, 136, 404, 389, 428, 442, 441, 53],
    "dragapult": [337, 247, 404, 53, 85, 406, 57, 94],
    "corviknight": [413, 442, 355, 404, 776, 211, 65, 371],
    "grimmsnarl": [789, 663, 389, 583, 409, 7, 8, 9],
    "greninja-ash": [594, 399, 56, 58, 404, 326, 441, 400]
}

def get_stat(stats_array, stat_name):
    for stat in stats_array:
        if stat['stat']['name'] == stat_name:
            return stat['base_stat']
    return 0

def fetch_pokemon_and_moves():
    print("Iniciando descarga desde PokéAPI... Esto puede tomar unos segundos ⏳")
    
    os.makedirs('data', exist_ok=True)
    
    pokemon_pool = []
    moves_pool = {} 
    
    for name, target_moves in POKEMON_MOVES.items():
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
            sp_attack = get_stat(data['stats'], 'special-attack') 
            sp_defense = get_stat(data['stats'], 'special-defense') 
            speed = get_stat(data['stats'], 'speed')
            
            types = [t['type']['name'].upper() for t in data['types']]
            
            # --- EXTRAER MOVIMIENTOS ESPECÍFICOS ---
            chosen_moves_ids = []
            
            for move_id in target_moves:
                if move_id not in moves_pool:
                    # Descargar el movimiento directamente por su ID
                    move_req = requests.get(f"https://pokeapi.co/api/v2/move/{move_id}").json()
                    
                    # Manejo seguro de la data "meta" para ataques de estado
                    meta = move_req.get('meta') or {}
                    ailment = meta.get('ailment', {})
                    
                    moves_pool[move_id] = {
                        "id": move_id,
                        "name": move_req['name'],
                        # Aceptamos poder 0 para incluir ataques como Leech Seed o Rest
                        "power": move_req['power'] if move_req['power'] is not None else 0,
                        "accuracy": move_req['accuracy'] if move_req['accuracy'] is not None else 100,
                        "move_type": move_req['type']['name'].upper(),
                        "category": move_req['damage_class']['name'].upper(), # PHYSICAL, SPECIAL o STATUS
                        "max_pp": move_req['pp'],
                        "current_pp": move_req['pp'],
                        "drain": meta.get('drain', 0),
                        "healing": meta.get('healing', 0),
                        "ailment": ailment.get('name', 'NONE').upper() if ailment.get('name') != 'none' else "NONE",
                        "ailment_chance": meta.get('ailment_chance', 0)
                    }
                
                chosen_moves_ids.append(move_id)

            # --- ARMAR EL OBJETO POKÉMON ---
            pkm_obj = {
                "poke_id": data['id'],
                "name": name,
                "types": types,
                "max_hp": hp,
                "attack": attack,
                "defense": defense,
                "special_attack": sp_attack,   
                "special_defense": sp_defense, 
                "speed": speed,
                "move_ids": chosen_moves_ids 
            }
            pokemon_pool.append(pkm_obj)
            
        except Exception as e:
            print(f"❌ Error procesando {name}: {e}")

    # --- GUARDAR EN ARCHIVOS JSON ---
    with open('data/pokemon_pool.json', 'w', encoding='utf-8') as f:
        json.dump(pokemon_pool, f, indent=4)
        
    moves_list = list(moves_pool.values())
    with open('data/moves_pool.json', 'w', encoding='utf-8') as f:
        json.dump(moves_list, f, indent=4)

    print("\n✅ ¡Descarga completada con éxito!")
    print(f"-> data/pokemon_pool.json ({len(pokemon_pool)} Pokémon)")
    print(f"-> data/moves_pool.json ({len(moves_list)} Movimientos únicos)")

if __name__ == "__main__":
    fetch_pokemon_and_moves()