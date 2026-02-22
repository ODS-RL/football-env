#!/usr/bin/env python3
"""
Team Composition Tournament System

Systematically tests different team compositions against each other
to find optimal strategies and agent combinations.
"""

import argparse
import itertools
import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple
import sys

from game.config import GameConfig
from game.engine import Game
from agents.base import BaseAgent
from agents.random_agent import (
    RandomAgent, ChaserAgent, GoalieAgent,
    StrikerAgent, DefenderAgent, InterceptorAgent,
    MidfielderAgent, AggressorAgent, WingerAgent,
)
try:
    from agents.messi_agent import MessiAgent
except ImportError:
    MessiAgent = None


# Agent class mapping
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

if MessiAgent is not None:
    AGENT_CLASSES["messi"] = MessiAgent


def get_preset_agent_types(preset: str) -> list[str]:
    """Return agent types for a named preset, filtered by availability."""
    presets = {
        "common": ["goalie", "striker", "defender", "midfielder", "messi"],
        "competitive": ["goalie", "striker", "defender", "messi", "interceptor", "aggressor"],
        "all": list(AGENT_CLASSES.keys()),
    }
    if preset not in presets:
        raise ValueError(f"Unknown preset: {preset}")

    selected = [agent for agent in presets[preset] if agent in AGENT_CLASSES]
    if not selected:
        raise ValueError(f"Preset '{preset}' has no available agent types")
    return selected


@dataclass
class MatchResult:
    """Result of a single match."""
    team0_composition: List[str]
    team1_composition: List[str]
    team0_score: int
    team1_score: int
    ticks_played: int
    winner: int  # 0, 1, or -1 for draw


@dataclass
class TeamStats:
    """Statistics for a team composition."""
    composition: Tuple[str, ...]
    games_played: int = 0
    wins: int = 0
    losses: int = 0
    draws: int = 0
    goals_scored: int = 0
    goals_conceded: int = 0
    win_rate: float = 0.0
    avg_goals_scored: float = 0.0
    avg_goals_conceded: float = 0.0
    goal_difference: int = 0

    def update_stats(self):
        """Recalculate derived statistics."""
        if self.games_played > 0:
            self.win_rate = self.wins / self.games_played
            self.avg_goals_scored = self.goals_scored / self.games_played
            self.avg_goals_conceded = self.goals_conceded / self.games_played
        self.goal_difference = self.goals_scored - self.goals_conceded


def create_team_agents(composition: List[str], team_id: int) -> List[BaseAgent]:
    """Create a team of agents from a composition list."""
    agents = []
    for player_id, agent_type in enumerate(composition):
        agent_class = AGENT_CLASSES[agent_type]
        agents.append(agent_class(team_id=team_id, player_id=player_id))
    return agents


def play_match(
    team0_comp: List[str],
    team1_comp: List[str],
    ticks: int = 3000,
    win_score: int = 5,
) -> MatchResult:
    """Play a single match between two team compositions."""
    # Create config
    config = GameConfig(
        players_per_team=len(team0_comp),
        max_ticks=ticks,
        win_score=win_score,
    )

    # Create agents
    team0_agents = create_team_agents(team0_comp, team_id=0)
    team1_agents = create_team_agents(team1_comp, team_id=1)

    # Run game
    game = Game(config, team0_agents, team1_agents)

    tick_count = 0
    while game.status.value == "running":
        game.step()
        tick_count += 1

    # Return result
    winner = -1  # draw
    if game.score[0] > game.score[1]:
        winner = 0
    elif game.score[1] > game.score[0]:
        winner = 1

    return MatchResult(
        team0_composition=team0_comp,
        team1_composition=team1_comp,
        team0_score=game.score[0],
        team1_score=game.score[1],
        ticks_played=tick_count,
        winner=winner,
    )


def generate_team_compositions(
    players_per_team: int,
    agent_types: List[str],
    include_duplicates: bool = True,
    max_compositions: int = None,
) -> List[List[str]]:
    """
    Generate team compositions to test.

    Args:
        players_per_team: Number of players per team
        agent_types: List of agent types to use
        include_duplicates: Allow multiple agents of same type
        max_compositions: Limit number of compositions (None = all)

    Returns:
        List of team compositions (each is a list of agent types)
    """
    if include_duplicates:
        # All combinations with replacement
        compositions = list(itertools.product(agent_types, repeat=players_per_team))
    else:
        # Only unique combinations (no duplicates)
        if len(agent_types) < players_per_team:
            raise ValueError(
                f"Need at least {players_per_team} different agent types "
                f"when include_duplicates=False, but only {len(agent_types)} provided"
            )
        compositions = list(itertools.combinations(agent_types, players_per_team))

    # Convert to list format
    compositions = [list(comp) for comp in compositions]

    # Limit if requested
    if max_compositions and len(compositions) > max_compositions:
        import random
        random.shuffle(compositions)
        compositions = compositions[:max_compositions]

    return compositions


def run_tournament(
    compositions: List[List[str]],
    matches_per_pairing: int = 3,
    ticks: int = 3000,
    win_score: int = 5,
    verbose: bool = True,
) -> Tuple[Dict[Tuple[str, ...], TeamStats], List[MatchResult]]:
    """
    Run a round-robin tournament with all compositions.

    Args:
        compositions: List of team compositions to test
        matches_per_pairing: Number of times each pair plays
        ticks: Max ticks per match
        win_score: Score needed to win
        verbose: Print progress

    Returns:
        Tuple of (team_stats_dict, all_match_results)
    """
    stats: Dict[Tuple[str, ...], TeamStats] = {}
    all_results: List[MatchResult] = []

    # Initialize stats for all compositions
    for comp in compositions:
        comp_tuple = tuple(comp)
        stats[comp_tuple] = TeamStats(composition=comp_tuple)

    # Generate all pairings
    total_matches = len(compositions) * (len(compositions) - 1) * matches_per_pairing // 2
    total_matches += len(compositions) * matches_per_pairing  # Include self-matches

    if verbose:
        print(f"\nRunning tournament with {len(compositions)} teams")
        print(f"Total matches: {total_matches}")
        print("-" * 60)

    match_count = 0

    # Round-robin: each team plays each other team (including itself)
    for i, team0_comp in enumerate(compositions):
        for j, team1_comp in enumerate(compositions):
            if i > j:
                continue  # Avoid duplicate pairings (A vs B and B vs A)

            for match_num in range(matches_per_pairing):
                match_count += 1

                if verbose and match_count % 10 == 0:
                    print(f"Progress: {match_count}/{total_matches} matches completed")

                # Play match
                result = play_match(team0_comp, team1_comp, ticks, win_score)
                all_results.append(result)

                # Update stats
                comp0 = tuple(team0_comp)
                comp1 = tuple(team1_comp)

                if comp0 == comp1:
                    # Same composition on both sides: count one mirror match.
                    stats[comp0].games_played += 1
                    goals_total = result.team0_score + result.team1_score
                    stats[comp0].goals_scored += goals_total
                    stats[comp0].goals_conceded += goals_total
                    stats[comp0].draws += 1
                else:
                    stats[comp0].games_played += 1
                    stats[comp0].goals_scored += result.team0_score
                    stats[comp0].goals_conceded += result.team1_score

                    stats[comp1].games_played += 1
                    stats[comp1].goals_scored += result.team1_score
                    stats[comp1].goals_conceded += result.team0_score

                    if result.winner == 0:
                        stats[comp0].wins += 1
                        stats[comp1].losses += 1
                    elif result.winner == 1:
                        stats[comp0].losses += 1
                        stats[comp1].wins += 1
                    else:  # draw
                        stats[comp0].draws += 1
                        stats[comp1].draws += 1

    # Calculate final stats
    for team_stats in stats.values():
        team_stats.update_stats()

    if verbose:
        print(f"\nTournament complete! {match_count} matches played")

    return stats, all_results


def print_leaderboard(stats: Dict[Tuple[str, ...], TeamStats], top_n: int = 10):
    """Print tournament leaderboard."""
    # Sort by win rate, then goal difference
    sorted_teams = sorted(
        stats.values(),
        key=lambda s: (s.win_rate, s.goal_difference, s.goals_scored),
        reverse=True,
    )

    print("\n" + "=" * 100)
    print("TOURNAMENT LEADERBOARD")
    print("=" * 100)
    print(
        f"{'Rank':<5} {'Team Composition':<35} {'W-D-L':<12} "
        f"{'Win%':<8} {'GF':<6} {'GA':<6} {'GD':<6}"
    )
    print("-" * 100)

    for rank, team_stat in enumerate(sorted_teams[:top_n], 1):
        comp_str = ", ".join(team_stat.composition)
        wdl = f"{team_stat.wins}-{team_stat.draws}-{team_stat.losses}"
        win_pct = f"{team_stat.win_rate * 100:.1f}%"

        print(
            f"{rank:<5} {comp_str:<35} {wdl:<12} "
            f"{win_pct:<8} {team_stat.goals_scored:<6} "
            f"{team_stat.goals_conceded:<6} {team_stat.goal_difference:<+6}"
        )

    print("=" * 100)


def save_results(
    stats: Dict[Tuple[str, ...], TeamStats],
    results: List[MatchResult],
    output_file: str,
):
    """Save tournament results to JSON file."""
    data = {
        "team_stats": [
            {
                "composition": list(s.composition),
                **{k: v for k, v in asdict(s).items() if k != "composition"},
            }
            for s in stats.values()
        ],
        "matches": [asdict(r) for r in results],
    }

    with open(output_file, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nResults saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Team Composition Tournament System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test common 2v2 compositions
  python tournament.py --players 2 --preset common

  # Test all 3v3 combinations with specific agents
  python tournament.py --players 3 --agents goalie,striker,defender,messi

  # Quick test with fewer matches
  python tournament.py --players 2 --preset common --matches 2 --ticks 1000

  # Generate custom compositions and save results
  python tournament.py --players 2 --agents messi,goalie,striker --max-teams 20 --output results.json
        """,
    )

    parser.add_argument(
        "--players",
        type=int,
        default=2,
        help="Players per team (default: 2)",
    )
    parser.add_argument(
        "--agents",
        type=str,
        help="Comma-separated list of agent types to use in compositions",
    )
    parser.add_argument(
        "--preset",
        type=str,
        choices=["common", "all", "competitive"],
        help="Use preset agent selection (common, all, or competitive)",
    )
    parser.add_argument(
        "--max-teams",
        type=int,
        help="Limit number of team compositions to test (random sample)",
    )
    parser.add_argument(
        "--matches",
        type=int,
        default=3,
        help="Number of matches per team pairing (default: 3)",
    )
    parser.add_argument(
        "--ticks",
        type=int,
        default=2000,
        help="Max ticks per match (default: 2000)",
    )
    parser.add_argument(
        "--win-score",
        type=int,
        default=5,
        help="Score needed to win (default: 5)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=15,
        help="Number of top teams to display (default: 15)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Save detailed results to JSON file",
    )
    parser.add_argument(
        "--no-duplicates",
        action="store_true",
        help="Don't allow duplicate agent types in a team",
    )

    args = parser.parse_args()

    # Determine agent types to use
    if args.agents:
        agent_types = [a.strip() for a in args.agents.split(",")]
        # Validate
        for at in agent_types:
            if at not in AGENT_CLASSES:
                print(f"Error: Unknown agent type '{at}'")
                print(f"Valid types: {', '.join(sorted(AGENT_CLASSES.keys()))}")
                sys.exit(1)
    elif args.preset in {"common", "competitive", "all"}:
        agent_types = get_preset_agent_types(args.preset)
    else:
        print("Error: Must specify either --agents or --preset")
        sys.exit(1)

    print(f"Agent types: {', '.join(agent_types)}")

    # Generate compositions
    compositions = generate_team_compositions(
        players_per_team=args.players,
        agent_types=agent_types,
        include_duplicates=not args.no_duplicates,
        max_compositions=args.max_teams,
    )

    print(f"Generated {len(compositions)} team compositions")

    # Run tournament
    stats, results = run_tournament(
        compositions=compositions,
        matches_per_pairing=args.matches,
        ticks=args.ticks,
        win_score=args.win_score,
        verbose=True,
    )

    # Display results
    print_leaderboard(stats, top_n=args.top)

    # Save if requested
    if args.output:
        save_results(stats, results, args.output)


if __name__ == "__main__":
    main()
