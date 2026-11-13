"""Keyboard-controlled agent for human players."""

from typing import TYPE_CHECKING, Optional, Set

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

from agents.base import BaseAgent, Action

if TYPE_CHECKING:
    from game.config import GameConfig
    from game.state import GameState


class KeyboardAgent(BaseAgent):
    """Agent controlled by keyboard input, with AI fallback when not active."""

    def __init__(self, team_id: int, player_id: int, fallback_agent: Optional[BaseAgent] = None):
        self.fallback_agent = fallback_agent
        super().__init__(team_id, player_id)
        self.pressed_keys: Optional[Set[int]] = None
        self.is_active = False
        if fallback_agent is not None:
            # Share the fallback's RNG so seeding this wrapper seeds it too
            self.rng = fallback_agent.rng

    def set_config(self, config: 'GameConfig') -> None:
        """Forward the match config so the fallback AI plays the same physics."""
        super().set_config(config)
        if self.fallback_agent is not None:
            self.fallback_agent.set_config(config)

    def reset(self) -> None:
        """Forward resets so the fallback AI clears its state after goals."""
        if self.fallback_agent:
            self.fallback_agent.reset()

    def set_key_state(self, pressed_keys: Set[int]):
        """Link to renderer's key state set."""
        self.pressed_keys = pressed_keys

    def set_active(self, active: bool):
        """Set whether this agent responds to keyboard input."""
        self.is_active = active

    def get_action(self, state: 'GameState') -> Action:
        # When not active, delegate to fallback AI agent
        if not self.is_active or self.pressed_keys is None:
            if self.fallback_agent:
                return self.fallback_agent.get_action(state)
            return Action(0, 0, False)

        if not PYGAME_AVAILABLE:
            return Action(0, 0, False)

        ax, ay = 0.0, 0.0
        accel = self.config.player_max_acceleration

        if pygame.K_w in self.pressed_keys:
            ay -= accel
        if pygame.K_s in self.pressed_keys:
            ay += accel
        if pygame.K_a in self.pressed_keys:
            ax -= accel
        if pygame.K_d in self.pressed_keys:
            ax += accel

        kick = pygame.K_SPACE in self.pressed_keys
        return Action(ax, ay, kick)


class KeyboardController:
    """Manages switching between keyboard-controlled players."""

    def __init__(self, agents: list[KeyboardAgent]):
        self.agents = agents
        self.active_index = 0
        if agents:
            agents[0].set_active(True)

    def switch_next(self):
        """Switch control to the next player on the team."""
        if not self.agents:
            return
        self.agents[self.active_index].set_active(False)
        self.active_index = (self.active_index + 1) % len(self.agents)
        self.agents[self.active_index].set_active(True)

    def get_active_player_id(self) -> int:
        """Return the player_id of the currently active player."""
        if not self.agents:
            return -1
        return self.agents[self.active_index].player_id
