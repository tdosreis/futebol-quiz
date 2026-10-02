#!/usr/bin/env python3
"""Find a source photograph for a person the album has no picture of.

The person's Wikipedia article (Portuguese first, then English) names its lead
image; Wikimedia Commons says who took it and under what licence. Only a free
licence is accepted, and only an article that is about football — "Cuca" is a
coach, not the folklore monster. Returns the photo bytes and its credit, or
None. Run from GitHub Actions: Wikimedia is not reachable from every sandbox.

  python3 tools/gemini/sources.py "Carlo Ancelotti"   # try one, print what it found
"""
import json, re, sys, urllib.parse, urllib.request

UA = 'futebol-quiz-portraits/1.0 (https://github.com/tdosreis/futebol-quiz)'
FREE = re.compile(r'^(cc0|cc[- ]by|public domain|pd|gfdl|attribution|copyrighted free use|no restrictions)', re.I)
FOOTBALL = re.compile(r'futebol|football|soccer|futbol|fútbol|calcio|fußball|treinador|técnico|coach|manager|'
                      r'jogador|jogadora|árbitro|referee|goleir|atacante|zagueir|meio-campista|dirigente', re.I)


def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read()


def api(host, **params):
    params.update(format='json', formatversion='2')
    return json.loads(get(f'https://{host}/w/api.php?' + urllib.parse.urlencode(params)))


def article_image(name, lang):
    q = api(f'{lang}.wikipedia.org', action='query', titles=name, redirects=1,
            prop='pageimages|description|pageprops|extracts', piprop='name', exintro=1, explaintext=1, exchars=600)
    pages = (q.get('query') or {}).get('pages') or []
    if not pages or pages[0].get('missing'):
        return None
    p = pages[0]
    if 'disambiguation' in (p.get('pageprops') or {}):
        return None
    about = (p.get('description') or '') + ' ' + (p.get('extract') or '')
    if not FOOTBALL.search(about) or not p.get('pageimage'):
        return None
    return p['pageimage'], p.get('title')


def commons_file(fname, width=900):
    q = api('commons.wikimedia.org', action='query', titles='File:' + fname, prop='imageinfo',
            iiprop='url|extmetadata', iiurlwidth=width)
    pages = (q.get('query') or {}).get('pages') or []
    if not pages or 'imageinfo' not in pages[0]:
        return None
    ii = pages[0]['imageinfo'][0]
    md = ii.get('extmetadata') or {}
    val = lambda k: re.sub(r'<[^>]+>', '', (md.get(k) or {}).get('value') or '').strip()
    lic = val('LicenseShortName')
    if not FREE.search(lic):
        return None
    return {'url': ii.get('thumburl') or ii.get('url'), 'a': val('Artist')[:120] or 'Wikimedia Commons',
            'l': lic, 'page': ii.get('descriptionurl', '')}


def find(name):
    for lang in ('pt', 'en'):
        try:
            hit = article_image(name, lang)
            if not hit:
                continue
            f = commons_file(hit[0])
            if not f:
                continue
            data = get(f['url'])
            if len(data) < 6000:
                continue
            f.update(article=f'{lang}:{hit[1]}')
            return data, f
        except Exception as e:      # a page that will not load is a person without a photo, not a crash
            print(f'  {name} ({lang}): {type(e).__name__}: {str(e)[:120]}', flush=True)
    return None


if __name__ == '__main__':
    for n in sys.argv[1:]:
        r = find(n)
        print(n, '->', r[1] if r else 'nothing usable')
