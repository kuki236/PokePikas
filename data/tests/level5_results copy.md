# Level5 GA quick run results

Date: 2026-05-28

Summary:
- Performed a quick genetic algorithm run to produce an initial `level5_weights.json`.
- GA config used (short run): `max_generations=3`, `battles_per_opponent=1`, `population_size=6`, `elite_size=1`, `mutation_rate=0.20`, `mutation_strength=0.25`.

Best weights saved to `data/ai/level5_weights.json` (trimmed):

```
"hp_balance": 0.3307
"alive_balance": 0.5049
"type_pressure": 0.0927
"speed_pressure": 0.0039
"status_pressure": 0.4237
"move_pressure": 0.6981
"switch_pressure": 0.4036
"ko_pressure": 0.2332
```

Metadata present in the JSON shows `generation=2` and `best_fitness=149.1` for this short run.

Sanity check:
- Ran a single headless battle `Level5Agent (P1) vs Level4Agent (P2)` with random teams; result was `winner: P2` in `8` turns.

Next steps you can run locally (longer training):

```bash
# example - longer GA run
cd PokePikas
.venv\Scripts\python.exe -c "from src.ai.genetic_algo import run_genetic_algorithm, GeneticConfig; cfg=GeneticConfig(max_generations=60, battles_per_opponent=8, population_size=48, elite_size=6); run_genetic_algorithm(cfg)"
```

Notes:
- The GA is offline-only and writes the best weights to `data/ai/level5_weights.json` as `{"weights": {...}, "metadata": {...}}`.
- `Level5Agent` loads that file on construction and falls back to defaults if missing/corrupt.

Logs:
- GA quick run output printed a candidate vector and the file was saved.
