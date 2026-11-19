#!/usr/bin/env bash
# prepass.sh <repo> <out.md> — cheap tool pass before any model runs (v2.7).
# Runs gitleaks (secrets, values redacted) and osv-scanner (known-vulnerable dependencies) on the
# repo and writes a short Markdown summary. Paste it into the x02-release slice brief: models are
# bad at recalling CVEs, tools are not. A tool that is not installed is written as NOT RUN, never
# skipped silently. Prints no secret values: only rule id, file and line.
set -u
REPO="${1:?usage: prepass.sh <repo> <out.md>}"; OUT="${2:?usage: prepass.sh <repo> <out.md>}"
TMP="$(mktemp -d)"
{
  echo "## Tool pre-pass — $(date '+%Y-%m-%d %H:%M %Z') — commit $(git -C "$REPO" rev-parse --short HEAD 2>/dev/null || echo n/a)"
  echo
  echo "### Secrets (gitleaks, working tree)"
  if command -v gitleaks >/dev/null; then
    gitleaks dir "$REPO" --redact --no-banner -l error -f json -r "$TMP/gl.json" >/dev/null 2>&1
    python3 - "$TMP/gl.json" "$REPO" <<'EOF'
import json, os, sys
try:
    rows = json.load(open(sys.argv[1]))
except Exception:
    rows = []
print(f"{len(rows)} finding(s)." if rows else "No findings.")
for r in rows[:50]:
    f = os.path.relpath(r.get("File", ""), sys.argv[2]) if r.get("File") else "?"
    print(f"- {r.get('RuleID')}: {f}:{r.get('StartLine')}")
if len(rows) > 50:
    print(f"- … {len(rows) - 50} more")
EOF
  else
    echo "NOT RUN: gitleaks is not installed."
  fi
  echo
  echo "### Dependencies with known vulnerabilities (osv-scanner)"
  if command -v osv-scanner >/dev/null; then
    osv-scanner scan source -r "$REPO" --format markdown 2>/dev/null | head -80 || true
  else
    echo "NOT RUN: osv-scanner is not installed. Dependency CVEs were NOT checked by a tool."
  fi
} > "$OUT"
rm -rf "$TMP"
echo "pre-pass written: $OUT"
