"""Verifica que la traducci\u00f3n de movimientos no rompa el motor ni el process_turn."""
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils.data_loader import DataLoader
from src.entities.move import Move
from src.entities.enums import PokemonType, AilmentType
from src.core.battle_engine import process_turn
from src.core.interfaces import Action, ActionType

PATH_PKMN = "data/pokemon_pool.json"
PATH_MOV = "data/moves_pool.json"

# 1) Todos los nombres est\u00e1n en espa\u00f1ol (sin espacios, ASCII lower, con guiones)
with open(PATH_MOV, "r", encoding="utf-8") as f:
    moves = json.load(f)
print(f"[1/5] {len(moves)} movimientos cargados.")
for m in moves:
    assert " " not in m["name"], f"espacio en nombre: {m['name']}"
    assert m["name"] == m["name"].lower(), f"mayusculas: {m['name']}"
assert not any("rest" == m["name"] for m in moves), "aun queda 'rest'"
assert any("descanso" == m["name"] for m in moves), "no se encontro 'descanso'"
print("      nombres en formato slug-lowercase OK; 'rest'->'descanso' OK")

# 2) El DataLoader reconstruye los Moves sin errores
loader = DataLoader(PATH_PKMN, PATH_MOV)
rest = next(m for m in loader.move_templates.values() if m.name == "descanso")
assert isinstance(rest, Move)
assert rest.power == 0
assert rest.category == "STATUS"
print(f"[2/5] DataLoader construy\u00f3 Move('descanso') OK: power={rest.power}, type={rest.move_type.value}")

# 3) Cargar dos pokemones aleatorios y ejecutar una batalla corta
p1_team = loader.generate_random_team(2)
p2_team = loader.generate_random_team(2)
print(f"[3/5] Equipos generados: {[p.name for p in p1_team]} vs {[p.name for p in p2_team]}")

# Mostrar nombres de sus movimientos para confirmar que est\u00e1n en espa\u00f1ol
all_moves_es = []
for p in p1_team + p2_team:
    for mv in p.moves:
        all_moves_es.append(mv.name)
print(f"      Movs en batalla: {all_moves_es}")
for n in all_moves_es:
    assert " " not in n, f"movimiento con espacios: {n}"

# 4) Forzar que un pokemon use 'descanso' y verificar que el motor lo trata como REST
from src.entities.move import Move
import copy
forzar = None
for p in p1_team:
    if p.moves and p.current_hp > 0 and not p.is_fainted():
        forzar = p
        break
assert forzar is not None
m_descanso = next(m for m in loader.move_templates.values() if m.name == "descanso")
forzar.moves = [copy.deepcopy(m_descanso)]
forzar.moves[0].current_pp = 1
forzar.current_hp = 1  # casi muerto
print(f"[4/5] {forzar.name} forzado a usar 'descanso' (HP=1)")

p1_active = 0
p2_active = 0
turn = 0
descanso_funciono = False
while turn < 50:
    turn += 1
    p1_action = Action(type=ActionType.MOVE, target_index=0)
    p2_action = Action(type=ActionType.MOVE, target_index=0)
    result, p1_active, p2_active = process_turn(
        p1_team, p1_active, p1_action,
        p2_team, p2_active, p2_action
    )
    # Verificar que en alg\u00fan outcome aparezca el id del move descanso
    for out in result.outcomes:
        if out.action_type == ActionType.MOVE and out.action_id == m_descanso.id:
            descanso_funciono = True
            print(f"      -> Turno {turn}: 'descanso' (id={m_descanso.id}) ejecutado. HP restante: {out.attacker_hp_remaining}")
    if result.match_over:
        break

assert descanso_funciono, "El motor NUNCA reconoci\u00f3 el movimiento 'descanso'"
print(f"[5/5] Motor reconoce 'descanso' y la batalla se jug\u00f3 OK ({turn} turnos).")
print("\n\u2705 TODO OK - traducci\u00f3n de movimientos no rompe el motor.")
