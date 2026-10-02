#!/usr/bin/env python3
"""Find a real, freely licensed reference photograph for each mascot.

The mascots were painted from emoji, and an emoji gives Gemini a flat toy to
copy. A good photograph of the real animal (or object) gives it anatomy,
texture and character to stylise instead. For each kind of mascot this asks
Wikimedia Commons for photographs, keeps only free licences and large files,
prefers Commons' own Quality / Featured / Valued pictures, and saves the best
three as candidates to review:

  <OUT>/src/img/msc-src/<art>-1.jpg  (+ .json with author, licence, page)

Nothing is chosen automatically: a person picks one per mascot and writes it
into mascots.json as "src". Run from GitHub Actions — Wikimedia is not
reachable from every sandbox.
"""
import json, os, re, sys, time, urllib.parse, urllib.request

UA = 'futebol-quiz-mascots/1.0 (https://github.com/tdosreis/futebol-quiz)'
FREE = re.compile(r'^(cc0|cc[- ]by|public domain|pd|gfdl|attribution|copyrighted free use|no restrictions)', re.I)
GOOD = re.compile(r'quality images|featured pictures|valued images|picture of the (day|year)', re.I)
BAD = re.compile(r'logo|emblem|escudo|crest|badge|map|drawing|clipart|icon|svg|diagram|stamp|coat of arms', re.I)

# what to photograph for each mascot kind: Commons search strings, best first
SUBJECT = {
    'galo':        ['rooster Gallus gallus domesticus', 'rooster portrait'],
    'raposa':      ['Vulpes vulpes red fox', 'red fox portrait'],
    'porco':       ['domestic pig Sus scrofa domesticus', 'pig portrait farm'],
    'urubu':       ['Coragyps atratus black vulture', 'black vulture portrait'],
    'peixe':       ['whale shark Rhincodon typus', 'Salminus brasiliensis'],
    'leao':        ['Panthera leo male lion portrait', 'male lion mane'],
    'coelho':      ['Oryctolagus cuniculus rabbit', 'wild rabbit portrait'],
    'macaca':      ['Sapajus capuchin monkey', 'capuchin monkey portrait'],
    'tigre':       ['Panthera tigris tigris Bengal tiger walking', 'Bengal tiger Ranthambore'],
    'touro':       ['Hereford bull', 'Nelore bull', 'bull in pasture'],
    'dragao':      ['Varanus komodoensis Komodo dragon', 'Komodo dragon'],
    'cobra':       ['Micrurus coral snake', 'coral snake'],
    'periquito':   ['Brotogeris chiriri parakeet', 'Brotogeris tirica'],
    'elefante':    ['Loxodonta africana elephant portrait', 'African elephant'],
    'tubarao':     ['Carcharhinus shark', 'reef shark underwater'],
    'timbu':       ['Didelphis albiventris opossum', 'Didelphis opossum'],
    'almirante':   ['admiral portrait painting navy uniform', 'Almirante Tamandaré'],
    'mosqueteiro': ['musketeer costume', 'musketeer reenactment'],
    'saci':        ['Saci Pererê', 'Saci-pererê folclore'],
    'poDeArroz':   ['top hat', 'silk top hat'],
    'cachorro':    ['Smooth Fox Terrier', 'Fox Terrier dog'],
    'santo':       ['Saint Paul statue', 'São Paulo apóstolo estátua'],
    'furacao':     ['hurricane from space', 'hurricane satellite'],
    'heroi':       ['caped superhero costume cosplay', 'cape costume'],
    'vovo':        ['elderly man portrait smiling', 'grandfather portrait'],
    'coxa':        ['white chicken leg', 'Coxa-branca'],
    'dourado':     ['Salminus brasiliensis dourado', 'golden dorado fish'],
    'verdao':      ['Ara chloropterus macaw', 'green-winged macaw'],
    'figueira':    ['Ficus tree large', 'fig tree Ficus'],
    'papao':       ['Paysandu Papão', 'folk monster costume'],
    'caravela':    ['caravel replica sailing', 'caravela'],
    'azulao':      ['Cyanoloxia brissonii', 'ultramarine grosbeak'],
    'pantera':     ['Panthera onca melanistic black jaguar', 'black leopard Panthera pardus melanistic'],
}


def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read()


def api(**params):
    params.update(format='json', formatversion='2')
    return json.loads(get('https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode(params)))


def candidates(term, n=25):
    q = api(action='query', generator='search', gsrsearch=f'{term} filetype:bitmap', gsrnamespace=6, gsrlimit=n,
            prop='imageinfo|categories', iiprop='url|size|extmetadata|mime', iiurlwidth=1100, cllimit=50)
    out = []
    for p in (q.get('query') or {}).get('pages') or []:
        ii = (p.get('imageinfo') or [{}])[0]
        md = ii.get('extmetadata') or {}
        val = lambda k: re.sub(r'<[^>]+>', '', (md.get(k) or {}).get('value') or '').strip()
        lic = val('LicenseShortName')
        title = p.get('title', '')
        cats = ' | '.join(c.get('title', '') for c in p.get('categories') or [])
        if not FREE.search(lic) or BAD.search(title) or ii.get('mime') not in ('image/jpeg', 'image/png', 'image/webp'):
            continue
        w, h = ii.get('width', 0), ii.get('height', 0)
        if min(w, h) < 900:
            continue
        score = (100 if GOOD.search(cats) else 0) + min(w * h / 1e6, 24) - (30 if w / max(h, 1) > 2.2 or h / max(w, 1) > 2.2 else 0)
        out.append({'score': round(score, 1), 'title': title, 'url': ii.get('thumburl') or ii.get('url'),
                    'a': val('Artist')[:120] or 'Wikimedia Commons', 'l': lic, 'page': ii.get('descriptionurl', ''),
                    'good': bool(GOOD.search(cats)), 'size': [w, h]})
    return out


def main():
    out = os.environ.get('OUT') or 'ai-batch'
    only = [x for x in (os.environ.get('ONLY') or '').split(',') if x.strip()]
    dst = os.path.join(out, 'src', 'img', 'msc-src')
    os.makedirs(dst, exist_ok=True)
    report = {}
    for art, terms in SUBJECT.items():
        if only and art not in only:
            continue
        seen, pool = set(), []
        for t in terms:
            try:
                for c in candidates(t):
                    if c['title'] not in seen:
                        seen.add(c['title']); pool.append(c)
            except Exception as e:
                print(f'  {art} "{t}": {type(e).__name__}: {str(e)[:120]}', flush=True)
            time.sleep(1)
        pool.sort(key=lambda c: -c['score'])
        report[art] = []
        for i, c in enumerate(pool[:3], 1):
            try:
                data = get(c['url'])
                open(os.path.join(dst, f'{art}-{i}.jpg'), 'wb').write(data)
                json.dump(c, open(os.path.join(dst, f'{art}-{i}.json'), 'w'), ensure_ascii=False, indent=1)
                report[art].append(c['title'])
            except Exception as e:
                print(f'  {art} #{i}: {type(e).__name__}: {str(e)[:120]}', flush=True)
            time.sleep(1)
        print(f'{art}: {len(pool)} free candidates, kept {len(report[art])}'
              f'{" (quality/featured)" if pool and pool[0]["good"] else ""}', flush=True)
    json.dump(report, open(os.path.join(dst, 'report.json'), 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
