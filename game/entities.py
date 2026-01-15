from dataclasses import dataclass
from typing import Tuple
import math


@dataclass
class Player:
    x: float
    y: float
    vx: float
    vy: float
    radius: float
    team_id: int
    player_id: int
    mass: float = 1.0
    kick_cooldown: int = 0  # Ticks until player can kick again

    @property
    def position(self) -> Tuple[float, float]:
        return (self.x, self.y)

    @property
    def velocity(self) -> Tuple[float, float]:
        return (self.vx, self.vy)

    @property
    def speed(self) -> float:
        return math.sqrt(self.vx ** 2 + self.vy ** 2)

    def to_dict(self) -> dict:
        return {
            'x': self.x,
            'y': self.y,
            'vx': self.vx,
            'vy': self.vy,
            'radius': self.radius,
            'team_id': self.team_id,
            'player_id': self.player_id,
            'mass': self.mass,
            'kick_cooldown': self.kick_cooldown,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Player':
        return cls(**data)


@dataclass
class Ball:
    x: float
    y: float
    vx: float
    vy: float
    radius: float
    mass: float = 0.5

    @property
    def position(self) -> Tuple[float, float]:
        return (self.x, self.y)

    @property
    def velocity(self) -> Tuple[float, float]:
        return (self.vx, self.vy)

    @property
    def speed(self) -> float:
        return math.sqrt(self.vx ** 2 + self.vy ** 2)

    def to_dict(self) -> dict:
        return {
            'x': self.x,
            'y': self.y,
            'vx': self.vx,
            'vy': self.vy,
            'radius': self.radius,
            'mass': self.mass,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Ball':
        return cls(**data)


@dataclass
class Goal:
    x: float  # Center x position
    y: float  # Center y position
    width: float
    height: float
    team_id: int  # Which team defends this goal (0=left, 1=right)

    @property
    def left(self) -> float:
        return self.x - self.width / 2

    @property
    def right(self) -> float:
        return self.x + self.width / 2

    @property
    def top(self) -> float:
        return self.y - self.height / 2

    @property
    def bottom(self) -> float:
        return self.y + self.height / 2

    def contains_point(self, px: float, py: float) -> bool:
        """Check if a point is inside the goal area."""
        return (self.left <= px <= self.right and
                self.top <= py <= self.bottom)

    def to_dict(self) -> dict:
        return {
            'x': self.x,
            'y': self.y,
            'width': self.width,
            'height': self.height,
            'team_id': self.team_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Goal':
        return cls(**data)
