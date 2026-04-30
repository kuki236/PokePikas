from abc import ABC, abstractmethod
from src.core.interfaces import BattleState, Action


class BaseAgent(ABC):
    def __init__(self, player_id: int):
        self.player_id = player_id

    @abstractmethod
    def get_action(self, state: BattleState) -> Action:
        """Devuelve un `Action` válido según el `BattleState` recibido."""
        raise NotImplementedError()
