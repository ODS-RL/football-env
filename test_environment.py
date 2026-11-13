"""Tests for randomized environments and how agents receive the match config."""
import argparse

import pytest

from agents.keyboard_agent import KeyboardAgent
from agents.random_agent import AGENT_CLASSES
from game.config import GameConfig
from game.engine import Game
from game.environment import ENV_FIELDS, parse_env_seed, roll_environment


def test_roll_is_reproducible_and_varies():
    base = GameConfig(players_per_team=3, max_ticks=1234, win_score=7, seed=5)
    a, b = roll_environment(base, 11), roll_environment(base, 11)
    assert a == b
    assert a.env_seed == 11
    other = roll_environment(base, 12)
    assert any(getattr(a, f) != getattr(other, f) for f in ENV_FIELDS)
    # Rules are not rolled
    assert (a.players_per_team, a.max_ticks, a.win_score, a.seed) == (3, 1234, 7, 5)


@pytest.mark.parametrize("env_seed", range(200))
def test_rolled_environments_are_playable(env_seed):
    c = roll_environment(GameConfig(), env_seed)
    goal_top = (c.field_height - c.goal_height) / 2
    assert c.corner_radius < goal_top  # Corners end before the goal mouth
    assert c.goal_width > 2 * c.ball_radius  # Ball fits in the net
    assert c.goal_height >= 3.5 * 2 * c.player_radius  # One player can't wall the goal
    assert c.kick_range > c.player_radius + c.ball_radius  # Kicks connect before contact
    assert c.kick_power > c.player_top_speed  # A kick outruns the kicker
    assert 0.45 * c.field_width <= c.kick_reach <= c.field_width
    assert 0 < c.player_friction < 1 and 0 < c.ball_friction < 1


def test_parse_env_seed():
    assert parse_env_seed("42") == 42
    assert isinstance(parse_env_seed("random"), int)
    with pytest.raises(argparse.ArgumentTypeError):
        parse_env_seed("abc")


def test_agents_get_private_copy_of_config_without_seed():
    config = roll_environment(GameConfig(players_per_team=1, max_ticks=5, seed=9), 3)
    a = AGENT_CLASSES["striker"](0, 0)
    b = AGENT_CLASSES["goalie"](1, 0)
    game = Game(config, [a], [b])
    try:
        assert a.config.kick_power == config.kick_power
        assert a.config.seed is None  # Agents can't replay the game RNG
        assert a.kick_power == config.kick_power  # Derived values follow the config
        a.config.kick_power = 999  # Tampering stays local to that agent
        assert game.config.kick_power == config.kick_power
        assert b.config.kick_power == config.kick_power
    finally:
        game.close()


def test_keyboard_agent_forwards_config_to_fallback():
    fallback = AGENT_CLASSES["striker"](0, 0)
    agent = KeyboardAgent(0, 0, fallback_agent=fallback)
    config = roll_environment(GameConfig(), 4)
    agent.set_config(config)
    assert agent.config is config
    assert fallback.config is config
    assert fallback.top_speed == pytest.approx(config.player_top_speed)


@pytest.mark.parametrize("env_seed", [0, 1, 2])
def test_game_runs_in_rolled_environment(env_seed):
    config = roll_environment(GameConfig(players_per_team=2, max_ticks=600, seed=1), env_seed)
    team0 = [AGENT_CLASSES[t](0, i) for i, t in enumerate(["goalie", "striker"])]
    team1 = [AGENT_CLASSES[t](1, i) for i, t in enumerate(["defender", "aggressor"])]
    game = Game(config, team0, team1)
    while game.status.value == "running":
        game.step()
        assert game.physics.validate_state(game.players, game.ball)
