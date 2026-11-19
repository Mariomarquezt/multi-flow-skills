#!/usr/bin/env python3
"""claude_extract.py <claude -p json> — print the answer; print the usage line on stderr for the ledger."""
import json, sys
d = json.load(open(sys.argv[1]))
print(d.get("result", ""))
u = d.get("usage", {})
print(f"claude usage: cost={d.get('total_cost_usd')} in={u.get('input_tokens')} cache_read={u.get('cache_read_input_tokens')} "
      f"cache_write={u.get('cache_creation_input_tokens')} out={u.get('output_tokens')} turns={d.get('num_turns')}", file=sys.stderr)
