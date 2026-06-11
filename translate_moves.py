"""Traduce los nombres de los movimientos en data/moves_pool.json a espa\u00f1ol."""
import json

TRANSLATIONS = {
    "acrobatics": "acrobacias",
    "air-slash": "corte-aereo",
    "aura-sphere": "esfera-aura",
    "blaze-kick": "patada-llameante",
    "body-press": "planchado",
    "body-slam": "golpe-cuerpo",
    "boomburst": "estruendo",
    "brave-bird": "ave-brava",
    "bullet-punch": "puno-bala",
    "clanging-scales": "choque-escamas",
    "close-combat": "combate-cercano",
    "cross-chop": "golpe-cruzado",
    "crunch": "triturar",
    "dark-pulse": "pulso-umbrio",
    "darkest-lariat": "lariat-siniestro",
    "dazzling-gleam": "brillo-magico",
    "draco-meteor": "meteorodragon",
    "dragon-claw": "garra-dragon",
    "dragon-pulse": "pulso-dragon",
    "drain-punch": "puno-drenaje",
    "draining-kiss": "beso-drenaje",
    "drill-peck": "pico-taladro",
    "drill-run": "perforacion",
    "earthquake": "terremoto",
    "energy-ball": "energia-bola",
    "extrasensory": "extrasensible",
    "extreme-speed": "velocidad-extrema",
    "fire-blast": "llamarada",
    "fire-fang": "colmillo-igneo",
    "fire-punch": "puno-igneo",
    "flame-charge": "carga-llamas",
    "flamethrower": "lanzallamas",
    "flare-blitz": "envite-igneo",
    "flash-cannon": "canon-flash",
    "flying-press": "presion-voladora",
    "focus-blast": "onda-certera",
    "giga-drain": "gigadrenado",
    "gunk-shot": "bazuca-lodo",
    "hammer-arm": "brazo-martillo",
    "heavy-slam": "golpe-pesado",
    "hex": "maleficio",
    "high-horsepower": "alta-potencia",
    "high-jump-kick": "patada-salto-alta",
    "hurricane": "huracan",
    "hydro-pump": "hidrobomba",
    "hyper-voice": "voz-arrolladora",
    "ice-beam": "rayo-hielo",
    "ice-punch": "puno-hielo",
    "iron-head": "cabezazo-hierro",
    "leaf-blade": "hoja-aguda",
    "leaf-storm": "tormenta-foliar",
    "leech-life": "chupavidas",
    "leech-seed": "drenadoras",
    "liquidation": "liquidacion",
    "mach-punch": "puno-mach",
    "meteor-mash": "puno-meteoro",
    "moonblast": "fuerza-lunar",
    "muddy-water": "agua-fangosa",
    "mystical-fire": "fuego-mistico",
    "night-slash": "tajo-nocturno",
    "outrage": "ultraataque",
    "payback": "venganza",
    "play-rough": "carantona",
    "poison-jab": "puntada-toxica",
    "power-whip": "latigazo",
    "psychic": "psiquico",
    "psyshock": "psicocarga",
    "pyro-ball": "bola-de-fuego",
    "quick-attack": "ataque-rapido",
    "rapid-spin": "giro-rapido",
    "rest": "descanso",
    "roost": "respiro",
    "shadow-ball": "esfera-sombra",
    "shadow-claw": "garra-sombra",
    "sleep-powder": "polvo-sueno",
    "sludge-bomb": "bomba-lodo",
    "sparkling-aria": "aria-espumosa",
    "spirit-break": "quiebre-espiritu",
    "spirit-shackle": "grillete-espectral",
    "steel-wing": "ala-de-acero",
    "stone-edge": "filo-de-piedra",
    "sucker-punch": "golpe-bajo",
    "superpower": "superpoder",
    "surf": "surf",
    "synthesis": "sintesis",
    "thunder-punch": "puno-trueno",
    "thunderbolt": "rayo",
    "toxic": "toxico",
    "water-shuriken": "shuriken-de-agua",
    "water-spout": "surtidor",
    "waterfall": "cascada",
    "wild-charge": "carga-salvaje",
    "will-o-wisp": "fuego-fatuo",
    "x-scissor": "tijera-x",
    "zen-headbutt": "cabezazo-zen",
}

PATH = "data/moves_pool.json"
with open(PATH, "r", encoding="utf-8") as f:
    moves = json.load(f)

unmapped = []
for m in moves:
    old = m["name"]
    if old in TRANSLATIONS:
        m["name"] = TRANSLATIONS[old]
    else:
        unmapped.append(old)

if unmapped:
    print("WARNING: unmapped names:", unmapped)
    raise SystemExit(1)

with open(PATH, "w", encoding="utf-8") as f:
    json.dump(moves, f, ensure_ascii=False, indent=4)

print(f"OK: {len(moves)} movimientos traducidos.")
print("Primeros 3 ejemplos:")
for m in moves[:3]:
    print(" ", m["name"])
