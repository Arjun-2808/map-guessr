"""Build Philippines features + items.
usage: python3 -I prep_phl.py <dir with r*.json> <out.geojson> <items.json>
Regions follow 2024 changes: Negros Island Region (RA 12000) and Sulu outside BARMM (SC ruling, 2024).
"""
import json, sys, glob, os
from shapely.geometry import shape, mapping
from shapely.ops import unary_union

src_dir, out_geo, out_items = sys.argv[1:4]

PSGC_REGION = {1: 'I', 2: 'II', 3: 'III', 4: 'IVA', 5: 'V', 6: 'VI', 7: 'VII', 8: 'VIII', 9: 'IX',
               10: 'X', 11: 'XI', 12: 'XII', 13: 'NCR', 14: 'CAR', 16: 'XIII', 17: 'IVB', 19: 'BARMM'}
REGIONS = [  # key, designation (sign top line), name, island group
    ('NCR', 'NCR', 'National Capital Region', 'luzon'),
    ('CAR', 'CAR', 'Cordillera Administrative Region', 'luzon'),
    ('I', 'Region I', 'Ilocos Region', 'luzon'),
    ('II', 'Region II', 'Cagayan Valley', 'luzon'),
    ('III', 'Region III', 'Central Luzon', 'luzon'),
    ('IVA', 'Region IV-A', 'Calabarzon', 'luzon'),
    ('IVB', 'Region IV-B', 'Mimaropa', 'luzon'),
    ('V', 'Region V', 'Bicol Region', 'luzon'),
    ('VI', 'Region VI', 'Western Visayas', 'visayas'),
    ('NIR', 'NIR', 'Negros Island Region', 'visayas'),
    ('VII', 'Region VII', 'Central Visayas', 'visayas'),
    ('VIII', 'Region VIII', 'Eastern Visayas', 'visayas'),
    ('IX', 'Region IX', 'Zamboanga Peninsula', 'mindanao'),
    ('X', 'Region X', 'Northern Mindanao', 'mindanao'),
    ('XI', 'Region XI', 'Davao Region', 'mindanao'),
    ('XII', 'Region XII', 'Soccsksargen', 'mindanao'),
    ('XIII', 'Region XIII', 'Caraga', 'mindanao'),
    ('BARMM', 'BARMM', 'Bangsamoro', 'mindanao'),
]
RINFO = {k: (d, n, g) for k, d, n, g in REGIONS}
MOVE = {'Negros Occidental': 'NIR', 'Negros Oriental': 'NIR', 'Siquijor': 'NIR', 'Sulu': None}
ALIAS = {'Davao de Oro': 'Formerly Compostela Valley.', 'Cotabato': 'Also called North Cotabato.',
         'Samar': 'Also called Western Samar.', 'Maguindanao del Norte': 'Split from Maguindanao in 2022.',
         'Maguindanao del Sur': 'Split from Maguindanao in 2022.',
         'Negros Occidental': 'Moved to the new Negros Island Region in 2024.',
         'Negros Oriental': 'Moved to the new Negros Island Region in 2024.',
         'Siquijor': 'Moved to the new Negros Island Region in 2024.',
         'Sulu': 'The Supreme Court ruled in 2024 that Sulu is not part of BARMM.'}

feats, ncr = [], []
for f in sorted(glob.glob(os.path.join(src_dir, 'r*.json'))):
    for x in json.load(open(f))['features']:
        p = x['properties']
        reg = PSGC_REGION[p['adm1_psgc'] // 100000000]
        name = p['adm2_en']
        geom = shape(x['geometry']).buffer(0)
        if reg == 'NCR':
            ncr.append(geom); continue
        if name and name.startswith('City of Isabela'):
            feats.append({'k': 'isabela-city', 'kind': 'city', 'n': 'Isabela City', 'reg': 'IX', 'geom': geom,
                          'lbl': 'Isabela City · Zamboanga Peninsula (independent of Basilan province)'})
            continue
        if name is None:
            feats.append({'k': 'barmm-sga', 'kind': 'sga', 'n': 'BARMM Special Geographic Area', 'reg': 'BARMM', 'geom': geom,
                          'lbl': 'Special Geographic Area · Bangsamoro (not part of a province)'})
            continue
        reg = MOVE.get(name, reg)
        feats.append({'k': name.lower().replace(' ', '-'), 'kind': 'prov', 'n': name, 'reg': reg, 'geom': geom})
feats.append({'k': 'metro-manila', 'kind': 'ncr', 'n': 'Metro Manila', 'reg': 'NCR', 'geom': unary_union(ncr).buffer(0)})

def island(reg, geom):
    if reg: return RINFO[reg][2]
    return 'mindanao'  # Sulu

out, items = [], []
for f in feats:
    g1 = island(f['reg'], f['geom'])
    props = {'k': f['k'], 'g1': g1}
    if f['reg']: props['g2'] = f['reg']
    if f.get('lbl'): props['lbl'] = f['lbl']
    out.append({'type': 'Feature', 'properties': props, 'geometry': mapping(f['geom'])})
    if f['kind'] in ('prov', 'ncr'):
        reg = f['reg']
        items.append({'set': 'prov', 'n': f['n'], 'kind': 'Province' if f['kind'] == 'prov' else 'National Capital Region',
                      's': RINFO[reg][1] if reg else 'No region', 'g1': g1, 'g2': reg, 'f': [f['k']],
                      **({'x': ALIAS[f['n']]} if f['n'] in ALIAS else {})})
for k, d, n, g in REGIONS:
    members = [f['k'] for f in feats if f['reg'] == k]
    items.append({'set': 'reg', 'n': n, 'kind': d, 's': {'luzon': 'Luzon', 'visayas': 'Visayas', 'mindanao': 'Mindanao'}[g],
                  'g1': g, 'g2': k, 'f': members,
                  **({'x': 'Created in 2024 from Negros Occidental, Negros Oriental and Siquijor.'} if k == 'NIR' else {}),
                  **({'x': 'Sulu is no longer part of BARMM after a 2024 Supreme Court ruling.'} if k == 'BARMM' else {})})

json.dump({'type': 'FeatureCollection', 'features': out}, open(out_geo, 'w'))
json.dump(items, open(out_items, 'w'), ensure_ascii=False)
from collections import Counter
print('features', len(out), 'items', Counter(i['set'] for i in items))
print(Counter((i['g2'] or '-') for i in items if i['set'] == 'prov'))
print([(i['n'], len(i['f'])) for i in items if i['set'] == 'reg'])
