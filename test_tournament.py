import tournament
from tournament import AGENT_CLASSES, MatchResult, get_preset_agent_types, run_tournament


def test_common_preset_only_uses_available_agents():
    """Preset expansion should never include unavailable agent types."""
    common = get_preset_agent_types("common")
    assert common
    for agent_type in common:
        assert agent_type in AGENT_CLASSES


def test_competitive_preset_only_uses_available_agents():
    """Competitive preset should be valid even if optional agents are missing."""
    competitive = get_preset_agent_types("competitive")
    assert competitive
    for agent_type in competitive:
        assert agent_type in AGENT_CLASSES


def test_self_match_counts_once():
    """Self-match should count as a single game, not double-counted stats."""
    stats, _ = run_tournament(
        compositions=[["chaser"]],
        matches_per_pairing=1,
        ticks=1,
        win_score=1,
        verbose=False,
    )

    team = stats[("chaser",)]
    assert team.games_played == 1
    assert team.wins == 0
    assert team.losses == 0
    assert team.draws == 1


def test_seeded_tournament_is_reproducible():
    """Same seed -> same results for every match."""
    def run():
        _, results = run_tournament(
            compositions=[["chaser", "goalie"], ["striker", "random"]],
            matches_per_pairing=2,
            ticks=300,
            win_score=2,
            verbose=False,
            seed=11,
        )
        return [(r.team0_score, r.team1_score, r.ticks_played) for r in results]

    assert run() == run()


def test_sides_alternate_between_matches(monkeypatch):
    """Each composition plays on the left in half of an even pairing."""
    def left_side_wins(team0_comp, team1_comp, ticks, win_score, seed=None):
        return MatchResult(team0_comp, team1_comp, 1, 0, 10, winner=0)

    monkeypatch.setattr(tournament, "play_match", left_side_wins)
    stats, results = run_tournament(
        compositions=[["chaser"], ["goalie"]],
        matches_per_pairing=2,
        verbose=False,
    )

    cross = [r for r in results if r.team0_composition != r.team1_composition]
    assert sorted(tuple(r.team0_composition) for r in cross) == [("chaser",), ("goalie",)]
    for comp in [("chaser",), ("goalie",)]:
        assert (stats[comp].wins, stats[comp].losses) == (1, 1), stats[comp]
        stats[comp].update_stats()
        assert stats[comp].goal_difference == 0, stats[comp]


import pytest


@pytest.mark.parametrize("num_teams", [3, 4, 5, 6])
def test_sides_balanced_with_one_match_per_pairing(monkeypatch, num_teams):
    """With odd match counts every composition still plays left about half the time."""
    from collections import Counter

    def record(team0_comp, team1_comp, ticks, win_score, seed=None):
        return MatchResult(team0_comp, team1_comp, 0, 0, 1, winner=-1)

    monkeypatch.setattr(tournament, "play_match", record)
    comps = [[f"team{k}"] for k in range(num_teams)]
    _, results = run_tournament(comps, matches_per_pairing=1, verbose=False)

    cross = [r for r in results if r.team0_composition != r.team1_composition]
    left = Counter(r.team0_composition[0] for r in cross)
    cross_games = num_teams - 1
    for comp in comps:
        assert abs(left[comp[0]] - cross_games / 2) <= 0.5, (comp, left)


def test_coverage_sampling_uses_selected_agent_types():
    """Coverage sampling balances the agents in play, not the full registry."""
    import random
    from collections import Counter
    from quick_tournament import select_representative_teams
    from tournament import generate_team_compositions

    random.seed(0)
    comps = generate_team_compositions(3, ["goalie", "striker", "defender"])
    selected = select_representative_teams(comps, max_teams=9, strategy="coverage")
    counts = Counter(agent for comp in selected for agent in comp)
    assert len(selected) == 9
    assert set(counts) == {"goalie", "striker", "defender"}
    assert min(counts.values()) >= 3, counts
