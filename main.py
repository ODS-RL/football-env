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
from agents.random_agent import AGENT_CLASSES
from agents.keyboard_agent import KeyboardAgent, KeyboardController
from game_logging.logger import GameLogger

# Strategy presets: same formation for both teams (except "randomized")
STRATEGY_PRESETS = ["mixed", "tactical", "aggressive", "balanced", "wings", "diverse", "randomized"]

DIVERSE_CYCLE = ["goalie", "defender", "striker", "midfielder", "interceptor", "aggressor", "winger"]
RANDOMIZED_POOL = ["goalie", "defender", "striker", "midfielder", "interceptor", "aggressor", "winger", "chaser"]


def _preset_team(preset: str, n: int) -> List[str]:
    """Agent type names for one team of n players under a preset."""
    if preset == "mixed":
        return (["goalie"] + ["chaser"] * n)[:n]
    if preset == "tactical":
        return (["goalie", "defender"] + ["striker"] * n)[:n]
    if preset == "aggressive":
        return ["aggressor"] * n
    if preset == "balanced":
        return (["goalie", "midfielder"] + ["striker"] * n)[:n]
    if preset == "wings":
        return (["goalie"] + ["winger"] * n)[:n]
    if preset == "diverse":
        return [DIVERSE_CYCLE[i % len(DIVERSE_CYCLE)] for i in range(n)]
    if preset == "randomized":
        return [random.choice(RANDOMIZED_POOL) for _ in range(n)]
    raise ValueError(f"Unknown preset '{preset}'")


def create_agents(config: GameConfig, agent_type: str = "mixed") -> tuple:
    """Create agent teams based on type.

    agent_type can be:
    - A preset strategy: mixed, tactical, aggressive, balanced, wings, diverse, randomized
    - A single agent type, used for every player: random, chaser, goalie, striker, ...
    - Comma-separated agent types: goalie,striker,defender,chaser (first players_per_team
      go to team 0, the rest to team 1). Missing slots are filled with random types.

    Raises ValueError for unknown names or more agents than players.
    """
    n = config.players_per_team
    total_needed = 2 * n
    spec = agent_type.strip()

    if spec in STRATEGY_PRESETS:
        team0_types = _preset_team(spec, n)
        team1_types = _preset_team(spec, n)
    else:
        agent_types = [t.strip() for t in spec.split(",")]

        for i, at in enumerate(agent_types):
            if at not in AGENT_CLASSES:
                raise ValueError(
                    f"Unknown agent type '{at}' at position {i + 1}. "
                    f"Valid types: {', '.join(sorted(AGENT_CLASSES))}. "
                    f"Valid presets: {', '.join(STRATEGY_PRESETS)}"
                )

        if len(agent_types) > total_needed:
            raise ValueError(
                f"Too many agents specified: {len(agent_types)} given, but only {total_needed} needed "
                f"(2 teams × {n} players). Remove {len(agent_types) - total_needed} agent(s)."
            )

        if len(agent_types) == 1 and "," not in spec:
            # A single type name means every player uses it
            agent_types = agent_types * total_needed
        else:
            all_agent_types = list(AGENT_CLASSES)
            while len(agent_types) < total_needed:
                agent_types.append(random.choice(all_agent_types))

        team0_types = agent_types[:n]
        team1_types = agent_types[n:]

    team0_agents: List[BaseAgent] = [
        AGENT_CLASSES[t](team_id=0, player_id=i) for i, t in enumerate(team0_types)
    ]
    team1_agents: List[BaseAgent] = [
        AGENT_CLASSES[t](team_id=1, player_id=i) for i, t in enumerate(team1_types)
    ]

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
        game.close()  # Window may close before the game ends
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
  python main.py --agents striker                         # Every player is a striker
  python main.py --players 3 --agents goalie,striker      # Partial spec, rest are random
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
        help="Agent configuration. Can be a preset (mixed, tactical, aggressive, balanced, wings, diverse, randomized), "
             "a single agent type used for every player (e.g., striker), "
             "or comma-separated agent types for each player (e.g., goalie,striker,defender,chaser). "
             "Available agent types: random, chaser, goalie, striker, defender, interceptor, midfielder, aggressor, winger. "
             "If fewer agents are specified than needed (2 * players_per_team), remaining slots are filled randomly. "
             "Error if more agents specified than needed (2 * players_per_team).",
    )
    parser.add_argument(
        "--log",
        metavar="PATH",
        help="Save game log to PATH (implies --save-log)",
    )
    parser.add_argument(
        "--save-log",
        action="store_true",
        help="Save game log to a timestamped file",
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=1.0,
        help="Display scale factor (default: 1.0)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Random seed for a reproducible game (agent picks, kickoff, agent noise)",
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

    if args.players < 1:
        print("Error: --players must be at least 1")
        sys.exit(1)

    if args.keyboard and args.no_viz:
        print("Error: --keyboard requires visualization (cannot use with --no-viz)")
        sys.exit(1)

    if args.seed is not None:
        random.seed(args.seed)  # Random fills in --agents / randomized preset

    # Create config
    config = GameConfig(
        players_per_team=args.players,
        max_ticks=args.ticks,
        win_score=args.win_score,
        seed=args.seed,
    )

    # Create agents
    try:
        team0, team1 = create_agents(config, args.agents)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    keyboard_controller = None
    if args.keyboard:
        # Wrap team 0 AI agents with keyboard control (AI is fallback when not active)
        keyboard_agents = [
            KeyboardAgent(0, i, fallback_agent=team0[i])
            for i in range(config.players_per_team)
        ]
        team0 = list(keyboard_agents)
        keyboard_controller = KeyboardController(keyboard_agents)
        print("Team 0: Keyboard-controlled (AI fallback when not active)")

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
        save_log=args.save_log or args.log is not None,
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
