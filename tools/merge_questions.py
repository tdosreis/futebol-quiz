#!/usr/bin/env python3
"""Merge the written question sets in tools/questions/*.json into index.html.

Each file is one category:
  { "id", "name", "emoji" | "flag", "tag", "col", "diff", "qs": [ row, ... ] }

A row is
  t        the question
  a        the answers: player ids (type "player"), Brazilian club ids (no
           type), or the exact text of a choice (type "txt")
  type     "player" | "txt" | omitted for a club
  choices  txt only: six options, the answers among them
  d        tier, 1 (easy) to 5 (for the few)
  art      exactly one of {"who": playerId} {"crest": clubId} {"flag": CODE}
           {"stad": key} {"icon": key} {"map": UF} — what the question is illustrated with
  src      [lang, article, [terms]] — the Wikipedia article that settles it and
           the words that must appear there (tools/check_questions.py)
  x        optional: the "Você sabia?" line shown after the answer
  xs       the words that line adds, checked against the same article
  xsrc     or [lang, article, [terms]] when the story rests on another article

The rows go between the NEW-QS markers inside CATS, so a re-run replaces what
the last run wrote. The ids it checks against are read from the page itself in
a headless browser, not guessed from the source text.

  python3 tools/merge_questions.py          # validate and write
  python3 tools/merge_questions.py --check  # validate only
"""
import glob, io, json, os, re, subprocess, sys, unicodedata

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
P = os.path.join(ROOT, "index.html")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
BEGIN = "  /* NEW-QS:BEGIN — written by tools/merge_questions.py from tools/questions/*.json */"
END = "  /* NEW-QS:END */"


def fold(x):
    x = unicodedata.normalize("NFD", str(x).lower())
    return "".join(c for c in x if unicodedata.category(c) != "Mn")


def inventory(src):
    """Ids the page actually has, with the new rows stripped out first."""
    a, b = src.index(BEGIN), src.index(END)
    bare = src[:a + len(BEGIN)] + "\n" + src[b:]
    probe = ("<script>window.addEventListener('load',function(){setTimeout(function(){"
             "var o={pl:PL.map(function(p){return [p.id,p.n]}),cl:CL.map(function(c){return [c.id,c.n]}),"
             "logos:Object.keys(LOGOS),flags:Object.keys(FLAGS),ctry:CTRY_NAME,"
             "stad:Object.keys(STAD_IMGS),icons:Object.keys(QICON),ufs:Object.keys(ART.UF_XY),"
             "texts:[].concat.apply([],CATS.map(function(c){return c.qs.map(function(q){return q.t})}))};"
             "var p=document.createElement('pre');p.id='inv';p.textContent=JSON.stringify(o);"
             "document.body.appendChild(p);},200);});</script>")
    tmp = os.path.join(ROOT, "_merge_inv.html")
    io.open(tmp, "w", encoding="utf-8").write(bare.replace("</body>", probe + "</body>"))
    try:
        out = subprocess.run([CHROME, "--headless", "--disable-gpu", "--allow-file-access-from-files",
                              "--virtual-time-budget=3000", "--dump-dom", "file://" + tmp],
                             capture_output=True, text=True, timeout=240).stdout
    finally:
        os.remove(tmp)
    m = re.search(r'<pre id="inv">(.*?)</pre>', out, re.S)
    if not m:
        sys.exit("could not read the page inventory")
    import html
    return json.loads(html.unescape(m.group(1)))


def main():
    check_only = "--check" in sys.argv
    src = io.open(P, encoding="utf-8").read()
    inv = inventory(src)
    pl = dict(inv["pl"]); cl = dict(inv["cl"])
    logos, flags, stad, icons = set(inv["logos"]), set(inv["flags"]), set(inv["stad"]), set(inv["icons"])
    ufs = set(inv["ufs"])
    seen = {fold(t): "existing" for t in inv["texts"]}

    errs, cats, total = [], [], 0
    for f in sorted(glob.glob(os.path.join(ROOT, "tools", "questions", "*.json"))):
        name = os.path.basename(f)
        cat = json.load(io.open(f, encoding="utf-8"))
        for k in ("id", "name", "tag", "col", "diff", "qs"):
            if k not in cat:
                errs.append(f"{name}: category is missing '{k}'")
        rows = []
        for i, q in enumerate(cat.get("qs", [])):
            where = f"{name}#{i + 1}"
            bad = lambda msg: errs.append(f"{where}: {msg} :: {q.get('t', '')[:70]}")
            t, a, typ = q.get("t", ""), q.get("a") or [], q.get("type")
            if not t.endswith("?"): bad("question does not end in '?'")
            key = fold(t + ' ' + q["clues"][0]) if q.get("clues") else fold(t)
            if key in seen: bad(f"duplicate of a question in {seen[key]}")
            seen[key] = where
            cl_ = q.get("clues")
            if cl_ is not None and (not isinstance(cl_, list) or not 3 <= len(cl_) <= 5 or typ != "player"):
                bad("clues must be 3-5 lines, on a player question")
            if not a: bad("no answer")
            if not isinstance(q.get("d"), int) or not 1 <= q["d"] <= 5: bad("d must be 1..5")
            fx = q.get("fixed")
            if fx is not None:
                if typ not in ("player", None) or len(fx) < 2 or len(set(fx)) != len(fx): bad("fixed: 2+ different ids on a player or club question")
                if any(x not in fx for x in a): bad("fixed: an answer is not among the tiles")
                for x in fx:
                    if x not in (pl if typ == "player" else cl): bad(f"fixed: unknown id '{x}'")
            sc_, xi_ = q.get("score"), q.get("xi")
            if sc_ is not None and ([sc_.get("h"), sc_.get("a")].count("?") != 1 or "hg" not in sc_ or "ag" not in sc_):
                bad("score needs h, hg, ag, a with exactly one side '?'")
            if xi_ is not None and sum(r.count("?") for r in xi_.get("rows", [])) != 1:
                bad("xi needs exactly one '?' on the pitch")
            if typ == "order":
                it = q.get("order") or []
                if not 3 <= len(it) <= 5: bad("order needs 3-5 cards")
                ids = [e.get("id") for e in it]
                if len(set(ids)) != len(ids): bad("order: repeated card id")
                if a != [e["id"] for e in sorted(it, key=lambda e: e["y"])]: bad("order: the answer is not the cards sorted by year")
                if len({e["y"] for e in it}) != len(it): bad("order: two cards share a year")
                for e in it:
                    if not (e.get("face") in pl or e.get("crest") in logos or e.get("flag")): bad(f"order: card '{e.get('id')}' has no picture")
            elif typ == "txt":
                ch = q.get("choices") or []
                need = 2 if q.get("duel") else 6
                if len(ch) != need or len({fold(c) for c in ch}) != need: bad(f"txt needs {need} different choices")
                if any(x not in ch for x in a): bad("an answer is not among the choices")
            elif typ == "player":
                for x in a:
                    if x not in pl: bad(f"unknown player '{x}'")
                    elif fold(pl[x]) in fold(t) and not q.get("duel"): bad(f"the question names its own answer ({pl[x]})")
            elif typ is None:
                for x in a:
                    if x not in cl: bad(f"unknown club '{x}'")
                    elif fold(cl[x]) in fold(t) and not q.get("duel"): bad(f"the question names its own answer ({cl[x]})")
            else:
                bad(f"unknown type '{typ}'")

            art = q.get("art") or {}
            pictured = typ == "order" or sc_ is not None or xi_ is not None
            if len(art) != (0 if pictured else 1): bad("art needs exactly one key" if not pictured else "a scoreboard, pitch or timeline is its own picture: no art")
            for k, v in art.items():
                if k == "who":
                    if v not in pl: bad(f"art: unknown player '{v}'")
                    if v in a: bad("art: the pictured player is the answer")
                    if typ == "txt" and any(fold(pl.get(v, "")) == fold(c) for c in q.get("choices", [])):
                        bad("art: the pictured player is one of the choices")
                elif k == "crest":
                    if v not in logos: bad(f"art: no crest for '{v}'")
                    if v in a: bad("art: the pictured crest is the answer")
                    if typ == "txt" and v in cl and any(fold(cl[v]) == fold(x) for x in a):
                        bad("art: the pictured crest names the answer")
                elif k == "flag":
                    if v not in flags: bad(f"art: no flag for '{v}'")
                    if typ == "txt" and any(fold(inv["ctry"].get(v, "")) == fold(x) for x in a):
                        bad("art: the flag is the answer")
                elif k == "stad":
                    if v not in stad: bad(f"art: no stadium photo '{v}'")
                elif k == "icon":
                    if v not in icons: bad(f"art: no icon '{v}'")
                elif k == "map":
                    if v not in ufs: bad(f"art: the map has no state '{v}'")
                else:
                    bad(f"art: unknown key '{k}'")

            s_ = q.get("src")
            if not (isinstance(s_, list) and len(s_) == 3 and s_[2]): bad("src must be [lang, article, [terms]]")

            row = {"t": t, "a": a}
            if typ: row["type"] = typ
            if typ == "txt": row["choices"] = q["choices"]
            for k_ in ("fixed", "clues", "score", "xi", "order"):
                if q.get(k_) is not None: row[k_] = q[k_]
            if q.get("clues"):
                # a clue card hides what the tiles would otherwise give away
                row.update({"_shown": 1, "opts": 6, "strict": 1, "_noFlag": True, "_hideCtry": True, "_hideEra": True})
                nm = fold(pl.get(a[0], ""))
                for c_ in q["clues"]:
                    if nm and (nm in fold(c_) or nm.split()[-1] in fold(c_).split()): bad(f"a clue names the answer: {c_[:50]}")
            row["d"] = q.get("d")
            x_ = q.get("x")
            if x_ is not None:
                if not isinstance(x_, str) or not (20 <= len(x_) <= 240): bad("x must be a story of 20-240 characters")
                row["x"] = x_
            row.update({("uf" if k == "map" else k): v for k, v in art.items()})
            rows.append(row)
        total += len(rows)
        cats.append((cat, rows))

    for e in errs: print("  !!", e)
    print(f"{total} questions in {len(cats)} categories, {len(errs)} problem(s)")
    if errs: sys.exit(1)
    if check_only: return

    out = [BEGIN]
    for cat, rows in cats:
        badge = f"flag:{json.dumps(cat['flag'])}" if cat.get("flag") else f"emoji:{json.dumps(cat.get('emoji', '⚽'), ensure_ascii=False)}"
        out.append(f"  {{\n    id:{json.dumps(cat['id'])}, name:{json.dumps(cat['name'], ensure_ascii=False)}, {badge},")
        out.append(f"    tag:{json.dumps(cat['tag'], ensure_ascii=False)}, col:{json.dumps(cat['col'])}, diff:{json.dumps(cat['diff'], ensure_ascii=False)},")
        out.append("    qs:[")
        for r in rows:
            out.append("      " + json.dumps(r, ensure_ascii=False) + ",")
        out.append("    ]\n  },")
    a, b = src.index(BEGIN), src.index(END)
    src = src[:a] + "\n".join(out) + "\n" + src[b:]
    io.open(P, "w", encoding="utf-8").write(src)
    print("written into index.html")


main()
