#!/usr/bin/env python3
"""
AI Football Competition Environment

Usage:
    python main.py                    # Run game with visualization
    python main.py --no-viz          # Run game without visualization
    python main.py --replay LOG.json # Replay a game log
    python main.py --help            # Show help
"""

import argparse
import random
import sys
from typing import List, Optional

from game.config import GameConfig
from game.engine import Game
from agents.base import BaseAgent
from agents.random_agent import (
    RandomAgent, ChaserAgent, GoalieAgent,
    StrikerAgent, DefenderAgent, InterceptorAgent,
    MidfielderAgent, AggressorAgent, WingerAgent,
)
from game_logging.logger import GameLogger


def create_agents(config: GameConfig, agent_type: str = "mixed") -> tuple:
    """Create agent teams based on type."""
    team0_agents: List[BaseAgent] = []
    team1_agents: List[BaseAgent] = []
    n = config.players_per_team

    if agent_type == "random":
        for i in range(n):
            team0_agents.append(RandomAgent(team_id=0, player_id=i))
            team1_agents.append(RandomAgent(team_id=1, player_id=i))

    elif agent_type == "chaser":
        for i in range(n):
            team0_agents.append(ChaserAgent(team_id=0, player_id=i))
            team1_agents.append(ChaserAgent(team_id=1, player_id=i))

    elif agent_type == "mixed":
        # First player is goalie, rest are chasers
        for i in range(n):
            if i == 0:
                team0_agents.append(GoalieAgent(team_id=0, player_id=i))
                team1_agents.append(GoalieAgent(team_id=1, player_id=i))
            else:
                team0_agents.append(ChaserAgent(team_id=0, player_id=i))
                team1_agents.append(ChaserAgent(team_id=1, player_id=i))

    elif agent_type == "tactical":
        # Goalie + Defender + Striker formation
        for i in range(n):
            if i == 0:
                team0_agents.append(GoalieAgent(team_id=0, player_id=i))
                team1_agents.append(GoalieAgent(team_id=1, player_id=i))
            elif i == 1:
                team0_agents.append(DefenderAgent(team_id=0, player_id=i))
                team1_agents.append(DefenderAgent(team_id=1, player_id=i))
            else:
                team0_agents.append(StrikerAgent(team_id=0, player_id=i))
                team1_agents.append(StrikerAgent(team_id=1, player_id=i))

    elif agent_type == "aggressive":
        # All aggressors
        for i in range(n):
            team0_agents.append(AggressorAgent(team_id=0, player_id=i))
            team1_agents.append(AggressorAgent(team_id=1, player_id=i))

    elif agent_type == "interceptor":
        # Goalie + Interceptors
        for i in range(n):
            if i == 0:
                team0_agents.append(GoalieAgent(team_id=0, player_id=i))
                team1_agents.append(GoalieAgent(team_id=1, player_id=i))
            else:
                team0_agents.append(InterceptorAgent(team_id=0, player_id=i))
                team1_agents.append(InterceptorAgent(team_id=1, player_id=i))

    elif agent_type == "balanced":
        # Goalie + Midfielder + Striker
        for i in range(n):
            if i == 0:
                team0_agents.append(GoalieAgent(team_id=0, player_id=i))
                team1_agents.append(GoalieAgent(team_id=1, player_id=i))
            elif i == 1:
                team0_agents.append(MidfielderAgent(team_id=0, player_id=i))
                team1_agents.append(MidfielderAgent(team_id=1, player_id=i))
            else:
                team0_agents.append(StrikerAgent(team_id=0, player_id=i))
                team1_agents.append(StrikerAgent(team_id=1, player_id=i))

    elif agent_type == "wings":
        # Goalie + Wingers
        for i in range(n):
            if i == 0:
                team0_agents.append(GoalieAgent(team_id=0, player_id=i))
                team1_agents.append(GoalieAgent(team_id=1, player_id=i))
            else:
                team0_agents.append(WingerAgent(team_id=0, player_id=i))
                team1_agents.append(WingerAgent(team_id=1, player_id=i))

    elif agent_type == "diverse":
        # Each team gets different agent types
        agent_classes = [GoalieAgent, DefenderAgent, StrikerAgent, MidfielderAgent, InterceptorAgent, AggressorAgent, WingerAgent]
        for i in range(n):
            cls = agent_classes[i % len(agent_classes)]
            team0_agents.append(cls(team_id=0, player_id=i))
            team1_agents.append(cls(team_id=1, player_id=i))

    elif agent_type == "randomized":
        # Randomly assign agent types to each player
        agent_classes = [GoalieAgent, DefenderAgent, StrikerAgent, MidfielderAgent, InterceptorAgent, AggressorAgent, WingerAgent, ChaserAgent]
        for i in range(n):
            cls0 = random.choice(agent_classes)
            cls1 = random.choice(agent_classes)
            team0_agents.append(cls0(team_id=0, player_id=i))
            team1_agents.append(cls1(team_id=1, player_id=i))

    return team0_agents, team1_agents


def run_game(
    config: GameConfig,
    team0_agents: list[BaseAgent],
    team1_agents: list[BaseAgent],
    visualize: bool = True,
    log_path: Optional[str] = None,
    save_log: bool = True,
) -> tuple:
    """
    Run a game with optional visualization and logging.

    Returns:
        Tuple of (final_score, log_path)
    """
    # Setup logger
    logger = None
    if save_log:
        if log_path is not None:
            logger = GameLogger(config, output_path=log_path)
        else:
            logger = GameLogger(config)  # Auto-generate path

    # Create game
    game = Game(config, team0_agents, team1_agents, logger=logger)

    if visualize:
        try:
            from visualization.renderer import Renderer
            renderer = Renderer(config, scale=1.0)
        except ImportError:
            print("Warning: pygame not available, running without visualization")
            visualize = False

    # Run game loop
    if visualize:
        running = True
        while running and game.status.value == "running":
            game.step()
            running = renderer.render(game.get_state())
            renderer.tick(config.ticks_per_second)

        # Show final state
        if running:
            final_state = game.get_state()
            for _ in range(120):  # Show for 2 seconds
                if not renderer.render(final_state):
                    break
                renderer.tick(60)

        renderer.close()
    else:
        # Run without visualization
        game.run()

    # Finalize logger
    if logger and not logger.finalized:
        logger.log_state(game.get_state())
        logger.finalize()

    return tuple(game.score), logger.get_output_path() if logger else None


def replay_game(log_path: str, scale: float = 1.0) -> None:
    """Replay a game from log file."""
    from visualization.replay import ReplayViewer
    viewer = ReplayViewer(log_path, scale=scale)
    viewer.run()


def main():
    parser = argparse.ArgumentParser(
        description="AI Football Competition Environment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                         # Run with default settings
  python main.py --players 3             # 3v3 game
  python main.py --no-viz --ticks 5000   # Long game, no visualization
  python main.py --replay game.json      # Replay a saved game
  python main.py --agents chaser         # Use chaser agents
        """,
    )

    parser.add_argument(
        "--replay",
        metavar="LOG",
        help="Replay a game log file",
    )
    parser.add_argument(
        "--no-viz",
        action="store_true",
        help="Run without visualization",
    )
    parser.add_argument(
        "--players",
        type=int,
        default=2,
        help="Players per team (default: 2)",
    )
    parser.add_argument(
        "--ticks",
        type=int,
        default=3000,
        help="Max game ticks (default: 3000)",
    )
    parser.add_argument(
        "--win-score",
        type=int,
        default=5,
        help="Score to win (default: 5)",
    )
    parser.add_argument(
        "--agents",
        choices=["random", "chaser", "mixed", "tactical", "aggressive", "interceptor", "balanced", "wings", "diverse", "randomized"],
        default="randomized",
        help="Agent type (default: randomized). Options: random, chaser, mixed, tactical, aggressive, interceptor, balanced, wings, diverse, randomized",
    )
    parser.add_argument(
        "--log",
        metavar="PATH",
        help="Path to save game log",
    )
    parser.add_argument(
        "--no-log",
        action="store_true",
        help="Disable game log saving",
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=1.0,
        help="Display scale factor (default: 1.0)",
    )

    args = parser.parse_args()

    # Replay mode
    if args.replay:
        try:
            replay_game(args.replay, scale=args.scale)
        except FileNotFoundError:
            print(f"Error: Log file not found: {args.replay}")
            sys.exit(1)
        return

    # Create config
    config = GameConfig(
        players_per_team=args.players,
        max_ticks=args.ticks,
        win_score=args.win_score,
    )

    # Create agents
    team0, team1 = create_agents(config, args.agents)

    print(f"Starting {args.players}v{args.players} game")
    print(f"Max ticks: {args.ticks}, Win score: {args.win_score}")
    print(f"Agent type: {args.agents}")
    print()

    # Run game
    score, log_path = run_game(
        config,
        team0,
        team1,
        visualize=not args.no_viz,
        log_path=args.log,
        save_log=not args.no_log,
    )

    print()
    print(f"Final Score: {score[0]} - {score[1]}")
    if score[0] > score[1]:
        print("Blue Team (0) Wins!")
    elif score[1] > score[0]:
        print("Red Team (1) Wins!")
    else:
        print("Draw!")

    if log_path:
        print(f"Game log saved to: {log_path}")


if __name__ == "__main__":
    main()
