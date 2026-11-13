"""Built-in ("standard") agents.

Every agent except RandomAgent is built on PlayerAgent, which provides:
- arrival steering: brake into a target instead of overshooting and
  oscillating around it
- ball prediction with friction and wall bounces
- approaching the ball from behind (relative to where it should go),
  circling around it instead of running through it
- kicks only when the resulting ball direction is useful; never toward
  the agent's own goal or straight into a nearby opponent

The engine always kicks the ball along the player -> ball line, so where a
kick goes is decided by where the player stands, not by the action.

Physics constants come from ``self.config`` (the match's GameConfig), never
from hardcoded values: physics and geometry can be re-rolled per competition.
"""
import math
from typing import TYPE_CHECKING, Optional, Tuple

from .base import BaseAgent, Action

if TYPE_CHECKING:
    from game.config import GameConfig
    from game.state import GameState, PlayerState


def _norm(x: float, y: float) -> Tuple[float, float]:
    d = math.hypot(x, y)
    return (x / d, y / d) if d > 1e-9 else (0.0, 0.0)


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _fold(v: float, lo: float, hi: float) -> Tuple[float, float]:
    """Reflect v into [lo, hi] like a bounce; returns (position, velocity sign)."""
    span = hi - lo
    if span <= 0:
        return lo, 1.0
    t = (v - lo) % (2 * span)
    if t <= span:
        return lo + t, 1.0
    return hi - (t - span), -1.0


class RandomAgent(BaseAgent):
    """Agent that takes random actions."""

    def get_action(self, state: 'GameState') -> Action:
        """Return random acceleration."""
        angle = self.rng.uniform(0, 2 * math.pi)
        magnitude = self.rng.uniform(0, self.config.player_max_acceleration)
        return Action(
            ax=math.cos(angle) * magnitude,
            ay=math.sin(angle) * magnitude,
        )


class PlayerAgent(BaseAgent):
    """Base for the standard agents: movement, ball prediction and safe kicking."""

    # Minimum forward component of the kicked ball's direction (shots on goal
    # always pass). Lower = kicks more readily.
    kick_threshold = 0.3
    # Half-angle of the cone behind the ball from which the agent charges it;
    # outside the cone it circles around the ball first.
    approach_cone = math.radians(35)
    # Clearance kept from the ball while circling it, as a fraction of the
    # player + ball contact distance
    orbit_gap = 0.5

    def __init__(self, team_id: int, player_id: int,
                 max_acceleration: Optional[float] = None, kick_range: Optional[float] = None):
        # Optional handicaps; the game's own limits apply when lower or unset
        self.acceleration_cap = max_acceleration
        self.kick_range_cap = kick_range
        super().__init__(team_id, player_id)

    def set_config(self, config: 'GameConfig') -> None:
        super().set_config(config)
        self.max_acceleration = config.player_max_acceleration
        if self.acceleration_cap is not None:
            self.max_acceleration = min(self.max_acceleration, self.acceleration_cap)
        self.kick_range = config.kick_range
        if self.kick_range_cap is not None:
            self.kick_range = min(self.kick_range, self.kick_range_cap)
        self.player_radius = config.player_radius
        self.ball_radius = config.ball_radius
        self.contact_dist = config.player_radius + config.ball_radius
        self.kick_power = config.kick_power
        self.player_friction = config.player_friction
        self.ball_friction = config.ball_friction
        # Distance per tick at full acceleration
        self.top_speed = min(config.player_max_speed,
                             self.max_acceleration / (1 - config.player_friction))
        # Distance a kick from rest rolls
        self.ball_reach = config.kick_power / (1 - config.ball_friction)
        self.orbit_radius = self.contact_dist * (1 + self.orbit_gap)

    # --- Geometry -----------------------------------------------------------

    @property
    def forward(self) -> float:
        """+1 if this team attacks toward larger x, -1 otherwise."""
        return 1.0 if self.team_id == 0 else -1.0

    def own_goal(self, state: 'GameState') -> Tuple[float, float]:
        return (0.0 if self.team_id == 0 else state.field_width, state.field_height / 2)

    def opp_goal(self, state: 'GameState') -> Tuple[float, float]:
        return (state.field_width if self.team_id == 0 else 0.0, state.field_height / 2)

    def depth(self, state: 'GameState', x: float) -> float:
        """Distance of x from our own goal line (0 = our goal, field_width = theirs)."""
        return x if self.team_id == 0 else state.field_width - x

    def x_at_depth(self, state: 'GameState', depth: float) -> float:
        return depth if self.team_id == 0 else state.field_width - depth

    # --- Movement -----------------------------------------------------------

    def steer(self, state: 'GameState', me: 'PlayerState', tx: float, ty: float,
              arrive: bool = True) -> Tuple[float, float]:
        """Acceleration toward (tx, ty).

        With arrive=True the agent slows down and stops on the target instead
        of overshooting it; otherwise it runs through at full speed.
        """
        r = self.player_radius
        tx = _clamp(tx, r, state.field_width - r)
        ty = _clamp(ty, r, state.field_height - r)
        dx, dy = tx - me.x, ty - me.y
        dist = math.hypot(dx, dy)
        if arrive:
            if dist < 1.0 and math.hypot(me.vx, me.vy) < 0.3:
                return 0.0, 0.0
            # Target speed proportional to distance. Braking (acceleration plus
            # friction) can follow that down to zero as long as the gain is at
            # most 2 * (1 - friction); higher overshoots.
            speed = min(2 * self.top_speed, dist * 2 * (1 - self.player_friction))
        else:
            speed = 2 * self.top_speed
        ux, uy = _norm(dx, dy)
        # The next move uses velocity + acceleration, so steer the velocity
        # itself (this also cancels sideways drift).
        ax, ay = ux * speed - me.vx, uy * speed - me.vy
        mag = math.hypot(ax, ay)
        if mag > self.max_acceleration:
            ax, ay = ax / mag * self.max_acceleration, ay / mag * self.max_acceleration
        return ax, ay

    # --- Ball prediction ----------------------------------------------------

    def predict_ball(self, state: 'GameState', ticks: int) -> Tuple[float, float, float, float]:
        """Ball (x, y, vx, vy) after `ticks` ticks, with friction and wall bounces."""
        ball = state.ball
        decay = self.ball_friction ** ticks
        travel = (1 - decay) / (1 - self.ball_friction)
        r = self.ball_radius
        x, sx = _fold(ball.x + ball.vx * travel, r, state.field_width - r)
        y, sy = _fold(ball.y + ball.vy * travel, r, state.field_height - r)
        return x, y, ball.vx * decay * sx, ball.vy * decay * sy

    def ticks_to_reach(self, p: 'PlayerState', x: float, y: float) -> float:
        """Rough ticks for player p to touch a ball at (x, y), including speeding up."""
        dx, dy = x - p.x, y - p.y
        dist = math.hypot(dx, dy)
        gap = dist - self.contact_dist
        if gap <= 0:
            return 0.0
        # Speeding up takes about one velocity time constant, less when
        # already moving that way (and more when moving away)
        toward = (p.vx * dx + p.vy * dy) / dist
        ramp = 0.7 / (1 - self.player_friction) * _clamp(1 - toward / self.top_speed, 0.0, 2.0)
        return gap / self.top_speed + ramp

    def intercept(self, state: 'GameState', p: 'PlayerState',
                  horizon: int = 90) -> Tuple[float, float, float, float, int]:
        """Earliest predicted ball position player p can get to in time."""
        for t in range(0, horizon + 1, 3):
            x, y, vx, vy = self.predict_ball(state, t)
            if self.ticks_to_reach(p, x, y) + 3 <= t or t == horizon:
                return x, y, vx, vy, t
        return self.predict_ball(state, horizon) + (horizon,)

    def ball_eta(self, state: 'GameState', p: 'PlayerState') -> int:
        return self.intercept(state, p)[4]

    def first_to_ball(self, state: 'GameState', me: 'PlayerState', margin: float = 0.0) -> bool:
        """True if no teammate gets to the ball more than `margin` ticks sooner."""
        mine = self.ball_eta(state, me)
        return all(self.ball_eta(state, t) + margin >= mine for t in self.get_teammates(state))

    def opponents_first(self, state: 'GameState', me: 'PlayerState', margin: float = 0.0) -> bool:
        """True if some opponent gets to the ball more than `margin` ticks sooner."""
        mine = self.ball_eta(state, me)
        return any(self.ball_eta(state, o) + margin < mine for o in self.get_opponents(state))

    # --- Kicking ------------------------------------------------------------

    def heads_into_goal(self, state: 'GameState', x: float, y: float, dx: float, dy: float,
                        goal_x: float, margin: float, max_dist: float = math.inf) -> bool:
        """Whether a ball at (x, y) moving along (dx, dy) crosses goal_x inside the goal mouth."""
        if abs(dx) < 1e-6:
            return False
        t = (goal_x - x) / dx
        if t <= 0 or t > max_dist:
            return False
        cross_y, _ = _fold(y + dy * t, self.ball_radius, state.field_height - self.ball_radius)
        return abs(cross_y - state.field_height / 2) <= state.goal_height / 2 + margin

    def ball_pinned(self, state: 'GameState') -> bool:
        """Whether the ball is (nearly) stopped against a wall or corner."""
        b = state.ball
        if math.hypot(b.vx, b.vy) > 0.5:
            return False
        w, h = state.field_width, state.field_height
        m = self.ball_radius + 2
        if b.x < m or b.x > w - m or b.y < m or b.y > h - m:
            return True
        # Rounded corners: near the arc instead of a straight wall
        c = self.config.corner_radius
        cx = c if b.x < c else w - c if b.x > w - c else None
        cy = c if b.y < c else h - c if b.y > h - c else None
        return cx is not None and cy is not None and math.hypot(b.x - cx, b.y - cy) > c - m

    def defending(self, state: 'GameState', x: float) -> bool:
        """Whether a ball at x is deep enough in our half to clear rather than build up."""
        return self.depth(state, x) < state.field_width * 0.3

    def clearance_aim(self, state: 'GameState', bx: float, by: float) -> Tuple[float, float]:
        """Point to clear a ball at (bx, by) toward: away from our goal and upfield."""
        gx, gy = self.own_goal(state)
        rx, ry = _norm(bx - gx, by - gy)
        ux, uy = _norm(rx + self.forward, ry)
        return bx + ux * 200, by + uy * 200

    def kick_score(self, state: 'GameState', me: 'PlayerState',
                   allow_blocked: bool = False) -> Optional[float]:
        """Value of kicking now, or None if the ball is out of range or the kick is unsafe.

        2.0 for a shot on goal, otherwise how far (-1..1) the resulting ball
        direction points upfield; deep in our own half pointing away from our
        goal counts too. allow_blocked permits kicking into a nearby opponent,
        which breaks up a ball pinned against a wall between two players.
        """
        ball = state.ball
        dx, dy = ball.x - me.x, ball.y - me.y
        dist = math.hypot(dx, dy)
        if dist > self.kick_range or dist < 1e-6 or not me.can_kick():
            return None
        nx, ny = dx / dist, dy / dist
        ux, uy = _norm(ball.vx + nx * self.kick_power, ball.vy + ny * self.kick_power)
        if self.heads_into_goal(state, ball.x, ball.y, ux, uy, self.own_goal(state)[0],
                                margin=2.5 * self.ball_radius):
            return None
        # A kick straight into a nearby opponent just rebounds
        for o in ([] if allow_blocked else self.get_opponents(state)):
            ox, oy = o.x - ball.x, o.y - ball.y
            along = ox * ux + oy * uy
            if 0 < along < 3 * self.contact_dist and abs(ox * uy - oy * ux) < self.contact_dist - 4:
                return None
        if self.heads_into_goal(state, ball.x, ball.y, ux, uy, self.opp_goal(state)[0],
                                margin=-self.ball_radius, max_dist=self.ball_reach * 0.9):
            return 2.0
        score = ux * self.forward
        if self.defending(state, ball.x):
            gx, gy = self.own_goal(state)
            rx, ry = _norm(ball.x - gx, ball.y - gy)
            score = max(score, ux * rx + uy * ry)
        return score

    def wants_kick(self, state: 'GameState', me: 'PlayerState', threshold: float,
                   allow_blocked: bool = False) -> bool:
        score = self.kick_score(state, me, allow_blocked)
        return score is not None and score >= threshold

    def shot_target(self, state: 'GameState', bx: float, by: float) -> Tuple[float, float]:
        """Point in the opponent goal mouth with the clearest line from (bx, by)."""
        gx, gy = self.opp_goal(state)
        spread = state.goal_height / 2 - self.ball_radius - 8
        opponents = self.get_opponents(state)
        best, best_clear = (gx, gy), -1.0
        for ty in (gy, gy - spread, gy + spread):
            sx, sy = gx - bx, ty - by
            seg = math.hypot(sx, sy)
            clear = math.inf
            for o in opponents:
                t = _clamp(((o.x - bx) * sx + (o.y - by) * sy) / (seg * seg), 0.0, 1.0) if seg > 0 else 0.0
                clear = min(clear, math.hypot(o.x - (bx + sx * t), o.y - (by + sy * t)))
            if clear > best_clear + 15:  # Prefer the centre unless a post is clearly better
                best, best_clear = (gx, ty), clear
        return best

    # --- Ball handling ------------------------------------------------------

    def attack(self, state: 'GameState', me: 'PlayerState', aim: Optional[Tuple[float, float]] = None,
               threshold: Optional[float] = None, horizon: int = 90) -> Action:
        """Go to the ball, get behind it and kick/push it toward `aim`.

        The default aim is the goal, or a clearance when the ball is deep in
        our half (so the approach is from the safe, goal side).
        """
        bx, by, bvx, bvy, _ = self.intercept(state, me, horizon)
        if aim is None:
            if self.defending(state, bx):
                aim = self.clearance_aim(state, bx, by)
            else:
                aim = self.shot_target(state, bx, by)
        if threshold is None:
            threshold = self.kick_threshold
        ax_, ay_ = _norm(aim[0] - bx, aim[1] - by)
        nx, ny = self._contact_normal(bvx, bvy, ax_, ay_)
        px, py = -ny, nx
        rx, ry = me.x - bx, me.y - by
        along = rx * nx + ry * ny  # Negative when we are behind the ball
        lat = rx * px + ry * py
        theta = math.atan2(lat, -along)  # 0 = directly behind

        stuck = False
        if abs(theta) <= self.approach_cone:
            # Converge onto the line behind the ball, then run through it
            k = _clamp(-along * 0.5 - 5, 0.0, 2 * self.contact_dist)
            tx, ty = bx - nx * k, by - ny * k
            arrive = False
        else:
            tx, ty, stuck = self._orbit_waypoint(state, bx, by, nx, ny, theta)
            arrive = False
            if stuck:
                if self.defending(state, bx):
                    # Pinned near our goal: block the way in rather than push it in
                    gx, gy = self.own_goal(state)
                    ux, uy = _norm(gx - bx, gy - by)
                    tx, ty = bx + ux * self.contact_dist, by + uy * self.contact_dist
                    arrive = True
                else:
                    tx, ty = bx, by

        ax, ay = self.steer(state, me, tx, ty, arrive=arrive)
        # Near walls the ideal spot may be unreachable: accept rougher kicks.
        # A ball pinned against a wall may need kicking into the opponent on
        # its other side, or neither player ever moves it.
        kick = self.wants_kick(state, me, threshold - (0.6 if stuck else 0.0),
                               allow_blocked=stuck or self.ball_pinned(state))
        return Action(ax=ax, ay=ay, kick=kick)

    def _contact_normal(self, bvx: float, bvy: float, ax: float, ay: float) -> Tuple[float, float]:
        """Kick direction that sends a ball moving at (bvx, bvy) along (ax, ay)."""
        p = ax * bvx + ay * bvy
        disc = p * p - (bvx * bvx + bvy * bvy) + self.kick_power * self.kick_power
        if disc < 0:
            return ax, ay
        k = p + math.sqrt(disc)
        return _norm(k * ax - bvx, k * ay - bvy)

    def _orbit_waypoint(self, state: 'GameState', bx: float, by: float, nx: float, ny: float,
                        theta: float) -> Tuple[float, float, bool]:
        """Next point on a circle around the ball, moving toward its back side."""
        r = self.orbit_radius
        lo, hi_x, hi_y = self.player_radius, state.field_width - self.player_radius, state.field_height - self.player_radius

        def point(phi: float) -> Tuple[float, float, float]:
            x = bx - nx * r * math.cos(phi) - ny * r * math.sin(phi)
            y = by - ny * r * math.cos(phi) + nx * r * math.sin(phi)
            off = math.hypot(x - _clamp(x, lo, hi_x), y - _clamp(y, lo, hi_y))
            return x, y, off

        # Go round on the side we are already on (moving away from the front
        # keeps that choice stable)
        step = 0.9
        sign = math.copysign(1.0, theta)
        x, y, off = point(theta - sign * min(abs(theta), step))
        if off > 5:
            # Blocked by a wall: try the other way round
            ax_, ay_, aoff = point(theta + sign * step)
            if aoff <= 5:
                return ax_, ay_, False
            return x, y, True
        return x, y, False

    def opportunistic_kick(self, state: 'GameState', me: 'PlayerState', ax: float, ay: float,
                           threshold: Optional[float] = None) -> Action:
        """Positional move that still kicks if the ball happens to be well placed."""
        if threshold is None:
            threshold = self.kick_threshold
        return Action(ax=ax, ay=ay, kick=self.wants_kick(state, me, threshold))


class ChaserAgent(PlayerAgent):
    """Simple agent that chases the ball and kicks it toward goal, with noisy movement.

    noise is the size of the random acceleration added each tick, as a
    fraction of the max acceleration.
    """

    def __init__(self, team_id: int, player_id: int, max_acceleration: Optional[float] = None,
                 noise: float = 0.3, kick_range: Optional[float] = None):
        super().__init__(team_id, player_id, max_acceleration, kick_range)
        self.noise = noise

    def get_action(self, state: 'GameState') -> Action:
        me = self.get_my_player(state)
        action = self.attack(state, me, aim=self.opp_goal(state))
        n = self.noise * self.max_acceleration
        return Action(
            ax=action.ax + self.rng.uniform(-n, n),
            ay=action.ay + self.rng.uniform(-n, n),
            kick=action.kick,
        )


class GoalieAgent(PlayerAgent):
    """Stays in front of its goal, blocks shots and clears balls that come close."""

    kick_threshold = 0.1  # Any clearance away from goal will do

    def __init__(self, team_id: int, player_id: int, max_acceleration: Optional[float] = None,
                 noise: float = 0.0, kick_range: Optional[float] = None):
        super().__init__(team_id, player_id, max_acceleration, kick_range)
        self.noise = noise
        self.clearing = False

    def reset(self) -> None:
        self.clearing = False

    def get_action(self, state: 'GameState') -> Action:
        me = self.get_my_player(state)
        ball = state.ball
        gx, gy = self.own_goal(state)
        ball_dist = math.hypot(ball.x - gx, ball.y - gy)

        # Rush out to clear balls near goal if nobody else is closer; the
        # looser exit condition stops it flip-flopping between the two modes
        w = state.field_width
        if self.clearing:
            self.clearing = ball_dist < 0.23 * w and self.first_to_ball(state, me, margin=0)
        else:
            self.clearing = ball_dist < 0.17 * w and self.first_to_ball(state, me, margin=8)

        if self.clearing:
            bx, by, _, _, _ = self.intercept(state, me, 30)
            rx, ry = _norm(bx - gx, by - gy)
            action = self.attack(state, me, aim=(bx + rx * 200, by + ry * 200), horizon=30)
        else:
            tx, ty = self._guard_position(state)
            ax, ay = self.steer(state, me, tx, ty)
            action = self.opportunistic_kick(state, me, ax, ay)

        if self.noise:  # Fraction of max acceleration, as for ChaserAgent
            n = self.noise * self.max_acceleration
            return Action(ax=action.ax + self.rng.uniform(-n, n),
                          ay=action.ay + self.rng.uniform(-n, n), kick=action.kick)
        return action

    def _guard_position(self, state: 'GameState') -> Tuple[float, float]:
        ball = state.ball
        gx, gy = self.own_goal(state)
        half = state.goal_height / 2
        line_x = gx + self.forward * (self.player_radius + 4)

        # Ball heading for goal: get in its path
        if ball.vx * self.forward < -0.5 and self.heads_into_goal(
                state, ball.x, ball.y, ball.vx, ball.vy, gx, margin=self.player_radius):
            t = (gx - ball.x) / ball.vx
            cross_y, _ = _fold(ball.y + ball.vy * t, self.ball_radius, state.field_height - self.ball_radius)
            return line_x, _clamp(cross_y, gy - half, gy + half)

        # Otherwise stand on the line from goal centre to ball, covering the near post
        ux, uy = _norm(ball.x - gx, ball.y - gy)
        if ux * self.forward <= 0.05:  # Ball level with the goal line
            ux, uy = self.forward * 0.05, math.copysign(1.0, uy or 1.0)
        dist = min(0.375 * state.goal_height, math.hypot(ball.x - gx, ball.y - gy) * 0.4)
        tx = gx + ux * dist
        ty = gy + uy * dist
        if (tx - line_x) * self.forward < 0:
            tx = line_x
        return tx, _clamp(ty, gy - half + 10, gy + half - 10)


class StrikerAgent(PlayerAgent):
    """Forward: takes the ball toward goal and shoots; waits upfield while teammates defend."""

    kick_threshold = 0.45
    approach_cone = math.radians(30)

    def get_action(self, state: 'GameState') -> Action:
        me = self.get_my_player(state)
        ball = state.ball
        if (self.get_teammates(state) and self.depth(state, ball.x) < state.field_width * 0.35
                and not self.first_to_ball(state, me, margin=20)):
            # Teammates are handling it at the back: offer an outlet upfield
            tx = self.x_at_depth(state, state.field_width * 0.55)
            ty = state.field_height / 2 - (ball.y - state.field_height / 2) * 0.4
            ax, ay = self.steer(state, me, tx, ty)
            return self.opportunistic_kick(state, me, ax, ay)
        return self.attack(state, me)


class DefenderAgent(PlayerAgent):
    """Stays between ball and own goal; tackles and clears when the ball enters its half."""

    kick_threshold = 0.15

    def get_action(self, state: 'GameState') -> Action:
        me = self.get_my_player(state)
        ball = state.ball
        gx, gy = self.own_goal(state)
        ball_depth = self.depth(state, ball.x)
        near = math.hypot(ball.x - me.x, ball.y - me.y) < 3 * self.contact_dist

        if ball_depth < state.field_width * 0.55 and (near or self.first_to_ball(state, me, margin=10)):
            return self.attack(state, me)

        # Hold a spot on the ball-goal line, inside our own half
        tx = gx + (ball.x - gx) * 0.4
        ty = gy + (ball.y - gy) * 0.4
        d = _clamp(self.depth(state, tx), state.field_width * 0.12, state.field_width * 0.42)
        tx = self.x_at_depth(state, d)
        reach_y = state.field_height * 0.28
        ty = _clamp(ty, gy - reach_y, gy + reach_y)
        ax, ay = self.steer(state, me, tx, ty)
        return self.opportunistic_kick(state, me, ax, ay)


class InterceptorAgent(PlayerAgent):
    """Reads the ball's path: cuts it off goal-side when opponents get there first, else attacks."""

    def __init__(self, team_id: int, player_id: int, max_acceleration: Optional[float] = None,
                 kick_range: Optional[float] = None, prediction_ticks: int = 60):
        super().__init__(team_id, player_id, max_acceleration, kick_range)
        self.prediction_ticks = prediction_ticks

    def get_action(self, state: 'GameState') -> Action:
        me = self.get_my_player(state)
        ball = state.ball
        cover = 2.5 * self.contact_dist
        if (math.hypot(ball.x - me.x, ball.y - me.y) > cover
                and self.opponents_first(state, me, margin=10)):
            # Block the lane between the ball and our goal
            bx, by, _, _, _ = self.intercept(state, me, self.prediction_ticks)
            gx, gy = self.own_goal(state)
            ux, uy = _norm(gx - bx, gy - by)
            ax, ay = self.steer(state, me, bx + ux * cover, by + uy * cover)
            return self.opportunistic_kick(state, me, ax, ay)
        return self.attack(state, me, horizon=self.prediction_ticks)


class MidfielderAgent(PlayerAgent):
    """Covers the middle of the pitch, wins balls there and supports both ends."""

    def get_action(self, state: 'GameState') -> Action:
        me = self.get_my_player(state)
        ball = state.ball
        w, h = state.field_width, state.field_height
        ball_depth = self.depth(state, ball.x)
        in_zone = w * 0.25 <= ball_depth <= w * 0.75
        near = math.hypot(ball.x - me.x, ball.y - me.y) < w * 0.15

        if self.first_to_ball(state, me, margin=10) or (in_zone and near):
            return self.attack(state, me)

        # Support: drop back when defending, push up for rebounds when attacking
        if ball_depth < w * 0.5:
            d = _clamp(ball_depth + w * 0.12, w * 0.3, w * 0.5)
            ty = h / 2 + (ball.y - h / 2) * 0.5
        else:
            d = _clamp(ball_depth - w * 0.15, w * 0.45, w * 0.65)
            ty = h / 2 - (ball.y - h / 2) * 0.5
        ax, ay = self.steer(state, me, self.x_at_depth(state, d), ty)
        return self.opportunistic_kick(state, me, ax, ay)


class AggressorAgent(PlayerAgent):
    """Relentless ball chaser: short loops around the ball, kicks at any forward chance."""

    kick_threshold = 0.0
    approach_cone = math.radians(50)
    orbit_gap = 0.33

    def get_action(self, state: 'GameState') -> Action:
        return self.attack(state, self.get_my_player(state))


class WingerAgent(PlayerAgent):
    """Holds a flank ahead of the ball and attacks when the ball comes its way."""

    kick_threshold = 0.2

    def __init__(self, team_id: int, player_id: int, max_acceleration: Optional[float] = None,
                 kick_range: Optional[float] = None, preferred_y: float | None = None):
        super().__init__(team_id, player_id, max_acceleration, kick_range)
        self.preferred_y = preferred_y  # Top or bottom of field

    def get_action(self, state: 'GameState') -> Action:
        me = self.get_my_player(state)
        ball = state.ball
        w, h = state.field_width, state.field_height
        if self.preferred_y is not None:
            flank_y = self.preferred_y
        else:
            flank_y = h * (0.2 if self.player_id % 2 == 0 else 0.8)

        near = math.hypot(ball.x - me.x, ball.y - me.y) < w * 0.15
        if near or self.first_to_ball(state, me, margin=5):
            return self.attack(state, me)

        d = _clamp(self.depth(state, ball.x) + w * 0.1, w * 0.3, w * 0.8)
        ax, ay = self.steer(state, me, self.x_at_depth(state, d), flank_y)
        return self.opportunistic_kick(state, me, ax, ay)


# Registry of selectable agent types (name used on the command line -> class).
# Register new agents here; main.py, tournament.py and client.py all use it.
AGENT_CLASSES = {
    "random": RandomAgent,
    "chaser": ChaserAgent,
    "goalie": GoalieAgent,
    "striker": StrikerAgent,
    "defender": DefenderAgent,
    "interceptor": InterceptorAgent,
    "midfielder": MidfielderAgent,
    "aggressor": AggressorAgent,
    "winger": WingerAgent,
}
