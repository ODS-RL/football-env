from tournament import AGENT_CLASSES, get_preset_agent_types, run_tournament


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

