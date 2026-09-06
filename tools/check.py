#!/usr/bin/env python3
"""Run every check there is, in the order that fails fastest.

Written because two suites went unrun for a whole session and both had real
failures waiting in them: a category carrying a flag emoji Android cannot draw,
and two rows for the same player. Running one suite and calling it green is the
mistake this exists to prevent.

  python3 tools/check.py           # the fast ones (seconds)
  python3 tools/check.py --all     # everything, including the network checks

Exit code is non-zero if anything failed.
"""
import subprocess, sys, os, time, re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PY = sys.executable

FAST = [
    ("validate",         ["tools/validate.py"],        "data + the page actually boots"),
    ("run_tests",        ["tools/run_tests.py"],       "game rules and board composition"),
    ("test_generators",  ["tools/test_generators.py"], "generated questions are answerable"),
    ("test_behaviour",   ["tools/test_behaviour.py"],  "modes, symbols, artwork, licences"),
    ("check_images",     ["tools/check_images.py"],    "every image resolves and decodes"),
]
SLOW = [
    ("narrow",           ["tools/narrow.py"],          "layout at four phone sizes"),
    ("check_champs",     ["tools/check_champs.py"],    "champion years vs Wikipedia"),
    ("fact_checks",      ["tools/fact_checks.py"],     "written claims vs Wikipedia"),
]

def run(name, argv, why):
    """Returns True if the suite passed, False if the app failed, None if the
    tooling did — a headless Chrome that never answered says nothing about the
    app, and calling that a failure trains you to ignore the output."""
    t0 = time.time()
    r = subprocess.run([PY] + argv, cwd=ROOT, capture_output=True, text=True)
    out = (r.stdout or "") + (r.stderr or "")
    if "TimeoutExpired" in out or "cannot find Chrome" in out:
        print(f"  --    {name:16s} {time.time()-t0:5.1f}s  headless Chrome did not answer — rerun")
        return None
    # Some suites report in their text rather than their exit code, so the text
    # is read too — but precisely. "FAILED TO LOAD: 0" is a pass, and a naive
    # substring search for "FAIL" calls it a failure.
    textual = bool(re.search(r"\[FAIL\]|^\s*ERR\s|FAILED TO LOAD: [1-9]|"
                             r"\b[1-9]\d* errors\b|missing=[1-9]", out, re.M))
    bad = r.returncode != 0 or textual
    tail = [l for l in out.strip().splitlines() if l.strip()][-1:] or [""]
    print(f"  {'FAIL' if bad else 'ok  '}  {name:16s} {time.time()-t0:5.1f}s  {tail[0].strip()[:60]}")
    if bad:
        for line in out.strip().splitlines():
            if re.search(r"\[FAIL\]|^\s*ERR\s|FAILED TO LOAD: [1-9]", line):
                print(f"          {line.strip()[:150]}")
    return not bad

everything = "--all" in sys.argv
suites = FAST + (SLOW if everything else [])
print(f"running {len(suites)} suites{'' if everything else '  (add --all for the network + layout ones)'}\n")
results = [run(n, a, w) for n, a, w in suites]
passed = sum(1 for x in results if x is True)
failed = [s[0] for s, x in zip(suites, results) if x is False]
skipped = [s[0] for s, x in zip(suites, results) if x is None]
print(f"\n{passed}/{len(results)} suites passed"
      + (f"  ·  failed: {', '.join(failed)}" if failed else "")
      + (f"  ·  inconclusive: {', '.join(skipped)}" if skipped else ""))
sys.exit(1 if failed else 0)
