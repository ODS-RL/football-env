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

# Specify agents per player
uv run python main.py --agents goalie,striker,defender

# Replay saved game
uv run python main.py --replay LOG.json

# Run tests
uv run python test_game.py

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
- **engine.py**: Main game loop, manages players/ball/goals, processes kicks, handles scoring with goal celebration phase (agents freeze, physics continues)
- **physics.py**: Deterministic physics - velocity clamping, friction (0.98), collisions, boundary enforcement, corner regions (50 unit radius), goal net physics
- **state.py**: Immutable frozen dataclasses (PlayerState, BallState, GameState) for thread safety and replay
- **config.py**: GameConfig dataclass - field 1000x600, kick range 35 units, kick power 12, cooldown 30 ticks, agent timeout 100ms
- **entities.py**: Simple Player, Ball, Goal classes

### Agents (`agents/`)
- **base.py**: Abstract BaseAgent with Action dataclass (acceleration + kick), timeout handling, helper methods (get_my_player, get_teammates, get_opponents)
- **random_agent.py**: 9 agent types - RandomAgent, ChaserAgent, GoalieAgent, StrikerAgent, DefenderAgent, InterceptorAgent, MidfielderAgent, AggressorAgent, WingerAgent

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

1. Create class in `agents/random_agent.py` extending BaseAgent
2. Implement `get_action(game_state)` returning Action
3. Register in `AGENT_CLASSES` dict

## Key Design Decisions

- Deterministic physics for reproducibility
- Immutable state snapshots for logging/replay
- Parallel agent execution with 100ms timeout (falls back to default action)
- Goal celebration phase freezes agents for 45 ticks but physics continues
- Use quick_tournament.py for 4v4+ (combinatorial explosion: 5v5 has 7,776 compositions)
- Network mode: server-authoritative (server runs physics, clients send actions only)
- Network tick rate: 30 Hz default (configurable via --tick-rate)
