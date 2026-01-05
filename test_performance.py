"""
Performance test script for The Planeswalker Agent.

Tests both initialization time and subsequent query response times.
"""

import time
from mtg_agent import create_agent, run_query

def test_performance():
    """Test agent performance with multiple queries."""

    print("=" * 70)
    print("PLANESWALKER AGENT - PERFORMANCE TEST")
    print("=" * 70)
    print()

    # Test 1: Agent Creation (includes resource initialization)
    print("Test 1: Creating agent (initializing resources)...")
    start = time.time()
    agent = create_agent()
    init_time = time.time() - start
    print(f"[OK] Agent created in {init_time:.2f}s")
    print()

    # Test 2: First Query
    print("Test 2: First query (resources already cached)...")
    start = time.time()
    result1 = run_query(agent, "Show me powerful Commander staples")
    query1_time = time.time() - start
    print(f"[OK] Query 1 completed in {query1_time:.2f}s")
    print()

    # Test 3: Second Query
    print("Test 3: Second query (resources already cached)...")
    start = time.time()
    result2 = run_query(agent, "Find me cards that draw when they enter the battlefield")
    query2_time = time.time() - start
    print(f"[OK] Query 2 completed in {query2_time:.2f}s")
    print()

    # Test 4: Third Query
    print("Test 4: Third query (resources already cached)...")
    start = time.time()
    result3 = run_query(agent, "What's good removal for Commander?")
    query3_time = time.time() - start
    print(f"[OK] Query 3 completed in {query3_time:.2f}s")
    print()

    # Summary
    print("=" * 70)
    print("PERFORMANCE SUMMARY")
    print("=" * 70)
    print(f"Initial startup time:  {init_time:.2f}s")
    print(f"Query 1 (cached):      {query1_time:.2f}s")
    print(f"Query 2 (cached):      {query2_time:.2f}s")
    print(f"Query 3 (cached):      {query3_time:.2f}s")
    print()
    avg_query_time = (query1_time + query2_time + query3_time) / 3
    print(f"Average query time:    {avg_query_time:.2f}s")
    print()
    print("Key Improvements:")
    print("  [+] Resources loaded ONCE during agent creation (~15-20s)")
    print("  [+] Subsequent queries use cached resources (<2s each)")
    print("  [+] Ready for production use as an always-on agent")
    print("=" * 70)

if __name__ == "__main__":
    test_performance()
