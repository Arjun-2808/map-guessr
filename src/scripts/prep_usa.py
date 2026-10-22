"""Build US area code cells (planar) + one item per in-service code.
usage: python3 -I prep_usa.py <mosaic.geojson> <areacodes.json> <npa_report.csv> <out.geojson> <items.json>
mosaic.geojson = mapshaper -mosaic of the 2010 HSIP polygons, each cell with S = 2010 codes covering it.
"""
import json, sys, csv
from collections import Counter, defaultdict
from shapely.geometry import shape, mapping
from shapely.ops import unary_union

mosaic_path, meta_path, csv_path, out_geo, out_items = sys.argv[1:6]
SKIP = {'PR', 'VI', 'GU', 'MP', 'AS'}
STATES = {'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California', 'CO': 'Colorado',
          'CT': 'Connecticut', 'DE': 'Delaware', 'DC': 'District of Columbia', 'FL': 'Florida', 'GA': 'Georgia',
          'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas',
          'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland', 'MA': 'Massachusetts',
          'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi', 'MO': 'Missouri', 'MT': 'Montana',
          'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico',
          'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma',
          'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina', 'SD': 'South Dakota',
          'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington',
          'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming'}
REGION = {}
for r, ss in {'northeast': 'CT ME MA NH RI VT NJ NY PA',
              'midwest': 'IL IN MI OH WI IA KS MN MO NE ND SD',
              'south': 'DE DC FL GA MD NC SC VA WV AL KY MS TN AR LA OK TX',
              'west': 'AZ CO ID MT NV NM UT WY AK CA HI OR WA'}.items():
    for s in ss.split():
        REGION[s] = r

meta = {c['npa']: c for c in json.load(open(meta_path))['areaCodes'] if c['country'] == 'US' and c['region'] not in SKIP}
rows = {r['NPA_ID']: r for r in csv.DictReader(open(csv_path).readlines()[1:])}
from datetime import datetime
def since(n):
    try: return datetime.strptime(rows[n]['IN_SERVICE_DT'], '%d-%b-%Y')
    except Exception: return datetime(2100, 1, 1)
def complex_of(n):
    cx = {n}
    for part in (rows.get(n, {}).get('OVERLAY_COMPLEX') or '').split(','):
        cx |= {x.strip() for x in part.split('/') if x.strip()}
    return cx

# ---- cells
cells = []
for f in json.load(open(mosaic_path))['features']:
    if not f['geometry']: continue
    g = shape(f['geometry']).buffer(0)
    if g.is_empty: continue
    cells.append({'g': g, 'S': frozenset(f['properties']['S'] or [])})
TINY = 0.0003  # deg^2, ~3 km^2
def merge_small(cells):
    changed = True
    while changed:
        changed = False
        cells.sort(key=lambda c: c['g'].area)
        for i, c in enumerate(cells):
            if c['g'].area >= TINY and c['S']: continue
            best, bl = None, 0
            for j, o in enumerate(cells):
                if j == i or not o['S'] or (o['g'].area < TINY): continue
                if not c['g'].buffer(1e-9).intersects(o['g']): continue
                l = c['g'].buffer(1e-6).intersection(o['g'].boundary).length
                if l > bl: best, bl = j, l
            if best is None:
                if c['g'].area < TINY or not c['S']:
                    cells.pop(i); changed = True; break
                continue
            cells[best]['g'] = unary_union([cells[best]['g'], c['g']]).buffer(0)
            cells.pop(i); changed = True; break
    return cells
cells = merge_small(cells)
byS = defaultdict(list)
for c in cells: byS[c['S']].append(c['g'])
cells = [{'S': S, 'g': unary_union(gs).buffer(0)} for S, gs in byS.items()]
print('cells after merge', len(cells))
have2010 = set().union(*[c['S'] for c in cells])

# ---- assign current codes to cells
assign = {}
for n, m in meta.items():
    cx = complex_of(n)
    shp = (cx & have2010) or (set(m['shapeIds']) & have2010)
    cand = [i for i, c in enumerate(cells) if c['S'] & shp]
    tgt = [i for i in cand if cells[i]['S'] <= cx]
    if not tgt:
        tgt = [i for i in cand if n in cells[i]['S']] or cand
        print('loose', n, [sorted(cells[i]['S']) for i in tgt][:4])
    assign[n] = tgt
cell_codes = defaultdict(set)
for n, t in assign.items():
    for i in t: cell_codes[i].add(n)
# orphan cells (overlap slivers no code claims): merge into the neighbour with the longest shared edge
for i, c in enumerate(cells):
    if cell_codes[i]: continue
    best, bl = None, 0
    for j, o in enumerate(cells):
        if j == i or not cell_codes[j]: continue
        l = c['g'].buffer(1e-6).intersection(o['g'].boundary).length
        if l > bl: best, bl = j, l
    print('orphan cell', sorted(c['S']), round(c['g'].area, 4), '-> merged into', sorted(cell_codes[best]) if best is not None else None)
    if best is not None:
        cells[best]['g'] = unary_union([cells[best]['g'], c['g']]).buffer(0)
# dissolve cells that ended up with identical code sets
groups = defaultdict(list)
for i in range(len(cells)):
    if cell_codes[i]: groups[frozenset(cell_codes[i])].append(i)
cells2, codes2 = [], []
for cs, idx in groups.items():
    cells2.append({'g': unary_union([cells[i]['g'] for i in idx]).buffer(0)}); codes2.append(set(cs))
remap = {i: gi for gi, idx in enumerate(groups.values()) for i in idx}
assign = {n: sorted({remap[i] for i in t if i in remap}) for n, t in assign.items()}
cells, cell_codes = cells2, dict(enumerate(codes2))
print('cells after dissolve', len(cells))
keep = [i for i in range(len(cells)) if cell_codes[i]]
key_of = {}
feats = []
for i in keep:
    codes = sorted(cell_codes[i], key=since)
    st = Counter(meta[n]['region'] for n in codes).most_common(1)[0][0]
    k = codes[0] + ('' if codes[0] not in key_of.values() else '-' + str(i))
    key_of[i] = k
    feats.append({'type': 'Feature', 'properties': {'k': k, 'g1': REGION[st], 'g2': st,
                  'lbl': ' · '.join(sorted(codes)) + ' · ' + STATES[st]}, 'geometry': mapping(cells[i]['g'])})
base_codes = {sorted(cell_codes[i], key=since)[0] for i in keep}

items = []
for n in sorted(meta):
    m = meta[n]
    tgt = [key_of[i] for i in assign[n] if i in key_of]
    others = sorted({c for i in assign[n] for c in cell_codes[i]} - {n})
    x = []
    if m['cities']: x.append('Covers ' + ', '.join(m['cities'][:3]) + '.')
    if others: x.append('Shares its area with ' + (', '.join(others[:-1]) + ' and ' + others[-1] if len(others) > 1 else others[0]) + '.')
    items.append({'set': 'all', 'n': n, 'kind': 'Area code', 's': STATES[m['region']], 'g1': REGION[m['region']],
                  'g2': m['region'], 'f': tgt, 't': 'base' if n in base_codes else 'overlay',
                  **({'x': ' '.join(x)} if x else {})})

json.dump({'type': 'FeatureCollection', 'features': feats}, open(out_geo, 'w'))
json.dump(items, open(out_items, 'w'))
print('cells', len(feats), 'items', len(items), Counter(i['t'] for i in items))
print('multi-cell', [(i['n'], i['f']) for i in items if len(i['f']) > 1])
for n in ('212', '646', '718', '465', '917', '404', '770', '943', '219', '941', '305'):
    it = next(i for i in items if i['n'] == n); print(n, it['f'], it['t'], it.get('x'))
