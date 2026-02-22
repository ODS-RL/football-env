#!/usr/bin/env python3
"""Test script to verify the AI Football environment works correctly."""

def test_imports():
    """Test all imports work."""
    print("Testing imports...")
    from game.config import GameConfig
    from game.entities import Player, Ball, Goal
    from game.state import GameState, PlayerState, BallState, GameStatus
    from game.physics import Physics
    from agents.base import BaseAgent, Action
    from agents.random_agent import RandomAgent, ChaserAgent, GoalieAgent
    print("  All imports successful!")


def test_config():
    """Test game configuration."""
    print("Testing config...")
    from game.config import GameConfig

    config = GameConfig(players_per_team=2)
    print(f"  Field: {config.field_width}x{config.field_height}")
    print(f"  Players per team: {config.players_per_team}")
    print(f"  Max ticks: {config.max_ticks}")
    print(f"  Win score: {config.win_score}")

    positions = config.get_initial_player_positions(0)
    print(f"  Team 0 positions: {positions}")


def test_entities():
    """Test entity classes."""
    print("Testing entities...")
    from game.entities import Player, Ball, Goal

    player = Player(x=100, y=200, vx=1, vy=0, radius=20, team_id=0, player_id=0)
    print(f"  Player: pos={player.position}, vel={player.velocity}, speed={player.speed:.2f}")

    ball = Ball(x=500, y=300, vx=2, vy=3, radius=10)
    print(f"  Ball: pos={ball.position}, vel={ball.velocity}, speed={ball.speed:.2f}")

    goal = Goal(x=0, y=300, width=10, height=120, team_id=0)
    print(f"  Goal: center=({goal.x}, {goal.y}), bounds=({goal.left}, {goal.top}) to ({goal.right}, {goal.bottom})")


def test_physics():
    """Test physics engine."""
    print("Testing physics...")
    from game.config import GameConfig
    from game.entities import Player, Ball
    from game.physics import Physics

    config = GameConfig()
    physics = Physics(config)

    player = Player(x=100, y=200, vx=0, vy=0, radius=20, team_id=0, player_id=0)
    physics.apply_acceleration(player, 0.5, 0.3)
    print(f"  After acceleration: vel=({player.vx:.2f}, {player.vy:.2f})")

    ball = Ball(x=500, y=300, vx=5, vy=0, radius=10)
    physics.update_positions([player], ball)
    print(f"  After position update: ball at ({ball.x:.1f}, {ball.y:.1f})")


def test_physics_state_validity():
    """Test that physics always produces valid state."""
    import math
    import random
    from game.config import GameConfig
    from game.entities import Player, Ball, Goal
    from game.physics import Physics

    print("Testing physics state validity...")
    config = GameConfig()
    physics = Physics(config)

    def create_goals():
        goal_y = config.field_height / 2
        return [
            Goal(x=0, y=goal_y, width=config.goal_width, height=config.goal_height, team_id=0),
            Goal(x=config.field_width, y=goal_y, width=config.goal_width, height=config.goal_height, team_id=1),
        ]

    # Test 1: Overlapping entities get separated
    print("  Test 1: Overlapping entities...")
    p1 = Player(x=100, y=100, vx=0, vy=0, radius=20, team_id=0, player_id=0)
    p2 = Player(x=110, y=100, vx=0, vy=0, radius=20, team_id=1, player_id=0)  # Overlapping!
    ball = Ball(x=500, y=300, vx=0, vy=0, radius=10)
    physics.handle_all_collisions([p1, p2], ball, create_goals())
    assert physics.validate_state([p1, p2], ball), "State should be valid after collision handling"

    # Test 2: Entity outside boundary gets pushed in
    print("  Test 2: Boundary enforcement...")
    player = Player(x=-50, y=300, vx=0, vy=0, radius=20, team_id=0, player_id=0)
    ball = Ball(x=500, y=300, vx=0, vy=0, radius=10)
    physics.handle_all_collisions([player], ball, create_goals())
    assert physics.validate_state([player], ball), "State should be valid after boundary enforcement"
    assert player.x >= player.radius, f"Player should be inside field, got x={player.x}"

    # Test 3: Corner region enforcement
    print("  Test 3: Corner enforcement...")
    player = Player(x=10, y=10, vx=0, vy=0, radius=20, team_id=0, player_id=0)  # In corner
    ball = Ball(x=500, y=300, vx=0, vy=0, radius=10)
    physics.handle_all_collisions([player], ball, create_goals())
    assert physics.validate_state([player], ball), "State should be valid in corner"

    # Test 4: Multiple overlapping entities (pile-up)
    print("  Test 4: Multiple overlapping entities...")
    players = [
        Player(x=100, y=100, vx=0, vy=0, radius=20, team_id=0, player_id=0),
        Player(x=105, y=100, vx=0, vy=0, radius=20, team_id=0, player_id=1),
        Player(x=100, y=105, vx=0, vy=0, radius=20, team_id=1, player_id=0),
        Player(x=105, y=105, vx=0, vy=0, radius=20, team_id=1, player_id=1),
    ]
    ball = Ball(x=102, y=102, vx=0, vy=0, radius=10)  # Ball in the middle!
    physics.handle_all_collisions(players, ball, create_goals())
    assert physics.validate_state(players, ball), "State should be valid after pile-up resolution"

    # Test 5: High-speed collisions
    print("  Test 5: High-speed scenario...")
    player = Player(x=100, y=300, vx=5, vy=0, radius=20, team_id=0, player_id=0)
    ball = Ball(x=130, y=300, vx=-15, vy=0, radius=10)  # Coming at each other fast
    physics.handle_all_collisions([player], ball, create_goals())
    assert physics.validate_state([player], ball), "State should be valid after high-speed collision"

    # Test 6: Ball and player in corner
    print("  Test 6: Corner pile-up...")
    player = Player(x=30, y=30, vx=-2, vy=-2, radius=20, team_id=0, player_id=0)
    ball = Ball(x=25, y=25, vx=-5, vy=-5, radius=10)
    physics.handle_all_collisions([player], ball, create_goals())
    assert physics.validate_state([player], ball), "State should be valid in corner pile-up"

    # Test 7: Random stress test
    print("  Test 7: Random stress test (100 scenarios)...")
    random.seed(42)  # Reproducible
    for i in range(100):
        players = []
        for team in range(2):
            for pid in range(2):
                players.append(Player(
                    x=random.uniform(0, config.field_width),
                    y=random.uniform(0, config.field_height),
                    vx=random.uniform(-5, 5),
                    vy=random.uniform(-5, 5),
                    radius=config.player_radius,
                    team_id=team,
                    player_id=pid
                ))
        ball = Ball(
            x=random.uniform(0, config.field_width),
            y=random.uniform(0, config.field_height),
            vx=random.uniform(-15, 15),
            vy=random.uniform(-15, 15),
            radius=config.ball_radius
        )
        physics.handle_all_collisions(players, ball, create_goals())
        assert physics.validate_state(players, ball), f"State should be valid in random scenario {i}"

    print("  All state validity tests passed!")


def test_physics_determinism():
    """Test that physics is deterministic - same inputs always produce same outputs."""
    print("Testing physics determinism...")
    from game.config import GameConfig
    from game.entities import Player, Ball, Goal
    from game.physics import Physics

    config = GameConfig()

    def create_scenario():
        """Create identical starting scenario."""
        players = [
            Player(x=100, y=100, vx=3, vy=2, radius=20, team_id=0, player_id=0),
            Player(x=150, y=120, vx=-2, vy=1, radius=20, team_id=1, player_id=0),
        ]
        ball = Ball(x=120, y=110, vx=-5, vy=3, radius=10)
        goals = [
            Goal(x=0, y=300, width=10, height=120, team_id=0),
            Goal(x=1000, y=300, width=10, height=120, team_id=1),
        ]
        return players, ball, goals

    # Run scenario twice
    physics1 = Physics(config)
    players1, ball1, goals1 = create_scenario()
    physics1.handle_all_collisions(players1, ball1, goals1)

    physics2 = Physics(config)
    players2, ball2, goals2 = create_scenario()
    physics2.handle_all_collisions(players2, ball2, goals2)

    # Compare results
    for i, (p1, p2) in enumerate(zip(players1, players2)):
        assert p1.x == p2.x, f"Player {i} x mismatch: {p1.x} != {p2.x}"
        assert p1.y == p2.y, f"Player {i} y mismatch: {p1.y} != {p2.y}"
        assert p1.vx == p2.vx, f"Player {i} vx mismatch: {p1.vx} != {p2.vx}"
        assert p1.vy == p2.vy, f"Player {i} vy mismatch: {p1.vy} != {p2.vy}"

    assert ball1.x == ball2.x, f"Ball x mismatch: {ball1.x} != {ball2.x}"
    assert ball1.y == ball2.y, f"Ball y mismatch: {ball1.y} != {ball2.y}"
    assert ball1.vx == ball2.vx, f"Ball vx mismatch: {ball1.vx} != {ball2.vx}"
    assert ball1.vy == ball2.vy, f"Ball vy mismatch: {ball1.vy} != {ball2.vy}"

    print("  Determinism verified!")


def test_goal_net_physics():
    """Test that ball enters goal net properly and stops at back."""
    print("Testing goal net physics...")
    from game.config import GameConfig
    from game.entities import Player, Ball, Goal
    from game.physics import Physics

    # Use larger goal depth for clearer testing
    config = GameConfig(goal_width=30)  # 30 units deep net
    physics = Physics(config)
    goal_depth = config.goal_width
    ball_radius = config.ball_radius  # 10

    def create_goals():
        goal_y = config.field_height / 2
        return [
            Goal(x=0, y=goal_y, width=config.goal_width, height=config.goal_height, team_id=0),
            Goal(x=config.field_width, y=goal_y, width=config.goal_width, height=config.goal_height, team_id=1),
        ]

    player = Player(x=500, y=300, vx=0, vy=0, radius=20, team_id=0, player_id=0)

    # Test 1: Ball entering left goal continues into net (ball fully inside net area)
    print("  Test 1: Ball enters left goal...")
    # Ball at x=-10 with radius 10 spans from -20 to 0, which is inside goal_depth=30
    ball = Ball(x=-10, y=300, vx=-5, vy=0, radius=ball_radius)
    physics.handle_all_collisions([player], ball, create_goals())
    assert ball.x < 0, f"Ball should stay in goal area, got x={ball.x}"
    assert physics.validate_state([player], ball), "State should be valid with ball in goal"

    # Test 2: Ball stops at back of net
    print("  Test 2: Ball stops at back of net...")
    # Ball way past the back - should be pushed to back of net
    ball = Ball(x=-50, y=300, vx=-10, vy=0, radius=ball_radius)
    physics.handle_all_collisions([player], ball, create_goals())
    expected_x = -goal_depth + ball_radius  # -30 + 10 = -20
    assert ball.x >= expected_x - 0.1, f"Ball should stop at back of net (x>={expected_x}), got x={ball.x}"
    assert ball.vx == 0, f"Ball should have zero x-velocity at back of net, got vx={ball.vx}"

    # Test 3: Ball in net overlapping top edge gets pushed inside
    print("  Test 3: Ball in net pushed inside from top edge...")
    goal_top = config.field_height / 2 - config.goal_height / 2  # 240
    # Ball overlaps the top edge of goal (y - radius < goal_top)
    ball = Ball(x=-15, y=goal_top + ball_radius - 5, vx=0, vy=-10, radius=ball_radius)  # y=245, bottom edge at 235
    physics.handle_all_collisions([player], ball, create_goals())
    # Ball should be pushed down to stay inside goal opening
    assert ball.y >= goal_top + ball_radius - 0.1, f"Ball should stay inside goal height, got y={ball.y}"
    assert ball.vy == 0, f"Ball should have zero y-velocity against side netting, got vy={ball.vy}"

    # Test 4: Right goal - ball enters and stays
    print("  Test 4: Ball enters right goal...")
    ball = Ball(x=config.field_width + 10, y=300, vx=5, vy=0, radius=ball_radius)
    physics.handle_all_collisions([player], ball, create_goals())
    assert ball.x > config.field_width, f"Ball should stay in right goal area, got x={ball.x}"
    assert physics.validate_state([player], ball), "State should be valid with ball in right goal"

    # Test 5: Ball stops at back of right net
    print("  Test 5: Ball stops at back of right net...")
    ball = Ball(x=config.field_width + 50, y=300, vx=10, vy=0, radius=ball_radius)
    physics.handle_all_collisions([player], ball, create_goals())
    expected_x = config.field_width + goal_depth - ball_radius  # 1000 + 30 - 10 = 1020
    assert ball.x <= expected_x + 0.1, f"Ball should stop at back of right net (x<={expected_x}), got x={ball.x}"
    assert ball.vx == 0, f"Ball should have zero x-velocity, got vx={ball.vx}"

    print("  Goal net physics verified!")


def test_game_physics_integration():
    """Test that physics state stays valid throughout a full game."""
    print("Testing game physics integration...")
    from game.config import GameConfig
    from game.engine import Game
    from game.state import GameStatus
    from game.physics import Physics
    from agents.random_agent import ChaserAgent

    config = GameConfig(players_per_team=2, max_ticks=500)
    physics = Physics(config)

    team0 = [ChaserAgent(team_id=0, player_id=i) for i in range(config.players_per_team)]
    team1 = [ChaserAgent(team_id=1, player_id=i) for i in range(config.players_per_team)]

    game = Game(config, team0, team1)

    invalid_ticks = []
    for tick in range(config.max_ticks):
        game.step()

        # Validate state after each tick
        if not physics.validate_state(game.players, game.ball):
            invalid_ticks.append(tick)

        if game.status != GameStatus.RUNNING:
            break

    assert len(invalid_ticks) == 0, f"Invalid state at ticks: {invalid_ticks[:10]}..."
    print(f"  Game ran for {game.tick} ticks, all states valid!")


def test_game_engine():
    """Test full game engine."""
    print("Testing game engine...")
    from game.config import GameConfig
    from game.engine import Game
    from agents.random_agent import ChaserAgent

    config = GameConfig(players_per_team=2, max_ticks=100)

    team0 = [ChaserAgent(team_id=0, player_id=i) for i in range(config.players_per_team)]
    team1 = [ChaserAgent(team_id=1, player_id=i) for i in range(config.players_per_team)]

    game = Game(config, team0, team1)
    print(f"  Initial state: tick={game.tick}, score={game.score}")

    # Run a few steps
    for _ in range(10):
        game.step()

    print(f"  After 10 steps: tick={game.tick}, score={game.score}")

    state = game.get_state()
    print(f"  Ball position: ({state.ball.x:.1f}, {state.ball.y:.1f})")


def test_game_step_handles_agent_timeouts():
    """Test that slow agents don't crash the game loop on timeout."""
    print("Testing agent timeout handling...")
    import time
    from agents.base import BaseAgent, Action
    from game.config import GameConfig
    from game.engine import Game

    class SlowAgent(BaseAgent):
        def get_action(self, state):
            time.sleep(0.2)
            return Action(1.0, 1.0)

    config = GameConfig(players_per_team=1, agent_timeout_ms=10, max_ticks=5)
    game = Game(config, [SlowAgent(0, 0)], [SlowAgent(1, 0)])

    # Should not raise TimeoutError even though both agents exceed timeout.
    game.step()
    assert game.tick == 1, "Game tick should advance after a timed-out agent step"


def test_logging():
    """Test game logging."""
    print("Testing logging...")
    from game.config import GameConfig
    from game.engine import Game
    from agents.random_agent import ChaserAgent
    from game_logging.logger import GameLogger

    config = GameConfig(players_per_team=1, max_ticks=50)
    logger = GameLogger(config, output_path="test_log.json")

    team0 = [ChaserAgent(team_id=0, player_id=0)]
    team1 = [ChaserAgent(team_id=1, player_id=0)]

    game = Game(config, team0, team1, logger=logger)
    game.run()

    print(f"  Game finished: score={game.score}")
    print(f"  Log saved to: {logger.get_output_path()}")

    # Verify log can be loaded
    from game_logging.logger import load_game_log
    log_data = load_game_log("test_log.json")
    print(f"  Log contains {log_data['total_ticks']} states")


def test_agents():
    """Test different agent types."""
    print("Testing agents...")
    from game.state import GameState, PlayerState, BallState, GameStatus
    from agents.random_agent import RandomAgent, ChaserAgent, GoalieAgent

    # Create a mock state
    players = (
        PlayerState(x=250, y=300, vx=0, vy=0, team_id=0, player_id=0),
        PlayerState(x=750, y=300, vx=0, vy=0, team_id=1, player_id=0),
    )
    ball = BallState(x=500, y=300, vx=0, vy=0)
    state = GameState(
        players=players,
        ball=ball,
        score=(0, 0),
        tick=0,
        status=GameStatus.RUNNING,
        field_width=1000,
        field_height=600,
        goal_height=120,
    )

    # Test each agent type
    random_agent = RandomAgent(team_id=0, player_id=0)
    action = random_agent.get_action(state)
    print(f"  RandomAgent action: ({action.ax:.2f}, {action.ay:.2f})")

    chaser = ChaserAgent(team_id=0, player_id=0)
    action = chaser.get_action(state)
    print(f"  ChaserAgent action: ({action.ax:.2f}, {action.ay:.2f})")

    goalie = GoalieAgent(team_id=0, player_id=0)
    action = goalie.get_action(state)
    print(f"  GoalieAgent action: ({action.ax:.2f}, {action.ay:.2f})")


def main():
    print("=" * 50)
    print("AI Football Environment Test Suite")
    print("=" * 50)
    print()

    test_imports()
    print()

    test_config()
    print()

    test_entities()
    print()

    test_physics()
    print()

    test_physics_state_validity()
    print()

    test_physics_determinism()
    print()

    test_goal_net_physics()
    print()

    test_game_physics_integration()
    print()

    test_agents()
    print()

    test_game_engine()
    print()

    test_game_step_handles_agent_timeouts()
    print()

    test_logging()
    print()

    print("=" * 50)
    print("All tests passed!")
    print("=" * 50)
    print()
    print("You can now run:")
    print("  python main.py              # Run with visualization")
    print("  python main.py --no-viz     # Run without visualization")
    print("  python main.py --replay test_log.json  # Replay the test game")


if __name__ == "__main__":
    main()
