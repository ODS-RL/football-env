#!/usr/bin/env python3
"""
Quick Tournament - Optimized for fast results with large team counts

Uses intelligent sampling and parallel processing to handle
large combination spaces efficiently.
"""

import argparse
import random
import sys
from tournament import (
    AGENT_CLASSES,
    generate_team_compositions,
    run_tournament,
    print_leaderboard,
    save_results,
    get_preset_agent_types,
)


def select_representative_teams(
    all_compositions,
    max_teams: int,
    strategy: str = "diverse"
) -> list:
    """
    Select representative subset of teams using smart sampling.

    Strategies:
    - diverse: Maximize agent diversity across selected teams
    - random: Pure random sampling
    - coverage: Ensure all agents appear roughly equally
    """
    if len(all_compositions) <= max_teams:
        return all_compositions

    if strategy == "random":
        return random.sample(all_compositions, max_teams)

    elif strategy == "coverage":
        # Ensure each agent type appears in multiple teams
        selected = []
        agent_counts = {agent: 0 for agent in AGENT_CLASSES.keys()}

        # First pass: ensure minimum coverage
        min_appearances = max_teams // len(AGENT_CLASSES)

        shuffled = all_compositions.copy()
        random.shuffle(shuffled)

        for comp in shuffled:
            if len(selected) >= max_teams:
                break

            # Check if this team helps balance agent representation
            min_agent_count = min(agent_counts[agent] for agent in comp)

            if min_agent_count < min_appearances or len(selected) < len(AGENT_CLASSES):
                selected.append(comp)
                for agent in comp:
                    agent_counts[agent] += 1

        # Fill remaining spots randomly
        remaining = [c for c in shuffled if c not in selected]
        while len(selected) < max_teams and remaining:
            selected.append(remaining.pop())

        return selected

    elif strategy == "diverse":
        # Select teams that maximize overall diversity
        selected = []

        # Start with a random team
        remaining = all_compositions.copy()
        random.shuffle(remaining)
        selected.append(remaining.pop(0))

        # Iteratively select teams that are most different from selected ones
        while len(selected) < max_teams and remaining:
            # Score each remaining team by how different it is
            best_score = -1
            best_team = None
            best_idx = -1

            # Sample a subset to avoid O(n²) complexity
            sample_size = min(1000, len(remaining))
            sample_indices = random.sample(range(len(remaining)), sample_size)

            for idx in sample_indices:
                candidate = remaining[idx]

                # Calculate diversity score (different agents from selected teams)
                score = 0
                for selected_team in selected[-20:]:  # Compare with recent selections
                    # Count how many agents are different
                    diff_count = sum(
                        1 for i, agent in enumerate(candidate)
                        if i >= len(selected_team) or agent != selected_team[i]
                    )
                    score += diff_count

                if score > best_score:
                    best_score = score
                    best_team = candidate
                    best_idx = idx

            if best_team:
                selected.append(best_team)
                remaining.pop(best_idx)

        return selected

    return random.sample(all_compositions, max_teams)


def estimate_runtime(num_teams: int, matches_per_pairing: int, ticks: int) -> float:
    """Estimate runtime in seconds."""
    total_matches = num_teams * (num_teams + 1) // 2 * matches_per_pairing
    # Rough estimate: 0.1-0.3 seconds per 1000 ticks
    seconds_per_match = (ticks / 1000) * 0.2
    return total_matches * seconds_per_match


def main():
    parser = argparse.ArgumentParser(
        description="Quick Tournament - Optimized for large team counts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 5v5 with intelligent sampling (finishes in minutes)
  python quick_tournament.py --players 5 --preset competitive --sample 100

  # 4v4 with maximum diversity sampling
  python quick_tournament.py --players 4 --preset common --sample 50 --strategy diverse

  # Quick 3v3 test
  python quick_tournament.py --players 3 --agents messi,goalie,striker --sample 30 --fast
        """,
    )

    parser.add_argument(
        "--players",
        type=int,
        required=True,
        help="Players per team",
    )
    parser.add_argument(
        "--agents",
        type=str,
        help="Comma-separated list of agent types",
    )
    parser.add_argument(
        "--preset",
        type=str,
        choices=["common", "all", "competitive"],
        help="Use preset agent selection",
    )
    parser.add_argument(
        "--sample",
        type=int,
        required=True,
        help="Number of teams to sample from all combinations (REQUIRED)",
    )
    parser.add_argument(
        "--strategy",
        type=str,
        choices=["diverse", "random", "coverage"],
        default="diverse",
        help="Sampling strategy (default: diverse)",
    )
    parser.add_argument(
        "--matches",
        type=int,
        default=3,
        help="Matches per team pairing (default: 3)",
    )
    parser.add_argument(
        "--ticks",
        type=int,
        default=1500,
        help="Max ticks per match (default: 1500 for speed)",
    )
    parser.add_argument(
        "--win-score",
        type=int,
        default=3,
        help="Score to win (default: 3 for speed)",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Use fastest settings (reduces matches and ticks)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=20,
        help="Number of top teams to display (default: 20)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Save results to JSON file",
    )
    parser.add_argument(
        "--no-duplicates",
        action="store_true",
        help="Don't allow duplicate agent types",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt",
    )

    args = parser.parse_args()

    # Apply fast presets
    if args.fast:
        args.matches = min(args.matches, 2)
        args.ticks = min(args.ticks, 1000)
        args.win_score = min(args.win_score, 3)
        print("⚡ Fast mode enabled: matches=2, ticks=1000, win_score=3")

    # Determine agent types
    if args.agents:
        agent_types = [a.strip() for a in args.agents.split(",")]
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

    # Generate all possible compositions
    print("\n⏳ Generating all possible team compositions...")
    all_compositions = generate_team_compositions(
        players_per_team=args.players,
        agent_types=agent_types,
        include_duplicates=not args.no_duplicates,
        max_compositions=None,  # Generate all first
    )

    total_possible = len(all_compositions)
    total_matches_full = total_possible * (total_possible + 1) // 2 * args.matches

    print(f"📊 Total possible compositions: {total_possible:,}")
    print(f"📊 Full tournament would require: {total_matches_full:,} matches")

    # Estimate full runtime
    est_full_hours = estimate_runtime(total_possible, args.matches, args.ticks) / 3600
    if est_full_hours > 1:
        print(f"⏰ Full tournament estimated time: {est_full_hours:.1f} hours")
    else:
        print(f"⏰ Full tournament estimated time: {est_full_hours * 60:.0f} minutes")

    # Sample teams
    print(f"\n🎯 Sampling {args.sample} teams using '{args.strategy}' strategy...")
    selected_compositions = select_representative_teams(
        all_compositions,
        max_teams=args.sample,
        strategy=args.strategy,
    )

    sampled_matches = len(selected_compositions) * (len(selected_compositions) + 1) // 2 * args.matches
    print(f"📊 Sampled tournament matches: {sampled_matches:,}")

    # Estimate sampled runtime
    est_sample_minutes = estimate_runtime(len(selected_compositions), args.matches, args.ticks) / 60
    print(f"⏰ Estimated time: {est_sample_minutes:.1f} minutes")
    print(f"⚡ Speed-up: {total_matches_full / sampled_matches:.0f}x faster")

    # Run tournament
    if not args.yes:
        print("\n" + "=" * 60)
        response = input("Proceed with tournament? (y/n): ")
        if response.lower() != 'y':
            print("Tournament cancelled.")
            sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("Starting tournament...")
        print("=" * 60)

    stats, results = run_tournament(
        compositions=selected_compositions,
        matches_per_pairing=args.matches,
        ticks=args.ticks,
        win_score=args.win_score,
        verbose=True,
    )

    # Display results
    print_leaderboard(stats, top_n=args.top)

    # Show sampling info
    print("\n" + "=" * 100)
    print("📈 SAMPLING STATISTICS")
    print("=" * 100)
    print(f"Total possible compositions: {total_possible:,}")
    print(f"Teams tested: {len(selected_compositions):,} ({len(selected_compositions)/total_possible*100:.2f}%)")
    print(f"Sampling strategy: {args.strategy}")
    print(f"Matches per pairing: {args.matches}")
    print(f"Total matches played: {sampled_matches:,}")

    # Agent coverage
    from collections import Counter
    agent_counts = Counter()
    for comp in selected_compositions:
        agent_counts.update(comp)

    print(f"\nAgent representation in sampled teams:")
    for agent, count in sorted(agent_counts.items()):
        pct = count / (len(selected_compositions) * args.players) * 100
        print(f"  {agent:12s}: {count:4d} appearances ({pct:.1f}%)")

    print("=" * 100)

    # Save if requested
    if args.output:
        save_results(stats, results, args.output)
        print(f"\n💾 Full results saved to: {args.output}")
        print(f"   Analyze with: python analyze_team.py --results {args.output}")


if __name__ == "__main__":
    main()
