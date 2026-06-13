"""
Entry-point principal de PokePikas. Lanza la interfaz grafica
del menu del juego.

Uso:
    python main.py
"""
import os
import sys


def main() -> None:
    """
    Configura sys.path para que los modulos de la GUI puedan
    importarse y arranca el menu principal del juego.

    Args:
        None

    Returns:
        None
    """
    project_root = os.path.abspath(os.path.dirname(__file__))
    gui_dir = os.path.join(project_root, "src", "gui")

    for path in (project_root, gui_dir):
        if path not in sys.path:
            sys.path.insert(0, path)

    from src.gui.menu import main as menu_main
    menu_main()


if __name__ == "__main__":
    main()
