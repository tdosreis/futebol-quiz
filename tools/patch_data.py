#!/usr/bin/env python3
"""Insert enriched player/club metadata into index.html (idempotent)."""
import re, sys, io, os

P = os.path.join(os.path.dirname(__file__), "..", "index.html")
s = io.open(P, encoding="utf-8").read()

MARK = "PLAYER METADATA"
if MARK in s:
    print("already patched; nothing to do")
    sys.exit(0)

BLOCK = r"""
/* ═══════════════════════════════════════════════════
   DATA — PLAYER METADATA  (position, era, clubs, country)
   Powers smart distractors, generated questions & career mode
═══════════════════════════════════════════════════ */
const POS_NAME = { GK:'Goleiro', DF:'Defensor', MF:'Meia', FW:'Atacante' };
const CTRY_NAME = { BRA:'Brasil', ARG:'Argentina', POR:'Portugal', FRA:'França',
  NED:'Holanda', GER:'Alemanha', BUL:'Bulgária', ITA:'Itália', ENG:'Inglaterra',
  SWE:'Suécia', POL:'Polônia', CIV:'Costa do Marfim', LBR:'Libéria', CRO:'Croácia',
  COL:'Colômbia' };

/* Display names for clubs outside the Brazilian crest set */
const CLUB_NAMES = {
  cosmos:'New York Cosmos', udinese:'Udinese', kashima:'Kashima Antlers',
  psv:'PSV', barcelona:'Barcelona', inter:'Inter de Milão', realmadrid:'Real Madrid',
  milan:'Milan', psg:'PSG', orlando:'Orlando City', fiorentina:'Fiorentina',
  deportivo:'Deportivo La Coruña', olympiacos:'Olympiacos', valencia:'Valencia',
  alhilal:'Al-Hilal', fenerbahce:'Fenerbahçe', roma:'Roma', parma:'Parma',
  atalanta:'Atalanta', galatasaray:'Galatasaray', torino:'Torino',
  marseille:'Marseille', benfica:'Benfica', argentinos:'Argentinos Juniors',
  boca:'Boca Juniors', napoli:'Napoli', sevilla:'Sevilla', intermiami:'Inter Miami',
  sporting:'Sporting', manutd:'Manchester United', juventus:'Juventus',
  alnassr:'Al-Nassr', cannes:'Cannes', bordeaux:'Bordeaux', ajax:'Ajax',
  kaiserslautern:'Kaiserslautern', werder:'Werder Bremen', bayern:'Bayern de Munique',
  lazio:'Lazio', riverplate:'River Plate', cska:'CSKA Sofia', feyenoord:'Feyenoord',
  nice:'Nice', reims:'Reims', banfield:'Banfield', porto:'Porto', monaco:'Monaco',
  everton:'Everton', bologna:'Bologna', brescia:'Brescia', nancy:'Nancy',
  saintetienne:'Saint-Étienne', lagalaxy:'LA Galaxy', arsenal:'Arsenal',
  nyrb:'New York Red Bulls', malmo:'Malmö', lech:'Lech Poznań',
  dortmund:'Borussia Dortmund', guingamp:'Guingamp', chelsea:'Chelsea',
  mancity:'Manchester City', dinamo:'Dinamo Zagreb', tottenham:'Tottenham',
  lyon:'Lyon', alittihad:'Al-Ittihad',
};
function clubName(id) {
  const c = CL.find(x => x.id === id);
  return c ? c.n : (CLUB_NAMES[id] || id);
}

const PL_META = {
  /* ── Brasileiros ── */
  pele:          { pos:'FW', era:[1956,1977], ctry:'BRA', clubs:['santos','cosmos'] },
  zico:          { pos:'MF', era:[1971,1994], ctry:'BRA', clubs:['flamengo','udinese','kashima'] },
  garrincha:     { pos:'FW', era:[1953,1972], ctry:'BRA', clubs:['botafogo','corinthians','flamengo'] },
  ronaldo:       { pos:'FW', era:[1993,2011], ctry:'BRA', clubs:['cruzeiro','psv','barcelona','inter','realmadrid','milan','corinthians'] },
  ronaldinho:    { pos:'MF', era:[1998,2015], ctry:'BRA', clubs:['gremio','psg','barcelona','milan','flamengo','atleticomg'] },
  kaka:          { pos:'MF', era:[2001,2017], ctry:'BRA', clubs:['saopaulo','milan','realmadrid','orlando'] },
  dinamite:      { pos:'FW', era:[1971,1993], ctry:'BRA', clubs:['vasco','barcelona'] },
  socrates:      { pos:'MF', era:[1974,1989], ctry:'BRA', clubs:['corinthians','fiorentina','flamengo','santos'] },
  romario:       { pos:'FW', era:[1985,2009], ctry:'BRA', clubs:['vasco','psv','barcelona','flamengo','valencia','fluminense'] },
  bebeto:        { pos:'FW', era:[1983,2002], ctry:'BRA', clubs:['flamengo','vasco','deportivo','botafogo','cruzeiro'] },
  rivaldo:       { pos:'FW', era:[1991,2015], ctry:'BRA', clubs:['palmeiras','deportivo','barcelona','milan','olympiacos','corinthians','saopaulo'] },
  adriano:       { pos:'FW', era:[1999,2016], ctry:'BRA', clubs:['flamengo','inter','parma','roma','corinthians'] },
  neymar:        { pos:'FW', era:[2009,2026], ctry:'BRA', clubs:['santos','barcelona','psg','alhilal'] },
  roberto_carlos:{ pos:'DF', era:[1992,2015], ctry:'BRA', clubs:['palmeiras','inter','realmadrid','fenerbahce','corinthians'] },
  cafu:          { pos:'DF', era:[1989,2008], ctry:'BRA', clubs:['saopaulo','palmeiras','roma','milan'] },
  taffarel:      { pos:'GK', era:[1985,2003], ctry:'BRA', clubs:['internacional','parma','atalanta','galatasaray'] },
  vinicius:      { pos:'FW', era:[2017,2026], ctry:'BRA', clubs:['flamengo','realmadrid'] },
  carlos_alberto:{ pos:'DF', era:[1963,1982], ctry:'BRA', clubs:['fluminense','santos','botafogo','cosmos'] },
  muller_sp:     { pos:'FW', era:[1983,2000], ctry:'BRA', clubs:['saopaulo','torino','palmeiras','cruzeiro'] },
  jairzinho:     { pos:'FW', era:[1959,1982], ctry:'BRA', clubs:['botafogo','marseille','cruzeiro'] },
  gabigol:       { pos:'FW', era:[2010,2026], ctry:'BRA', clubs:['santos','inter','benfica','flamengo','cruzeiro'] },
  falcao:        { pos:'MF', era:[1973,1986], ctry:'BRA', clubs:['internacional','roma','saopaulo'] },
  /* ── Internacionais ── */
  maradona:      { pos:'MF', era:[1976,1997], ctry:'ARG', clubs:['argentinos','boca','barcelona','napoli','sevilla'] },
  messi:         { pos:'FW', era:[2003,2026], ctry:'ARG', clubs:['barcelona','psg','intermiami'] },
  cr7:           { pos:'FW', era:[2002,2026], ctry:'POR', clubs:['sporting','manutd','realmadrid','juventus','alnassr'] },
  zidane:        { pos:'MF', era:[1988,2006], ctry:'FRA', clubs:['cannes','bordeaux','juventus','realmadrid'] },
  van_basten:    { pos:'FW', era:[1981,1995], ctry:'NED', clubs:['ajax','milan'] },
  klose:         { pos:'FW', era:[1999,2016], ctry:'GER', clubs:['kaiserslautern','werder','bayern','lazio'] },
  batistuta:     { pos:'FW', era:[1988,2005], ctry:'ARG', clubs:['riverplate','boca','fiorentina','roma','inter'] },
  stoichkov:     { pos:'FW', era:[1984,2003], ctry:'BUL', clubs:['cska','barcelona','parma'] },
  cruyff:        { pos:'FW', era:[1964,1984], ctry:'NED', clubs:['ajax','barcelona','feyenoord'] },
  fontaine:      { pos:'FW', era:[1953,1962], ctry:'FRA', clubs:['nice','reims'] },
  james:         { pos:'MF', era:[2006,2026], ctry:'COL', clubs:['banfield','porto','monaco','realmadrid','bayern','everton'] },
  baggio:        { pos:'FW', era:[1982,2004], ctry:'ITA', clubs:['fiorentina','juventus','milan','bologna','inter','brescia'] },
  platini:       { pos:'MF', era:[1972,1987], ctry:'FRA', clubs:['nancy','saintetienne','juventus'] },
  beckham:       { pos:'MF', era:[1992,2013], ctry:'ENG', clubs:['manutd','realmadrid','lagalaxy','milan','psg'] },
  henry:         { pos:'FW', era:[1994,2014], ctry:'FRA', clubs:['monaco','juventus','arsenal','barcelona','nyrb'] },
  ibrahimovic:   { pos:'FW', era:[1999,2023], ctry:'SWE', clubs:['malmo','ajax','juventus','inter','barcelona','milan','psg','manutd','lagalaxy'] },
  lewandowski:   { pos:'FW', era:[2006,2026], ctry:'POL', clubs:['lech','dortmund','bayern','barcelona'] },
  mbappe:        { pos:'FW', era:[2015,2026], ctry:'FRA', clubs:['monaco','psg','realmadrid'] },
  drogba:        { pos:'FW', era:[1998,2018], ctry:'CIV', clubs:['guingamp','marseille','chelsea','galatasaray'] },
  weah:          { pos:'FW', era:[1985,2003], ctry:'LBR', clubs:['monaco','psg','milan','chelsea','mancity'] },
  modric:        { pos:'MF', era:[2003,2026], ctry:'CRO', clubs:['dinamo','tottenham','realmadrid'] },
  benzema:       { pos:'FW', era:[2004,2026], ctry:'FRA', clubs:['lyon','realmadrid','alittihad'] },
};
PL.forEach(p => Object.assign(p, PL_META[p.id] || { pos:'FW', era:[1990,2010], ctry:'BRA', clubs:[] }));

/* Club metadata — founding year & major titles (for generated questions) */
const CL_META = {
  flamengo:{f:1895,br:8,lib:3},   fluminense:{f:1902,br:4,lib:1},
  vasco:{f:1898,br:4,lib:1},      botafogo:{f:1904,br:3,lib:1},
  corinthians:{f:1910,br:7,lib:1},palmeiras:{f:1914,br:12,lib:3},
  saopaulo:{f:1930,br:6,lib:3},   santos:{f:1912,br:8,lib:3},
  gremio:{f:1903,br:2,lib:3},     internacional:{f:1909,br:3,lib:2},
  cruzeiro:{f:1921,br:4,lib:2},   atleticomg:{f:1908,br:2,lib:1},
  atleticopr:{f:1924,br:1,lib:0}, bahia:{f:1931,br:2,lib:0},
  fortaleza:{f:1918,br:0,lib:0},  ceara:{f:1914,br:0,lib:0},
  sport:{f:1905,br:1,lib:0},      pontepreta:{f:1900,br:0,lib:0},
  bragantino:{f:1928,br:0,lib:0}, coritiba:{f:1909,br:1,lib:0},
  vitoria:{f:1899,br:0,lib:0},    criciuma:{f:1947,br:0,lib:0},
  americamg:{f:1912,br:0,lib:0},  guarani:{f:1911,br:1,lib:0},
  nautico:{f:1901,br:0,lib:0},
};
CL.forEach(c => Object.assign(c, CL_META[c.id] || { f:1900, br:0, lib:0 }));
"""

# insert right after the PL array closes
m = re.search(r"(const PL = \[.*?\n\];\n)", s, re.S)
if not m:
    print("ERROR: could not find PL array"); sys.exit(1)
s = s[:m.end(1)] + BLOCK + s[m.end(1):]

io.open(P, "w", encoding="utf-8").write(s)
print("inserted player/club metadata block")
