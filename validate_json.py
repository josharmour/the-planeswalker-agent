
import json
import sys

filename = "data/synergy_graph.json"

try:
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
        print(f"File Size: {len(content)} chars")
        
        try:
            json.loads(content)
            print("JSON is valid.")
        except json.JSONDecodeError as e:
            print(f"JSON Error: {e}")
            start = max(0, e.pos - 50)
            end = min(len(content), e.pos + 50)
            print(f"Context: {content[start:end]}")
            
except Exception as e:
    print(f"File Error: {e}")
