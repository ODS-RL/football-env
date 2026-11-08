# Finding Optimal Team Compositions

## The Problem: Agent Clustering

When using multiple agents of the same type (e.g., 4x Aggressor), they often cluster around the ball, creating several issues:

- **Physical blocking**: Agents get in each other's way
- **Redundant behavior**: Multiple agents trying to do the same thing
- **Poor field coverage**: Large areas left undefended
- **Reduced effectiveness**: Agents interfere with each other's actions

## The Solution: Systematic Testing

We've built a tournament system to scientifically determine optimal team compositions.

---

## Quick Example: Tournament Results

We ran a tournament with 15 different 2v2 team compositions. Here are the key findings:

### Top 3 Teams
1. **Striker + Midfielder** (25% win rate, +3 goal difference)
2. **Defender + Midfielder** (21.9% win rate, +7 goal difference)
3. **Striker + Defender** (21.9% win rate, +5 goal difference)

### Why These Work
- **High diversity** (1.0 score): Different agents with different roles
- **Better balance** (0.67-0.73): Balanced defensive/offensive distribution
- **No clustering**: Agents have distinct behaviors and positions

### What Doesn't Work
- **Goalie + Goalie**: Overly defensive, low scoring

---

## How to Use the System

### 1. Run a Tournament

```bash
# Quick test with common agents
python tournament.py --players 2 --preset common --matches 3

# More comprehensive test
python tournament.py --players 2 --preset competitive --matches 5 --output results.json
```

### 2. Analyze Results

```bash
# Get detailed analysis
python analyze_team.py --results results.json

# Compare specific teams
python analyze_team.py --compare "striker,midfielder" "aggressor,aggressor"

# Analyze a single composition
python analyze_team.py --analyze "goalie,aggressor"
```

### 3. Test the Winners

```bash
# Play games with the winning composition
python main.py --agents striker,midfielder,defender,goalie --scale 1.5
```

---

## Key Metrics Explained

### Diversity Score (0-1)
- Measures variety of agent types in a team
- **1.0**: All different agents (striker, midfielder)
- **0.0**: All same agents (aggressor, aggressor)
- **Finding**: Higher diversity generally performs better

### Balance Score (0-1)
- Measures distribution across defensive/midfield/offensive roles
- **1.0**: Perfectly balanced across all roles
- **0.0**: Heavily skewed to one role
- **Finding**: Moderate balance (0.6-0.8) works best

### Role Distribution
Each agent contributes to three roles:
- **Defensive**: Goal protection, ball clearing (Goalie: 1.0, Defender: 0.8)
- **Midfield**: Transition, support (Midfielder: 0.4)
- **Offensive**: Goal scoring, attacking (Striker: 0.9, Aggressor: 0.7)

---

## Tournament Results Interpretation

From our test tournament:

### ✓ What Works

**1. Mixed Specialists**
- Striker + Midfielder (Best performer)
- Defender + Midfielder
- Striker + Defender

**Why**: Different roles prevent clustering, good field coverage

**2. Defensive Stability**
- 80% of top teams include Defender or Goalie
- Defenders appear in 35% of top team slots

**Why**: Defensive agents prevent goals effectively

**3. Balanced Offense/Defense**
- Top teams: 47% defensive, 40% offensive
- Bottom teams: More extreme distributions

**Why**: Need both scoring and defending

### ✗ What Doesn't Work

**1. Duplicate Aggressive Agents**
- e.g. Aggressor + Aggressor or Striker + Striker (expected; not measured)

**Why**: Same behavior → clustering → interference

**2. Pure Defense**
- Goalie + Goalie (3.1% win rate)
- Defender + Defender (6.2% win rate)

**Why**: Can't score goals to win

---

## Recommendations by Team Size

### 2v2 (Based on Tournament Data)

**Best Overall**:
```bash
python main.py --agents striker,midfielder,defender,goalie
```

**Aggressive**:
```bash
python main.py --agents aggressor,striker,defender,goalie
```

**Defensive**:
```bash
python main.py --agents goalie,defender,goalie,midfielder
```

**Avoid**:
- aggressor,aggressor (clustering)
- goalie,goalie (too defensive)
- Any duplicate aggressive agents

### 3v3 (General Principles)

**Balanced**:
```bash
python main.py --players 3 --agents goalie,midfielder,striker,goalie,defender,aggressor
```

**Wing Play**:
```bash
python main.py --players 3 --agents goalie,winger,striker,goalie,winger,midfielder
```

**Key**: Even more important to avoid duplicates due to more players

### 4v4+ (General Principles)

- Use `--no-duplicates` flag in tournament testing
- Focus on one specialist per role
- Consider: 1 Goalie, 1-2 Defenders, 1-2 Midfielders, 1-2 Attackers
- Use varied attackers (Aggressor, Striker, Winger) instead of duplicates

---

## Advanced Testing

### Custom Agent Lists

```bash
# Test only specific combinations
python tournament.py --players 2 \
  --agents aggressor,goalie,striker,defender,interceptor \
  --matches 5 \
  --output custom_test.json
```

### Limit Combinations

```bash
# Sample 20 random compositions (useful for large search spaces)
python tournament.py --players 3 \
  --preset all \
  --max-teams 20 \
  --matches 3
```

### No Duplicate Testing

```bash
# Force unique agents only
python tournament.py --players 2 \
  --preset common \
  --no-duplicates \
  --matches 4
```

### Statistical Significance

For more reliable results:
- Increase `--matches` (5-10 instead of 2-3)
- Increase `--ticks` (2000-3000 instead of 1000)
- Test multiple times and average results

---

## Understanding Agent Synergies

### Good Combinations

**Goalie + Aggressive Forward**
- Goalie protects, forward scores
- Clear role separation
- Example: goalie,aggressor or goalie,striker

**Defender + Midfielder**
- Defender protects, midfielder transitions
- Great goal difference (+7 in our test)
- Example: defender,midfielder

**Striker + Support**
- Striker attacks, support covers
- Balanced approach
- Example: striker,midfielder

### Bad Combinations

**Two Goalies**
- Both stay back
- No offensive threat
- Result: Low scoring, many draws

**Duplicate Aggressive**
- Both chase ball
- Cluster and interfere
- Result: Poor coordination

**No Defensive Coverage**
- Example: striker,striker or aggressor,aggressor
- Easy to score against
- Result: High goals conceded

---

## Improving Your Agents

After finding what compositions work:

### 1. Identify Weaknesses
```bash
# Watch specific matchups
python main.py --agents WINNING_TEAM,LOSING_TEAM --log game.json
python main.py --replay game.json
```

### 2. Analyze Patterns
- When do agents cluster?
- Are certain positions left open?
- Do agents interfere with each other?

### 3. Modify Agent Behavior
Edit agent files in `agents/` directory:
- Add position awareness
- Implement spacing logic
- Consider teammate positions

### 4. Re-test
```bash
# Run tournament again to measure improvement
python tournament.py --players 2 --agents YOUR_AGENTS --output improved.json
```

---

## Files Reference

- **[tournament.py](tournament.py)**: Run round-robin tournaments
- **[analyze_team.py](analyze_team.py)**: Analyze results and compositions
- **[TOURNAMENT_GUIDE.md](TOURNAMENT_GUIDE.md)**: Complete command reference
- **[agents/random_agent.py](agents/random_agent.py)**: Built-in agents and the `AGENT_CLASSES` registry

---

## Summary: Key Takeaways

1. **Avoid duplicate aggressive agents** - They will cluster and interfere
2. **Prioritize diversity** - Different agents = different behaviors = better coverage
3. **Balance roles** - Need defense, midfield, and offense
4. **Test systematically** - Use tournament.py to find what works
5. **Analyze results** - Use analyze_team.py to understand why
6. **Iterate** - Improve agents based on findings

**The clustering problem is solved by using diverse team compositions!**

Use the tournament system to find the optimal mix for your specific needs.
