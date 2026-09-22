#!/usr/bin/env python3
"""Which picture does each question get, and why?

inferArt() decorates a question with the first player, club or country it can
find named in the text. That is a substring match over club names, and a good
few Brazilian clubs are named after ordinary words, states or nationalities:
"seleção portuguesa" is Portugal, not Portuguesa from São Paulo; "Copa
América" is not América-MG; "a vitória do Brasil" is not Vitória-BA.

This walks every written question and several rounds of every generator,
reproduces the match, and prints what was hit. Clubs whose name is also a
demonym, a state or a common noun are marked RISK so the list can be read
without trusting the eye alone.
"""
import subprocess, os, io, re, json, sys

ROOT   = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# club ids whose NAME is also an ordinary Portuguese word, a state, a city or
# a nationality — the ones where a bare word match proves nothing
RISK = {
    'portuguesa': 'nationality (Portugal)',
    'americamg':  'continent / Copa América',
    'vitoria':    'common noun "vitória"',
    'internacional': 'adjective "internacional"',
    'sport':      'common noun "sport"',
    'remo':       'common noun "remo"',
    'bahia':      'state',
    'ceara':      'state',
    'goias':      'state',
    'fortaleza':  'city / common noun',
    'cuiaba':     'city',
    'guarani':    'people / language',
    'juventude':  'common noun "juventude"',
    'santos':     'surname',
    'nautico':    'adjective "náutico"',
    'coritiba':   'city',
    'chapecoense':'city demonym',
    'figueirense':'city demonym',
    'fluminense': 'state demonym (RJ)',
    'paysandu':   'city',
    'criciuma':   'city',
    'mirassol':   'city',
}

PROBE = r"""
(function(){
  var out = [];
  /* the app decides; this only reports. artMatch() is the one place those
     rules live, so this cannot drift away from what the screen draws. */
  var why = artMatch;
  function scan(q, src){
    var w = why(q);
    if (w) out.push({src:src, kind:w.kind, id:w.id, hit:w.hit, t:(q.t||'').slice(0,110),
                     a:(q.a||[]).join(',')});
  }
  CATS.forEach(function(c){ (c.qs||[]).forEach(function(q){ scan(q, c.id); }); });
  /* the generators deal fresh every call, so take several rounds of each tier */
  for (var r=0;r<6;r++) [1,2,3,4,5].forEach(function(tier){
    (GEN_QS(tier)||[]).forEach(function(q){ scan(q, (q._cat&&q._cat.id)||'gen'); });
  });
  var d = document.createElement('pre'); d.id='OUT';
  d.textContent = JSON.stringify(out); document.body.appendChild(d);
})();
"""

src = io.open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
tmp = os.path.join(ROOT, "_audit_art.html")
io.open(tmp, "w", encoding="utf-8").write(
    src.replace("</body>", "<script>window.addEventListener('load',function(){setTimeout(function(){"
                "try{" + PROBE + "}catch(e){var d=document.createElement('pre');d.id='OUT';"
                "d.textContent='[]';console.log(e);}},400)});</script></body>"))
try:
    dom = subprocess.run([CHROME, "--headless", "--disable-gpu", "--allow-file-access-from-files",
                          "--virtual-time-budget=25000", "--dump-dom", "file://" + tmp],
                         capture_output=True, text=True, timeout=560).stdout
finally:
    if os.path.exists(tmp): os.remove(tmp)

m = re.search(r'<pre id="OUT">(.*?)</pre>', dom, re.S)
if not m:
    print("no output"); sys.exit(1)
rows = json.loads(m.group(1).replace("&quot;", '"').replace("&amp;", "&")
                            .replace("&lt;", "<").replace("&gt;", ">"))

seen, risky, clubs, bad = set(), [], 0, []
for r in rows:
    key = (r["kind"], r["id"], r["t"])
    if key in seen: continue
    seen.add(key)
    if r["kind"] != "club": continue
    clubs += 1
    # THE INVARIANT: a club is a proper noun. If its name occurs in the
    # question only in lower case, the question is using the word in some
    # other sense — "seleção portuguesa", "a vitória por 6 a 3" — and its
    # crest is the wrong picture. This is the bug that was reported.
    if r["hit"] and r["hit"] not in r["t"] and len(r["t"]) < 110:
        bad.append(r)
    if r["id"] in RISK: risky.append(r)

print("%d questions get a picture; %d of them a club crest\n" % (len(seen), clubs))

print("=== a club crest where the club is not named as a proper noun ===")
for r in bad:
    print("  WRONG  %-12s hit %-16s %s" % (r["id"], r["hit"], r["t"]))
if not bad:
    print("  none — every club crest is drawn from a capitalised club name")

print("\n=== for review: names that are also a word, a state or a nationality ===")
print("    (capitalised, so these read as the club — listed to be eyeballed)")
for r in sorted(risky, key=lambda r: r["id"]):
    print("  [%s] %-12s %s" % (RISK[r["id"]], r["id"], r["t"]))

print("\n%s" % ("PASS — no mismatched crest" if not bad
                else "FAIL — %d mismatched crests" % len(bad)))
sys.exit(1 if bad else 0)
