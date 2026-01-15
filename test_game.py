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

    test_agents()
    print()

    test_game_engine()
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
