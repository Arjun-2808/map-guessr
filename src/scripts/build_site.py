"""Assemble the three game pages.
usage: python3 -I build_site.py <scratchpad dir>
writes site/{index,philippines,area-codes}.html (full documents, for any static host)
and    kabupaten-guessr.html (body-only main artifact page) + art/{philippines,area-codes}.html
"""
import json, sys, os, re
R = sys.argv[1]
P = lambda *a: os.path.join(R, *a)
engine = open(P('engine', 'engine.html')).read()

# ---------- Indonesia: convert the existing topo to the shared format ----------
ISLANDS = [
    ('sumatera', 'Sumatera', ['Aceh', 'Sumatera Utara', 'Sumatera Barat', 'Riau', 'Kepulauan Riau', 'Jambi', 'Bengkulu', 'Sumatera Selatan', 'Kepulauan Bangka Belitung', 'Lampung']),
    ('jawa', 'Jawa', ['Banten', 'DKI Jakarta', 'Jawa Barat', 'Jawa Tengah', 'DI Yogyakarta', 'Jawa Timur']),
    ('nusra', 'Bali & Nusa Tenggara', ['Bali', 'Nusa Tenggara Barat', 'Nusa Tenggara Timur']),
    ('kalimantan', 'Kalimantan', ['Kalimantan Barat', 'Kalimantan Tengah', 'Kalimantan Selatan', 'Kalimantan Timur', 'Kalimantan Utara']),
    ('sulawesi', 'Sulawesi', ['Sulawesi Utara', 'Gorontalo', 'Sulawesi Tengah', 'Sulawesi Barat', 'Sulawesi Selatan', 'Sulawesi Tenggara']),
    ('maluku', 'Maluku', ['Maluku Utara', 'Maluku']),
    ('papua', 'Papua', ['Papua Barat Daya', 'Papua Barat', 'Papua Tengah', 'Papua', 'Papua Pegunungan', 'Papua Selatan']),
]
PROV_ISL = {p: k for k, _, ps in ISLANDS for p in ps}
slug = lambda s: re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')
idn = json.load(open(P('data', 'kab.topo.json')))
idn['objects'] = {'k': idn['objects']['k']}
idn_items = []
for g in idn['objects']['k']['geometries']:
    p = g['properties']
    np_ = {'g1': PROV_ISL[p['p']], 'g2': p['p']}
    if p.get('w'):
        np_.update(k='w-' + slug(p['n']), w=p['w'], lbl=p['n'])
    else:
        np_['k'] = p['t'] + '-' + slug(p['n'])
        it = {'n': p['n'], 'kind': 'Kabupaten' if p['t'] == 'kab' else 'Kota', 's': p['p'], 'g1': np_['g1'], 'g2': p['p'],
              'f': [np_['k']], 't': p['t']}
        if p.get('a'): it['x'] = f"Formerly {p['a']}."
        idn_items.append(it)
    g['properties'] = np_
idn_levels = [
    {'label': 'Island group', 'noun': 'island group', 'all': 'Seluruh Indonesia', 'opts': [{'key': k, 'name': n} for k, n, _ in ISLANDS]},
    {'label': 'Province', 'noun': 'province', 'all': 'All provinces', 'opts': [{'key': p, 'name': p, 'parent': k} for k, _, ps in ISLANDS for p in ps]},
]

# ---------- Philippines ----------
phl = json.load(open(P('data', 'phl', 'phl.topo.json')))
phl_items = json.load(open(P('data', 'phl', 'items.json')))
regs = [i for i in phl_items if i['set'] == 'reg']
phl_levels = [
    {'label': 'Island group', 'noun': 'island group', 'all': 'Whole Philippines',
     'opts': [{'key': 'luzon', 'name': 'Luzon'}, {'key': 'visayas', 'name': 'Visayas'}, {'key': 'mindanao', 'name': 'Mindanao'}]},
    {'label': 'Region', 'noun': 'region', 'all': 'All regions', 'opts': [{'key': r['g2'], 'name': r['n'], 'parent': r['g1']} for r in regs]},
]

# ---------- USA ----------
usa = json.load(open(P('data', 'usa', 'usa.topo.json')))
usa_items = json.load(open(P('data', 'usa', 'items.json')))
REG = [('northeast', 'Northeast'), ('midwest', 'Midwest'), ('south', 'South'), ('west', 'West')]
states = sorted({(i['g2'], i['s'], i['g1']) for i in usa_items}, key=lambda t: t[1])
usa_levels = [
    {'label': 'Census region', 'noun': 'region', 'all': 'Whole US', 'opts': [{'key': k, 'name': n} for k, n in REG]},
    {'label': 'State', 'noun': 'state', 'all': 'All states', 'opts': [{'key': k, 'name': n, 'parent': g} for k, n, g in states]},
]

GAMES = [
    dict(file='index.html', js='idn.js', topo=idn, items=idn_items, levels=idn_levels,
         title='Kabupaten Guessr', noun='name',
         lede='A name appears on the sign. Find that kabupaten or kota on a blank map of Indonesia.',
         maplabel='Map of Indonesia divided into kabupaten and kota',
         desc="Find Indonesia's 514 kabupaten and kota on a blank map. Score runs and drills by island or province.",
         credit='Boundaries: BPS 2020 via <a href="https://www.geoboundaries.org" target="_blank" rel="noopener">geoBoundaries</a> (CC BY 3.0 IGO). Provinces follow the 2022 Papua split; renamed regencies use current names.'),
    dict(file='philippines.html', js='phl.js', topo=phl, items=phl_items, levels=phl_levels,
         title='Philippines Guessr', noun='name',
         lede='A name appears on the sign. Find that province or region on a blank map of the Philippines.',
         maplabel='Map of the Philippines divided into provinces and regions',
         desc='Find the 82 provinces, Metro Manila and the 18 regions of the Philippines on a blank map.',
         credit='Boundaries: PSA/NAMRIA PSGC (Dec 2023) via <a href="https://github.com/faeldon/philippines-json-maps" target="_blank" rel="noopener">philippines-json-maps</a>. Includes the 2024 Negros Island Region; Sulu is shown outside BARMM after the 2024 Supreme Court ruling.'),
    dict(file='area-codes.html', js='usa.js', topo=usa, items=usa_items, levels=usa_levels,
         title='Area Code Guessr', noun='code',
         lede='An area code appears on the sign. Find where it rings on a blank map of the US.',
         maplabel='Map of the United States divided into telephone area code regions',
         desc='Find every in-service US area code on a blank map, overlays included, by region or state.',
         credit='Boundaries: HIFLD/HSIP 2010 area code polygons (public domain), with later overlays matched through the NANPA database via <a href="https://github.com/benaduggan/area-code-map" target="_blank" rel="noopener">area-code-map</a>. Puerto Rico and other territories aren\'t shown.'),
]

def page(g):
    data = json.dumps({'topo': g['topo'], 'items': g['items']}, separators=(',', ':'), ensure_ascii=False).replace('</', '<\\/')
    js = open(P('games', g['js'])).read().replace('__LEVELS__', json.dumps(g['levels'], ensure_ascii=False))
    s = engine
    for k, v in {'TITLE': g['title'], 'LEDE': g['lede'], 'MAPLABEL': g['maplabel'], 'NOUN': g['noun'], 'CREDIT': g['credit']}.items():
        s = s.replace('{{' + k + '}}', v)
    s = s.replace('{{GAME}}', js).replace('{{DATA}}', data)
    assert '{{' not in s.replace('{{DATA}}', ''), 'unfilled placeholder'
    return s

def full_doc(body, desc):
    i = body.index('</style>') + len('</style>')
    return ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            f'<meta name="description" content="{desc}">\n<style>body{{margin:0}}</style>\n'
            + body[:i] + '\n</head>\n<body>\n' + body[i:] + '\n</body>\n</html>\n')

os.makedirs(P('site'), exist_ok=True); os.makedirs(P('art'), exist_ok=True)
# server-side copies of the game data for the leaderboard API (re-scoring runs)
if os.path.isdir(P('repo', 'lib')):
    os.makedirs(P('repo', 'lib', 'data'), exist_ok=True)
    for g in GAMES:
        key = g['js'].split('.')[0]
        payload = json.dumps({'topo': g['topo'], 'items': g['items'], 'levels': g['levels']}, separators=(',', ':'), ensure_ascii=False)
        open(P('repo', 'lib', 'data', key + '.js'), 'w').write('// generated by src/scripts/build_site.py\nexport default ' + payload + ';\n')
for g in GAMES:
    body = page(g)
    open(P('site', g['file']), 'w').write(full_doc(body, g['desc'].replace('"', '&quot;')))
    if g['file'] == 'index.html':
        open(P('kabupaten-guessr.html'), 'w').write(body)
    else:
        open(P('art', g['file']), 'w').write(full_doc(body, g['desc'].replace('"', '&quot;')))
    print(g['file'], len(body), 'items', len(g['items']))
