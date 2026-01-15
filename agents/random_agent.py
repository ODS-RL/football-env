import random
import math
from typing import TYPE_CHECKING

from .base import BaseAgent, Action

if TYPE_CHECKING:
    from game.state import GameState


class RandomAgent(BaseAgent):
    """Agent that takes random actions."""

    def get_action(self, state: 'GameState') -> Action:
        """Return random acceleration."""
        angle = random.uniform(0, 2 * math.pi)
        magnitude = random.uniform(0, 0.5)
        return Action(
            ax=math.cos(angle) * magnitude,
            ay=math.sin(angle) * magnitude,
        )


class ChaserAgent(BaseAgent):
    """Simple agent that chases the ball and kicks when close."""

    def __init__(self, team_id: int, player_id: int, max_acceleration: float = 0.5, noise: float = 0.15, kick_range: float = 40.0):
        super().__init__(team_id, player_id)
        self.max_acceleration = max_acceleration
        self.noise = noise
        self.kick_range = kick_range

    def get_action(self, state: 'GameState') -> Action:
        """Move toward the ball with some noise, kick when close."""
        me = self.get_my_player(state)
        ball = state.ball

        # Vector from player to ball
        dx = ball.x - me.x
        dy = ball.y - me.y

        # Normalize and scale
        dist = math.sqrt(dx ** 2 + dy ** 2)
        if dist > 0:
            ax = (dx / dist) * self.max_acceleration
            ay = (dy / dist) * self.max_acceleration
        else:
            ax, ay = 0.0, 0.0

        # Add noise
        ax += random.uniform(-self.noise, self.noise)
        ay += random.uniform(-self.noise, self.noise)

        # Kick if close enough and cooldown is ready
        kick = dist <= self.kick_range and me.can_kick()

        return Action(ax=ax, ay=ay, kick=kick)


class GoalieAgent(BaseAgent):
    """Simple goalie agent that stays near its goal and kicks away threats."""

    def __init__(self, team_id: int, player_id: int, max_acceleration: float = 0.5, noise: float = 0.1, kick_range: float = 40.0):
        super().__init__(team_id, player_id)
        self.max_acceleration = max_acceleration
        self.noise = noise
        self.kick_range = kick_range

    def get_action(self, state: 'GameState') -> Action:
        """Stay between ball and goal, kick when ball is close."""
        me = self.get_my_player(state)
        ball = state.ball

        # Goal position
        if self.team_id == 0:
            goal_x = 50  # Left goal area
        else:
            goal_x = state.field_width - 50  # Right goal area

        # Target y is ball's y, clamped to goal area
        goal_half_height = state.goal_height / 2
        center_y = state.field_height / 2
        target_y = max(
            center_y - goal_half_height + 20,
            min(center_y + goal_half_height - 20, ball.y)
        )

        # Move toward target position
        dx = goal_x - me.x
        dy = target_y - me.y

        dist = math.sqrt(dx ** 2 + dy ** 2)
        if dist > 0:
            ax = (dx / dist) * self.max_acceleration
            ay = (dy / dist) * self.max_acceleration
        else:
            ax, ay = 0.0, 0.0

        # Add noise
        ax += random.uniform(-self.noise, self.noise)
        ay += random.uniform(-self.noise, self.noise)

        # Kick if ball is close enough
        ball_dx = ball.x - me.x
        ball_dy = ball.y - me.y
        ball_dist = math.sqrt(ball_dx ** 2 + ball_dy ** 2)
        kick = ball_dist <= self.kick_range and me.can_kick()

        return Action(ax=ax, ay=ay, kick=kick)


class StrikerAgent(BaseAgent):
    """Aggressive forward that pushes toward opponent's goal."""

    def __init__(self, team_id: int, player_id: int, max_acceleration: float = 0.5, kick_range: float = 40.0):
        super().__init__(team_id, player_id)
        self.max_acceleration = max_acceleration
        self.kick_range = kick_range

    def get_action(self, state: 'GameState') -> Action:
        """Chase ball aggressively, kick toward opponent goal."""
        me = self.get_my_player(state)
        ball = state.ball

        # Opponent goal position
        if self.team_id == 0:
            goal_x = state.field_width  # Right goal
        else:
            goal_x = 0  # Left goal

        goal_y = state.field_height / 2

        # Distance to ball
        ball_dx = ball.x - me.x
        ball_dy = ball.y - me.y
        ball_dist = math.sqrt(ball_dx ** 2 + ball_dy ** 2)

        # If close to ball, position behind it relative to goal
        if ball_dist < 100:
            # Get behind the ball (opposite side from goal)
            goal_to_ball_x = ball.x - goal_x
            goal_to_ball_y = ball.y - goal_y
            gtb_dist = math.sqrt(goal_to_ball_x ** 2 + goal_to_ball_y ** 2)

            if gtb_dist > 0:
                # Target position is behind ball
                target_x = ball.x + (goal_to_ball_x / gtb_dist) * 30
                target_y = ball.y + (goal_to_ball_y / gtb_dist) * 30
            else:
                target_x, target_y = ball.x, ball.y
        else:
            # Chase the ball
            target_x, target_y = ball.x, ball.y

        dx = target_x - me.x
        dy = target_y - me.y
        dist = math.sqrt(dx ** 2 + dy ** 2)

        if dist > 0:
            ax = (dx / dist) * self.max_acceleration
            ay = (dy / dist) * self.max_acceleration
        else:
            ax, ay = 0.0, 0.0

        # Kick when close
        kick = ball_dist <= self.kick_range and me.can_kick()

        return Action(ax=ax, ay=ay, kick=kick)


class DefenderAgent(BaseAgent):
    """Defensive player that stays between ball and own goal."""

    def __init__(self, team_id: int, player_id: int, max_acceleration: float = 0.5, kick_range: float = 40.0):
        super().__init__(team_id, player_id)
        self.max_acceleration = max_acceleration
        self.kick_range = kick_range

    def get_action(self, state: 'GameState') -> Action:
        """Position between ball and own goal, clear when close."""
        me = self.get_my_player(state)
        ball = state.ball

        # Own goal position
        if self.team_id == 0:
            goal_x = 0
        else:
            goal_x = state.field_width

        goal_y = state.field_height / 2

        # Position on line between ball and goal, closer to goal
        ball_to_goal_x = goal_x - ball.x
        ball_to_goal_y = goal_y - ball.y
        btg_dist = math.sqrt(ball_to_goal_x ** 2 + ball_to_goal_y ** 2)

        if btg_dist > 0:
            # Position 30% of the way from ball to goal
            target_x = ball.x + ball_to_goal_x * 0.3
            target_y = ball.y + ball_to_goal_y * 0.3

            # Clamp to defensive third
            if self.team_id == 0:
                target_x = min(target_x, state.field_width * 0.4)
            else:
                target_x = max(target_x, state.field_width * 0.6)
        else:
            target_x = me.x
            target_y = me.y

        dx = target_x - me.x
        dy = target_y - me.y
        dist = math.sqrt(dx ** 2 + dy ** 2)

        if dist > 0:
            ax = (dx / dist) * self.max_acceleration
            ay = (dy / dist) * self.max_acceleration
        else:
            ax, ay = 0.0, 0.0

        # Kick if ball is close
        ball_dx = ball.x - me.x
        ball_dy = ball.y - me.y
        ball_dist = math.sqrt(ball_dx ** 2 + ball_dy ** 2)
        kick = ball_dist <= self.kick_range and me.can_kick()

        return Action(ax=ax, ay=ay, kick=kick)


class InterceptorAgent(BaseAgent):
    """Agent that predicts ball movement and intercepts."""

    def __init__(self, team_id: int, player_id: int, max_acceleration: float = 0.5, kick_range: float = 40.0, prediction_ticks: int = 20):
        super().__init__(team_id, player_id)
        self.max_acceleration = max_acceleration
        self.kick_range = kick_range
        self.prediction_ticks = prediction_ticks

    def get_action(self, state: 'GameState') -> Action:
        """Move to intercept ball based on its velocity."""
        me = self.get_my_player(state)
        ball = state.ball

        # Predict ball position
        predicted_x = ball.x + ball.vx * self.prediction_ticks
        predicted_y = ball.y + ball.vy * self.prediction_ticks

        # Clamp to field
        predicted_x = max(0, min(state.field_width, predicted_x))
        predicted_y = max(0, min(state.field_height, predicted_y))

        # Move toward predicted position
        dx = predicted_x - me.x
        dy = predicted_y - me.y
        dist = math.sqrt(dx ** 2 + dy ** 2)

        if dist > 0:
            ax = (dx / dist) * self.max_acceleration
            ay = (dy / dist) * self.max_acceleration
        else:
            ax, ay = 0.0, 0.0

        # Kick if ball is close
        ball_dx = ball.x - me.x
        ball_dy = ball.y - me.y
        ball_dist = math.sqrt(ball_dx ** 2 + ball_dy ** 2)
        kick = ball_dist <= self.kick_range and me.can_kick()

        return Action(ax=ax, ay=ay, kick=kick)


class MidfielderAgent(BaseAgent):
    """Balanced agent that supports both attack and defense."""

    def __init__(self, team_id: int, player_id: int, max_acceleration: float = 0.5, kick_range: float = 40.0):
        super().__init__(team_id, player_id)
        self.max_acceleration = max_acceleration
        self.kick_range = kick_range

    def get_action(self, state: 'GameState') -> Action:
        """Stay in midfield, support based on ball position."""
        me = self.get_my_player(state)
        ball = state.ball

        center_x = state.field_width / 2
        center_y = state.field_height / 2

        # Determine if we should attack or defend based on ball position
        if self.team_id == 0:
            # Team 0 attacks right
            attacking = ball.x > center_x
        else:
            # Team 1 attacks left
            attacking = ball.x < center_x

        if attacking:
            # Move toward ball but stay in midfield area
            target_x = ball.x
            target_y = ball.y
            # Don't go too far forward
            if self.team_id == 0:
                target_x = min(target_x, state.field_width * 0.7)
            else:
                target_x = max(target_x, state.field_width * 0.3)
        else:
            # Fall back toward center
            target_x = center_x + (50 if self.team_id == 0 else -50)
            target_y = ball.y  # Track ball vertically

        dx = target_x - me.x
        dy = target_y - me.y
        dist = math.sqrt(dx ** 2 + dy ** 2)

        if dist > 0:
            ax = (dx / dist) * self.max_acceleration
            ay = (dy / dist) * self.max_acceleration
        else:
            ax, ay = 0.0, 0.0

        # Kick if ball is close
        ball_dx = ball.x - me.x
        ball_dy = ball.y - me.y
        ball_dist = math.sqrt(ball_dx ** 2 + ball_dy ** 2)
        kick = ball_dist <= self.kick_range and me.can_kick()

        return Action(ax=ax, ay=ay, kick=kick)


class AggressorAgent(BaseAgent):
    """Very aggressive ball chaser with maximum speed."""

    def __init__(self, team_id: int, player_id: int, max_acceleration: float = 0.5, kick_range: float = 45.0):
        super().__init__(team_id, player_id)
        self.max_acceleration = max_acceleration
        self.kick_range = kick_range

    def get_action(self, state: 'GameState') -> Action:
        """Aggressively chase ball at max speed, always kick."""
        me = self.get_my_player(state)
        ball = state.ball

        # Direct chase - no subtlety
        dx = ball.x - me.x
        dy = ball.y - me.y
        dist = math.sqrt(dx ** 2 + dy ** 2)

        if dist > 0:
            # Always max acceleration toward ball
            ax = (dx / dist) * self.max_acceleration
            ay = (dy / dist) * self.max_acceleration
        else:
            ax, ay = 0.0, 0.0

        # Always try to kick when possible
        kick = dist <= self.kick_range and me.can_kick()

        return Action(ax=ax, ay=ay, kick=kick)


class WingerAgent(BaseAgent):
    """Fast agent that stays on the flanks and crosses."""

    def __init__(self, team_id: int, player_id: int, max_acceleration: float = 0.5, kick_range: float = 40.0, preferred_y: float | None = None):
        super().__init__(team_id, player_id)
        self.max_acceleration = max_acceleration
        self.kick_range = kick_range
        self.preferred_y = preferred_y  # Top or bottom of field

    def get_action(self, state: 'GameState') -> Action:
        """Stay on flanks, move forward when team has ball."""
        me = self.get_my_player(state)
        ball = state.ball

        # Determine preferred y position (top or bottom flank)
        if self.preferred_y is None:
            # Default based on player_id
            if self.player_id % 2 == 0:
                flank_y = state.field_height * 0.2  # Top
            else:
                flank_y = state.field_height * 0.8  # Bottom
        else:
            flank_y = self.preferred_y

        # X position based on ball position
        if self.team_id == 0:
            # Team 0 attacks right
            target_x = min(ball.x + 100, state.field_width * 0.8)
        else:
            # Team 1 attacks left
            target_x = max(ball.x - 100, state.field_width * 0.2)

        # If ball is close to our flank, go for it
        ball_dx = ball.x - me.x
        ball_dy = ball.y - me.y
        ball_dist = math.sqrt(ball_dx ** 2 + ball_dy ** 2)

        if ball_dist < 150:
            target_x = ball.x
            target_y = ball.y
        else:
            target_y = flank_y

        dx = target_x - me.x
        dy = target_y - me.y
        dist = math.sqrt(dx ** 2 + dy ** 2)

        if dist > 0:
            ax = (dx / dist) * self.max_acceleration
            ay = (dy / dist) * self.max_acceleration
        else:
            ax, ay = 0.0, 0.0

        kick = ball_dist <= self.kick_range and me.can_kick()

        return Action(ax=ax, ay=ay, kick=kick)
