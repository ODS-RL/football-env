#!/usr/bin/env python3
"""
AI Football Competition Environment

Usage:
    python main.py                   # Run game with visualization
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
from agents.keyboard_agent import KeyboardAgent, KeyboardController
from game_logging.logger import GameLogger

# Mapping from agent type names to classes
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

# Strategy presets (for backward compatibility)
STRATEGY_PRESETS = ["mixed", "tactical", "aggressive", "balanced", "wings", "diverse", "randomized"]

DEFAULT_AGENT_TYPE = "chaser"


def create_agents(config: GameConfig, agent_type: str = "mixed") -> tuple:
    """Create agent teams based on type.

    agent_type can be:
    - A preset strategy: mixed, tactical, aggressive, balanced, wings, diverse, randomized
    - A single agent type: random, chaser, goalie, striker, defender, interceptor, midfielder, aggressor, winger
    - Comma-separated agent types: goalie,striker,defender,chaser (assigns to players in order, both teams)

    For comma-separated: if fewer agents than needed (2 * players_per_team), fills with default.
    Raises ValueError if more agents specified than needed.
    """
    team0_agents: List[BaseAgent] = []
    team1_agents: List[BaseAgent] = []
    n = config.players_per_team
    total_needed = 2 * n

    # Check if comma-separated or single agent type (not a preset strategy)
    if "," in agent_type or (agent_type in AGENT_CLASSES and agent_type not in STRATEGY_PRESETS):
        # Parse comma-separated agent types
        agent_types = [t.strip() for t in agent_type.split(",")]

        # Validate count
        if len(agent_types) > total_needed:
            raise ValueError(
                f"Too many agents specified: {len(agent_types)} given, but only {total_needed} needed "
                f"(2 teams × {n} players). Remove {len(agent_types) - total_needed} agent(s)."
            )

        # Validate each agent type
        for i, at in enumerate(agent_types):
            if at not in AGENT_CLASSES:
                valid_types = ", ".join(sorted(AGENT_CLASSES.keys()))
                raise ValueError(f"Unknown agent type '{at}' at position {i + 1}. Valid types: {valid_types}")

        # Fill with random agents if fewer specified
        all_agent_types = list(AGENT_CLASSES.keys())
        while len(agent_types) < total_needed:
            agent_types.append(random.choice(all_agent_types))

        # First n agents go to team0, next n to team1
        for i in range(n):
            cls0 = AGENT_CLASSES[agent_types[i]]
            cls1 = AGENT_CLASSES[agent_types[n + i]]
            team0_agents.append(cls0(team_id=0, player_id=i))
            team1_agents.append(cls1(team_id=1, player_id=i))

        # Log selected agents
        team0_names = [agent.__class__.__name__.replace("Agent", "") for agent in team0_agents]
        team1_names = [agent.__class__.__name__.replace("Agent", "") for agent in team1_agents]
        print(f"Team 0: {', '.join(team0_names)}")
        print(f"Team 1: {', '.join(team1_names)}")

        return team0_agents, team1_agents

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

    # Log selected agents
    team0_names = [agent.__class__.__name__.replace("Agent", "") for agent in team0_agents]
    team1_names = [agent.__class__.__name__.replace("Agent", "") for agent in team1_agents]
    print(f"Team 0: {', '.join(team0_names)}")
    print(f"Team 1: {', '.join(team1_names)}")

    return team0_agents, team1_agents


def run_game(
    config: GameConfig,
    team0_agents: list[BaseAgent],
    team1_agents: list[BaseAgent],
    visualize: bool = True,
    log_path: Optional[str] = None,
    save_log: bool = True,
    keyboard_controller: Optional[KeyboardController] = None,
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

    renderer = None
    if visualize:
        try:
            from visualization.renderer import Renderer
            import pygame
            renderer = Renderer(config, scale=1.0)
        except ImportError:
            print("Warning: pygame not available, running without visualization")
            visualize = False

    # Link keyboard agents to renderer's key state
    if keyboard_controller and renderer:
        for agent in keyboard_controller.agents:
            agent.set_key_state(renderer.pressed_keys)
        # Set initial active player highlight
        renderer.set_active_player(0, keyboard_controller.get_active_player_id())

    # Run game loop
    if visualize and renderer:
        import pygame
        running = True
        while running and game.status.value == "running":
            game.step()
            running = renderer.render(game.get_state())

            # Handle Tab key for player switching
            if keyboard_controller and pygame.K_TAB in renderer.pressed_keys:
                keyboard_controller.switch_next()
                renderer.set_active_player(0, keyboard_controller.get_active_player_id())
                renderer.pressed_keys.discard(pygame.K_TAB)

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
  python main.py                                          # Run with default settings
  python main.py --players 3                              # 3v3 game
  python main.py --no-viz --ticks 5000                    # Long game, no visualization
  python main.py --replay game.json                       # Replay a saved game
  python main.py --agents tactical                        # Use tactical preset
  python main.py --agents goalie,striker                  # Specify each player's agent
  python main.py --agents goalie,striker,goalie,defender  # Full team specification (2v2)
  python main.py --players 3 --agents goalie,striker      # Partial spec, rest use default
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
        default="randomized",
        help="Agent configuration. Can be a preset (mixed, tactical, aggressive, balanced, wings, diverse, randomized) "
             "or comma-separated agent types for each player (e.g., goalie,striker,defender,chaser). "
             "Available agent types: random, chaser, goalie, striker, defender, interceptor, midfielder, aggressor, winger. "
             "If fewer agents specified than players, remaining use default (chaser). "
             "Error if more agents specified than needed (2 * players_per_team).",
    )
    parser.add_argument(
        "--log",
        metavar="PATH",
        help="Path to save game log",
    )
    parser.add_argument(
        "--save-log",
        action="store_true",
        help="Save game log to file",
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=1.0,
        help="Display scale factor (default: 1.0)",
    )
    parser.add_argument(
        "--keyboard",
        action="store_true",
        help="Enable keyboard control for team 0 (WASD=move, Space=kick, Tab=switch player)",
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
    keyboard_controller = None
    if args.keyboard:
        if args.no_viz:
            print("Error: --keyboard requires visualization (cannot use with --no-viz)")
            sys.exit(1)
        # Create AI agents for both teams first
        ai_team0, team1 = create_agents(config, args.agents)
        # Wrap team 0 AI agents with keyboard control (AI is fallback when not active)
        keyboard_agents = [
            KeyboardAgent(0, i, fallback_agent=ai_team0[i])
            for i in range(config.players_per_team)
        ]
        team0: List[BaseAgent] = list(keyboard_agents)
        keyboard_controller = KeyboardController(keyboard_agents)
        print(f"Team 0: Keyboard-controlled (AI fallback when not active)")
    else:
        try:
            team0, team1 = create_agents(config, args.agents)
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)

    print(f"Starting {args.players}v{args.players} game")
    print(f"Max ticks: {args.ticks}, Win score: {args.win_score}")
    if args.keyboard:
        print("Controls: WASD=move, Space=kick, Tab=switch player")
    else:
        print(f"Agent type: {args.agents}")
    print()

    # Run game
    score, log_path = run_game(
        config,
        team0,
        team1,
        visualize=not args.no_viz,
        log_path=args.log,
        save_log=args.save_log,
        keyboard_controller=keyboard_controller,
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
