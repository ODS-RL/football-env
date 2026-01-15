import math
from typing import List, Optional

from .config import GameConfig
from .entities import Player, Ball, Goal


class Physics:
    def __init__(self, config: GameConfig):
        self.config = config

    def apply_acceleration(self, player: Player, ax: float, ay: float) -> None:
        """Apply acceleration to a player, clamping to max values."""
        max_acc = self.config.player_max_acceleration
        acc_mag = math.sqrt(ax ** 2 + ay ** 2)
        if acc_mag > max_acc:
            ax = ax / acc_mag * max_acc
            ay = ay / acc_mag * max_acc

        player.vx += ax
        player.vy += ay
        self._clamp_velocity(player, self.config.player_max_speed)

    def _clamp_velocity(self, entity, max_speed: float) -> None:
        """Clamp entity velocity to max speed."""
        speed = math.sqrt(entity.vx ** 2 + entity.vy ** 2)
        if speed > max_speed:
            entity.vx = entity.vx / speed * max_speed
            entity.vy = entity.vy / speed * max_speed

    def update_positions(self, players: List[Player], ball: Ball) -> None:
        """Update all entity positions based on velocities."""
        for player in players:
            player.x += player.vx
            player.y += player.vy

        ball.x += ball.vx
        ball.y += ball.vy

        # Apply friction to ball
        ball.vx *= self.config.ball_friction
        ball.vy *= self.config.ball_friction
        self._clamp_velocity(ball, self.config.ball_max_speed)

    def _is_in_corner_region(self, x: float, y: float) -> Optional[tuple]:
        """
        Check if position is in a corner region.
        Returns (corner_center_x, corner_center_y) if in corner, None otherwise.
        """
        field_w = self.config.field_width
        field_h = self.config.field_height
        corner_r = self.config.corner_radius

        corners = [
            (corner_r, corner_r),                      # Top-left
            (field_w - corner_r, corner_r),           # Top-right
            (corner_r, field_h - corner_r),           # Bottom-left
            (field_w - corner_r, field_h - corner_r), # Bottom-right
        ]

        # Check each corner
        if x < corner_r and y < corner_r:
            return corners[0]
        elif x > field_w - corner_r and y < corner_r:
            return corners[1]
        elif x < corner_r and y > field_h - corner_r:
            return corners[2]
        elif x > field_w - corner_r and y > field_h - corner_r:
            return corners[3]

        return None

    def _enforce_boundary(self, entity, radius: float, is_ball: bool = False) -> None:
        """Enforce that entity stays within field boundaries."""
        field_w = self.config.field_width
        field_h = self.config.field_height
        corner_r = self.config.corner_radius
        restitution = 0.8 if is_ball else 0.5

        # Goal area check for ball
        goal_top = field_h / 2 - self.config.goal_height / 2
        goal_bottom = field_h / 2 + self.config.goal_height / 2

        # Check if in corner region
        corner = self._is_in_corner_region(entity.x, entity.y)

        if corner is not None:
            cx, cy = corner
            # Distance from corner center
            dx = entity.x - cx
            dy = entity.y - cy
            dist = math.sqrt(dx ** 2 + dy ** 2)

            # In corner region, entity must be CLOSER to corner center than corner_r
            # (the playable area is inside the quarter circle)
            max_dist = corner_r - radius

            if dist > max_dist:
                # Entity is outside playable area, push toward corner center
                if dist > 0.001:
                    nx = dx / dist
                    ny = dy / dist
                    entity.x = cx + nx * max_dist
                    entity.y = cy + ny * max_dist

                    # Reflect velocity
                    dot = entity.vx * nx + entity.vy * ny
                    if dot > 0:  # Moving away from center (toward corner)
                        entity.vx -= 2 * dot * nx * restitution
                        entity.vy -= 2 * dot * ny * restitution
                else:
                    # At center, valid position
                    pass
            return  # Corner handled, skip wall checks

        # Standard wall boundaries (only for non-corner regions)
        # Left wall
        if entity.x - radius < 0:
            if not is_ball or not (goal_top <= entity.y <= goal_bottom):
                entity.x = radius
                if entity.vx < 0:
                    entity.vx = -entity.vx * restitution

        # Right wall
        if entity.x + radius > field_w:
            if not is_ball or not (goal_top <= entity.y <= goal_bottom):
                entity.x = field_w - radius
                if entity.vx > 0:
                    entity.vx = -entity.vx * restitution

        # Top wall
        if entity.y - radius < 0:
            entity.y = radius
            if entity.vy < 0:
                entity.vy = -entity.vy * restitution

        # Bottom wall
        if entity.y + radius > field_h:
            entity.y = field_h - radius
            if entity.vy > 0:
                entity.vy = -entity.vy * restitution

    def _resolve_circle_collision(self, e1, r1: float, e2, r2: float,
                                   m1: float, m2: float, restitution: float) -> bool:
        """
        Resolve collision between two circular entities.
        Returns True if collision was resolved.
        """
        dx = e2.x - e1.x
        dy = e2.y - e1.y
        dist = math.sqrt(dx ** 2 + dy ** 2)
        min_dist = r1 + r2

        if dist >= min_dist:
            return False  # No collision

        if dist < 0.001:
            # Overlapping centers, push apart arbitrarily
            dx, dy, dist = 1.0, 0.0, 1.0

        # Normalize
        nx = dx / dist
        ny = dy / dist

        # Separate the entities (push apart)
        overlap = min_dist - dist
        total_mass = m1 + m2
        e1.x -= nx * overlap * (m2 / total_mass)
        e1.y -= ny * overlap * (m2 / total_mass)
        e2.x += nx * overlap * (m1 / total_mass)
        e2.y += ny * overlap * (m1 / total_mass)

        # Relative velocity
        dvx = e2.vx - e1.vx
        dvy = e2.vy - e1.vy
        dvn = dvx * nx + dvy * ny

        # Only resolve if moving toward each other
        if dvn < 0:
            # Impulse
            j = -(1 + restitution) * dvn / (1 / m1 + 1 / m2)

            e1.vx -= j / m1 * nx
            e1.vy -= j / m1 * ny
            e2.vx += j / m2 * nx
            e2.vy += j / m2 * ny

        return True

    def handle_all_collisions(self, players: List[Player], ball: Ball,
                              goals: List[Goal]) -> None:
        """Handle all collisions with multiple iterations to ensure no overlaps."""
        max_iterations = 10

        for _ in range(max_iterations):
            had_collision = False

            # Enforce boundaries for all entities
            for player in players:
                self._enforce_boundary(player, player.radius, is_ball=False)

            self._enforce_boundary(ball, ball.radius, is_ball=True)

            # Player-ball collisions
            for player in players:
                if self._resolve_circle_collision(
                    player, player.radius,
                    ball, ball.radius,
                    player.mass, ball.mass,
                    restitution=0.9
                ):
                    had_collision = True

            # Player-player collisions
            for i, p1 in enumerate(players):
                for p2 in players[i + 1:]:
                    if self._resolve_circle_collision(
                        p1, p1.radius,
                        p2, p2.radius,
                        p1.mass, p2.mass,
                        restitution=0.5
                    ):
                        had_collision = True

            # Final boundary enforcement
            for player in players:
                self._enforce_boundary(player, player.radius, is_ball=False)
            self._enforce_boundary(ball, ball.radius, is_ball=True)

            if not had_collision:
                break

    def check_goal(self, ball: Ball, goals: List[Goal]) -> Optional[int]:
        """
        Check if entire ball has crossed the goal line.
        Returns the team_id that SCORED (opponent of the goal owner), or None.
        """
        for goal in goals:
            # Check if ball is within goal height (y-range)
            if not (goal.top <= ball.y <= goal.bottom):
                continue

            # Check if entire ball has crossed the goal line
            # Left goal (team 0 defends): ball must fully cross x=0 going left
            # Right goal (team 1 defends): ball must fully cross x=field_width going right
            if goal.team_id == 0:
                # Left goal - entire ball must be past x=0
                if ball.x + ball.radius <= 0:
                    return 1 - goal.team_id
            else:
                # Right goal - entire ball must be past field width
                if ball.x - ball.radius >= self.config.field_width:
                    return 1 - goal.team_id
        return None
