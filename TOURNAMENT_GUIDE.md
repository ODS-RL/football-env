# Team Composition Optimization Guide

This guide explains how to find optimal team compositions and avoid issues like clustering (e.g. four aggressors chasing the same ball).

## The Problem

When you use multiple agents of the same type (especially aggressive ball-chasers like Aggressor), they can cluster around the ball, blocking each other and reducing effectiveness. This happens because:

1. **No coordination**: Agents don't communicate or coordinate
2. **Similar behavior**: Identical agents make identical decisions
3. **Physical interference**: Agents block each other's movement and shots

## The Solution: Team Composition Testing

We've created a tournament system to systematically test different team compositions.

---

## Quick Start

### 1. Run a Quick Tournament

Test common agent combinations:

```bash
# Quick test with common agents (2v2)
python tournament.py --players 2 --preset common --matches 2 --ticks 1000

# More thorough test
python tournament.py --players 2 --preset common --matches 5 --ticks 2000
```

### 2. Test Specific Agents

Focus on agents you're interested in:

```bash
# Test compositions with Aggressor, Goalie, Striker, Defender
python tournament.py --players 2 --agents aggressor,goalie,striker,defender --matches 3
```

### 3. Save and Analyze Results

```bash
# Run tournament and save results
python tournament.py --players 2 --preset common --output results.json

# Analyze the results
python analyze_team.py --results results.json --top 15
```

---

## Available Presets

### `--preset common`
Balanced set of effective agents:
- goalie, striker, defender, midfielder

### `--preset competitive`
Extended competitive set:
- goalie, striker, defender, interceptor, aggressor

### `--preset all`
All available agent types (generates many combinations)

---

## Command Options

### Tournament Options

```bash
python tournament.py [OPTIONS]
```

| Option | Description | Default |
|--------|-------------|---------|
| `--players N` | Players per team | 2 |
| `--agents LIST` | Comma-separated agent types | Required* |
| `--preset NAME` | Use preset (common/competitive/all) | Required* |
| `--matches N` | Matches per team pairing | 3 |
| `--ticks N` | Max ticks per match | 2000 |
| `--win-score N` | Score needed to win | 5 |
| `--max-teams N` | Limit team compositions tested | All |
| `--top N` | Top teams to display | 15 |
| `--output FILE` | Save results to JSON | None |
| `--no-duplicates` | No duplicate agents in team | False |

*Either `--agents` or `--preset` is required

### Analysis Options

```bash
python analyze_team.py [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--results FILE` | Analyze tournament results JSON |
| `--analyze COMP` | Analyze single composition (comma-separated) |
| `--compare C1 C2` | Compare two compositions |
| `--top N` | Number of top/bottom teams to analyze |

---

## Example Workflows

### Finding the Best 2v2 Composition

```bash
# 1. Run comprehensive tournament
python tournament.py --players 2 --preset competitive --matches 5 --output results_2v2.json

# 2. Analyze results
python analyze_team.py --results results_2v2.json --top 10

# 3. Test top composition against others
# (use the winning composition from step 2)
python main.py --agents goalie,aggressor,striker,defender --ticks 3000
```

### Testing Aggressor Combinations

```bash
# Find best Aggressor pairings
python tournament.py --players 2 --agents aggressor,goalie,striker,defender,midfielder --matches 4 --output aggressor_test.json

# Analyze what works best with Aggressor
python analyze_team.py --results aggressor_test.json
```

### Comparing Two Specific Teams

```bash
# Compare Aggressor+Goalie vs Striker+Defender
python analyze_team.py --compare "aggressor,goalie" "striker,defender"
```

### Testing 3v3 Compositions

```bash
# Note: 3v3 generates many more combinations, so use --max-teams
python tournament.py --players 3 --preset common --max-teams 30 --matches 2 --output 3v3_results.json

python analyze_team.py --results 3v3_results.json --top 20
```

---

## Understanding the Results

### Leaderboard Columns

- **Rank**: Position in tournament
- **Team Composition**: List of agents
- **W-D-L**: Wins-Draws-Losses
- **Win%**: Win percentage
- **GF**: Goals For (scored)
- **GA**: Goals Against (conceded)
- **GD**: Goal Difference (GF - GA)

### Analysis Metrics

**Diversity Score** (0-1)
- 1.0 = All different agents
- 0.0 = All same agent
- Higher diversity often reduces clustering

**Balance Score** (0-1)
- Measures role distribution (defense/midfield/offense)
- 1.0 = Perfectly balanced
- 0.0 = Heavily skewed

**Role Distribution**
- Defensive: Goal protection and ball clearing
- Midfield: Support and transition
- Offensive: Goal scoring and attacking

---

## Tips for Optimal Compositions

### General Principles

1. **Avoid duplicate aggressive agents**: Multiple Aggressor/Striker/Chaser agents will cluster
2. **Include a goalie**: Usually provides defensive stability
3. **Balance roles**: Mix defensive, midfield, and offensive agents
4. **Consider synergy**: Some combinations work better together

### Recommended Starting Points (2v2)

**Balanced**:
```bash
python main.py --agents goalie,midfielder,goalie,midfielder
```

**Aggressive**:
```bash
python main.py --agents goalie,aggressor,goalie,striker
```

**Defensive**:
```bash
python main.py --agents goalie,defender,goalie,defender
```

**Mixed**:
```bash
python main.py --agents goalie,striker,defender,aggressor
```

### For Larger Teams (3v3+)

- Increase diversity to avoid clustering
- Consider specialized roles (winger, interceptor)
- Test with `--no-duplicates` flag first

---

## Advanced: Custom Agent Development

After finding optimal compositions, you might want to improve your agents:

1. **Identify weaknesses**: Which situations does your composition struggle with?
2. **Watch replays**: Use `--log` to save games and `--replay` to watch
3. **Modify agents**: Edit agent behavior in `agents/` directory
4. **Re-test**: Run tournaments again to measure improvement

---

## Quick Reference

```bash
# Quick 2v2 tournament with common agents
python tournament.py --players 2 --preset common --matches 3

# Thorough 2v2 test with specific agents
python tournament.py --players 2 --agents aggressor,goalie,striker,defender,midfielder --matches 5 --output results.json

# Analyze results
python analyze_team.py --results results.json

# Test winning composition
python main.py --agents [WINNER_COMPOSITION] --scale 1.5

# Compare two teams
python analyze_team.py --compare "aggressor,goalie" "striker,defender"

# Analyze single composition
python analyze_team.py --analyze "aggressor,striker"
```

---

## Troubleshooting

**Tournament takes too long**:
- Reduce `--matches` (try 2 instead of 3)
- Reduce `--ticks` (try 1000 instead of 2000)
- Use `--max-teams` to limit combinations
- Use smaller `--preset` (common instead of all)

**Too many combinations**:
- Use `--max-teams` to sample randomly
- Use `--no-duplicates` to prevent repeated agents
- Specify fewer agents with `--agents`

**Results not meaningful**:
- Increase `--matches` for more statistical significance
- Increase `--ticks` to allow games to develop
- Use `--win-score` to adjust game length

---

## Next Steps

1. Run your first tournament with common agents
2. Analyze the results to understand what works
3. Test the top compositions visually
4. Experiment with custom combinations
5. Develop new agents based on what you learn!
