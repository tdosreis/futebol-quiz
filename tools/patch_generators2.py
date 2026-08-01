#!/usr/bin/env python3
"""More question variety: stadiums, decades, head-to-head comparisons,
'odd one out', shirt-number and state-derby templates."""
import re, io, os, sys

P = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "index.html"))
s = io.open(P, encoding="utf-8").read()
if "GEN2" in s:
    print("already patched"); sys.exit(0)

NEW = r"""
  /* ═════ GEN2 — extra templates ═════ */

  /* 11. Stadium → club */
  const STIDS = Object.keys(typeof STAD !== 'undefined' ? STAD : {});
  const STAD_CLUB = { allianz:'palmeiras', neoq:'corinthians', beirario:'internacional',
    vilabelmiro:'santos', saojanua:'vasco', arena_gre:'gremio' };
  pick(STIDS.filter(k => STAD_CLUB[k]), 4).forEach(k => {
    const owner = STAD_CLUB[k];
    out.push({
      t: `Qual clube manda seus jogos no ${STAD[k].name}, em ${STAD[k].city}?`,
      a: [owner],
      pool: CL.filter(c => c.id !== owner).map(c => c.id),
      stad: k,
      _cat: GC.hist, d: 2,
    });
  });

  /* 12. Which club is from this state? */
  const byState = {};
  CL.forEach(c => { (byState[c.s] = byState[c.s] || []).push(c); });
  const ST_NAME = { RJ:'Rio de Janeiro', SP:'São Paulo', RS:'Rio Grande do Sul',
    MG:'Minas Gerais', PR:'Paraná', BA:'Bahia', CE:'Ceará', PE:'Pernambuco', SC:'Santa Catarina' };
  pick(Object.keys(byState).filter(st => ST_NAME[st] && byState[st].length >= 2), 4).forEach(st => {
    const yes = rndOf(byState[st]);
    out.push({
      t: `Qual destes clubes é de ${ST_NAME[st]}?`,
      a: [yes.id],
      pool: CL.filter(c => c.s !== st).map(c => c.id),
      _cat: GC.hist, d: 1,
    });
  });

  /* 13. Head-to-head: who played longer? */
  for (let i = 0; i < 4; i++) {
    const two = pick(PL.filter(p => p.era), 2);
    if (two.length < 2) break;
    const span = p => p.era[1] - p.era[0];
    if (span(two[0]) === span(two[1])) continue;
    const longer = span(two[0]) > span(two[1]) ? two[0] : two[1];
    out.push({
      t: 'Quem teve a carreira mais longa?',
      a: [longer.id], type: 'player',
      fixed: two.map(p => p.id),
      _cat: GC.era, d: 2,
    });
  }

  /* 14. Odd one out — nine share a trait, one doesn't */
  ['GK', 'DF', 'MF', 'FW'].forEach(pos => {
    const same = PL.filter(p => p.pos === pos);
    const other = PL.filter(p => p.pos !== pos);
    if (same.length < 9 || !other.length) return;
    const odd = rndOf(other);
    out.push({
      t: `Qual destes NÃO era ${POS_NAME[pos].toLowerCase()}?`,
      a: [odd.id], type: 'player',
      fixed: pick(same, 9).map(p => p.id).concat(odd.id),
      _cat: GC.pos, d: 2,
    });
  });

  /* 15. Which club was founded in this decade? */
  for (let i = 0; i < 3; i++) {
    const c = rndOf(CL);
    const dec = Math.floor(c.f / 10) * 10;
    const others = CL.filter(x => Math.floor(x.f / 10) * 10 !== dec);
    if (others.length < 9) continue;
    out.push({
      t: `Qual destes clubes foi fundado na década de ${dec}?`,
      a: [c.id],
      pool: others.map(x => x.id),
      _cat: GC.hist, d: 3,
    });
  }

  /* 16. Contemporaries — who played in the same era? */
  pick(PL.filter(p => p.era), 5).forEach(p => {
    const overlaps = x => x.id !== p.id &&
      Math.min(x.era[1], p.era[1]) - Math.max(x.era[0], p.era[0]) >= 5;
    const mates = PL.filter(overlaps);
    const strangers = PL.filter(x => x.id !== p.id && !overlaps(x));
    if (!mates.length || strangers.length < 9) return;
    const mate = rndOf(mates);
    out.push({
      t: `Quem jogou na mesma época que ${p.n}?`,
      a: [mate.id], type: 'player',
      fixed: pick(strangers, 9).map(x => x.id).concat(mate.id),
      face: p.img,
      _cat: GC.era, d: 3,
    });
  });

  /* 17. Most Libertadores titles among these */
  for (let i = 0; i < 3; i++) {
    const set = pick(CL, 10);
    const top = set.reduce((a, b) => (a.lib >= b.lib ? a : b));
    if (top.lib === 0 || set.filter(c => c.lib === top.lib).length > 1) continue;
    out.push({ t: 'Qual destes clubes tem mais títulos da Libertadores?',
               a: [top.id], fixed: set.map(c => c.id), _cat: GC.hist, d: 2 });
  }

  /* 18. Country → multi-select */
  Object.keys(byCtry).filter(c => byCtry[c].length >= 2 && c !== 'BRA').slice(0, 4).forEach(c => {
    const yes = pick(byCtry[c], 2);
    const no = PL.filter(p => p.ctry !== c);
    if (no.length < 8) return;
    out.push({
      t: `Selecione os 2 jogadores de ${CTRY_NAME[c] || c}`,
      a: yes.map(p => p.id), type: 'player',
      fixed: yes.map(p => p.id).concat(pick(no, 8).map(p => p.id)),
      _cat: GC.nat, d: 3,
    });
  });
"""

m = re.search(r"(\n  // Safety net)", s)
if not m:
    print("ERR: safety-net anchor not found"); sys.exit(1)
s = s[:m.start(1)] + NEW + s[m.start(1):]

io.open(P, "w", encoding="utf-8").write(s)
print("extra generators patched")
