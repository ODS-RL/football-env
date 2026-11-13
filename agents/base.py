import math
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game.config import GameConfig
    from game.state import GameState


@dataclass
class Action:
    """Agent action: acceleration vector and optional kick."""
    ax: float
    ay: float
    kick: bool = False  # Whether to attempt a kick this tick

    def __post_init__(self):
        # Ensure values are floats
        self.ax = float(self.ax)
        self.ay = float(self.ay)
        self.kick = bool(self.kick)
        # Reject inf/nan and clamp to valid range
        if not math.isfinite(self.ax):
            self.ax = 0.0
        if not math.isfinite(self.ay):
            self.ay = 0.0
        self.ax = max(-1.0, min(1.0, self.ax))
        self.ay = max(-1.0, min(1.0, self.ay))

    def to_dict(self) -> dict:
        """Serialize action to dictionary for network transmission."""
        return {
            'ax': self.ax,
            'ay': self.ay,
            'kick': self.kick,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Action':
        """Create action from dictionary."""
        return cls(
            ax=data.get('ax', 0.0),
            ay=data.get('ay', 0.0),
            kick=data.get('kick', False),
        )


class BaseAgent(ABC):
    """Base class for AI agents."""

    def __init__(self, team_id: int, player_id: int):
        """
        Initialize agent.

        Args:
            team_id: Team this agent belongs to (0 or 1)
            player_id: Player index within the team
        """
        self.team_id = team_id
        self.player_id = player_id
        # Per-agent RNG. The game reseeds it from its own seed so runs are
        # reproducible even though agents execute on parallel threads.
        self.rng = random.Random()
        # Imported here: game.engine imports this module, so a top-level
        # import of the game package from here would be circular
        from game.config import GameConfig
        self.set_config(GameConfig())

    def set_config(self, config: 'GameConfig') -> None:
        """Receive the match's physics, geometry and rules.

        The game calls this with its own config before the match starts;
        until then agents see the defaults. Physics can be randomized per
        competition (--env-seed), so read constants from ``self.config``
        rather than hardcoding them. Override to precompute derived values
        (call super).
        """
        self.config = config

    @abstractmethod
    def get_action(self, state: 'GameState') -> Action:
        """
        Compute action based on current game state.

        This method is called every tick. It must return within the
        configured timeout or a default action (0, 0) will be used.

        Args:
            state: Current game state snapshot

        Returns:
            Action with acceleration (ax, ay) to apply
        """
        pass

    def reset(self) -> None:
        """
        Called when game resets (after goal scored).

        Override to reset any internal state.
        """
        pass

    def get_my_player(self, state: 'GameState'):
        """Helper to get this agent's player state."""
        return state.get_player(self.team_id, self.player_id)

    def get_teammates(self, state: 'GameState'):
        """Helper to get teammate player states (excluding self)."""
        return [
            p for p in state.get_team_players(self.team_id)
            if p.player_id != self.player_id
        ]

    def get_opponents(self, state: 'GameState'):
        """Helper to get opponent player states."""
        return state.get_team_players(1 - self.team_id)
