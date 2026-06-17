import os
from functools import lru_cache

from src.utils.data_loader import DataLoader

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_HERE))

DEFAULT_POKEMON_PATH = os.path.join(_PROJECT_ROOT, "data", "pokemon_pool.json")
DEFAULT_MOVES_PATH = os.path.join(_PROJECT_ROOT, "data", "moves_pool.json")


@lru_cache(maxsize=1)
def get_data_loader(
    pokemon_path: str = DEFAULT_POKEMON_PATH,
    moves_path: str = DEFAULT_MOVES_PATH,
) -> DataLoader:
    """Devuelve (y cachea) una instancia compartida de DataLoader.

    Usa `lru_cache` para que cada proceso tenga un unico DataLoader.
    Util cuando los workers de `multiprocessing.Pool` necesitan el mismo
    catalogo de movimientos sin recargar los JSON.

    Args:
        pokemon_path (str): Ruta al JSON de Pokemon.
        moves_path (str): Ruta al JSON de movimientos.

    Returns:
        DataLoader: Instancia cacheada de DataLoader.
    """
    return DataLoader(pokemon_path, moves_path)


MOVE_TEMPLATES = get_data_loader().move_templates
