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
        """Decide la proxima accion del agente en funcion del estado de batalla.

        Args:
            state (BattleState): Estado actual completo de la batalla.

        Returns:
            Action: Accion legal a ejecutar (MOVE o SWITCH).
        """
        raise NotImplementedError()
