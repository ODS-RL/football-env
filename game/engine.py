import random
import math
import weakref
from typing import List, Tuple, Optional, TYPE_CHECKING

from .agent_runner import AgentRunner
from .config import GameConfig
from .entities import Player, Ball, Goal
from .physics import Physics
from .state import GameState, GameStatus, PlayerState, BallState

if TYPE_CHECKING:
    from agents.base import BaseAgent, Action


class Game:
    def __init__(
        self,
        config: GameConfig,
        team0_agents: List['BaseAgent'],
        team1_agents: List['BaseAgent'],
        logger=None,
    ):
        self.config = config
        self.team0_agents = team0_agents
        self.team1_agents = team1_agents
        self.logger = logger
        self.physics = Physics(config)

        # All game randomness comes from this RNG; agents get child seeds so a
        # fixed config.seed reproduces the whole match.
        self.rng = random.Random(config.seed)
        for agent in team0_agents + team1_agents:
            agent_rng = getattr(agent, "rng", None)
            if isinstance(agent_rng, random.Random):
                agent_rng.seed(self.rng.getrandbits(64))
            # Each agent gets its own copy of the match parameters, so one
            # agent mutating it can't change the physics or other agents' view
            set_config = getattr(agent, "set_config", None)
            if set_config is not None:
                set_config(config.for_agents())

        # Initialize game state
        self.players: List[Player] = []
        self.ball: Ball = None
        self.goals: List[Goal] = []
        self.score: List[int] = [0, 0]
        self.tick: int = 0
        self.status: GameStatus = GameStatus.RUNNING

        # Goal celebration state (agents freeze but physics continues)
        self.goal_celebration_remaining: int = 0
        self.pending_goal_scorer: Optional[int] = None

        self._setup_game()

        # Agents run on persistent worker threads with a per-tick deadline.
        self._agent_runner = AgentRunner(team0_agents + team1_agents)
        # Also stops workers if the game is dropped before it ends.
        self._finalizer = weakref.finalize(self, self._agent_runner.close)

    def _setup_game(self) -> None:
        """Set up initial game state."""
        self._setup_players()
        self._setup_ball()
        self._setup_goals()

    def _setup_players(self) -> None:
        """Create players for both teams."""
        self.players = []

        # Team 0 (left)
        positions = self.config.get_initial_player_positions(0)
        for i, (x, y) in enumerate(positions):
            player = Player(
                x=x, y=y, vx=0.0, vy=0.0,
                radius=self.config.player_radius,
                team_id=0, player_id=i,
                mass=self.config.player_mass,
            )
            self.players.append(player)

        # Team 1 (right)
        positions = self.config.get_initial_player_positions(1)
        for i, (x, y) in enumerate(positions):
            player = Player(
                x=x, y=y, vx=0.0, vy=0.0,
                radius=self.config.player_radius,
                team_id=1, player_id=i,
                mass=self.config.player_mass,
            )
            self.players.append(player)

    def _setup_ball(self) -> None:
        """Create ball at center of field with random initial velocity."""
        x, y = self.config.get_initial_ball_position()
        # Random initial velocity
        angle = self.rng.uniform(0, 2 * math.pi)
        speed = self.rng.uniform(2.0, 5.0)
        vx = math.cos(angle) * speed
        vy = math.sin(angle) * speed
        self.ball = Ball(
            x=x, y=y, vx=vx, vy=vy,
            radius=self.config.ball_radius,
            mass=self.config.ball_mass,
        )

    def _setup_goals(self) -> None:
        """Create goals on both ends of field."""
        self.goals = [
            Goal(
                x=0,
                y=self.config.field_height / 2,
                width=self.config.goal_width,
                height=self.config.goal_height,
                team_id=0,  # Team 0 defends left goal
            ),
            Goal(
                x=self.config.field_width,
                y=self.config.field_height / 2,
                width=self.config.goal_width,
                height=self.config.goal_height,
                team_id=1,  # Team 1 defends right goal
            ),
        ]

    def get_state(self) -> GameState:
        """Get current game state snapshot."""
        player_states = tuple(
            PlayerState.from_player(p) for p in self.players
        )
        ball_state = BallState.from_ball(self.ball)

        return GameState(
            players=player_states,
            ball=ball_state,
            score=tuple(self.score),
            tick=self.tick,
            status=self.status,
            field_width=self.config.field_width,
            field_height=self.config.field_height,
            goal_height=self.config.goal_height,
        )

    def reset_positions(self) -> None:
        """Reset players and ball to initial positions after goal."""
        # Reset ball with random velocity
        x, y = self.config.get_initial_ball_position()
        angle = self.rng.uniform(0, 2 * math.pi)
        speed = self.rng.uniform(2.0, 5.0)
        self.ball.x = x
        self.ball.y = y
        self.ball.vx = math.cos(angle) * speed
        self.ball.vy = math.sin(angle) * speed

        # Reset players with slight position jitter
        team0_positions = self.config.get_initial_player_positions(0)
        team1_positions = self.config.get_initial_player_positions(1)
        jitter = 20.0  # Max position jitter

        for player in self.players:
            if player.team_id == 0:
                x, y = team0_positions[player.player_id]
            else:
                x, y = team1_positions[player.player_id]
            player.x = x + self.rng.uniform(-jitter, jitter)
            player.y = y + self.rng.uniform(-jitter, jitter)
            player.vx = 0.0
            player.vy = 0.0
            player.kick_cooldown = 0  # Reset kick cooldown

        # Notify agents of reset (deferred for agents still mid-call)
        self._agent_runner.reset_agents()

    def _process_kicks(self, actions: dict) -> None:
        """Process kick actions from all players."""
        for player in self.players:
            key = (player.team_id, player.player_id)
            action = actions.get(key)

            # Decrement cooldown
            if player.kick_cooldown > 0:
                player.kick_cooldown -= 1

            # Check if player wants to kick and can kick
            if action and action.kick and player.kick_cooldown == 0:
                # Check if ball is in range
                dx = self.ball.x - player.x
                dy = self.ball.y - player.y
                dist = math.sqrt(dx ** 2 + dy ** 2)

                if dist <= self.config.kick_range:
                    # Kick the ball - apply impulse in direction from player to ball
                    if dist > 0.001:
                        # Normalize direction
                        nx = dx / dist
                        ny = dy / dist
                        # Apply kick impulse
                        self.ball.vx += nx * self.config.kick_power
                        self.ball.vy += ny * self.config.kick_power
                    else:
                        # Ball exactly on player, kick in player's velocity direction
                        player_speed = math.sqrt(player.vx ** 2 + player.vy ** 2)
                        if player_speed > 0.001:
                            self.ball.vx += (player.vx / player_speed) * self.config.kick_power
                            self.ball.vy += (player.vy / player_speed) * self.config.kick_power

                    # Set cooldown
                    player.kick_cooldown = self.config.kick_cooldown_ticks

    def _get_agent_actions(self, state: GameState) -> dict:
        """Get actions from all agents; late or invalid answers become (0, 0)."""
        timeout_sec = self.config.agent_timeout_ms / 1000.0
        return self._agent_runner.get_actions(state, timeout_sec)

    def close(self) -> None:
        """Stop agent worker threads. Called automatically when the game ends."""
        self._finalizer()

    def _award_pending_goal(self) -> None:
        """Add the pending goal to the score and end the game on a win."""
        scorer = self.pending_goal_scorer
        if scorer is None:
            return
        self.pending_goal_scorer = None
        self.goal_celebration_remaining = 0
        self.score[scorer] += 1
        if self.score[scorer] >= self.config.win_score:
            self.status = GameStatus.ENDED

    def step(self) -> Optional[int]:
        """
        Advance game by one tick.
        Returns the scoring team on the tick a goal is detected, None otherwise.
        The score itself updates when the celebration ends (or at the time limit).
        """
        if self.status != GameStatus.RUNNING:
            return None

        state = self.get_state()

        # Log state if logger is present
        if self.logger:
            self.logger.log_state(state)

        scoring_team = None

        # Check if we're in goal celebration phase
        if self.goal_celebration_remaining > 0:
            # Agents are frozen - only update physics (ball continues moving)
            self.physics.update_positions(self.players, self.ball)
            self.physics.handle_all_collisions(self.players, self.ball, self.goals)

            self.goal_celebration_remaining -= 1

            # Celebration ended - update score and reset
            if self.goal_celebration_remaining == 0 and self.pending_goal_scorer is not None:
                self._award_pending_goal()
                self.reset_positions()
        else:
            # Normal gameplay - get actions from agents
            actions = self._get_agent_actions(state)

            # Apply actions to players
            for player in self.players:
                key = (player.team_id, player.player_id)
                action = actions.get(key)
                if action:
                    self.physics.apply_acceleration(player, action.ax, action.ay)

            # Process kicks (before physics update so kick applies before collisions)
            self._process_kicks(actions)

            # Update physics
            self.physics.update_positions(self.players, self.ball)
            self.physics.handle_all_collisions(self.players, self.ball, self.goals)

            # Check for goal
            detected_scorer = self.physics.check_goal(self.ball, self.goals)
            if detected_scorer is not None:
                # Start celebration phase - freeze agents but keep env active
                self.goal_celebration_remaining = self.config.goal_celebration_ticks
                self.pending_goal_scorer = detected_scorer
                scoring_team = detected_scorer
                if self.goal_celebration_remaining <= 0:
                    # No celebration configured: count it right away
                    self._award_pending_goal()
                    self.reset_positions()

        # Advance tick
        self.tick += 1

        # Check time limit; a goal still celebrating at the whistle counts
        if self.tick >= self.config.max_ticks and self.status == GameStatus.RUNNING:
            self._award_pending_goal()
            self.status = GameStatus.ENDED

        if self.status == GameStatus.ENDED:
            self.close()

        return scoring_team

    def run(self) -> Tuple[int, int]:
        """Run game until completion. Returns final score."""
        while self.status == GameStatus.RUNNING:
            self.step()

        # Log final state
        if self.logger:
            self.logger.log_state(self.get_state())
            self.logger.finalize()

        return tuple(self.score)

    def get_winner(self) -> Optional[int]:
        """Get winning team (0 or 1), or None if tie/ongoing."""
        if self.status != GameStatus.ENDED:
            return None
        if self.score[0] > self.score[1]:
            return 0
        elif self.score[1] > self.score[0]:
            return 1
        return None
