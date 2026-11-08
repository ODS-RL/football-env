#!/usr/bin/env python3
"""
Team Composition Analyzer

Analyzes why certain team compositions perform well by looking at
agent diversity, role coverage, and synergy patterns.
"""

import argparse
import json
from collections import Counter
from typing import List, Dict, Tuple


# Agent role classifications
AGENT_ROLES = {
    "goalie": {"defensive": 1.0, "offensive": 0.0, "midfield": 0.0},
    "defender": {"defensive": 0.8, "offensive": 0.1, "midfield": 0.1},
    "midfielder": {"defensive": 0.3, "offensive": 0.3, "midfield": 0.4},
    "striker": {"defensive": 0.0, "offensive": 0.9, "midfield": 0.1},
    "interceptor": {"defensive": 0.4, "offensive": 0.3, "midfield": 0.3},
    "aggressor": {"defensive": 0.2, "offensive": 0.7, "midfield": 0.1},
    "winger": {"defensive": 0.1, "offensive": 0.6, "midfield": 0.3},
    "chaser": {"defensive": 0.3, "offensive": 0.4, "midfield": 0.3},
    "random": {"defensive": 0.25, "offensive": 0.25, "midfield": 0.5},
}


def analyze_composition(composition: List[str]) -> Dict:
    """Analyze a single team composition."""
    # Count agent types
    agent_counts = Counter(composition)

    # Calculate role balance
    role_totals = {"defensive": 0.0, "offensive": 0.0, "midfield": 0.0}

    for agent_type in composition:
        for role, value in AGENT_ROLES[agent_type].items():
            role_totals[role] += value

    # Normalize by team size
    team_size = len(composition)
    role_balance = {role: total / team_size for role, total in role_totals.items()}

    # Calculate diversity score (1.0 = all different, 0.0 = all same)
    unique_agents = len(agent_counts)
    diversity_score = (unique_agents - 1) / (team_size - 1) if team_size > 1 else 0.0

    # Detect patterns
    has_goalie = "goalie" in composition
    has_dedicated_striker = any(a in composition for a in ["striker", "aggressor"])
    has_defender = any(a in composition for a in ["defender", "goalie"])

    # Balance score: how balanced is the team across roles?
    # Perfect balance would be equal distribution, calculate variance
    role_values = list(role_balance.values())
    mean_role = sum(role_values) / len(role_values)
    variance = sum((v - mean_role) ** 2 for v in role_values) / len(role_values)
    balance_score = 1.0 / (1.0 + variance * 10)  # Convert variance to 0-1 score

    return {
        "composition": composition,
        "agent_counts": dict(agent_counts),
        "role_balance": role_balance,
        "diversity_score": diversity_score,
        "balance_score": balance_score,
        "has_goalie": has_goalie,
        "has_dedicated_striker": has_dedicated_striker,
        "has_defender": has_defender,
        "team_size": team_size,
    }


def compare_compositions(comp1: List[str], comp2: List[str]) -> str:
    """Compare two compositions and explain differences."""
    analysis1 = analyze_composition(comp1)
    analysis2 = analyze_composition(comp2)

    report = []
    report.append(f"\nComparison: {comp1} vs {comp2}")
    report.append("=" * 70)

    # Diversity
    report.append(f"\nDiversity:")
    report.append(f"  Team 1: {analysis1['diversity_score']:.2f} ({len(analysis1['agent_counts'])} unique agents)")
    report.append(f"  Team 2: {analysis2['diversity_score']:.2f} ({len(analysis2['agent_counts'])} unique agents)")

    # Balance
    report.append(f"\nBalance Score:")
    report.append(f"  Team 1: {analysis1['balance_score']:.2f}")
    report.append(f"  Team 2: {analysis2['balance_score']:.2f}")

    # Role distribution
    report.append(f"\nRole Distribution:")
    for role in ["defensive", "midfield", "offensive"]:
        report.append(
            f"  {role.capitalize():12s}: Team1={analysis1['role_balance'][role]:.2f}, "
            f"Team2={analysis2['role_balance'][role]:.2f}"
        )

    # Key features
    report.append(f"\nKey Features:")
    report.append(f"  Goalie:            Team1={'Yes' if analysis1['has_goalie'] else 'No':3s}, Team2={'Yes' if analysis2['has_goalie'] else 'No':3s}")
    report.append(f"  Dedicated Striker: Team1={'Yes' if analysis1['has_dedicated_striker'] else 'No':3s}, Team2={'Yes' if analysis2['has_dedicated_striker'] else 'No':3s}")
    report.append(f"  Defender:          Team1={'Yes' if analysis1['has_defender'] else 'No':3s}, Team2={'Yes' if analysis2['has_defender'] else 'No':3s}")

    return "\n".join(report)


def analyze_tournament_results(results_file: str, top_n: int = 10):
    """Analyze patterns in tournament results."""
    with open(results_file, "r") as f:
        data = json.load(f)

    team_stats = data["team_stats"]

    # Sort by win rate
    sorted_teams = sorted(
        team_stats,
        key=lambda s: (s["win_rate"], s["goal_difference"]),
        reverse=True,
    )

    print("\n" + "=" * 80)
    print("TOURNAMENT ANALYSIS")
    print("=" * 80)

    # Analyze top teams
    print(f"\n📊 TOP {top_n} TEAMS ANALYSIS")
    print("-" * 80)

    top_teams = sorted_teams[:top_n]
    top_analyses = [analyze_composition(team["composition"]) for team in top_teams]

    # Calculate averages for top teams
    avg_diversity = sum(a["diversity_score"] for a in top_analyses) / len(top_analyses)
    avg_balance = sum(a["balance_score"] for a in top_analyses) / len(top_analyses)

    goalie_pct = sum(1 for a in top_analyses if a["has_goalie"]) / len(top_analyses) * 100
    striker_pct = sum(1 for a in top_analyses if a["has_dedicated_striker"]) / len(top_analyses) * 100
    defender_pct = sum(1 for a in top_analyses if a["has_defender"]) / len(top_analyses) * 100

    print(f"\nAverage Diversity Score: {avg_diversity:.2f}")
    print(f"Average Balance Score:   {avg_balance:.2f}")
    print(f"\nTeams with Goalie:            {goalie_pct:.0f}%")
    print(f"Teams with Dedicated Striker: {striker_pct:.0f}%")
    print(f"Teams with Defender:          {defender_pct:.0f}%")

    # Average role distribution
    avg_roles = {
        "defensive": sum(a["role_balance"]["defensive"] for a in top_analyses) / len(top_analyses),
        "midfield": sum(a["role_balance"]["midfield"] for a in top_analyses) / len(top_analyses),
        "offensive": sum(a["role_balance"]["offensive"] for a in top_analyses) / len(top_analyses),
    }

    print(f"\nAverage Role Distribution:")
    print(f"  Defensive: {avg_roles['defensive']:.2f}")
    print(f"  Midfield:  {avg_roles['midfield']:.2f}")
    print(f"  Offensive: {avg_roles['offensive']:.2f}")

    # Most common agents in top teams
    agent_frequency = Counter()
    for team in top_teams:
        agent_frequency.update(team["composition"])

    print(f"\nMost Common Agents in Top {top_n}:")
    for agent, count in agent_frequency.most_common(8):
        pct = count / (len(top_teams) * top_teams[0].get("team_size", 2)) * 100
        print(f"  {agent:12s}: {count:3d} appearances ({pct:.1f}%)")

    # Analyze bottom teams for comparison
    print(f"\n📉 BOTTOM {min(top_n, len(sorted_teams) - top_n)} TEAMS ANALYSIS")
    print("-" * 80)

    bottom_teams = sorted_teams[-top_n:]
    if len(bottom_teams) > 0:
        bottom_analyses = [analyze_composition(team["composition"]) for team in bottom_teams]

        avg_diversity_bottom = sum(a["diversity_score"] for a in bottom_analyses) / len(bottom_analyses)
        avg_balance_bottom = sum(a["balance_score"] for a in bottom_analyses) / len(bottom_analyses)

        print(f"\nAverage Diversity Score: {avg_diversity_bottom:.2f}")
        print(f"Average Balance Score:   {avg_balance_bottom:.2f}")

        print(f"\nDiversity Difference: {avg_diversity - avg_diversity_bottom:+.2f}")
        print(f"Balance Difference:   {avg_balance - avg_balance_bottom:+.2f}")

    # Recommendations
    print("\n" + "=" * 80)
    print("💡 RECOMMENDATIONS")
    print("=" * 80)

    if avg_diversity > 0.7:
        print("✓ Top teams favor diverse agent combinations")
    elif avg_diversity < 0.3:
        print("✓ Top teams use specialized compositions with repeated agents")
    else:
        print("✓ Top teams show mixed strategies on agent diversity")

    if goalie_pct > 80:
        print("✓ Having a dedicated goalie is crucial for success")
    elif goalie_pct < 20:
        print("✓ Goalie is not essential; aggressive strategies dominate")

    if avg_balance > 0.7:
        print("✓ Balanced role distribution across defense/midfield/offense is important")
    else:
        print("✓ Specialized roles outperform balanced distributions")

    if avg_roles["offensive"] > avg_roles["defensive"] + 0.2:
        print("✓ Offensive-heavy compositions perform better")
    elif avg_roles["defensive"] > avg_roles["offensive"] + 0.2:
        print("✓ Defensive-heavy compositions perform better")
    else:
        print("✓ Balanced offensive/defensive split is optimal")

    print("\n" + "=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="Team Composition Analyzer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--results",
        type=str,
        help="Path to tournament results JSON file",
    )
    parser.add_argument(
        "--compare",
        type=str,
        nargs=2,
        help="Compare two compositions (comma-separated agent lists)",
    )
    parser.add_argument(
        "--analyze",
        type=str,
        help="Analyze a single composition (comma-separated agent list)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="Number of top/bottom teams to analyze (default: 10)",
    )

    args = parser.parse_args()

    if args.results:
        analyze_tournament_results(args.results, top_n=args.top)

    elif args.compare:
        comp1 = args.compare[0].split(",")
        comp2 = args.compare[1].split(",")
        print(compare_compositions(comp1, comp2))

    elif args.analyze:
        composition = args.analyze.split(",")
        analysis = analyze_composition(composition)

        print("\n" + "=" * 70)
        print("TEAM COMPOSITION ANALYSIS")
        print("=" * 70)
        print(f"\nComposition: {', '.join(composition)}")
        print(f"\nDiversity Score: {analysis['diversity_score']:.2f}")
        print(f"Balance Score:   {analysis['balance_score']:.2f}")
        print(f"\nRole Distribution:")
        for role, value in analysis['role_balance'].items():
            print(f"  {role.capitalize():10s}: {value:.2f}")
        print(f"\nKey Features:")
        print(f"  Has Goalie:            {'Yes' if analysis['has_goalie'] else 'No'}")
        print(f"  Has Dedicated Striker: {'Yes' if analysis['has_dedicated_striker'] else 'No'}")
        print(f"  Has Defender:          {'Yes' if analysis['has_defender'] else 'No'}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
