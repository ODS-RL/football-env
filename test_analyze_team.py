import json

import pytest

from analyze_team import analyze_composition, analyze_tournament_results, parse_composition


def _write_results(path, compositions):
    team_stats = [
        {"composition": comp, "win_rate": 1.0 - i / 10, "goal_difference": -i}
        for i, comp in enumerate(compositions)
    ]
    path.write_text(json.dumps({"team_stats": team_stats, "matches": []}))
    return str(path)


def test_agent_percentages_use_real_team_size(tmp_path, capsys):
    results = _write_results(tmp_path / "r.json", [["goalie", "striker", "defender"]] * 2)
    analyze_tournament_results(results, top_n=2)
    out = capsys.readouterr().out
    assert "goalie      :   2 appearances (33.3%)" in out


def test_bottom_group_does_not_overlap_top(tmp_path, capsys):
    comps = [["goalie", "striker"], ["striker", "striker"], ["defender", "chaser"]]
    analyze_tournament_results(_write_results(tmp_path / "r.json", comps), top_n=2)
    out = capsys.readouterr().out
    assert "TOP 2 TEAMS" in out
    assert "BOTTOM 1 TEAMS" in out


def test_no_bottom_section_when_all_teams_are_top(tmp_path, capsys):
    comps = [["goalie", "striker"], ["striker", "striker"]]
    analyze_tournament_results(_write_results(tmp_path / "r.json", comps), top_n=10)
    out = capsys.readouterr().out
    assert "TOP 2 TEAMS" in out
    assert "BOTTOM" not in out


def test_unknown_agents_in_results_do_not_crash(tmp_path, capsys):
    comps = [["messi", "goalie"], ["striker", "defender"]]
    analyze_tournament_results(_write_results(tmp_path / "r.json", comps), top_n=1)
    assert "no role profile for messi" in capsys.readouterr().out
    assert analyze_composition(["messi"])["role_balance"]["midfield"] == pytest.approx(1 / 3)


def test_cli_rejects_unknown_agent_names():
    assert parse_composition("goalie, striker") == ["goalie", "striker"]
    with pytest.raises(SystemExit, match="unknown agent type"):
        parse_composition("goalie,bogus")


def test_registered_agent_without_role_profile_is_accepted(monkeypatch):
    import analyze_team
    from agents.random_agent import ChaserAgent

    monkeypatch.setitem(analyze_team.AGENT_CLASSES, "newbie", ChaserAgent)
    assert parse_composition("newbie,goalie") == ["newbie", "goalie"]
