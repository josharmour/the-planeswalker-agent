# Example Test Audit Output

This file shows what the improved audit logging looks like when running tests.

## Example: Commander Synergy Test

```bash
$ pytest tests/integration/test_commander.py::TestCommanderQueries::test_commander_synergy_atraxa -v -s
```

### Output:

```
================================================================================
TEST AUDIT: Commander Synergy - Atraxa
================================================================================

QUERY:
  What cards work well with Atraxa, Praetors' Voice?

SOURCE URL (for manual audit):
  https://edhrec.com/commanders/atraxa-praetors-voice

EXPECTED DATA FROM SOURCE:
  source: EDHREC
  commander: Atraxa, Praetors' Voice
  top_cards:
    1. Tekuthal, Inquiry Dominus
    2. Evolution Sage
    3. Karn's Bastion
    4. Ezuri, Stalker of Spheres
    5. Vraska, Betrayal's Sting
    6. Thrummingbird
    7. Inexorable Tide
    8. Tezzeret's Gambit
    9. Flux Channeler
    10. Vorinclex, Monstrous Raider
  themes:
    1. {'name': 'Infect', 'slug': 'infect', 'url': 'https://edhrec.com/themes/infect'}
    2. {'name': 'Planeswalkers', 'slug': 'planeswalkers', 'url': 'https://edhrec.com/themes/planeswalkers'}
    3. {'name': '+1/+1 Counters', 'slug': 'plus-1-plus-1-counters', 'url': 'https://edhrec.com/themes/plus-1-plus-1-counters'}
    ... and 178 more

================================================================================

[Agent processing output...]

================================================================================
TEST AUDIT: Commander Synergy - Atraxa
================================================================================

QUERY:
  What cards work well with Atraxa, Praetors' Voice?

SOURCE URL (for manual audit):
  https://edhrec.com/commanders/atraxa-praetors-voice

EXPECTED DATA FROM SOURCE:
  [Same as above...]

AGENT RESPONSE:
  Atraxa, Praetors' Voice is an excellent commander for proliferate and
  counter-based strategies. Based on EDHREC data and card synergies, here are
  some top cards that work well with Atraxa:

  **Proliferate Engines:**
  - Evolution Sage - Triggers proliferate on every land drop
  - Thrummingbird - Evasive creature with proliferate
  - Inexorable Tide - Proliferates whenever you cast a spell

  **Counter Doublers:**
  - Vorinclex, Monstrous Raider - Doubles counters you put on permanents
  - Tekuthal, Inquiry Dominus - Proliferate an additional two times

  **Planeswalkers:**
  Atraxa excels with planeswalkers due to proliferate adding loyalty counters:
  - Vraska, Betrayal's Sting - Generates poison counters and card advantage
  - Tezzeret's Gambit - Draws cards while proliferating

  **Utility Lands:**
  - Karn's Bastion - Repeatable proliferate on a land

  These cards synergize with Atraxa's proliferate ability and can support
  various strategies including +1/+1 counters, planeswalker superfriends, and
  even infect.

================================================================================

PASSED
```

## Benefits

With this improved audit logging, you can now:

1. **See the query** - Know exactly what question was asked
2. **View expected data** - See what data sources say (EDHREC, MTGGoldfish, 17Lands, etc.)
3. **Read agent response** - See the actual response your agent generated
4. **Verify accuracy** - Compare agent response against expected data and source URLs
5. **Audit quality** - Evaluate if the response is helpful, accurate, and complete

## Quick Audit Checklist

For each test, check:
- ✅ Does the agent response mention cards from the expected data?
- ✅ Is the response relevant to the query?
- ✅ Does it provide useful, actionable information?
- ✅ Can you verify the information at the source URL?
- ✅ Is the response up-to-date with current metagame/data?
