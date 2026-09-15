#!/usr/bin/env python3
"""Which candidate words does an article actually contain?

  SCRATCH=dir python3 tools/xs_probe.py lang "Article title" term [term ...]

Reads the same cache tools/check_questions.py fills, so writing a story is a
question of checking, not remembering.
"""
import hashlib, io, os, sys, unicodedata
C = os.path.join(os.environ["SCRATCH"], "wiki")
fold = lambda x: "".join(c for c in unicodedata.normalize("NFD", str(x).lower()) if unicodedata.category(c) != "Mn")
lang, title, terms = sys.argv[1], sys.argv[2], sys.argv[3:]
p = os.path.join(C, hashlib.sha1(f"{lang}:{title}".encode()).hexdigest()[:20] + ".txt")
body = fold(io.open(p, encoding="utf-8").read()) if os.path.exists(p) else ""
print(f"{lang}:{title}  ({len(body)} chars cached)")
for t in terms:
    print(("  yes  " if fold(t) in body else "  NO   ") + t)
