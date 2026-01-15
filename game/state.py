from dataclasses import dataclass
from typing import List, Tuple
from enum import Enum

from .entities import Player, Ball, Goal


class GameStatus(Enum):
    RUNNING = "running"
    ENDED = "ended"


@dataclass(frozen=True)
class PlayerState:
    x: float
    y: float
    vx: float
    vy: float
    team_id: int
    player_id: int
    kick_cooldown: int = 0  # Ticks until player can kick again

    def can_kick(self) -> bool:
        """Check if player can kick (cooldown expired)."""
        return self.kick_cooldown == 0

    def to_dict(self) -> dict:
        return {
            'x': self.x,
            'y': self.y,
            'vx': self.vx,
            'vy': self.vy,
            'team_id': self.team_id,
            'player_id': self.player_id,
            'kick_cooldown': self.kick_cooldown,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'PlayerState':
        return cls(**data)

    @classmethod
    def from_player(cls, player: Player) -> 'PlayerState':
        return cls(
            x=player.x,
            y=player.y,
            vx=player.vx,
            vy=player.vy,
            team_id=player.team_id,
            player_id=player.player_id,
            kick_cooldown=player.kick_cooldown,
        )


@dataclass(frozen=True)
class BallState:
    x: float
    y: float
    vx: float
    vy: float

    def to_dict(self) -> dict:
        return {
            'x': self.x,
            'y': self.y,
            'vx': self.vx,
            'vy': self.vy,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'BallState':
        return cls(**data)

    @classmethod
    def from_ball(cls, ball: Ball) -> 'BallState':
        return cls(
            x=ball.x,
            y=ball.y,
            vx=ball.vx,
            vy=ball.vy,
        )


@dataclass(frozen=True)
class GameState:
    players: Tuple[PlayerState, ...]
    ball: BallState
    score: Tuple[int, int]  # (team0_score, team1_score)
    tick: int
    status: GameStatus
    field_width: float
    field_height: float
    goal_height: float

    def get_player(self, team_id: int, player_id: int) -> PlayerState:
        """Get a specific player by team and player ID."""
        for p in self.players:
            if p.team_id == team_id and p.player_id == player_id:
                return p
        raise ValueError(f"Player not found: team={team_id}, player={player_id}")

    def get_team_players(self, team_id: int) -> List[PlayerState]:
        """Get all players of a team."""
        return [p for p in self.players if p.team_id == team_id]

    def to_dict(self) -> dict:
        return {
            'players': [p.to_dict() for p in self.players],
            'ball': self.ball.to_dict(),
            'score': list(self.score),
            'tick': self.tick,
            'status': self.status.value,
            'field_width': self.field_width,
            'field_height': self.field_height,
            'goal_height': self.goal_height,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'GameState':
        return cls(
            players=tuple(PlayerState.from_dict(p) for p in data['players']),
            ball=BallState.from_dict(data['ball']),
            score=tuple(data['score']),
            tick=data['tick'],
            status=GameStatus(data['status']),
            field_width=data['field_width'],
            field_height=data['field_height'],
            goal_height=data['goal_height'],
        )
