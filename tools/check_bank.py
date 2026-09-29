#!/usr/bin/env python3
"""Audit the written question bank without opening a browser.

Every other suite here drives headless Chrome, which means that on a machine
where Chrome will not start there is nothing at all standing between a bad
question and the Play Store. This one needs only JavaScriptCore, which ships
with macOS, so it still runs when check.py can do nothing but report timeouts.

It reads CATS straight out of index.html — bracket-matched, not regexed, because
a regex over 600k of nested literals undercounted 2,406 questions as 397 — hands
it to jsc, and checks the plain structural promises the game relies on, plus the
three things that are invisible in a diff: a question that contains its own
answer, an option set where the answer is the only long one, and the same
question asked twice in different words.

  python3 tools/check_bank.py          # non-zero exit if anything failed

Findings are split: an error is a question the engine can mishandle, a warning is
one a player can beat without knowing the answer.
"""
import io, os, re, json, subprocess, sys, unicodedata

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
JSC = ("/System/Library/Frameworks/JavaScriptCore.framework/Versions/A/"
       "Helpers/jsc")

# Names CATS mentions that live elsewhere in the page. Stubbing them is enough
# because nothing in the array reads their contents at definition time.
STUBS = ["LIB_CHAMPS", "BR_CHAMPS"]


def brace_match(s, start):
    """End index (exclusive) of the bracket opened at `start`, skipping strings
    and comments — the one part of this that a regex genuinely cannot do."""
    k, depth, n = start, 0, len(s)
    opener = s[start]
    closer = {"[": "]", "{": "}"}[opener]
    while k < n:
        c = s[k]
        if c in "\"'`":
            q, k = c, k + 1
            while k < n:
                if s[k] == "\\":
                    k += 2
                    continue
                if s[k] == q:
                    break
                k += 1
        elif c == "/" and s[k + 1:k + 2] == "/":
            k = s.index("\n", k)
        elif c == "/" and s[k + 1:k + 2] == "*":
            k = s.index("*/", k) + 1
        elif c == opener:
            depth += 1
        elif c == closer:
            depth -= 1
            if depth == 0:
                return k + 1
        k += 1
    raise ValueError("unbalanced brackets from offset %d" % start)


def load_cats():
    src = io.open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    i = src.find("const CATS = [")
    if i < 0:
        sys.exit("could not find `const CATS = [` in index.html")
    a = src.index("[", i)
    b = brace_match(src, a)
    prog = ("\n".join("var %s = [];" % n for n in STUBS)
            + "\nvar CATS = " + src[a:b] + ";\n"
            + "print(JSON.stringify(CATS));\n")
    tmp = os.path.join(ROOT, "_bank.js")
    io.open(tmp, "w", encoding="utf-8").write(prog)
    try:
        out = subprocess.run([JSC, tmp], capture_output=True, text=True, timeout=120)
    finally:
        os.remove(tmp)
    if out.returncode != 0 or not out.stdout.strip():
        sys.exit("jsc could not evaluate CATS:\n" + (out.stderr or "")[:800])
    return json.loads(out.stdout)


def fold(x):
    x = unicodedata.normalize("NFD", str(x).lower())
    x = "".join(c for c in x if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", x)).strip()


# Words that carry no subject, so that two questions are compared on what they
# are about rather than on the scaffolding they share.
STOP = set("qual quais quem que de do da dos das o a os as em no na nos nas um uma "
           "foi foram com por para pela pelo se sua seu mais menos este esta estes "
           "estas destes destas nunca como onde quando quantas quantos ano anos "
           "primeiro primeira e".split())

# 0.8, because the bank asks the same question about different subjects on
# purpose — "Quantas Copas a França ganhou" against "o Uruguai", six "NUNCA
# jogou no X" — and those land between 0.5 and 0.73. Above 0.8 is the same
# sentence twice: "Que país vai sediar a Copa de 2027" and "Qual país vai".
TWIN = 0.8


def subject(t):
    return set(w for w in fold(t).split() if w not in STOP and len(w) > 2)


def main():
    if not os.path.exists(JSC):
        sys.exit("no jsc at %s — this tool needs JavaScriptCore" % JSC)
    cats = load_cats()
    errs, warns = [], []
    seen = {}
    total = 0
    by_answer = {}

    for c in cats:
        for q in c.get("qs", []):
            total += 1
            key = tuple(sorted(fold(x) for x in (q.get("a") or [])))
            if key:
                by_answer.setdefault(key, []).append((c.get("id"), q.get("t") or ""))
            where = "[%s] %s" % (c.get("id"), (q.get("t") or "")[:72])
            a = q.get("a") or []
            if not a:
                errs.append("%s — no answer" % where)
                continue
            ch = q.get("choices")

            # the engine marks a tile correct by identity with `a`
            if ch:
                for one in a:
                    if one not in ch:
                        errs.append("%s — answer %r is not among the choices" % (where, one))
                fset = {}
                for one in ch:
                    if not str(one).strip():
                        errs.append("%s — blank choice" % where)
                    f = fold(one)
                    if f in fset:
                        errs.append("%s — repeated choice %r" % (where, one))
                    fset[f] = 1
            elif q.get("type") == "txt":
                errs.append("%s — a txt question with no choices" % where)

            d = q.get("d")
            if d is not None and (not isinstance(d, int) or not 1 <= d <= 5):
                errs.append("%s — difficulty %r is outside 1..5" % (where, d))

            t = q.get("t") or ""
            if t in seen:
                errs.append("%s — same text as [%s]" % (where, seen[t]))
            else:
                seen[t] = c.get("id")

            # a question that says its own answer
            ft = fold(t)
            for one in a:
                fa = fold(one)
                if len(fa) >= 5 and fa in ft:
                    warns.append("%s — says its answer (%r)" % (where, one))

            # the answer as the only option long enough to spot from across the room
            if ch and len(ch) > 2:
                lens = sorted(len(str(x)) for x in ch)
                med = lens[len(lens) // 2]
                longest = max(ch, key=lambda x: len(str(x)))
                if len(str(longest)) > med * 2.2 and len(str(longest)) > 18 and longest in a:
                    warns.append("%s — the answer is the only long option (%r)" % (where, longest))

    # the same question in two wordings — only worth comparing where the answer
    # already matches, which cuts it from 2.9M pairs to a few hundred
    for group in by_answer.values():
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                (c1, t1), (c2, t2) = group[i], group[j]
                s1, s2 = subject(t1), subject(t2)
                if not s1 or not s2:
                    continue
                if len(s1 & s2) / len(s1 | s2) >= TWIN:
                    warns.append("[%s] %s\n        is [%s] %s again" % (c1, t1[:66], c2, t2[:66]))

    print("%d categories, %d written questions" % (len(cats), total))
    for label, rows in (("ERROR", errs), ("warn", warns)):
        for r in rows:
            print("  %-5s %s" % (label, r))
    print("%d errors, %d warnings" % (len(errs), len(warns)))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
