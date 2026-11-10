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
"""
import math
from typing import TYPE_CHECKING, Optional, Tuple

from .base import BaseAgent, Action

if TYPE_CHECKING:
    from game.state import GameState, PlayerState


# Physics constants mirrored from GameConfig defaults (agents only see GameState)
PLAYER_RADIUS = 20.0
BALL_RADIUS = 10.0
KICK_RANGE = 35.0
KICK_POWER = 12.0
MAX_ACCELERATION = 0.5
PLAYER_FRICTION = 0.85
BALL_FRICTION = 0.98
CONTACT_DIST = PLAYER_RADIUS + BALL_RADIUS
TOP_SPEED = MAX_ACCELERATION / (1 - PLAYER_FRICTION)  # ~3.3 units/tick at full acceleration
BALL_REACH = KICK_POWER / (1 - BALL_FRICTION)  # Distance a kick from rest rolls (~600)


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
        magnitude = self.rng.uniform(0, 0.5)
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
    orbit_radius = 45.0

    def __init__(self, team_id: int, player_id: int,
                 max_acceleration: float = MAX_ACCELERATION, kick_range: float = KICK_RANGE):
        super().__init__(team_id, player_id)
        self.max_acceleration = max_acceleration
        self.kick_range = kick_range

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
        tx = _clamp(tx, PLAYER_RADIUS, state.field_width - PLAYER_RADIUS)
        ty = _clamp(ty, PLAYER_RADIUS, state.field_height - PLAYER_RADIUS)
        dx, dy = tx - me.x, ty - me.y
        dist = math.hypot(dx, dy)
        if arrive:
            if dist < 1.0 and math.hypot(me.vx, me.vy) < 0.3:
                return 0.0, 0.0
            speed = min(2 * TOP_SPEED, dist * 0.3)
        else:
            speed = 2 * TOP_SPEED
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
        decay = BALL_FRICTION ** ticks
        travel = (1 - decay) / (1 - BALL_FRICTION)
        x, sx = _fold(ball.x + ball.vx * travel, BALL_RADIUS, state.field_width - BALL_RADIUS)
        y, sy = _fold(ball.y + ball.vy * travel, BALL_RADIUS, state.field_height - BALL_RADIUS)
        return x, y, ball.vx * decay * sx, ball.vy * decay * sy

    @staticmethod
    def ticks_to_reach(p: 'PlayerState', x: float, y: float) -> float:
        return max(0.0, math.hypot(x - p.x, y - p.y) - CONTACT_DIST) / TOP_SPEED

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
        cross_y, _ = _fold(y + dy * t, BALL_RADIUS, state.field_height - BALL_RADIUS)
        return abs(cross_y - state.field_height / 2) <= state.goal_height / 2 + margin

    def defending(self, state: 'GameState', x: float) -> bool:
        """Whether a ball at x is deep enough in our half to clear rather than build up."""
        return self.depth(state, x) < state.field_width * 0.3

    def clearance_aim(self, state: 'GameState', bx: float, by: float) -> Tuple[float, float]:
        """Point to clear a ball at (bx, by) toward: away from our goal and upfield."""
        gx, gy = self.own_goal(state)
        rx, ry = _norm(bx - gx, by - gy)
        ux, uy = _norm(rx + self.forward, ry)
        return bx + ux * 200, by + uy * 200

    def kick_score(self, state: 'GameState', me: 'PlayerState') -> Optional[float]:
        """Value of kicking now, or None if the ball is out of range or the kick is unsafe.

        2.0 for a shot on goal, otherwise how far (-1..1) the resulting ball
        direction points upfield; deep in our own half pointing away from our
        goal counts too.
        """
        ball = state.ball
        dx, dy = ball.x - me.x, ball.y - me.y
        dist = math.hypot(dx, dy)
        if dist > min(self.kick_range, KICK_RANGE) or dist < 1e-6 or not me.can_kick():
            return None
        nx, ny = dx / dist, dy / dist
        ux, uy = _norm(ball.vx + nx * KICK_POWER, ball.vy + ny * KICK_POWER)
        if self.heads_into_goal(state, ball.x, ball.y, ux, uy, self.own_goal(state)[0], margin=25):
            return None
        # A kick straight into a nearby opponent just rebounds
        for o in self.get_opponents(state):
            ox, oy = o.x - ball.x, o.y - ball.y
            along = ox * ux + oy * uy
            if 0 < along < 90 and abs(ox * uy - oy * ux) < PLAYER_RADIUS + BALL_RADIUS - 4:
                return None
        if self.heads_into_goal(state, ball.x, ball.y, ux, uy, self.opp_goal(state)[0],
                                margin=-BALL_RADIUS, max_dist=BALL_REACH * 0.9):
            return 2.0
        score = ux * self.forward
        if self.defending(state, ball.x):
            gx, gy = self.own_goal(state)
            rx, ry = _norm(ball.x - gx, ball.y - gy)
            score = max(score, ux * rx + uy * ry)
        return score

    def wants_kick(self, state: 'GameState', me: 'PlayerState', threshold: float) -> bool:
        score = self.kick_score(state, me)
        return score is not None and score >= threshold

    def shot_target(self, state: 'GameState', bx: float, by: float) -> Tuple[float, float]:
        """Point in the opponent goal mouth with the clearest line from (bx, by)."""
        gx, gy = self.opp_goal(state)
        spread = state.goal_height / 2 - BALL_RADIUS - 8
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
            k = _clamp(-along * 0.5 - 5, 0.0, 60.0)
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
                    tx, ty = bx + ux * CONTACT_DIST, by + uy * CONTACT_DIST
                    arrive = True
                else:
                    tx, ty = bx, by

        ax, ay = self.steer(state, me, tx, ty, arrive=arrive)
        # Near walls the ideal spot may be unreachable: accept rougher kicks
        kick = self.wants_kick(state, me, threshold - (0.6 if stuck else 0.0))
        return Action(ax=ax, ay=ay, kick=kick)

    @staticmethod
    def _contact_normal(bvx: float, bvy: float, ax: float, ay: float) -> Tuple[float, float]:
        """Kick direction that sends a ball moving at (bvx, bvy) along (ax, ay)."""
        p = ax * bvx + ay * bvy
        disc = p * p - (bvx * bvx + bvy * bvy) + KICK_POWER * KICK_POWER
        if disc < 0:
            return ax, ay
        k = p + math.sqrt(disc)
        return _norm(k * ax - bvx, k * ay - bvy)

    def _orbit_waypoint(self, state: 'GameState', bx: float, by: float, nx: float, ny: float,
                        theta: float) -> Tuple[float, float, bool]:
        """Next point on a circle around the ball, moving toward its back side."""
        r = self.orbit_radius
        lo, hi_x, hi_y = PLAYER_RADIUS, state.field_width - PLAYER_RADIUS, state.field_height - PLAYER_RADIUS

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
    """Simple agent that chases the ball and kicks it toward goal, with noisy movement."""

    def __init__(self, team_id: int, player_id: int, max_acceleration: float = MAX_ACCELERATION,
                 noise: float = 0.15, kick_range: float = KICK_RANGE):
        super().__init__(team_id, player_id, max_acceleration, kick_range)
        self.noise = noise

    def get_action(self, state: 'GameState') -> Action:
        me = self.get_my_player(state)
        action = self.attack(state, me, aim=self.opp_goal(state))
        return Action(
            ax=action.ax + self.rng.uniform(-self.noise, self.noise),
            ay=action.ay + self.rng.uniform(-self.noise, self.noise),
            kick=action.kick,
        )


class GoalieAgent(PlayerAgent):
    """Stays in front of its goal, blocks shots and clears balls that come close."""

    kick_threshold = 0.1  # Any clearance away from goal will do

    def __init__(self, team_id: int, player_id: int, max_acceleration: float = MAX_ACCELERATION,
                 noise: float = 0.0, kick_range: float = KICK_RANGE):
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
        if self.clearing:
            self.clearing = ball_dist < 230 and self.first_to_ball(state, me, margin=0)
        else:
            self.clearing = ball_dist < 170 and self.first_to_ball(state, me, margin=8)

        if self.clearing:
            bx, by, _, _, _ = self.intercept(state, me, 30)
            rx, ry = _norm(bx - gx, by - gy)
            action = self.attack(state, me, aim=(bx + rx * 200, by + ry * 200), horizon=30)
        else:
            tx, ty = self._guard_position(state)
            ax, ay = self.steer(state, me, tx, ty)
            action = self.opportunistic_kick(state, me, ax, ay)

        if self.noise:
            return Action(ax=action.ax + self.rng.uniform(-self.noise, self.noise),
                          ay=action.ay + self.rng.uniform(-self.noise, self.noise), kick=action.kick)
        return action

    def _guard_position(self, state: 'GameState') -> Tuple[float, float]:
        ball = state.ball
        gx, gy = self.own_goal(state)
        half = state.goal_height / 2
        line_x = gx + self.forward * (PLAYER_RADIUS + 4)

        # Ball heading for goal: get in its path
        if ball.vx * self.forward < -0.5 and self.heads_into_goal(
                state, ball.x, ball.y, ball.vx, ball.vy, gx, margin=PLAYER_RADIUS):
            t = (gx - ball.x) / ball.vx
            cross_y, _ = _fold(ball.y + ball.vy * t, BALL_RADIUS, state.field_height - BALL_RADIUS)
            return line_x, _clamp(cross_y, gy - half, gy + half)

        # Otherwise stand on the line from goal centre to ball, covering the near post
        ux, uy = _norm(ball.x - gx, ball.y - gy)
        if ux * self.forward <= 0.05:  # Ball level with the goal line
            ux, uy = self.forward * 0.05, math.copysign(1.0, uy or 1.0)
        dist = min(45.0, math.hypot(ball.x - gx, ball.y - gy) * 0.4)
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
        near = math.hypot(ball.x - me.x, ball.y - me.y) < 90

        if ball_depth < state.field_width * 0.55 and (near or self.first_to_ball(state, me, margin=10)):
            return self.attack(state, me)

        # Hold a spot on the ball-goal line, inside our own half
        tx = gx + (ball.x - gx) * 0.4
        ty = gy + (ball.y - gy) * 0.4
        d = _clamp(self.depth(state, tx), 120.0, state.field_width * 0.42)
        tx = self.x_at_depth(state, d)
        ty = _clamp(ty, gy - 170, gy + 170)
        ax, ay = self.steer(state, me, tx, ty)
        return self.opportunistic_kick(state, me, ax, ay)


class InterceptorAgent(PlayerAgent):
    """Reads the ball's path: cuts it off goal-side when opponents get there first, else attacks."""

    def __init__(self, team_id: int, player_id: int, max_acceleration: float = MAX_ACCELERATION,
                 kick_range: float = KICK_RANGE, prediction_ticks: int = 60):
        super().__init__(team_id, player_id, max_acceleration, kick_range)
        self.prediction_ticks = prediction_ticks

    def get_action(self, state: 'GameState') -> Action:
        me = self.get_my_player(state)
        ball = state.ball
        if (math.hypot(ball.x - me.x, ball.y - me.y) > 70
                and self.opponents_first(state, me, margin=10)):
            # Block the lane between the ball and our goal
            bx, by, _, _, _ = self.intercept(state, me, self.prediction_ticks)
            gx, gy = self.own_goal(state)
            ux, uy = _norm(gx - bx, gy - by)
            ax, ay = self.steer(state, me, bx + ux * 70, by + uy * 70)
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
        near = math.hypot(ball.x - me.x, ball.y - me.y) < 150

        if self.first_to_ball(state, me, margin=10) or (in_zone and near):
            return self.attack(state, me)

        # Support: drop back when defending, push up for rebounds when attacking
        if ball_depth < w * 0.5:
            d = _clamp(ball_depth + 120, w * 0.3, w * 0.5)
            ty = h / 2 + (ball.y - h / 2) * 0.5
        else:
            d = _clamp(ball_depth - 150, w * 0.45, w * 0.65)
            ty = h / 2 - (ball.y - h / 2) * 0.5
        ax, ay = self.steer(state, me, self.x_at_depth(state, d), ty)
        return self.opportunistic_kick(state, me, ax, ay)


class AggressorAgent(PlayerAgent):
    """Relentless ball chaser: short loops around the ball, kicks at any forward chance."""

    kick_threshold = 0.0
    approach_cone = math.radians(50)
    orbit_radius = 40.0

    def __init__(self, team_id: int, player_id: int, max_acceleration: float = MAX_ACCELERATION,
                 kick_range: float = KICK_RANGE):
        super().__init__(team_id, player_id, max_acceleration, kick_range)

    def get_action(self, state: 'GameState') -> Action:
        return self.attack(state, self.get_my_player(state))


class WingerAgent(PlayerAgent):
    """Holds a flank ahead of the ball and attacks when the ball comes its way."""

    kick_threshold = 0.2

    def __init__(self, team_id: int, player_id: int, max_acceleration: float = MAX_ACCELERATION,
                 kick_range: float = KICK_RANGE, preferred_y: float | None = None):
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

        near = math.hypot(ball.x - me.x, ball.y - me.y) < 150
        if near or self.first_to_ball(state, me, margin=5):
            return self.attack(state, me)

        d = _clamp(self.depth(state, ball.x) + 100, w * 0.3, w * 0.8)
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
