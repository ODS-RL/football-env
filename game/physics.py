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
        """Update all entity positions based on velocities.

        Speeds are clamped before moving so kicks and collision impulses can
        never carry an entity further than its max speed in one tick.
        """
        for player in players:
            self._clamp_velocity(player, self.config.player_max_speed)
            player.x += player.vx
            player.y += player.vy
            # Apply friction to players
            player.vx *= self.config.player_friction
            player.vy *= self.config.player_friction

        self._clamp_velocity(ball, self.config.ball_max_speed)
        ball.x += ball.vx
        ball.y += ball.vy

        # Apply friction to ball
        ball.vx *= self.config.ball_friction
        ball.vy *= self.config.ball_friction

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
        goal_depth = self.config.goal_width  # How deep the net goes
        restitution = (self.config.ball_wall_restitution if is_ball
                       else self.config.player_wall_restitution)

        # Goal area check for ball
        goal_top = field_h / 2 - self.config.goal_height / 2
        goal_bottom = field_h / 2 + self.config.goal_height / 2

        # Check if ball is inside a goal net area
        in_left_goal = is_ball and entity.x < 0 and (goal_top <= entity.y <= goal_bottom)
        in_right_goal = is_ball and entity.x > field_w and (goal_top <= entity.y <= goal_bottom)

        # Handle ball inside goal nets
        if in_left_goal:
            # Back of net
            if entity.x - radius < -goal_depth:
                entity.x = -goal_depth + radius
                entity.vx = 0  # Stop at back of net
            # Top of goal
            if entity.y - radius < goal_top:
                entity.y = goal_top + radius
                entity.vy = 0  # Stop against side netting
            # Bottom of goal
            if entity.y + radius > goal_bottom:
                entity.y = goal_bottom - radius
                entity.vy = 0  # Stop against side netting
            return  # Skip other boundary checks

        if in_right_goal:
            # Back of net
            if entity.x + radius > field_w + goal_depth:
                entity.x = field_w + goal_depth - radius
                entity.vx = 0  # Stop at back of net
            # Top of goal
            if entity.y - radius < goal_top:
                entity.y = goal_top + radius
                entity.vy = 0  # Stop against side netting
            # Bottom of goal
            if entity.y + radius > goal_bottom:
                entity.y = goal_bottom - radius
                entity.vy = 0  # Stop against side netting
            return  # Skip other boundary checks

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

                    # Reflect the normal component, scaled by restitution
                    # (same rule as the straight walls: v_n -> -e * v_n)
                    dot = entity.vx * nx + entity.vy * ny
                    if dot > 0:  # Moving away from center (toward corner)
                        entity.vx -= (1 + restitution) * dot * nx
                        entity.vy -= (1 + restitution) * dot * ny
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

    def _is_valid_position(self, entity, radius: float, is_ball: bool = False) -> bool:
        """Check if entity is within field boundaries."""
        field_w = self.config.field_width
        field_h = self.config.field_height
        corner_r = self.config.corner_radius
        goal_depth = self.config.goal_width

        # Goal area for ball
        goal_top = field_h / 2 - self.config.goal_height / 2
        goal_bottom = field_h / 2 + self.config.goal_height / 2

        # Check if ball is validly inside a goal net
        if is_ball:
            in_goal_y = goal_top - 0.001 <= entity.y <= goal_bottom + 0.001
            in_left_net = entity.x < 0 and entity.x - radius >= -goal_depth - 0.001
            in_right_net = entity.x > field_w and entity.x + radius <= field_w + goal_depth + 0.001
            if in_goal_y and (in_left_net or in_right_net):
                return True

        # Check corner regions
        corner = self._is_in_corner_region(entity.x, entity.y)
        if corner is not None:
            cx, cy = corner
            dx = entity.x - cx
            dy = entity.y - cy
            dist = math.sqrt(dx ** 2 + dy ** 2)
            max_dist = corner_r - radius
            if dist > max_dist + 0.001:  # Small tolerance
                return False
            return True

        # Check wall boundaries
        if entity.x - radius < -0.001:
            if not is_ball or not (goal_top <= entity.y <= goal_bottom):
                return False
        if entity.x + radius > field_w + 0.001:
            if not is_ball or not (goal_top <= entity.y <= goal_bottom):
                return False
        if entity.y - radius < -0.001:
            return False
        if entity.y + radius > field_h + 0.001:
            return False

        return True

    def _has_overlap(self, e1, r1: float, e2, r2: float) -> bool:
        """Check if two circular entities overlap."""
        dx = e2.x - e1.x
        dy = e2.y - e1.y
        dist = math.sqrt(dx ** 2 + dy ** 2)
        min_dist = r1 + r2
        return dist < min_dist - 0.001  # Small tolerance

    def validate_state(self, players: List[Player], ball: Ball) -> bool:
        """
        Validate that the current state is correct:
        - No entity overlaps
        - All entities within boundaries
        Returns True if state is valid.
        """
        # Check all entities are within boundaries
        for player in players:
            if not self._is_valid_position(player, player.radius, is_ball=False):
                return False

        if not self._is_valid_position(ball, ball.radius, is_ball=True):
            return False

        # Check no player-ball overlaps
        for player in players:
            if self._has_overlap(player, player.radius, ball, ball.radius):
                return False

        # Check no player-player overlaps
        for i, p1 in enumerate(players):
            for p2 in players[i + 1:]:
                if self._has_overlap(p1, p1.radius, p2, p2.radius):
                    return False

        return True

    def handle_all_collisions(self, players: List[Player], ball: Ball,
                              goals: List[Goal]) -> None:  # noqa: ARG002
        """Handle all collisions with iterations until state is valid."""
        max_iterations = 20  # Increased for safety

        for _ in range(max_iterations):
            # Enforce boundaries for all entities
            for player in players:
                self._enforce_boundary(player, player.radius, is_ball=False)
            self._enforce_boundary(ball, ball.radius, is_ball=True)

            # Resolve player-ball collisions
            for player in players:
                self._resolve_circle_collision(
                    player, player.radius,
                    ball, ball.radius,
                    player.mass, ball.mass,
                    restitution=self.config.ball_player_restitution
                )

            # Resolve player-player collisions
            for i, p1 in enumerate(players):
                for p2 in players[i + 1:]:
                    self._resolve_circle_collision(
                        p1, p1.radius,
                        p2, p2.radius,
                        p1.mass, p2.mass,
                        restitution=self.config.player_player_restitution
                    )

            # Final boundary enforcement
            for player in players:
                self._enforce_boundary(player, player.radius, is_ball=False)
            self._enforce_boundary(ball, ball.radius, is_ball=True)

            # Check if state is now valid
            if self.validate_state(players, ball):
                return

        # If we get here, state might still be invalid after max iterations
        # Force a valid state by clamping everything
        self._force_valid_state(players, ball)

    def _force_valid_state(self, players: List[Player], ball: Ball) -> None:
        """
        Force state to be valid when iterations don't converge.
        This is a fallback - it may not preserve perfect physics but guarantees valid state.
        """
        # First, ensure all entities are in bounds
        for player in players:
            self._enforce_boundary(player, player.radius, is_ball=False)
        self._enforce_boundary(ball, ball.radius, is_ball=True)

        # Then separate any overlapping entities by pushing them apart
        # without worrying about physics accuracy
        for _ in range(10):
            all_clear = True

            # Player-ball separation
            for player in players:
                if self._has_overlap(player, player.radius, ball, ball.radius):
                    all_clear = False
                    self._separate_entities(player, player.radius, ball, ball.radius)

            # Player-player separation
            for i, p1 in enumerate(players):
                for p2 in players[i + 1:]:
                    if self._has_overlap(p1, p1.radius, p2, p2.radius):
                        all_clear = False
                        self._separate_entities(p1, p1.radius, p2, p2.radius)

            # Re-enforce boundaries
            for player in players:
                self._enforce_boundary(player, player.radius, is_ball=False)
            self._enforce_boundary(ball, ball.radius, is_ball=True)

            if all_clear:
                break

    def _separate_entities(self, e1, r1: float, e2, r2: float) -> None:
        """Push two overlapping entities apart equally."""
        dx = e2.x - e1.x
        dy = e2.y - e1.y
        dist = math.sqrt(dx ** 2 + dy ** 2)
        min_dist = r1 + r2

        if dist < 0.001:
            dx, dy, dist = 1.0, 0.0, 1.0

        # Normalize
        nx = dx / dist
        ny = dy / dist

        # Push apart equally
        overlap = min_dist - dist + 0.01  # Extra margin
        e1.x -= nx * overlap * 0.5
        e1.y -= ny * overlap * 0.5
        e2.x += nx * overlap * 0.5
        e2.y += ny * overlap * 0.5

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
