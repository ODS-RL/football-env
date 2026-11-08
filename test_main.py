import subprocess
import sys

import pytest

from game.config import GameConfig
from main import create_agents


def _types(team):
    return [type(agent).__name__ for agent in team]


def test_single_agent_type_fills_every_slot():
    team0, team1 = create_agents(GameConfig(players_per_team=3), "chaser")
    assert _types(team0) == ["ChaserAgent"] * 3
    assert _types(team1) == ["ChaserAgent"] * 3


def test_interceptor_is_a_single_type_not_a_preset():
    team0, team1 = create_agents(GameConfig(players_per_team=2), "interceptor")
    assert _types(team0 + team1) == ["InterceptorAgent"] * 4


def test_partial_list_assigns_in_order_and_fills_rest():
    team0, team1 = create_agents(GameConfig(players_per_team=2), "goalie,striker,defender")
    assert _types(team0) == ["GoalieAgent", "StrikerAgent"]
    assert _types(team1)[0] == "DefenderAgent"
    assert len(team1) == 2
    assert [a.team_id for a in team0 + team1] == [0, 0, 1, 1]
    assert [a.player_id for a in team0 + team1] == [0, 1, 0, 1]


def test_preset_builds_formation():
    team0, team1 = create_agents(GameConfig(players_per_team=3), "tactical")
    expected = ["GoalieAgent", "DefenderAgent", "StrikerAgent"]
    assert _types(team0) == expected
    assert _types(team1) == expected


def test_one_player_preset():
    team0, _ = create_agents(GameConfig(players_per_team=1), "mixed")
    assert _types(team0) == ["GoalieAgent"]


@pytest.mark.parametrize("spec", ["bogus", "goalie,bogus", ""])
def test_unknown_names_raise(spec):
    with pytest.raises(ValueError, match="Unknown agent type"):
        create_agents(GameConfig(players_per_team=2), spec)


def test_too_many_agents_raise():
    with pytest.raises(ValueError, match="Too many agents"):
        create_agents(GameConfig(players_per_team=1), "goalie,striker,defender")


def _run_main(*args, cwd):
    return subprocess.run(
        [sys.executable, "-m", "main", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(_repo_root()), "PATH": ""},
        timeout=60,
    )


def _repo_root():
    import pathlib
    return pathlib.Path(__file__).resolve().parent


def test_unknown_agents_exit_cleanly(tmp_path):
    result = _run_main("--no-viz", "--agents", "bogus", "--ticks", "5", cwd=tmp_path)
    assert result.returncode == 1
    assert "Error: Unknown agent type 'bogus'" in result.stdout
    assert "Traceback" not in result.stderr


def test_log_path_saves_without_save_log_flag(tmp_path):
    log = tmp_path / "game.json"
    result = _run_main("--no-viz", "--ticks", "10", "--log", str(log), cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    assert log.exists(), "--log PATH should save the log"
