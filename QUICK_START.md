# Quick Tournament Guide - Fast Results for Large Teams

## The Problem

When testing 5v5 teams with 6 agent types:
- **Possible combinations**: 7,776 teams
- **Full tournament**: 151+ million matches
- **Estimated time**: Days or weeks 🐌

## The Solution: Smart Sampling

Use `quick_tournament.py` to sample representative teams and finish in minutes!

---

## Quick Commands

### 5v5 Tournament (Finishes in ~5 minutes)

```bash
cd ~/code/football-agent
source venv/bin/activate

# Sample 100 teams with intelligent diversity
python quick_tournament.py --players 5 --preset competitive --sample 100 --fast
```

### 4v4 Tournament (Finishes in ~2 minutes)

```bash
python quick_tournament.py --players 4 --preset common --sample 50 --fast
```

### 3v3 Quick Test (Finishes in ~1 minute)

```bash
python quick_tournament.py --players 3 --preset common --sample 30 --fast
```

---

## How It Works

### 1. Smart Sampling Strategies

**Diverse (default)** - Recommended
- Selects teams that are maximally different from each other
- Ensures good coverage of the strategy space
- Best for finding optimal compositions

```bash
python quick_tournament.py --players 5 --preset competitive --sample 100 --strategy diverse
```

**Coverage**
- Ensures each agent type appears roughly equally
- Good for testing specific agent effectiveness
- Balanced representation

```bash
python quick_tournament.py --players 5 --preset competitive --sample 100 --strategy coverage
```

**Random**
- Pure random sampling
- Fastest selection, less optimized coverage
- Good for quick exploratory tests

```bash
python quick_tournament.py --players 5 --preset competitive --sample 100 --strategy random
```

### 2. Speed Optimizations

**--fast flag**
- Reduces matches per pairing to 2
- Reduces ticks to 1000
- Reduces win score to 3
- 2-3x faster with acceptable accuracy

```bash
python quick_tournament.py --players 5 --preset competitive --sample 100 --fast
```

**Manual optimization**
```bash
python quick_tournament.py --players 5 --preset competitive \
  --sample 100 \
  --matches 2 \
  --ticks 1000 \
  --win-score 3
```

---

## Recommended Settings by Team Size

### 2v2 (Small - Use Regular Tournament)
```bash
# Small enough for full tournament
python tournament.py --players 2 --preset competitive --matches 5
```

### 3v3 (Medium)
```bash
# Sample 50-100 teams
python quick_tournament.py --players 3 --preset competitive --sample 50 --fast
```

### 4v4 (Large)
```bash
# Sample 100-200 teams
python quick_tournament.py --players 4 --preset competitive --sample 100 --fast
```

### 5v5 (Very Large)
```bash
# Sample 100-200 teams, use fast mode
python quick_tournament.py --players 5 --preset competitive --sample 100 --fast

# For more accuracy (takes longer)
python quick_tournament.py --players 5 --preset competitive --sample 200 --matches 3
```

### 6v6+ (Extreme)
```bash
# Use no-duplicates to reduce space
python quick_tournament.py --players 6 --preset competitive \
  --sample 100 \
  --no-duplicates \
  --fast

# Or limit agent types
python quick_tournament.py --players 6 \
  --agents goalie,striker,defender,aggressor \
  --sample 50 \
  --fast
```

---

## Sample Size Guidelines

| Team Size | Possible Combos | Recommended Sample | Time (fast mode) |
|-----------|-----------------|-------------------|------------------|
| 2v2 | 25-100 | Use full tournament | 1-2 min |
| 3v3 | 125-1000 | 50-100 | 2-3 min |
| 4v4 | 625-10,000 | 100-200 | 5-8 min |
| 5v5 | 3,125-100,000 | 100-200 | 5-10 min |
| 6v6 | 15,625-1,000,000 | 100-150 | 5-12 min |

**Rule of thumb**: Sample size of 100-200 gives good results for most cases

---

## Complete Example Workflow

### Step 1: Quick exploratory test
```bash
# Fast test to get initial insights (2-3 minutes)
python quick_tournament.py --players 5 --preset competitive --sample 50 --fast
```

### Step 2: More thorough test
```bash
# Better sample size with more matches (8-10 minutes)
python quick_tournament.py --players 5 --preset competitive \
  --sample 150 \
  --matches 3 \
  --output results_5v5.json
```

### Step 3: Analyze results
```bash
# Get insights and recommendations
python analyze_team.py --results results_5v5.json --top 20
```

### Step 4: Test top compositions
```bash
# Watch the winning team play
python main.py --players 5 --agents [TOP_COMPOSITION] --scale 1.2
```

---

## Understanding the Output

### Before Tournament

```
📊 Total possible compositions: 7,776
📊 Full tournament would require: 30,269,040 matches
⏰ Full tournament estimated time: 16.8 hours
🎯 Sampling 100 teams using 'diverse' strategy...
📊 Sampled tournament matches: 5,050
⏰ Estimated time: 1.7 minutes
⚡ Speed-up: 5994x faster
```

This shows:
- You're avoiding 30 million matches!
- Getting results 6000x faster
- Still testing representative subset

### After Tournament

```
📈 SAMPLING STATISTICS
Total possible compositions: 7,776
Teams tested: 100 (1.29%)
Sampling strategy: diverse
```

Even with 1.29% sample, you get meaningful results because:
- Teams are selected for maximum diversity
- Representative of the full strategy space
- Statistics are still significant

---

## When to Use Each Tool

### Use `tournament.py` (full tournament)
- ✓ 2v2 or small 3v3 (< 1000 combinations)
- ✓ Need exhaustive testing
- ✓ Have time to spare
- ✓ Want perfect accuracy

### Use `quick_tournament.py` (sampled)
- ✓ 4v4 or larger (1000+ combinations)
- ✓ Want results in minutes
- ✓ Initial exploration
- ✓ Good-enough accuracy is fine

---

## Advanced Options

### Test specific agents only
```bash
# Reduce search space by limiting agent types
python quick_tournament.py --players 5 \
  --agents aggressor,goalie,striker,defender \
  --sample 100 \
  --fast
```

### No duplicate agents
```bash
# Force unique agents per team (smaller space)
python quick_tournament.py --players 5 \
  --preset competitive \
  --sample 100 \
  --no-duplicates \
  --fast
```

### Maximum accuracy (slower)
```bash
# More matches and ticks for better stats
python quick_tournament.py --players 5 \
  --preset competitive \
  --sample 200 \
  --matches 5 \
  --ticks 2000 \
  --win-score 5
```

---

## Troubleshooting

**"Still takes too long"**
- Reduce `--sample` (try 50 instead of 100)
- Use `--fast` flag
- Reduce `--matches` (try 2 instead of 3)
- Reduce `--ticks` (try 800-1000)

**"Results seem random/inconsistent"**
- Increase `--sample` (try 150-200)
- Increase `--matches` (try 4-5)
- Increase `--ticks` (try 1500-2000)
- Run multiple times and compare

**"Not testing the combinations I want"**
- Use `--strategy coverage` for balanced agent representation
- Use `--agents` to limit to specific agent types
- Increase `--sample` to test more combinations

---

## Your Specific Case

For your 5v5 tournament with competitive preset:

### Quick Test (2-3 minutes)
```bash
python quick_tournament.py --players 5 --preset competitive --sample 80 --fast
```

### Balanced (5-7 minutes)
```bash
python quick_tournament.py --players 5 --preset competitive --sample 150 --matches 3
```

### Thorough (10-15 minutes)
```bash
python quick_tournament.py --players 5 --preset competitive \
  --sample 200 \
  --matches 4 \
  --ticks 1500 \
  --output thorough_5v5.json
```

---

## Summary

| Approach | Combinations | Matches | Time | Accuracy |
|----------|-------------|---------|------|----------|
| Full tournament | 7,776 | 30M+ | 17+ hours | 100% |
| Sample 50 (fast) | 50 | ~2,550 | 2 min | Good |
| Sample 100 (fast) | 100 | ~5,050 | 3-4 min | Very Good |
| Sample 200 (normal) | 200 | ~20,100 | 10-12 min | Excellent |

**Recommendation**: Start with sample 100 + fast mode, then increase if needed!
