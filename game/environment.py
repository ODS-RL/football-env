"""Randomized environments.

``roll_environment`` re-rolls a config's physics and geometry from an
environment seed, so agents tuned to one set of constants stop working and
competitors have to write agents that read ``BaseAgent.config`` instead.
Rules (team size, match length, win score, game seed) are kept.

Ranges are built around the defaults and tied together so every roll stays
playable: the goal is always several player-widths wide, a kick is always
faster than a player, and a kick from rest rolls for 50-95% of the field.
"""
import argparse
import random
import secrets
from dataclasses import replace

from .config import GameConfig

# Fields roll_environment changes, in display order
ENV_FIELDS = (
    "field_width", "field_height", "corner_radius",
    "goal_height", "goal_width",
    "player_radius", "player_max_acceleration", "player_friction", "player_max_speed", "player_mass",
    "ball_radius", "ball_friction", "ball_max_speed", "ball_mass",
    "kick_power", "kick_range", "kick_cooldown_ticks",
    "ball_wall_restitution", "player_wall_restitution",
    "ball_player_restitution", "player_player_restitution",
)


def roll_environment(config: GameConfig, env_seed: int) -> GameConfig:
    """Copy of `config` with physics and geometry rolled from `env_seed`."""
    rng = random.Random(env_seed)

    def r(lo: float, hi: float, digits: int = 3) -> float:
        return round(rng.uniform(lo, hi), digits)

    # Geometry, sized relative to the players
    player_radius = r(15, 25, 1)
    ball_radius = round(player_radius * rng.uniform(0.5, 0.8), 1)
    goal_height = round(2 * player_radius * rng.uniform(3.6, 5.0), 1)
    field_width = r(850, 1200, 0)
    field_height = round(max(field_width * rng.uniform(0.4, 0.6), goal_height / 0.42), 0)
    # Corners must end before the goal mouth starts
    corner_radius = round(min(rng.uniform(30, 70), (field_height - goal_height) / 2 - 10), 1)
    goal_width = round(max(rng.uniform(30, 50), 2 * ball_radius + 8), 1)

    # Player dynamics: top speed and how long it takes to reach it
    player_friction = r(0.92, 0.975)
    top_speed = rng.uniform(2.6, 4.2)
    player_max_acceleration = round(top_speed * (1 - player_friction), 4)
    player_max_speed = round(top_speed * 1.5, 2)

    # Kicks: speed relative to players, and how far the ball rolls
    kick_power = round(top_speed * rng.uniform(1.6, 2.8), 2)
    reach = field_width * rng.uniform(0.5, 0.95)
    ball_friction = round(min(0.997, 1 - kick_power / reach), 4)
    ball_max_speed = round(kick_power * rng.uniform(1.6, 2.4), 2)
    kick_range = round(player_radius + ball_radius + rng.uniform(3, 9), 1)

    return replace(
        config,
        field_width=field_width,
        field_height=field_height,
        corner_radius=corner_radius,
        goal_height=goal_height,
        goal_width=goal_width,
        player_radius=player_radius,
        player_max_acceleration=player_max_acceleration,
        player_friction=player_friction,
        player_max_speed=player_max_speed,
        player_mass=1.0,
        ball_radius=ball_radius,
        ball_friction=ball_friction,
        ball_max_speed=ball_max_speed,
        ball_mass=r(0.3, 0.8, 2),
        kick_power=kick_power,
        kick_range=kick_range,
        kick_cooldown_ticks=rng.randint(6, 16),
        ball_wall_restitution=r(0.5, 0.95, 2),
        player_wall_restitution=r(0.2, 0.7, 2),
        ball_player_restitution=r(0.2, 0.9, 2),
        player_player_restitution=r(0.2, 0.7, 2),
        env_seed=env_seed,
    )


def parse_env_seed(value: str) -> int:
    """argparse type for --env-seed: an integer, or 'random' for a fresh one."""
    if value == "random":
        return secrets.randbelow(1_000_000)
    try:
        return int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected an integer or 'random', got '{value}'")


def add_env_seed_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--env-seed",
        type=parse_env_seed,
        metavar="N|random",
        help="Roll random physics and geometry from seed N ('random' picks and prints a seed); "
             "default: standard parameters",
    )


def apply_env_seed(config: GameConfig, env_seed) -> GameConfig:
    """Roll the environment if a seed was given and print it, else return config unchanged."""
    if env_seed is None:
        return config
    config = roll_environment(config, env_seed)
    print(describe_environment(config))
    return config


def describe_environment(config: GameConfig) -> str:
    """Human-readable summary of a config's physics and geometry."""
    title = f"Environment (env seed {config.env_seed})" if config.env_seed is not None else "Environment"
    lines = [f"{title}:"]
    for name in ENV_FIELDS:
        lines.append(f"  {name:<26} {getattr(config, name)}")
    lines.append(f"  {'-> player top speed':<26} {config.player_top_speed:.2f}")
    lines.append(f"  {'-> kick reach':<26} {config.kick_reach:.0f}")
    return "\n".join(lines)
