from dataclasses import asdict, dataclass, replace
from typing import Optional, Tuple


@dataclass
class GameConfig:
    """Game rules, physics and geometry.

    Defaults are Haxball's physics scaled to a 1000-unit-wide field (x1.35):
    heavy player inertia, a ball that keeps rolling but is kicked only about
    twice as fast as a player runs, so long shots die before the goal.
    Agents get a copy of the match's config (``BaseAgent.config``); physics
    and geometry can be re-rolled per competition with ``roll_environment``.
    """

    # Field dimensions
    field_width: float = 1000.0
    field_height: float = 460.0

    # Player settings
    player_radius: float = 20.0
    player_max_speed: float = 5.0  # Hard cap; acceleration/friction set the real top speed
    player_max_acceleration: float = 0.135
    player_mass: float = 1.0
    player_friction: float = 0.96  # Velocity kept per tick: high = more inertia

    # Ball settings
    ball_radius: float = 13.0
    ball_max_speed: float = 15.0
    ball_friction: float = 0.99
    ball_mass: float = 0.5

    # Goal settings
    goal_width: float = 40.0  # Net depth (must be > ball diameter for ball to fit)
    goal_height: float = 170.0

    # Kick settings
    kick_power: float = 7.0  # Impulse applied to ball when kicked
    kick_range: float = 38.0  # Max distance from player center to ball center to kick
    kick_cooldown_ticks: int = 10  # Ticks before player can kick again (~0.17 sec)

    # Bounciness (coefficient of restitution, 0 = dead stop, 1 = perfectly elastic)
    ball_wall_restitution: float = 0.8
    player_wall_restitution: float = 0.5
    ball_player_restitution: float = 0.5
    player_player_restitution: float = 0.5

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

    # Random seed for ball kickoff, reset jitter and agent RNGs (None = random)
    seed: Optional[int] = None

    # Seed physics and geometry were rolled from (None = the defaults above)
    env_seed: Optional[int] = None

    @property
    def player_top_speed(self) -> float:
        """Distance per tick a player covers at full acceleration."""
        return min(self.player_max_speed,
                   self.player_max_acceleration / (1 - self.player_friction))

    @property
    def kick_reach(self) -> float:
        """How far a ball kicked from rest rolls before stopping."""
        return self.kick_power / (1 - self.ball_friction)

    def for_agents(self) -> 'GameConfig':
        """Copy handed to agents: everything except the seed of the game RNG."""
        return replace(self, seed=None)

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
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'GameConfig':
        """Create config from dictionary.

        Fields missing from older logs take today's defaults, which may not be
        the physics those games were played with.
        """
        return cls(**data)
