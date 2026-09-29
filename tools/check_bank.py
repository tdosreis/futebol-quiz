#!/usr/bin/env python3
"""Audit the written question bank without opening a browser.

Every other suite here drives headless Chrome, which means that on a machine
where Chrome will not start there is nothing at all standing between a bad
question and the Play Store. This one needs only JavaScriptCore, which ships
with macOS, so it still runs when check.py can do nothing but report timeouts.

It reads CATS straight out of index.html — bracket-matched, not regexed, because
a regex over 600k of nested literals undercounted 2,406 questions as 397 — hands
it to jsc, and checks the plain structural promises the game relies on, plus the
four things that are invisible in a diff: a question pointing at a picture that
does not exist, a question that contains its own answer, an option set where the
answer is the only long one, and the same question asked twice in different
words.

  python3 tools/check_bank.py          # non-zero exit if anything failed

Findings are split: an error is a question the engine can mishandle, a warning is
one a player can beat without knowing the answer. A warning that has been looked
at and judged fair goes in ACCEPTED with its reason, because three warnings that
print on every run are how you learn to stop reading the output — the same
argument check.py makes for not calling a Chrome timeout a failure. ACCEPTED is
keyed on the exact question text, so rewording one retires its excuse and the
warning comes back.
"""
import io, os, re, json, subprocess, sys, unicodedata

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
JSC = ("/System/Library/Frameworks/JavaScriptCore.framework/Versions/A/"
       "Helpers/jsc")

# Names CATS mentions that live elsewhere in the page. Stubbing them is enough
# because nothing in the array reads their contents at definition time.
STUBS = ["LIB_CHAMPS", "BR_CHAMPS"]

# Warnings that have been read and judged fair. Keyed on the question's exact
# text: reword it and the excuse expires, which is the point.
ACCEPTED = {
    "Selecione TODOS os times do Ceará":
        "a multi-select for a state has to list the club named after it, or the "
        "answer is wrong; Ceará SC is one of several to find",
    "Selecione TODOS os times da Bahia":
        "same as Ceará — Bahia is one of the clubs the player has to pick out",
    "Como é chamado o clássico entre Benfica e Porto?":
        "the answer is O Clássico and every decoy is another league's version of "
        "the same word, so the shared 'clássico' narrows nothing",
}


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


def declaration(src, decl, bracket):
    """The literal that `decl` opens, bracket-matched out of the page."""
    i = src.find(decl)
    if i < 0:
        sys.exit("could not find `%s` in index.html" % decl)
    a = src.index(bracket, i)
    return src[a:brace_match(src, a)]


MISSING = re.compile(r"Can't find variable: ([A-Za-z0-9_$]+)")


def js_eval(body, want):
    """Run `body` under jsc and return the JSON it prints for `want`.

    The tables are lifted out of the page, so they reference helpers defined
    elsewhere in it — FLAGS is built with _VERT and _HORZ, QICON with _msc.
    Rather than keeping a list of those in step with the page, whatever jsc says
    is missing gets stubbed and the run repeats. A stub is only ever reached at
    definition time, where its value is thrown away, so what it returns does not
    matter; if a table ever starts *reading* one, the JSON will show it and the
    checks will say so.
    """
    stubs = []
    tmp = os.path.join(ROOT, "_bank.js")
    try:
        for _ in range(40):
            io.open(tmp, "w", encoding="utf-8").write(
                "\n".join(stubs) + "\n" + body + "\nprint(JSON.stringify(%s));\n" % want)
            out = subprocess.run([JSC, tmp], capture_output=True, text=True, timeout=180)
            blob = (out.stdout or "") + (out.stderr or "")
            m = MISSING.search(blob)
            if not m:
                if out.returncode != 0 or not out.stdout.strip():
                    sys.exit("jsc could not evaluate %s:\n%s" % (want, blob[:800]))
                return json.loads(out.stdout)
            stubs.append("var %s = function(){ return ''; };" % m.group(1))
        sys.exit("gave up stubbing for %s after 40 helpers" % want)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def load_cats():
    src = io.open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    body = ("\n".join("var %s = [];" % n for n in STUBS)
            + "\nvar CATS = " + declaration(src, "const CATS = [", "[") + ";")
    return js_eval(body, "CATS")


# What a question is allowed to point at. `icon` matters most: inferArt falls
# back to QICON[key] ? key : 'ball', so a misspelt icon is not an error at
# runtime, it is quietly the wrong picture.
ART_FIELDS = [
    ("crest", ["LOGOS"]),
    ("flag",  ["FLAGS"]),
    ("stad",  ["STAD"]),
    ("icon",  ["QICON", "FALLBACK_PHOTO"]),
    ("port",  ["PORT"]),
    ("who",   ["PL"]),
]


def load_vocab():
    """The key sets a question's art fields have to name."""
    src = io.open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    tables = ["LOGOS", "FLAGS", "STAD", "QICON", "PORT", "FALLBACK_PHOTO"]
    body = "\n".join(
        "var %s = %s;" % (t, declaration(src, "const %s = {" % t, "{")) for t in tables)
    body += "\nvar PL = " + declaration(src, "const PL = [", "[") + ";"
    body += ("\nvar _V = {};"
             + "".join("_V.%s = Object.keys(%s);" % (t, t) for t in tables)
             + "_V.PL = PL.map(function(p){ return p.id; });")
    return js_eval(body, "_V")


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
    vocab = load_vocab()
    allowed = {f: set().union(*(set(vocab[t]) for t in ts)) for f, ts in ART_FIELDS}
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

            # art the question points at has to exist
            for field, tables in ART_FIELDS:
                v = q.get(field)
                if v is None:
                    continue
                for one in (v if isinstance(v, list) else [v]):
                    if one not in allowed[field]:
                        errs.append("%s — %s=%r is in no %s" % (where, field, one, "/".join(tables)))

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
                    warns.append((t, "%s — says its answer (%r)" % (where, one)))

            # the answer as the only option long enough to spot from across the room
            if ch and len(ch) > 2:
                lens = sorted(len(str(x)) for x in ch)
                med = lens[len(lens) // 2]
                longest = max(ch, key=lambda x: len(str(x)))
                if len(str(longest)) > med * 2.2 and len(str(longest)) > 18 and longest in a:
                    warns.append((t, "%s — the answer is the only long option (%r)" % (where, longest)))

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
                    warns.append((t1, "[%s] %s\n        is [%s] %s again" % (c1, t1[:66], c2, t2[:66])))

    # split the warnings against ACCEPTED, and notice when an excuse has outlived
    # the question it was written for — a stale entry is how this would quietly
    # start excusing something nobody has read
    live, accepted_hit = [], set()
    for text, msg in warns:
        if text in ACCEPTED:
            accepted_hit.add(text)
        else:
            live.append(msg)
    stale = [t for t in ACCEPTED if t not in accepted_hit]

    print("%d categories, %d written questions" % (len(cats), total))
    for r in errs:
        print("  ERROR %s" % r)
    for r in live:
        print("  warn  %s" % r)
    for t in stale:
        errs.append("ACCEPTED still excuses %r, which no longer warns — delete the entry" % t[:60])
        print("  ERROR ACCEPTED still excuses %r, which no longer warns — delete the entry" % t[:60])
    print("%d errors, %d warnings, %d accepted" % (len(errs), len(live), len(accepted_hit)))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
