from dataclasses import dataclass, field
from typing import Tuple


@dataclass
class GameConfig:
    # Field dimensions
    field_width: float = 1000.0
    field_height: float = 600.0

    # Player settings
    player_radius: float = 20.0
    player_max_speed: float = 5.0
    player_max_acceleration: float = 0.5
    player_mass: float = 1.0

    # Ball settings
    ball_radius: float = 10.0
    ball_max_speed: float = 15.0
    ball_friction: float = 0.98
    ball_mass: float = 0.5

    # Goal settings
    goal_width: float = 10.0
    goal_height: float = 120.0

    # Kick settings
    kick_power: float = 12.0  # Impulse applied to ball when kicked
    kick_range: float = 35.0  # Max distance from player center to ball center to kick
    kick_cooldown_ticks: int = 30  # Ticks before player can kick again (~0.5 sec)

    # Field corner radius (rounded corners)
    corner_radius: float = 50.0

    # Team settings
    players_per_team: int = 2

    # Game rules
    max_ticks: int = 3000  # ~50 seconds at 60 ticks/sec
    win_score: int = 5
    ticks_per_second: int = 60

    # Agent settings
    agent_timeout_ms: float = 100.0

    # Goal celebration (ticks to freeze after goal before reset)
    goal_celebration_ticks: int = 45  # ~0.75 seconds at 60 ticks/sec

    def get_goal_positions(self) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """Return (left_goal_center, right_goal_center)."""
        goal_y = self.field_height / 2
        return (0.0, goal_y), (self.field_width, goal_y)

    def get_initial_player_positions(self, team_id: int) -> list[Tuple[float, float]]:
        """Return initial positions for players of a team."""
        positions = []

        if team_id == 0:
            # Left team
            base_x = self.field_width * 0.25
        else:
            # Right team
            base_x = self.field_width * 0.75

        center_y = self.field_height / 2
        spacing = self.field_height / (self.players_per_team + 1)

        for i in range(self.players_per_team):
            y = spacing * (i + 1)
            positions.append((base_x, y))

        return positions

    def get_initial_ball_position(self) -> Tuple[float, float]:
        """Return initial ball position (center of field)."""
        return (self.field_width / 2, self.field_height / 2)

    def to_dict(self) -> dict:
        """Serialize config to dictionary."""
        return {
            'field_width': self.field_width,
            'field_height': self.field_height,
            'player_radius': self.player_radius,
            'player_max_speed': self.player_max_speed,
            'player_max_acceleration': self.player_max_acceleration,
            'player_mass': self.player_mass,
            'ball_radius': self.ball_radius,
            'ball_max_speed': self.ball_max_speed,
            'ball_friction': self.ball_friction,
            'ball_mass': self.ball_mass,
            'goal_width': self.goal_width,
            'goal_height': self.goal_height,
            'corner_radius': self.corner_radius,
            'players_per_team': self.players_per_team,
            'max_ticks': self.max_ticks,
            'win_score': self.win_score,
            'ticks_per_second': self.ticks_per_second,
            'agent_timeout_ms': self.agent_timeout_ms,
            'goal_celebration_ticks': self.goal_celebration_ticks,
            'kick_power': self.kick_power,
            'kick_range': self.kick_range,
            'kick_cooldown_ticks': self.kick_cooldown_ticks,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'GameConfig':
        """Create config from dictionary."""
        return cls(**data)
