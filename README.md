# PokePikas — Simulador Estratégico de Combates Pokémon

[![Python](https://img.shields.io/badge/Python-3.7%2B-blue)](https://www.python.org/)
[![Pygame](https://img.shields.io/badge/Pygame-2.6.1-green)](https://www.pygame.org/)
[![License](https://img.shields.io/badge/License-Academic-lightgrey)](#)

PokePikas es un simulador de batallas Pokémon por turnos implementado en Python con Pygame. Combina un motor de combate completo, cinco niveles de agentes de inteligencia artificial (aleatorio, heurístico, Minimax con poda alfa-beta y algoritmo genético) y una interfaz gráfica con modo historia tipo "Alto Mando". El proyecto está diseñado como plataforma reproducible para experimentar con búsqueda adversarial, optimización evolutiva y modelado heurístico de estados.

---

## Tabla de contenidos

1. [Características](#1-características)
2. [Requisitos e instalación](#2-requisitos-e-instalación)
3. [Ejecución rápida](#3-ejecución-rápida)
4. [Modos de juego](#4-modos-de-juego)
5. [Estructura del proyecto](#5-estructura-del-proyecto)
6. [Arquitectura y capas](#6-arquitectura-y-capas)
7. [Modelo de combate](#7-modelo-de-combate)
8. [Agentes de inteligencia artificial](#8-agentes-de-inteligencia-artificial)
9. [Heurísticas y optimización genética](#9-heurísticas-y-optimización-genética)
10. [Interfaz gráfica](#10-interfaz-gráfica)
11. [Simulaciones, benchmarks y resultados](#11-simulaciones-benchmarks-y-resultados)
12. [Datos y persistencia](#12-datos-y-persistencia)
13. [Reproducibilidad](#13-reproducibilidad)
14. [Limitaciones conocidas](#14-limitaciones-conocidas)
15. [Referencias](#15-referencias)

---

## 1. Características

- **30 Pokémon** con 8 movimientos modelados cada uno, cargados desde `data/pokemon_pool.json` y `data/moves_pool.json`.
- **Batallas 3 vs 3 y 4 vs 4** con motor por turnos (orden por velocidad, soporte de cambios, estados alterados, tipos con tabla completa de efectividades).
- **Cinco niveles de IA** que abarcan desde línea base aleatoria hasta búsqueda Minimax con poda alfa-beta y pesos evolucionados por algoritmo genético.
- **Modo Alto Mando** con cinco batallas consecutivas contra IAs escalonadas (L1 → L5), conservando el HP del equipo entre salas y culminando en el salón de la fama.
- **Interfaz Pygame** con menús, sprites, música, efectos elementales y animaciones de combate.
- **Suite de simulaciones paralelizadas** para comparar agentes, optimizar hiperparámetros y producir resultados reproducibles.
- **Código documentado**: cada función y módulo incluye docstring; los `__init__.py` describen el contenido del paquete.

## 2. Requisitos e instalación

### 2.1 Requisitos

- Python 3.7 o superior.
- `pip` para gestionar dependencias.
- Sistema con audio (opcional, el juego sigue funcionando si Pygame no puede inicializar el mezclador).

### 2.2 Instalación

```bash
git clone https://github.com/kuki236/PokePikas.git
cd PokePikas
pip install -r requirements.txt
```

Dependencias (`requirements.txt`):

| Paquete | Versión | Uso |
|---|---|---|
| `pygame` | 2.6.1 | Render, audio, eventos e interfaz. |
| `requests` | ≥ 2.25.0 | Descarga inicial de datos desde PokéAPI. |

Los datos (`pokemon_pool.json`, `moves_pool.json`, `level5_weights.json`) ya están versionados en `data/`, por lo que el proyecto funciona sin conexión a internet.

## 3. Ejecución rápida

### 3.1 Interfaz gráfica

```bash
python main.py
```

Equivalente directo: `python src/gui/menu.py`.

### 3.2 Simulaciones headless (sin ventana)

```bash
python simulate_ai_4.py            # Matriz competitiva L1-L4 (3v3 y 4v4)
python simulate_ai_5.py            # Torneo L5 vs L1-L4
python benchmark_l4_vs_l5.py       # Benchmark L4 vs L5 con IC 95%
```

Opciones CLI comunes: `--n` (batallas por par), `--size 3|4|both`, `--cores N`.

## 4. Modos de juego

| Modo | Descripción | IA involucrada |
|---|---|---|
| **Humano vs PC** | El jugador controla un equipo; la máquina controla el otro. | L1 a L5 elegible. |
| **PC vs PC** | Simulación automática entre dos IAs seleccionables independientemente. | L1 a L5 para ambos lados. |
| **Alto Mando** | Historia de 5 salas consecutivas (Lorelei → ... → Campeón). El equipo conserva HP y estados; entre batallas se cura y restauran PP. | IAs L1, L2, L3, L4, L5 fijas por sala. |

Dificultad: estrellas 1 a 5 mapean a `Level1Agent` ... `Level5Agent`.

## 5. Estructura del proyecto

```text
PokePikas/
├── main.py                       # Entry point gráfico
├── config.py                     # Constantes (FACTOR_K, profundidades Minimax, INF)
├── requirements.txt
├── benchmark_l4_vs_l5.py         # Benchmark directo L4 vs L5 con IC 95%
├── simulate_ai_4.py              # Matriz L1-L4 (3v3 y 4v4)
├── simulate_ai_5.py              # Torneo L5 contra L1-L4
├── src/
│   ├── core/
│   │   ├── battle_engine.py      # process_turn, determine_turn_order, estados residuales
│   │   ├── damage_calc.py        # Fórmula de daño, type chart, stat stages, ailments
│   │   └── interfaces.py         # BattleState, Action, ActionType, MoveState, PokemonState
│   ├── entities/
│   │   ├── pokemon.py            # Clase Pokemon (HP, stats, stages, to_state/from_state)
│   │   ├── move.py               # Clase Move (power, accuracy, PP, ailment, drain, healing)
│   │   └── enums.py              # PokemonType, AilmentType
│   ├── ai/
│   │   ├── base_agent.py         # Interfaz ABC para todos los agentes
│   │   ├── level1_agent.py       # Baseline aleatorio
│   │   ├── level2_agent.py       # Heurística greedy (diferencia de HP)
│   │   ├── level3_agent.py       # Minimax + α-β con heurística simple
│   │   ├── level4_agent.py       # Minimax + α-β con heurística compuesta normalizada
│   │   ├── level5_agent.py       # Level4 + pesos evolucionados por AG
│   │   ├── heuristics.py         # Funciones de evaluación puras
│   │   └── genetic_algo.py       # Algoritmo genético (elitismo, torneo, BLX-α, mutación)
│   ├── gui/
│   │   ├── menu.py               # Menú principal, selección de modo/equipo/dificultad
│   │   ├── battle_ui.py          # BattleScreen con animaciones, barras, mensajes
│   │   ├── league_room.py        # Modo Alto Mando (exploración 2D + batallas)
│   │   └── renderer.py           # Helpers de dibujo (texto, botones, barras, sprites)
│   └── utils/
│       ├── data_loader.py        # Carga JSON y crea equipos/equipos aleatorios
│       └── move_registry.py      # Singleton de DataLoader + plantillas de movimientos
├── data/
│   ├── pokemon_pool.json         # 30 Pokémon con stats y move_ids
│   ├── moves_pool.json           # 95 movimientos modelados
│   └── ai/
│       ├── level5_weights.json   # Pesos evolucionados (consumidos por Level5Agent)
│       └── level5_ga.log         # Log del último entrenamiento genético
└── assets/                       # Sprites, fondos, música, efectos elementales
```

## 6. Arquitectura y capas

El sistema se organiza en cinco capas con responsabilidades bien delimitadas:

```
┌─────────────────────────────────────────────────────┐
│ Capa de presentación   src/gui  (Pygame)            │
├─────────────────────────────────────────────────────┤
│ Capa de IA             src/ai   (5 agentes + AG)    │
├─────────────────────────────────────────────────────┤
│ Capa core              src/core (motor + interfaces)│
├─────────────────────────────────────────────────────┤
│ Capa de entidades      src/entities                │
├─────────────────────────────────────────────────────┤
│ Capa de datos          src/utils + data/*.json     │
└─────────────────────────────────────────────────────┘
```

- **Capa de datos**: JSON locales cacheados + `DataLoader` singleton por proceso.
- **Capa de entidades**: modelo de dominio (`Pokemon`, `Move`, enums).
- **Capa core**: motor de batalla, fórmula de daño, estructuras inmutables (`BattleState`).
- **Capa de IA**: agentes de decisión + heurísticas + optimizador genético.
- **Capa de presentación**: render, eventos, animaciones, transiciones.

## 7. Modelo de combate

### 7.1 Atributos modelados

Cada Pokémon cuenta con: `max_hp`, `attack`, `defense`, `special_attack`, `special_defense`, `speed`, `types` (uno o dos), `moves` (4 seleccionados al azar de un pool de 8), `stat_stages` (-6 a +6) y `status_ailment`.

### 7.2 Fórmula de daño

Implementada en `src/core/damage_calc.py:calculate_damage`:

```python
base_damage = ((atk / max(1, dfe)) * move_power) / 3.5
speed_factor = defender_spd * FACTOR_K    # FACTOR_K = 0.0 (config.py)
raw_damage  = base_damage - speed_factor
final_damage = max(1, raw_damage * type_multiplier)
```

- `atk`/`dfe` ya aplican modificadores por `stat_stages` y `ailment` (parálisis → speed × 0.5, quemadura → attack × 0.5).
- `type_multiplier` proviene de la tabla completa de efectividades (18 tipos × 18 tipos) en `TYPE_CHART`.
- **`FACTOR_K = 0.0`** desactiva el término de "esquivar" de la fórmula original de la tarea. Es una decisión de balance: mantiene la consistencia de daño cuando la IA evalúa el estado.
- El **divisor 3.5** es un factor propio de calibración que evita one-shots y mantiene las partidas en rangos de turnos razonables.

### 7.3 Resolución de turnos (`process_turn`)

1. Determina el orden por velocidad (con `priority` para movimientos de prioridad, no modelado actualmente).
2. Aplica switches primero (resetea `stat_stages`).
3. Aplica cada movimiento: chequeo de PP, ailment (sleep/freeze 40% de despertar, paralysis 25% de fallar), precisión, tipo, daño, drain, recoil, ailment_chance, multi-hit (id 594).
4. Aplica daño residual al final (burn/poison/leech-seed).
5. Detecta KOs y promueve al siguiente Pokémon vivo automáticamente.

### 7.4 Estados alterados

`NONE`, `BURN`, `POISON`, `PARALYSIS`, `SLEEP`, `FREEZE`, `CONFUSION`, `LEECH_SEED`, `SILENCE` (definidos en `entities/enums.py`).

## 8. Agentes de inteligencia artificial

Todos los agentes implementan la interfaz `BaseAgent` (`get_action(state) -> Action`).

| Nivel | Clase | Estrategia | Profundidad |
|---|---|---|---|
| **L1** | `Level1Agent` | Selección uniforme entre acciones legales. | — |
| **L2** | `Level2Agent` | Greedy: elige el movimiento que maximiza `my_hp − (opp_hp − daño)`. | 1 |
| **L3** | `Level3Agent` | Minimax con α-β. Heurística: diferencia absoluta de HP. | 2 (`AI_LEVEL3_DEPTH`) |
| **L4** | `Level4Agent` | Minimax con α-β. Heurística compuesta normalizada (HP, ALIVE, TYPE, SPEED, STATUS). Acciones pre-ordenadas por score. | 3 (`AI_LEVEL4_DEPTH`) |
| **L5** | `Level5Agent` | Mismo motor que L4, pero los pesos (`hp_balance`, `type_pressure`, `ko_pressure`, ...) son los **evolucionados por AG**. | 3 |

Las profundidades se configuran en `config.py` y son modificables sin tocar el código de los agentes.

## 9. Heurísticas y optimización genética

### 9.1 Heurísticas

| Función | Uso | Factores |
|---|---|---|
| `calculate_hp_differential_l3` | L3, terminal y hojas de Minimax L3. | `Σ HP_actual(equipo)` propio − rival. |
| `evaluate_level3_state` (en `level3_agent`) | Hojas de L3 con peso. | HP (0.8) + KO flag (0.2). |
| `evaluate_level4_state` | Hojas de L4 y L5. | HP (0.50), ALIVE (0.30), TYPE (0.15), SPEED (0.03), STATUS (0.02). |
| `_evaluate_state` (L5) | Suma ponderada de factores pre-evaluados. | Pesos leídos de `level5_weights.json`. |

Todos los factores están normalizados al rango [-1, 1] mediante `_clamp` y divisiones por `max_hp` o `team_size`.

### 9.2 Algoritmo genético (`src/ai/genetic_algo.py`)

Configuración por defecto:

- **Población**: 40 individuos.
- **Elite**: 4 mejores pasan intactos.
- **Selección**: torneo de tamaño 5.
- **Cruce**: BLX-α con α=0.25 (explora el espacio entre padres).
- **Mutación**: gaussiana con tasa 0.15 y fuerza 0.20, con *annealing* dinámico (sube si hay estancamiento).
- **Función de fitness** (`_score_battle`): 0.65·resultado + 0.15·(HP normalizado) + 0.10·(vivos) + 0.10·(velocidad de victoria).
- **Holdout**: 30% superior se re-evalúa con `battles_phase2=8`; un set dedicado de 8 escenarios contra `Level4Agent` mide generalización.
- **Paralelización**: `multiprocessing.Pool` con `cpu_count() − 1` workers. Cada worker pre-carga el `DataLoader` singleton.
- **Anclaje de PRNG**: la semilla se deriva de `(generación, escenario, batalla)` para eliminar ruido estocástico en la comparación de fitness.
- **Criterio de paro**: `patience=15` generaciones sin mejora, o `max_generations=50`.

Pesos producidos por la última corrida (ver `data/ai/level5_weights.json`):

| Gen | Factor | Valor |
|---|---|---|
| 28 | hp_balance | 3.73 |
| 28 | type_pressure | 3.87 |
| 28 | speed_pressure | 1.60 |
| 28 | status_pressure | 0.22 |
| 28 | move_pressure | 2.18 |
| 28 | switch_pressure | 2.16 |
| 28 | ko_pressure | 4.15 |
| 28 | alive_balance | 0.00 |

L5 anula `alive_balance` (lo descubrió el AG) y sobrepondera `ko_pressure` y `type_pressure`.

### 9.3 Reentrenar los pesos

#### Opción A — Directa con la configuración por defecto

El módulo ya incluye un bloque `__main__`, basta con ejecutarlo:

```bash
python -m src.ai.genetic_algo
```

Equivalente: `python src/ai/genetic_algo.py`. Usa la `GeneticConfig()` con sus valores por defecto (40 individuos, 50 generaciones, paciencia 15, etc.) y guarda el mejor resultado en `data/ai/level5_weights.json`. El log detallado se escribe en `data/ai/level5_ga.log`.

#### Opción B — Personalizada desde código

Para modificar hiperparámetros (más generaciones, otra población, distinta semilla, paralelización a medida, etc.) crea un script o usa `-c`:

```bash
python -c "from src.ai.genetic_algo import run_genetic_algorithm, GeneticConfig; \
  cfg = GeneticConfig(max_generations=80, population_size=60, patience=20, seed=42); \
  run_genetic_algorithm(cfg)"
```

Campos más relevantes de `GeneticConfig`:

| Campo | Default | Significado |
|---|---|---|
| `population_size` | 40 | Individuos por generación. |
| `elite_size` | 4 | Elitismo: los N mejores pasan intactos. |
| `mutation_rate` | 0.15 | Probabilidad de mutar cada gen. |
| `mutation_strength` | 0.20 | Desviación gaussiana de la mutación. |
| `tournament_size` | 5 | Tamaño del torneo de selección. |
| `max_generations` | 50 | Tope duro de generaciones. |
| `patience` | 15 | Generaciones sin mejora antes de paro anticipado. |
| `seed` | 42 | Semilla base para reproducibilidad. |
| `team_size` | 3 | Tamaño de los equipos en el fitness. |
| `n_cores` | `None` | Workers de `multiprocessing.Pool` (None = `cpu_count()−1`). |

## 10. Interfaz gráfica

### 10.1 Componentes

- **`menu.py`**: máquina de estados (`START`, `MODE_SELECT`, `TEAM_SELECT`, `DIFFICULTY_SELECT`, `BATTLE`, `LEAGUE`) con render condicional por estado.
- **`battle_ui.py`** (`BattleScreen`):
  - Pantalla dividida tipo DS (80% superior batalla, 20% inferior diálogo/acciones).
  - Barras de HP interpoladas con `display_hp`/`target_hp` para animación fluida.
  - Sprites frontales y traseros, animaciones de daño, faint, switches, ataques elementales (overlay PNG).
  - Transformación especial de Greninja-Ash.
  - Cuadro de diálogo con cola de mensajes.
- **`league_room.py`**: exploración 2D del Alto Mando (overworld con sprite animado) + transición automática a `BattleScreen` con conservación de HP del equipo.
- **`renderer.py`**: abstracciones reutilizables (`draw_text`, `draw_button`, `draw_health_bar`, `load_sprite`, `draw_pokemon_grid`, ...).

### 10.2 Assets incluidos

- 30 sprites frontales + 28 sprites traseros (en `assets/sprites/` y `assets/sprites_back/`).
- 5 fondos de menú/batalla + 1 fondo Alto Mando + 1 fondo Salón de la Fama.
- 5 efectos elementales (`FIRE`, `WATER`, `GRASS`, `ELECTRIC`, `DARK`).
- 3 pistas de música (`menu`, `battle`, `ikuze` para transformación) + efecto de selección.

## 11. Simulaciones, benchmarks y resultados

### 11.1 Scripts

| Script | Función | Salida |
|---|---|---|
| `simulate_ai_4.py` | Matriz competitiva L1-L2, L1-L3, L1-L4, L2-L3, L2-L4, L3-L4. | Win rate, empates, turnos promedio, tiempo. |
| `simulate_ai_5.py` | Torneo L5 contra L1, L2, L3, L4. | Win rate L5, HP restante, vivos, turnos. |
| `benchmark_l4_vs_l5.py` | Comparación directa L4 vs L5. | Win rate L5 + intervalo de confianza 95% (Wilson), desglose por perspectiva P1/P2. |

Las simulaciones paralelizan con `multiprocessing.Pool` y alternan la perspectiva P1/P2 cada batalla para eliminar el sesgo de orden de turno.

### 11.2 Resultados representativos

Datos de `data/tests/level5_vs_all_stats.json` (≈100 batallas por par):

| Matchup | Win rate L5 | Empates |
|---|---|---|
| L5 vs L1 (azar) | ≈ 83% | — |
| L5 vs L2 (greedy) | ≈ 74% | — |
| L5 vs L3 (Minimax simple) | ≈ 60% | — |
| L5 vs L4 (Minimax avanzado) | ≈ 48% | — |

`Level5Agent` domina claramente las IAs débiles y se acerca a paridad con `Level4Agent` (su referencia de entrenamiento). Las partidas promedian entre 6 y 9 turnos en escenarios 3v3/4v4.

## 12. Datos y persistencia

| Archivo | Contenido | Generado por |
|---|---|---|
| `data/pokemon_pool.json` | 30 Pokémon con stats base y pool de move_ids. | `fetch_data.py` (PokéAPI) o manual. |
| `data/moves_pool.json` | 95 movimientos con todos sus atributos. | `fetch_data.py`. |
| `data/ai/level5_weights.json` | Pesos evolucionados consumidos por L5. | `genetic_algo.py`. |
| `data/ai/level5_ga.log` | Log estructurado del último entrenamiento. | `genetic_algo.py`. |

`utils/move_registry.py` mantiene un singleton de `DataLoader` cacheado con `lru_cache(maxsize=1)` para evitar lecturas repetidas del JSON, tanto en el proceso principal como en cada worker de `multiprocessing`.

## 13. Reproducibilidad

- **Semillas deterministas**: cada llamada a `simulate_ai_*.py` fija `random.seed` con la semilla pasada por argumento, garantizando que dos ejecuciones con la misma semilla produzcan resultados idénticos.
- **PRNG anclado en AG**: las batallas de fitness usan `generation_seed * 100000 + scenario_id * 1000 + battle_idx * 2` para que la comparación entre candidatos sea justa.
- **Datos versionados**: los JSON en `data/` están commiteados; no se requiere conexión a PokéAPI para ejecutar el proyecto.
- **Versiones fijadas**: `requirements.txt` especifica versiones exactas de las dependencias críticas.

Para reproducir exactamente la suite de benchmarks:

```bash
python simulate_ai_4.py --n 200 --size both
python simulate_ai_5.py --n 200 --size both
python benchmark_l4_vs_l5.py --n 500
```

## 14. Limitaciones conocidas

- **`FACTOR_K = 0.0`** desactiva el término de esquivar de la fórmula del enunciado. Decisión de balance; podría activarse para estudiar su efecto.
- El **divisor 3.5** en la fórmula de daño es propio del proyecto (no proviene de la fórmula original de la tarea).
- Los datos están **en español** y provienen de PokéAPI; no directamente de Pokémon Showdown (aunque el esquema es compatible).
- **No hay experimento explícito** que barra `AI_LEVEL3_DEPTH` / `AI_LEVEL4_DEPTH` y reporte resultados: las profundidades son configurables, pero producir una curva profundidad vs. win rate vs. tiempo queda como trabajo futuro.
- `move.priority` no se modela en `process_turn` (se usa para bonificar en heurísticas de L4/L5 pero no altera el orden de turnos).

## 15. Referencias

- [PokéAPI](https://pokeapi.co/) — fuente original de los datos de Pokémon y movimientos.
- [Pygame](https://www.pygame.org/) — framework de rendering y audio.
- [Pokémon Showdown](https://pokemonshowdown.com/) — referencia mecánica del juego.
- Repositorio del proyecto: <https://github.com/kuki236/PokePikas>
