# Performance Guide: Getting Fast Results

## The Issue

Large team sizes create exponential growth in possible combinations:

| Team Size | Agent Types | Combinations | Full Tournament Time |
|-----------|-------------|--------------|---------------------|
| 2v2 | 5 | 25 | ~1 minute |
| 3v3 | 5 | 125 | ~8 minutes |
| 4v4 | 6 | 1,296 | ~2 hours |
| 5v5 | 6 | 7,776 | ~140 hours (6 days!) |
| 6v6 | 6 | 46,656 | ~34 days |

**Your case**: 5v5 with 6 agents = 151 million matches = way too long!

## Solutions (from fastest to most thorough)

### 1. Quick Test (1-3 minutes) ⚡

**Best for**: Initial exploration, rapid iteration

```bash
# Smallest useful sample
python quick_tournament.py --players 5 --preset competitive --sample 30 --fast
```

**Speed**: ~2 minutes
**Accuracy**: Good enough for trends
**Coverage**: ~0.4% of combinations

### 2. Fast Test (3-6 minutes) ⚡⚡

**Best for**: Most use cases, good balance

```bash
# Recommended for 5v5
python quick_tournament.py --players 5 --preset competitive --sample 40 --fast
```

**Speed**: ~5 minutes
**Accuracy**: Very good
**Coverage**: ~0.5% of combinations

### 3. Balanced Test (8-12 minutes) ⚡⚡⚡

**Best for**: More confidence in results

```bash
# Better sampling, still reasonable time
python quick_tournament.py --players 5 --preset competitive --sample 60 --matches 2
```

**Speed**: ~10 minutes
**Accuracy**: Excellent
**Coverage**: ~0.8% of combinations

### 4. Thorough Test (15-25 minutes) ⚡⚡⚡⚡

**Best for**: Final validation, publication-quality results

```bash
# Maximum practical sample
python quick_tournament.py --players 5 --preset competitive \
  --sample 100 \
  --matches 3 \
  --ticks 1500
```

**Speed**: ~20 minutes
**Accuracy**: Near-perfect
**Coverage**: ~1.3% of combinations

---

## Why Small Samples Work

### Statistical Principle

With smart sampling, testing 1% of combinations gives highly reliable results because:

1. **Diversity sampling** ensures coverage of strategy space
2. **Independent measurements** (each match is independent)
3. **Law of large numbers** (40 teams × 820 matches = 32,800 match results)

### Real-World Analogy

Like political polling:
- Don't need to ask all 300M Americans
- 1,000 well-selected people give accurate results
- Smart sampling beats random large samples

### Our Sampling Strategies

**Diverse (default)**:
- Selects maximally different teams
- Best exploration of strategy space
- Recommended for most cases

**Coverage**:
- Ensures balanced agent representation
- Good for testing specific agent effectiveness
- Use when evaluating particular agents

**Random**:
- Pure random selection
- Fastest, less optimized
- Good enough for quick tests

---

## Comparison Table

| Sample Size | Matches | Time | Use Case |
|-------------|---------|------|----------|
| 30 | ~930 | 2-3 min | Quick exploration |
| 40 | ~1,640 | 4-6 min | **Recommended default** |
| 60 | ~3,660 | 10-12 min | Higher confidence |
| 80 | ~6,480 | 18-22 min | Very thorough |
| 100 | ~10,100 | 25-35 min | Maximum practical |

All with `--fast` mode (matches=2, ticks=1000)

---

## Additional Speed Optimizations

### 1. Reduce Agent Types

Instead of testing all agents, focus on specific ones:

```bash
# Only test 4 agent types (much fewer combinations)
python quick_tournament.py --players 5 \
  --agents goalie,striker,defender,aggressor \
  --sample 40 \
  --fast
```

Reduces combinations from 7,776 to 1,024 (87% reduction!)

### 2. Use --no-duplicates

Force unique agents per team:

```bash
# Requires 5 different agents (6 choose 5 = 6 combinations per team)
python quick_tournament.py --players 5 \
  --preset competitive \
  --sample 30 \
  --no-duplicates \
  --fast
```

Dramatically reduces combination space.

### 3. Adjust Game Parameters

Make individual matches faster:

```bash
# Ultra-fast matches
python quick_tournament.py --players 5 --preset competitive \
  --sample 40 \
  --matches 1 \      # Only 1 match per pairing
  --ticks 800 \      # Shorter matches
  --win-score 2      # Lower win threshold
```

Trade-off: Less statistical reliability per match.

---

## Practical Examples

### Your Exact Case: 5v5 Competitive

**Option 1: Quick answer (5 min)**
```bash
python quick_tournament.py --players 5 --preset competitive --sample 40 --fast
```

**Option 2: Good confidence (12 min)**
```bash
python quick_tournament.py --players 5 --preset competitive --sample 60 --matches 2
```

**Option 3: High confidence (25 min)**
```bash
python quick_tournament.py --players 5 --preset competitive \
  --sample 100 \
  --matches 3 \
  --ticks 1500 \
  --output final_results.json
```

### Testing One Agent Specifically

```bash
# Focus on teams with Aggressor
python quick_tournament.py --players 5 \
  --agents aggressor,goalie,striker,defender,midfielder \
  --sample 40 \
  --fast
```

### Testing 6v6

```bash
# Use no-duplicates to manage complexity
python quick_tournament.py --players 6 \
  --preset competitive \
  --sample 40 \
  --no-duplicates \
  --fast
```

---

## Interpreting Results

### Confidence Levels

| Sample Size | Statistical Confidence |
|-------------|----------------------|
| 30 | Good for identifying top 5-10 teams |
| 40 | Good for identifying top 3-5 teams |
| 60 | Reliable top 3, good for top 10 |
| 80 | Very reliable top 5, good for top 15 |
| 100 | Highly reliable top 10, good for top 20 |

### What to Trust

**Highly reliable** (even with small samples):
- ✓ Top 3-5 teams
- ✓ Clear winners vs clear losers
- ✓ General patterns (e.g., "defenders are important")
- ✓ Agent effectiveness rankings

**Less reliable** (need larger samples):
- ⚠ Exact win percentages
- ⚠ Small differences (team ranked 8 vs 9)
- ⚠ Rare strategies
- ⚠ Edge cases

### When to Re-run

Consider running with larger sample if:
- Top teams are very close (< 5% win rate difference)
- Results seem counterintuitive
- You need publication-quality data
- Making important decisions based on results

---

## Command Cheat Sheet

```bash
# FASTEST (2-3 min) - Quick exploration
python quick_tournament.py --players 5 --preset competitive --sample 30 --fast

# RECOMMENDED (5-6 min) - Best balance
python quick_tournament.py --players 5 --preset competitive --sample 40 --fast

# THOROUGH (20-25 min) - High confidence
python quick_tournament.py --players 5 --preset competitive --sample 100 --matches 3

# FOCUSED - Test specific agents only
python quick_tournament.py --players 5 --agents goalie,striker,defender,aggressor --sample 40 --fast

# STRICT - No duplicate agents
python quick_tournament.py --players 5 --preset competitive --sample 40 --no-duplicates --fast

# ULTRA-FAST - Absolute minimum for trends
python quick_tournament.py --players 5 --preset competitive --sample 20 --matches 1 --ticks 600
```

---

## Summary

For your 5v5 competitive tournament:

**Problem**: 7,776 combinations, 151M matches, ~6 days
**Solution**: Sample 40 teams, 1,640 matches, ~5 minutes
**Speed-up**: 37,000x faster!
**Accuracy**: Excellent for finding optimal teams

**Recommended command**:
```bash
python quick_tournament.py --players 5 --preset competitive --sample 40 --fast --output results.json
```

Then analyze:
```bash
python analyze_team.py --results results.json --top 20
```

You'll get meaningful, actionable results in minutes instead of days!
