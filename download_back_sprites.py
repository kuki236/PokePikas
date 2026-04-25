import json
import requests
import os

def download_back_sprites():
    save_dir = os.path.join('assets', 'sprites_back')
    os.makedirs(save_dir, exist_ok=True)

    try:
        with open('data/pokemon_pool.json', 'r', encoding='utf-8') as f:
            pokemon_pool = json.load(f)
    except FileNotFoundError:
        print("❌ Error: No se encontró 'data/pokemon_pool.json'.")
        return

    print(f"Iniciando descarga de {len(pokemon_pool)} sprites de espalda...")

    for pkm in pokemon_pool:
        poke_id = pkm['poke_id']
        name = pkm['name']
        
        # Fíjate que aquí agregamos "/back/" a la URL de la PokéAPI
        image_url = f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/back/{poke_id}.png"
        file_path = os.path.join(save_dir, f"{name}.png")
        
        if os.path.exists(file_path):
            print(f"⏭️  Saltando: {name}.png ya existe.")
            continue
            
        try:
            response = requests.get(image_url)
            if response.status_code == 200:
                with open(file_path, 'wb') as img_file:
                    img_file.write(response.content)
                print(f"✅ Descargado (Espalda): {name}.png")
            else:
                print(f"⚠️  No se encontró sprite de espalda para {name}")
        except Exception as e:
            print(f"❌ Error al descargar {name}: {e}")

    print(f"\n¡Listo! Revisa tu carpeta '{save_dir}'.")

if __name__ == "__main__":
    download_back_sprites()