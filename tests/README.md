# Planeswalker Agent - Integration Test Suite

Comprehensive integration tests that validate the Planeswalker Agent's responses against real MTG data sources.

## 🆕 New Features

### 🔄 Dynamic Testing
Tests now fetch **live metagame data** and adapt to current trends:
- Trending commanders from EDHREC
- Current Modern/Standard/Pioneer top decks
- Latest draft set data from 17Lands
- Popular cards and synergies

**See [DYNAMIC_TESTING.md](DYNAMIC_TESTING.md) for full details**

### 📊 Audit Logging
Every test now shows:
- Query being tested
- Expected data from sources
- **Agent's actual response**
- Source URL for manual verification

**See [AUDIT_LOGGING.md](AUDIT_LOGGING.md) for full details**

## Overview

This test suite validates that the agent correctly integrates with and returns accurate information from:
- **Scryfall**: Card database and semantic search
- **EDHREC**: Commander statistics and recommendations (live trending data)
- **17Lands**: Limited/Draft format win rates and archetypes (current sets)
- **MTGGoldfish**: Constructed format metagame data (current meta)

## Test Categories

### 1. Commander Queries (`test_commander.py`)
**Dynamic Tests:**
- **test_commander_synergy_trending** 🔄: Uses #1 trending commander from EDHREC
- **test_commander_recommendation_dynamic** 🔄: Random theme selection

**Static Tests:**
- **test_commander_synergy_atraxa**: Validates synergy recommendations against EDHREC data
- **test_commander_recommendation**: Tests commander recommendations for +1/+1 counters
- **test_commander_trending**: Validates trending commander information

### 2. Constructed Metagame (`test_constructed_metagame.py`)
**Dynamic Tests:**
- **test_metagame_dynamic** 🔄: Parametrized test for Modern/Standard/Pioneer with current top decks

**Static Tests:**
- **test_modern_metagame**: Validates Modern format metagame data from MTGGoldfish
- **test_standard_metagame**: Tests Standard format recommendations
- **test_pioneer_metagame**: Validates Pioneer format tier list

### 3. Limited/Draft (`test_limited.py`)
**Dynamic Tests:**
- **test_draft_color_pairs_dynamic** 🔄: Random recent set with live 17Lands color pair data

**Static Tests:**
- **test_draft_color_pairs_mkm**: Validates color pair win rates for MKM
- **test_draft_archetype**: Tests draft archetype recommendations for LCI
- **test_sealed_format**: Validates sealed format strategy advice for WOE

### 4. Semantic Card Search (`test_semantic_search.py`)
- **test_card_draw_search**: Tests semantic search for card advantage
- **test_removal_spell_search**: Validates removal spell recommendations
- **test_tribal_search**: Tests tribal synergy card search
- **test_mechanic_search**: Validates mechanic-specific card search

### 5. Synergy Detection (`test_synergy.py`)
**Dynamic Tests:**
- **test_synergy_trending_card** 🔄: Random trending/popular card synergies

**Static Tests:**
- **test_atraxa_synergies**: Validates card synergy detection for Atraxa
- **test_sacrifice_synergies**: Tests sacrifice strategy synergies
- **test_graveyard_synergies**: Validates graveyard strategy card recommendations

## Setup

### Prerequisites

1. **Python 3.8+** required
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Prepare data** (required for tests to run):
   ```bash
   # Download Scryfall data and build vector store
   python ingest_data.py

   # Build synergy graph (optional but recommended)
   python build_synergy_graph.py
   ```

4. **Environment variables** (create `.env` file):
   ```bash
   # Required for LLM-powered synthesis
   ANTHROPIC_API_KEY=your_api_key_here
   # or
   OPENAI_API_KEY=your_api_key_here
   ```

### Data Requirements

The tests require the following data to be present:

| Data Source | Location | Required | Setup Command |
|-------------|----------|----------|---------------|
| Scryfall cards | `data/oracle-cards.json` | Yes | `python ingest_data.py` |
| ChromaDB vector store | `data/chroma_db/` | Yes | `python ingest_data.py` |
| Synergy graph | `data/synergy_graph.json` | No* | `python build_synergy_graph.py` |
| EDHREC cache | `data/edhrec_cache/` | No** | Auto-created on first query |
| 17Lands cache | `data/17lands_cache/` | No** | Auto-created on first query |
| MTGGoldfish cache | `data/mtggoldfish_cache/` | No** | Auto-created on first query |

*Synergy tests will be skipped if graph is not available
**Caches are created automatically when tests run

## Running Tests

### Quick Start

Run all integration tests with the custom test runner:

```bash
python tests/run_integration_tests.py
```

This will:
1. Run all integration test files
2. Display verbose output for each test
3. Show a summary of passed/failed tests
4. Report success if ≥8/10 tests pass (80% threshold)

### Using pytest Directly

You can also run tests using pytest:

```bash
# Run all integration tests with audit logging
pytest tests/integration/ -v -s

# Run only dynamic tests (recommended for current validation)
pytest tests/integration/ -k "dynamic" -v -s

# Run only static tests (baseline validation)
pytest tests/integration/ -k "not dynamic" -v -s

# Run specific test file
pytest tests/integration/test_commander.py -v -s

# Run specific test
pytest tests/integration/test_commander.py::TestCommanderQueries::test_commander_synergy_trending -v -s

# Run tests with detailed output
pytest tests/integration/ -vv --tb=long -s
```

**Note:** The `-s` flag is important for seeing audit logging output!

### Test Markers (Optional)

Tests can be run by category using markers:

```bash
# Run only commander tests
pytest tests/integration/ -v -m commander

# Run only limited format tests
pytest tests/integration/ -v -m limited

# Skip slow tests
pytest tests/integration/ -v -m "not slow"
```

## Success Criteria

The test suite is considered **successful** if:
- ✅ At least **8 out of 10 tests pass** (80% pass rate)
- ✅ No critical infrastructure failures (ChromaDB, vector store, agent initialization)
- ✅ At least one test passes in each category:
  - Commander queries
  - Constructed metagame
  - Limited/Draft
  - Semantic search
  - Synergy detection

### Why 80% Threshold?

The 80% threshold accounts for:
- **External API availability**: EDHREC, 17Lands, and MTGGoldfish may be temporarily unavailable
- **Data staleness**: Metagame data changes frequently; exact matches may fail
- **Set rotation**: Some sets may rotate out of Standard/Modern
- **Rate limiting**: API rate limits may cause occasional failures

Tests that depend on external data sources will automatically skip if data is unavailable.

## Interpreting Results

### Successful Test Output
```
tests/integration/test_commander.py::TestCommanderQueries::test_commander_synergy_atraxa PASSED
```

### Skipped Test
```
tests/integration/test_synergy.py::TestSynergyDetection::test_atraxa_synergies SKIPPED (Synergy graph not available)
```
*Skipped tests do not count toward the 8/10 threshold*

### Failed Test
```
tests/integration/test_commander.py::TestCommanderQueries::test_commander_trending FAILED
AssertionError: Agent should mention at least 2 EDHREC staples for Atraxa (found 1)
```

## Troubleshooting

### Common Issues

#### 1. ChromaDB Not Found
```
Error: ChromaDB not initialized
```
**Solution**: Run `python ingest_data.py` to build the vector store

#### 2. API Rate Limiting
```
Error: 429 Too Many Requests
```
**Solution**: Wait a few minutes and re-run tests. External APIs may have rate limits.

#### 3. Missing API Keys
```
Error: ANTHROPIC_API_KEY not set
```
**Solution**: Create a `.env` file with your API key:
```bash
echo "ANTHROPIC_API_KEY=your_key_here" > .env
```

#### 4. Tests Skip Due to Missing Data
```
SKIPPED (EDHREC data unavailable)
```
**Solution**: This is expected behavior. Tests skip gracefully when external data is unavailable.

#### 5. Import Errors
```
ModuleNotFoundError: No module named 'mtg_agent'
```
**Solution**: Ensure you're running tests from the project root directory

### Debug Mode

Run tests with maximum verbosity:

```bash
pytest tests/integration/ -vv --tb=long --capture=no
```

This will show:
- Full test names and docstrings
- Complete assertion failure details
- Print statements from tests
- Full stack traces

## Test Development

### Adding New Tests

1. Create a new test file in `tests/integration/`:
   ```python
   # tests/integration/test_new_feature.py
   import pytest
   from mtg_agent import run_query

   class TestNewFeature:
       def test_new_functionality(self, agent):
           query = "Your test query"
           result = run_query(agent, query)
           assert result["final_response"], "Should return response"
   ```

2. Add markers in `pytest.ini` if needed:
   ```ini
   markers =
       new_feature: Tests for new functionality
   ```

3. Document in this README

### Test Best Practices

- **Use fixtures**: Share the `agent` fixture across tests to avoid reloading
- **Skip gracefully**: Use `pytest.skip()` when external data is unavailable
- **Test real data**: Always fetch comparison data from real sources
- **Fuzzy matching**: Use partial matches for card names (agent may abbreviate)
- **Timeouts**: Expect tests to take 5-30 seconds each (LLM latency)
- **Assertions**: Include descriptive messages in assertions

## CI/CD Integration

The test suite can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run integration tests
  run: |
    python ingest_data.py --limit 1000  # Use limited dataset for CI
    python tests/run_integration_tests.py
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

## Performance

Expected test execution times:

| Test File | Tests | Avg Time |
|-----------|-------|----------|
| `test_commander.py` | 3 | ~30s |
| `test_constructed_metagame.py` | 3 | ~25s |
| `test_limited.py` | 3 | ~25s |
| `test_semantic_search.py` | 4 | ~35s |
| `test_synergy.py` | 3 | ~30s |
| **Total** | **16** | **~2-3 min** |

First run will be slower due to:
- Vector store initialization (~2-3s)
- Model loading (sentence-transformers, ~2s)
- Cache warming for external APIs

## Maintenance

### Updating Test Data

Tests should be reviewed quarterly to ensure:
- Set codes are current (update MKM, LCI, WOE references as new sets release)
- Metagame expectations match current meta (Tier 1 decks change)
- Known card lists are updated (new staples, bans, rotations)

### Monitoring External APIs

The test suite depends on:
- `https://api.17lands.com` - Limited format data
- `https://edhrec.com` - Commander statistics
- `https://www.mtggoldfish.com` - Constructed metagame
- `https://api.scryfall.com` - Card database (ingestion only)

If any service is down, tests will gracefully skip those cases.

## Documentation

- **[DYNAMIC_TESTING.md](DYNAMIC_TESTING.md)** - Dynamic testing strategy and benefits
- **[AUDIT_LOGGING.md](AUDIT_LOGGING.md)** - Audit logging format and usage
- **[EXAMPLE_OUTPUT.md](EXAMPLE_OUTPUT.md)** - Example test outputs

## Support

For issues or questions:
1. Check the [main README](../README.md) for agent setup
2. Review test output and error messages (especially AGENT RESPONSE in audit logs)
3. Enable debug mode with `-vv --tb=long -s`
4. Check that data files exist in `data/` directory
5. Visit source URLs from audit logs to verify expected data

## License

Same as parent project.
