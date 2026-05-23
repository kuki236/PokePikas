from src.utils.data_loader import DataLoader

_loader = DataLoader(
    pokemon_file_path="data/pokemon_pool.json",
    moves_file_path="data/moves_pool.json"
)

MOVE_TEMPLATES = _loader.move_templates