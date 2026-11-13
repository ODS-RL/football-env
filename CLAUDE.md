# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python 2D football (soccer) simulation for AI agent competition. Agents compete in matches and tournaments to find optimal team compositions.

## Commands

```bash
# Install dependencies
uv sync

# Run game with visualization
uv run python main.py

# Run headless (faster)
uv run python main.py --no-viz

# Configure game
uv run python main.py --players 3 --agents tactical --ticks 3000 --win-score 5

# Specify agents per player (a single type fills every slot)
uv run python main.py --agents goalie,striker,defender
uv run python main.py --agents striker

# Reproducible game / tournament
uv run python main.py --no-viz --seed 42
uv run python tournament.py --players 2 --preset common --seed 42

# Random environment: physics and geometry rolled from a seed ("random" picks and prints one)
uv run python main.py --env-seed random
uv run python tournament.py --players 2 --preset common --env-seed 1234

# Replay saved game
uv run python main.py --replay LOG.json

# Run tests
uv run pytest
uv run python test_game.py  # same game tests as a verbose script

# Tournament (full - use for 2v2, 3v3)
uv run python tournament.py --players 2 --preset common --matches 5

# Tournament (sampled - use for 4v4+)
uv run python quick_tournament.py --players 5 --preset competitive --sample 100 --fast

# Analyze tournament results
uv run python analyze_team.py --results results.json --top 10

# Network multiplayer - start server
uv run python server.py --players 2

# Network multiplayer - connect client
uv run python client.py localhost --agent striker
uv run python client.py 192.168.1.50 --agent goalie

# Network multiplayer - keyboard control
uv run python client.py localhost --keyboard
```

## Architecture

### Core Engine (`game/`)
- **engine.py**: Main game loop, manages players/ball/goals, processes kicks, handles scoring with goal celebration phase (agents freeze, physics continues), owns the seeded RNG, hands each agent a copy of the config (`set_config`, seed stripped)
- **agent_runner.py**: Runs each agent on a persistent daemon thread with a per-tick deadline; late, raising or non-Action results become `Action(0, 0)`
- **physics.py**: Deterministic physics - speed clamping before movement, friction, collisions and wall bounces (restitutions from config), boundary enforcement, rounded corners, goal net physics
- **state.py**: Immutable frozen dataclasses (PlayerState, BallState, GameState) for thread safety and replay
- **config.py**: GameConfig dataclass - all rules, physics and geometry. Defaults are Haxball's physics scaled x1.35: field 1000x460, goal 170, player radius 20 / friction 0.96 / acceleration 0.135, ball radius 13 / friction 0.99, kick power 7, kick range 38, cooldown 10 ticks, ball-player restitution 0.5, agent timeout 100ms, optional `seed` and `env_seed`
- **environment.py**: `roll_environment(config, env_seed)` re-rolls physics and geometry (not rules) within playable ranges; `--env-seed` CLI helpers shared by main.py, tournament.py, quick_tournament.py and server.py
- **entities.py**: Simple Player, Ball, Goal classes

### Agents (`agents/`)
- **base.py**: Abstract BaseAgent with Action dataclass (acceleration + kick, clamped/sanitized), per-agent `self.rng`, the match's `self.config` (set via `set_config` before the match; defaults until then), helper methods (get_my_player, get_teammates, get_opponents)
- **random_agent.py**: 9 agent types - RandomAgent, ChaserAgent, GoalieAgent, StrikerAgent, DefenderAgent, InterceptorAgent, MidfielderAgent, AggressorAgent, WingerAgent - and the `AGENT_CLASSES` registry used by main.py, tournament.py, client.py and analyze_team.py. All but RandomAgent extend `PlayerAgent`, which provides arrival steering (`steer`), ball prediction (`predict_ball`, `intercept`), approaching the ball from behind (`attack`) and safe kicking (`kick_score` rejects kicks toward the agent's own goal or into a nearby opponent). Kicks always go along the player -> ball line, so positioning decides where they go. `PlayerAgent.set_config` derives its physics values (top speed, contact distance, kick reach...) from the config; there are no hardcoded physics constants
- **keyboard_agent.py**: Human control for local games, with an AI fallback for inactive players (resets and config are forwarded to it)

### Agent Presets
- mixed, tactical, aggressive, balanced, wings, diverse, randomized

### Visualization (`visualization/`)
- **renderer.py**: Pygame real-time rendering
- **replay.py**: Frame-by-frame replay viewer

### Logging (`game_logging/`)
- **logger.py**: JSON game state recording for replay

### Network (`network/`)
- **protocol.py**: Message types (config, state, action, assign, game_over) and JSON serialization
- **network_agent.py**: Server-side wrapper implementing BaseAgent for remote clients
- **server.py**: WebSocket game server - broadcasts state, collects actions
- **client.py**: WebSocket client - connects to server, runs local agent or keyboard control

## Adding New Agents

1. Create class in `agents/random_agent.py` extending BaseAgent, or PlayerAgent for the movement/kicking helpers (call `super().__init__`)
2. Implement `get_action(game_state)` returning Action; use `self.rng` (not the `random` module) so seeded runs stay reproducible, and read physics/geometry from `self.config` (never hardcode them: `--env-seed` changes them). To precompute derived values, override `set_config` and call super
3. Register in `AGENT_CLASSES` at the bottom of `agents/random_agent.py`
4. Optionally add a role profile to `AGENT_ROLES` in `analyze_team.py` (unknown agents default to evenly split roles)

## Key Design Decisions

- Deterministic physics; all game randomness comes from `GameConfig.seed` (`--seed`), which also seeds each agent's `self.rng`
- Haxball-like feel: heavy player inertia and a kick only ~2x player speed, so goalies can be beaten by movement and long shots die
- Randomized environments per competition (`--env-seed`): physics and geometry change so overfit agents break; parameters are visible to agents via `self.config`, and a tournament uses one environment for all its matches
- Immutable state snapshots for logging/replay
- Agents run in parallel on persistent threads with a 100ms per-tick deadline; a slow agent is skipped until it finishes. Threads can't be killed, so a hung agent leaks its thread until exit — untrusted agents would need process isolation
- Goal celebration phase freezes agents for 45 ticks but physics continues
- Use quick_tournament.py for 4v4+ (combinatorial explosion: 5v5 has 7,776 compositions)
- Tournaments alternate which composition plays on the left; mirror matches count as one draw
- Network mode: server-authoritative (server runs physics, clients send actions only)
- Network tick rate: 60 Hz default (configurable via --tick-rate)
