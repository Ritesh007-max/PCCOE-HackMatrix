import json
import re

with open('data/interim/sample_10_schemes.json', 'r', encoding='utf-8') as f:
    schemes = json.load(f)

for s in schemes:
    ascii_name = s['scheme_name'].encode('ascii', errors='replace').decode('ascii')
    print(f"=== {s['slug']} : {ascii_name} ===")
    elig = s['eligibility'] if s.get('eligibility') is not None else ""
    excl = s['exclusions'] if s.get('exclusions') is not None else ""
    
    elig_str = str(elig) if elig is not None else ""
    excl_str = str(excl) if excl is not None else ""
    
    # Split clauses
    elig_clauses = [c.strip() for c in re.split(r';|\n', elig_str) if c.strip() and c.strip() != 'nan']
    excl_clauses = [c.strip() for c in re.split(r';|\n', excl_str) if c.strip() and c.strip() != 'nan']
    
    print(f"  Eligibility Clauses ({len(elig_clauses)}):")
    for i, c in enumerate(elig_clauses[:5], 1):
        ascii_c = c.encode('ascii', errors='replace').decode('ascii')
        print(f"    {i}. {ascii_c[:120]}")
    if len(elig_clauses) > 5:
        print(f"    ... and {len(elig_clauses) - 5} more clauses")
        
    print(f"  Exclusion Clauses ({len(excl_clauses)}):")
    for i, c in enumerate(excl_clauses[:5], 1):
        ascii_c = c.encode('ascii', errors='replace').decode('ascii')
        print(f"    {i}. {ascii_c[:120]}")
    if len(excl_clauses) > 5:
        print(f"    ... and {len(excl_clauses) - 5} more clauses")
    print()
