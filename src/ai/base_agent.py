from abc import ABC, abstractmethod
from src.core.interfaces import BattleState, Action


class BaseAgent(ABC):
    """Clase base abstracta para todos los agentes de combate."""

    def __init__(self, player_id: int):
        """
        Inicializa el agente con el identificador del jugador que controla.

        Args:
            player_id (int): Identificador del jugador (1 o 2).
        """
        self.player_id = player_id

    @abstractmethod
    def get_action(self, state: BattleState) -> Action:
        """Devuelve un `Action` válido según el `BattleState` recibido."""
        raise NotImplementedError()
