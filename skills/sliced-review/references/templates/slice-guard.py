#!/usr/bin/env python3
"""Slice guard: file hashes per slice + a mechanical check of every file:line a lane cites.

  slice-guard.py record <kit> <slice>            save SHA-256 of each file the slice lists
  slice-guard.py check  <kit> <slice> <report>   compare hashes, check every citation in a report

<kit> holds slices/<slice>.md (files listed after a line with "exactly these files" ending in ":", until a blank line)
and WORKDIR (one line: the repo path; else env REPO). Hashes go to <kit>/hashes/<slice>.json.

check prints one JSON object and a one-line summary on stderr:
  stale        files that changed since record -> findings on them are STALE: recheck vs current code
  citations    every path:LINE in the report with a status:
               ok | out-of-slice (file exists, not in the slice list -> route to x01-chains/triage)
               | missing-file | bad-line (beyond the end of the file)
               plus quote_not_near: true when none of the line's quoted code is within +-5 lines
               of a line it cites (the judges re-read that one; it is not dropped)
A finding whose every citation is missing-file or bad-line is dropped before triage.
Python 3 stdlib only. Never edits the repo.
"""
import hashlib, json, os, re, sys

NEAR = 5
CITE = re.compile(r"(?<![\w/.-])((?:[\w.-]+/)*[\w.-]+\.[A-Za-z0-9]{1,6}):(\d+)(?:-(\d+))?")
CODE = re.compile(r"`([^`]{6,120})`")


def repo_of(kit):
    p = os.path.join(kit, "WORKDIR")
    r = open(p).read().strip() if os.path.exists(p) else os.environ.get("REPO", "")
    if not r or not os.path.isdir(os.path.expanduser(r)):
        sys.exit(f"slice-guard: no repo (WORKDIR in {kit} or env REPO)")
    return os.path.expanduser(r)


def slice_files(kit, sl):
    text = open(os.path.join(kit, "slices", f"{sl}.md")).read()
    # any line with "exactly these files" that ends in ":" ("Read exactly these files:",
    # "…then exactly these files (the entry files it cites):"), then the list up to a blank line
    m = re.search(r"exactly these files[^\n]*:[ \t]*\n(.*?)(?:\n\s*\n|\Z)", text, re.S | re.I)
    if not m:
        sys.exit(f"slice-guard: no 'exactly these files:' list in slices/{sl}.md")
    return [l.strip().strip("-* `") for l in m.group(1).splitlines() if l.strip()]


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 16), b""):
            h.update(b)
    return h.hexdigest()


def record(kit, sl):
    repo = repo_of(kit)
    out = {f: (sha(os.path.join(repo, f)) if os.path.isfile(os.path.join(repo, f)) else None)
           for f in slice_files(kit, sl)}
    os.makedirs(os.path.join(kit, "hashes"), exist_ok=True)
    json.dump(out, open(os.path.join(kit, "hashes", f"{sl}.json"), "w"), indent=1)
    missing = [f for f, h in out.items() if h is None]
    print(f"recorded {len(out)} files for {sl}" + (f"; MISSING in repo: {missing}" if missing else ""))


def resolve(repo, ref, listed):
    """repo-relative path for a cited name: exact, else a unique slice-list or repo match by suffix."""
    if os.path.isfile(os.path.join(repo, ref)):
        return ref
    hits = [f for f in listed if f.endswith("/" + ref) or f == ref]
    if len(hits) == 1:
        return hits[0]
    base = os.path.basename(ref)
    found = []
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "vendor", "dist", "build")]
        if base in files:
            rel = os.path.relpath(os.path.join(root, base), repo)
            if rel.endswith(ref):
                found.append(rel)
        if len(found) > 1:
            break
    return found[0] if len(found) == 1 else None


def norm(code):
    return code.strip().rstrip("()").lstrip("$").strip()


def check(kit, sl, report):
    repo = repo_of(kit)
    listed = slice_files(kit, sl)
    hp = os.path.join(kit, "hashes", f"{sl}.json")
    old = json.load(open(hp)) if os.path.exists(hp) else {}
    stale = [f for f, h in old.items()
             if h and (not os.path.isfile(os.path.join(repo, f)) or sha(os.path.join(repo, f)) != h)]
    cache, cites = {}, []
    for ln, line in enumerate(open(report, errors="ignore").read().splitlines(), 1):
        refs = CITE.findall(line)
        if not refs:
            continue
        codes = [norm(c) for c in CODE.findall(line) if not CITE.search(c)]
        codes = [c for c in codes if len(c) >= 6]
        recs, windows = [], []
        for ref, a, b in refs:
            a = int(a); b = int(b or a)
            path = resolve(repo, ref, listed)
            rec = {"report_line": ln, "ref": f"{ref}:{a}" + (f"-{b}" if b != a else ""), "file": path}
            if not path:
                rec["status"] = "missing-file"
            else:
                if path not in cache:
                    cache[path] = open(os.path.join(repo, path), errors="ignore").read().splitlines()
                src = cache[path]
                if a > len(src):
                    rec["status"] = "bad-line"
                else:
                    windows.append("\n".join(src[max(0, a - 1 - NEAR): b + NEAR]))
                    rec["status"] = "ok" if path in listed else "out-of-slice"
                    if path in stale:
                        rec["stale"] = True
            recs.append(rec)
        # the line's quoted code must show up near at least one of the lines it cites
        if codes and windows and not any(c in w for c in codes for w in windows):
            for rec in recs:
                if rec["status"] in ("ok", "out-of-slice"):
                    rec["quote_not_near"] = True
        cites += recs
    res = {"slice": sl, "report": report, "stale": stale, "citations": cites}
    print(json.dumps(res, indent=1))
    bad = sum(1 for c in cites if c["status"] in ("missing-file", "bad-line"))
    far = sum(1 for c in cites if c.get("quote_not_near"))
    oos = sum(1 for c in cites if c["status"] == "out-of-slice")
    print(f"{sl}: {len(cites)} citations, {bad} bad, {far} quote not near, {oos} out-of-slice, "
          f"{len(stale)} stale files",
          file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "record":
        record(sys.argv[2], sys.argv[3])
    elif len(sys.argv) >= 5 and sys.argv[1] == "check":
        check(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        sys.exit(__doc__)
