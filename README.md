# AI Football Competition Environment

A 2D football (soccer) simulation environment for AI agent competition.

![Football Game Demo](football.gif)

## Installation

### With uv (recommended)

```bash
uv sync
```

Then prefix commands with `uv run`:

```bash
uv run python main.py
```

### With pip

```bash
pip install -e .
```

Then run commands directly:

```bash
python main.py
```

## Usage

```bash
python main.py                              # Run game with visualization
python main.py --no-viz                     # Run game without visualization
python main.py --replay LOG.json            # Replay a game log
python main.py --players 3                  # 3v3 game
python main.py --agents tactical            # Use tactical preset
python main.py --agents goalie,striker      # Specify each player's agent
python main.py --agents striker             # Every player is a striker
python main.py --no-viz --seed 42           # Reproducible game
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--replay LOG` | Replay a game log file | - |
| `--no-viz` | Run without visualization | False |
| `--players N` | Players per team | 2 |
| `--ticks N` | Max game ticks | 3000 |
| `--win-score N` | Score to win | 5 |
| `--agents TYPE` | Preset, single agent type, or comma-separated list (see below) | randomized |
| `--log PATH` | Save game log to PATH | - |
| `--save-log` | Save game log to a timestamped file | False |
| `--seed N` | Random seed for a reproducible game | random |
| `--keyboard` | Control team 0 with WASD/Space, Tab to switch player | False |
| `--scale F` | Display scale factor | 1.0 |

## Agents

Each agent type has a distinct behavior and playing style.

All agents except RandomAgent share a common base (`PlayerAgent`) that:
- brakes into its target position instead of overshooting and oscillating around it
- predicts the ball's path (friction and wall bounces) and goes to where it can meet it
- circles around the ball to get behind it, instead of running through it
- only kicks when the kick sends the ball somewhere useful: never toward its own goal or straight into a nearby opponent. The engine kicks along the player → ball line, so positioning decides where a kick goes
- deep in its own half, approaches from the goal side and clears the ball away from goal

### RandomAgent
- **Behavior**: Takes completely random actions
- **Use case**: Baseline/testing
- **Strategy**: Moves in random directions with random acceleration magnitudes

### ChaserAgent
- **Behavior**: Chases the ball and drives it toward goal
- **Use case**: Simple ball pursuit
- **Strategy**: Always goes for the ball and aims at the centre of the goal, with slight noise in its movement

### GoalieAgent
- **Behavior**: Stays in front of its goal, blocks shots and clears
- **Use case**: Defensive goalkeeper role
- **Strategy**: Stands on the line between ball and goal centre and steps into the path of balls heading for goal. Rushes out to clear balls near goal when it is the first teammate to reach them

### StrikerAgent
- **Behavior**: Forward that takes the ball to goal and shoots
- **Use case**: Offensive scoring role
- **Strategy**: Approaches from behind the ball and aims at the part of the goal mouth with the clearest line. Waits upfield as an outlet while teammates deal with balls deep in its own half

### DefenderAgent
- **Behavior**: Stays between ball and own goal
- **Use case**: Defensive protection role
- **Strategy**: Holds a spot on the ball–goal line inside its own half; tackles and clears when the ball enters its half and it is the closest teammate or the ball is near

### InterceptorAgent
- **Behavior**: Reads the ball's path
- **Use case**: Proactive ball recovery
- **Strategy**: Attacks the predicted ball position. When an opponent will get there first, it cuts off the lane between the ball and its own goal instead

### MidfielderAgent
- **Behavior**: Balanced support for attack and defense
- **Use case**: All-around midfield role
- **Strategy**: Wins balls in the middle of the pitch or when it is the closest teammate. Otherwise drops back to support the defence, or pushes up on the far side for rebounds

### AggressorAgent
- **Behavior**: Relentless ball chaser
- **Use case**: High-pressure play style
- **Strategy**: Always goes for the ball, loops tightly around it and kicks at any chance that sends the ball forward

### WingerAgent
- **Behavior**: Flank player that stays wide
- **Use case**: Wing attack
- **Strategy**: Holds the top or bottom flank (20% or 80% of field height, by player_id) ahead of the ball and attacks when the ball comes within 150 units or it is the closest teammate

## Tactics (Strategy Presets)

Presets configure entire teams with specific formations:

### mixed
- **Formation**: Goalie + Chasers
- **Description**: First player is goalkeeper, rest are ball chasers
- **Best for**: Simple balanced play

### tactical
- **Formation**: Goalie + Defender + Strikers
- **Description**: Classic defensive structure with forward attackers
- **Best for**: Organized play with clear roles

### aggressive
- **Formation**: All Aggressors
- **Description**: Every player aggressively chases the ball
- **Best for**: High-pressure, chaotic gameplay

### balanced
- **Formation**: Goalie + Midfielder + Strikers
- **Description**: Goalkeeper with midfield support and forwards
- **Best for**: Flexible attack/defense transitions

### wings
- **Formation**: Goalie + Wingers
- **Description**: Goalkeeper with wide flank players
- **Best for**: Spread-out attacking play

### diverse
- **Formation**: One of each agent type (cycled)
- **Description**: Goalie, Defender, Striker, Midfielder, Interceptor, Aggressor, Winger assigned in order
- **Best for**: Testing different agent behaviors together

### randomized
- **Formation**: Random assignment
- **Description**: Each player randomly assigned any agent type
- **Best for**: Unpredictable, varied gameplay

## Custom Agent Configuration

You can specify exact agents for each player using comma-separated values:

```bash
# 2v2 game with specific agents for each of 4 players
python main.py --players 2 --agents goalie,striker,goalie,defender

# First 2 agents = Team 0, Next 2 agents = Team 1
# Team 0: goalie (player 0), striker (player 1)
# Team 1: goalie (player 0), defender (player 1)

# Partial specification (remaining players are filled randomly)
python main.py --players 3 --agents goalie,striker
# Team 0: goalie, striker, <random>
# Team 1: <random>, <random>, <random>
```

## Agent Type Reference

| Type | Class | Key Behavior |
|------|-------|--------------|
| `random` | RandomAgent | Random movement |
| `chaser` | ChaserAgent | Direct ball pursuit |
| `goalie` | GoalieAgent | Goal protection |
| `striker` | StrikerAgent | Offensive positioning |
| `defender` | DefenderAgent | Defensive positioning |
| `interceptor` | InterceptorAgent | Ball prediction |
| `midfielder` | MidfielderAgent | Zone-based support |
| `aggressor` | AggressorAgent | Maximum aggression |
| `winger` | WingerAgent | Flank positioning |
