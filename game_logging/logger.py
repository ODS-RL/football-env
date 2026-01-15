import json
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from game.state import GameState
    from game.config import GameConfig


class GameLogger:
    """Logger for recording game states for replay."""

    def __init__(
        self,
        config: 'GameConfig',
        output_path: Optional[str] = None,
        log_interval: int = 1,
    ):
        """
        Initialize game logger.

        Args:
            config: Game configuration
            output_path: Path to save log file. If None, generates timestamped name.
            log_interval: Log every N ticks (1 = every tick)
        """
        self.config = config
        self.log_interval = log_interval
        self.states: List[dict] = []
        self.finalized = False

        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"game_log_{timestamp}.json"

        self.output_path = Path(output_path)

    def log_state(self, state: 'GameState') -> None:
        """Log a game state."""
        if self.finalized:
            return

        if state.tick % self.log_interval == 0:
            self.states.append(state.to_dict())

    def finalize(self) -> None:
        """Finalize and save the log."""
        if self.finalized:
            return

        self.finalized = True

        log_data = {
            'version': '1.0',
            'config': self.config.to_dict(),
            'states': self.states,
            'total_ticks': len(self.states),
        }

        with open(self.output_path, 'w') as f:
            json.dump(log_data, f)

    def get_output_path(self) -> str:
        """Get the path where log will be/was saved."""
        return str(self.output_path)


def load_game_log(path: str) -> dict:
    """Load a game log from file."""
    with open(path, 'r') as f:
        return json.load(f)
