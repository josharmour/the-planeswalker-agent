# Dynamic Testing Strategy

## Overview

The test suite now includes **dynamic tests** that fetch live metagame data and test against current trends, ensuring tests stay relevant as the game evolves.

## Philosophy

### Static Tests (Legacy)
- Test against hardcoded expectations
- Example: "Atraxa should mention proliferate"
- **Problem**: Become outdated as metagame shifts

### Dynamic Tests (New)
- Fetch current trending data at test runtime
- Generate queries based on live metagame
- Test against actual current expectations
- **Benefit**: Always test against reality

## Dynamic Test Categories

### 1. Commander Tests

#### `test_commander_synergy_trending`
Fetches the **#1 trending commander** from EDHREC and tests synergy recommendations.

**What it does:**
1. Fetches top trending commanders (last 7 days)
2. Uses #1 commander to generate query
3. Fetches that commander's EDHREC page for expected cards
4. Tests if agent mentions relevant synergies

**Example Test Flow:**
```python
# Runtime fetches current data
trending = ["The Ur-Dragon", "Edgar Markov", "Atraxa"]  # This week's top 3

# Generates query for #1
query = "What cards work well with The Ur-Dragon?"

# Fetches expected cards from EDHREC
expected_cards = ["Dragon's Hoard", "Scion of the Ur-Dragon", "Dragonlord's Servant", ...]

# Tests agent response
assert agent_mentions(expected_cards) or discusses_dragon_theme
```

#### `test_commander_recommendation_dynamic`
Tests commander recommendations with randomized themes.

**Themes Tested:**
- +1/+1 counters
- Tokens
- Graveyard
- Artifacts
- Tribal

**What it does:**
1. Randomly picks a theme
2. Generates query: "What's a good commander for a {theme} deck?"
3. Tests if response discusses that theme

### 2. Constructed Metagame Tests

#### `test_metagame_dynamic`
**Parametrized test** that runs for Modern, Standard, and Pioneer.

**What it does:**
1. Fetches CURRENT metagame from MTGGoldfish for each format
2. Generates query: "What are the top decks in {format}?"
3. Tests if agent mentions actual current top decks

**Example:**
```
Week 1: Tests if agent mentions "Boros Energy" (current #1 Modern deck)
Week 2: Tests if agent mentions "Izzet Prowess" (new #1 after shifts)
```

**Why this matters:**
- Metagames shift weekly
- Static tests would fail when metagame changes
- Dynamic tests adapt automatically

### 3. Limited/Draft Tests

#### `test_draft_color_pairs_dynamic`
Tests draft advice with a **randomly selected recent set**.

**Sets Rotated:**
- MKM (Murders at Karlov Manor)
- LCI (The Lost Caverns of Ixalan)
- WOE (Wilds of Eldraine)
- LTR (Lord of the Rings)
- MOM (March of the Machine)

**What it does:**
1. Randomly picks a set from rotation
2. Fetches 17Lands color pair win rates
3. Generates query: "What are the best color pairs in {set} draft?"
4. Tests if agent mentions actual top-performing colors

**Example:**
```
Test picks: MKM
Fetches: Boros (58.9%), Selesnya (57.3%), Simic (57.0%)
Query: "What are the best color pairs in Murders at Karlov Manor draft?"
Expects: Agent mentions Boros, Selesnya, or Simic
```

### 4. Synergy Tests

#### `test_synergy_trending_card`
Tests synergy detection with **currently trending cards**.

**What it does:**
1. Fetches trending commanders (as proxy for popular cards)
2. Randomly selects one
3. Queries synergies from local synergy graph
4. Tests if agent mentions those synergies

**Fallback cards** (if trending data unavailable):
- Sol Ring
- Rhystic Study
- Arcane Signet
- Cyclonic Rift
- Smothering Tithe

### Run All Consolidated Dynamic Tests
```bash
pytest tests/integration/test_dynamic_consolidated.py -v -s
```

### Run Specific Test Categories
```bash
# Trending commander test
pytest tests/integration/test_dynamic_consolidated.py::TestDynamicConsolidated::test_commander_synergy_trending -v -s

# Dynamic metagame tests
pytest tests/integration/test_dynamic_consolidated.py::TestDynamicConsolidated::test_metagame_dynamic -v -s

# Dynamic draft test
pytest tests/integration/test_dynamic_consolidated.py::TestDynamicConsolidated::test_draft_color_pairs_dynamic -v -s

# Specific static baseline test
pytest tests/integration/test_dynamic_consolidated.py::TestDynamicConsolidated::test_commander_synergy_atraxa -v -s
```

### Run Legacy (Static) Tests
```bash
# These still exist for baseline validation
pytest tests/integration/ -k "not dynamic" -v -s
```

## Test Output Example

### Dynamic Commander Test
```
================================================================================
TEST AUDIT: Commander Synergy - The Ur-Dragon (Trending #1)
================================================================================

QUERY:
  What cards work well with The Ur-Dragon?

SOURCE URL (for manual audit):
  https://edhrec.com/commanders/the-ur-dragon

EXPECTED DATA FROM SOURCE:
  source: EDHREC (Live Trending Data)
  commander: The Ur-Dragon
  trending_rank: 1
  top_cards:
    1. Dragon's Hoard
    2. Scion of the Ur-Dragon
    3. Dragonlord's Servant
    4. Urza's Incubator
    5. Cavern of Souls
    ...

AGENT RESPONSE:
  The Ur-Dragon is an exceptional commander for dragon tribal strategies.
  Here are some key synergy cards:

  **Mana Acceleration:**
  - Dragon's Hoard provides both ramp and card draw
  - Urza's Incubator reduces dragon costs significantly

  **Dragon Support:**
  - Scion of the Ur-Dragon enables tutoring and graveyard strategies
  - Dragonlord's Servant reduces costs by 1

  **Protection:**
  - Cavern of Souls makes dragons uncounterable

  These cards synergize with The Ur-Dragon's eminence ability and tribal theme.

================================================================================

PASSED ✓
```

## Benefits of Dynamic Testing

### 1. Always Current
- Tests adapt to metagame shifts
- No manual updates needed
- Validates against reality

### 2. Realistic Validation
- Tests what users actually ask
- Validates against current online data
- Catches drift from real-world sources

### 3. Comprehensive Coverage
- Parametrized tests cover multiple formats
- Randomized tests cover variety of cards/themes
- Both breadth and depth

### 4. Easy Auditing
- Audit logs show what was tested
- Source URLs for manual verification
- Agent response for quality check

## Test Rotation Strategy

### How Tests Vary

1. **Commander Tests**
   - Different trending commander each week
   - Different theme each run (random)

2. **Metagame Tests**
   - Different top decks as meta evolves
   - All 3 formats tested each run

3. **Draft Tests**
   - Random set selection each run
   - Different color pairs as data updates

4. **Synergy Tests**
   - Random trending card each run

### Test Stability

While queries vary, tests remain stable because:
- **Flexible assertions**: Check for ANY top card, not specific ones
- **Multiple validation paths**: Pass if mentions cards OR themes OR substantial content
- **Graceful degradation**: Skip if data unavailable

## Monitoring Test Health

### When Tests Fail

Dynamic test failure could mean:

1. **Agent Issue** - Agent not using correct data sources
2. **Data Issue** - External API unavailable
3. **Metagame Shift** - Very rapid meta change (rare)

### Debugging Failed Dynamic Tests

```bash
# Run with full audit logging
pytest tests/integration/test_commander.py::TestCommanderQueries::test_commander_synergy_trending -v -s

# Check:
# 1. What was the query?
# 2. What was expected from source?
# 3. What did agent respond?
# 4. Visit source URL to verify data
```

### Test Skip Reasons

Tests skip gracefully when:
- External API unavailable (EDHREC, MTGGoldfish, 17Lands)
- Data unavailable for specific format/set
- Synergy graph not built locally

## Future Enhancements

### Potential Additions

1. **More Parametrization**
   - Test top 3 trending commanders (not just #1)
   - Test multiple draft sets in parallel

2. **Time-Based Testing**
   - Track test results over time
   - Alert on consistent failures
   - Trend agent accuracy

3. **Data Caching**
   - Cache trending data per test session
   - Reduce API calls
   - Faster test runs

4. **Custom Assertions**
   - Fuzzy card name matching
   - Semantic similarity checks
   - Response quality scoring

## Comparison: Static vs Dynamic

| Aspect | Static Tests | Dynamic Tests |
|--------|-------------|---------------|
| **Data Source** | Hardcoded | Live API calls |
| **Maintenance** | Manual updates | Self-updating |
| **Relevance** | Decays over time | Always current |
| **Speed** | Faster | Slightly slower (API calls) |
| **Stability** | Very stable | Stable with flexible assertions |
| **Coverage** | Fixed scenarios | Rotating scenarios |
| **Best For** | Baseline validation | Real-world validation |

## Best Practices

1. **Run Both Types**
   - Keep some static tests for baseline
   - Add dynamic tests for current validation

2. **Monitor Skips**
   - Track which tests skip frequently
   - Investigate if too many skips

3. **Review Audit Logs**
   - Regularly check what queries are tested
   - Verify agent responses make sense
   - Visit source URLs periodically

4. **Update Rotation**
   - Add new sets to draft rotation
   - Add new themes to commander rotation
   - Keep lists current

## Conclusion

Dynamic testing ensures your MTG agent stays accurate as the game evolves. Combined with audit logging, you have full visibility into:
- What's being tested
- What's expected
- What the agent actually responds
- Where to verify manually

This approach provides confidence that your agent works with **current** metagame data, not just historical snapshots.
