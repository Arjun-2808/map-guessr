"""Enrich geoBoundaries IDN ADM2 with province, type, current names.
usage: python3 -I prep.py adm1.geojson adm2.geojson out.geojson
"""
import json, sys
from shapely.geometry import shape

adm1_path, adm2_path, out_path = sys.argv[1:4]

PROV_ID = {  # geoBoundaries English name -> Indonesian name
    'Aceh': 'Aceh', 'North Sumatra': 'Sumatera Utara', 'West Sumatra': 'Sumatera Barat',
    'Riau': 'Riau', 'Riau Islands': 'Kepulauan Riau', 'Jambi': 'Jambi', 'Bengkulu': 'Bengkulu',
    'South Sumatra': 'Sumatera Selatan', 'Bangka-Belitung Islands': 'Kepulauan Bangka Belitung',
    'Lampung': 'Lampung', 'Banten': 'Banten', 'Jakarta Special Capital Region': 'DKI Jakarta',
    'West Java': 'Jawa Barat', 'Central Java': 'Jawa Tengah',
    'Special Region of Yogyakarta': 'DI Yogyakarta', 'East Java': 'Jawa Timur', 'Bali': 'Bali',
    'West Nusa Tenggara': 'Nusa Tenggara Barat', 'East Nusa Tenggara': 'Nusa Tenggara Timur',
    'West Kalimantan': 'Kalimantan Barat', 'Central Kalimantan': 'Kalimantan Tengah',
    'South Kalimantan': 'Kalimantan Selatan', 'East Kalimantan': 'Kalimantan Timur',
    'North Kalimantan': 'Kalimantan Utara', 'North Sulawesi': 'Sulawesi Utara',
    'Gorontalo': 'Gorontalo', 'Central Sulawesi': 'Sulawesi Tengah', 'West Sulawesi': 'Sulawesi Barat',
    'South Sulawesi': 'Sulawesi Selatan', 'Southeast Sulawesi': 'Sulawesi Tenggara',
    'Maluku': 'Maluku', 'North Maluku': 'Maluku Utara', 'Papua': 'Papua', 'West Papua': 'Papua Barat',
}

# 2022 Papua split: regencies moved out of Papua / Papua Barat
PAPUA_SPLIT = {
    'Papua Selatan': ['Merauke', 'Boven Digoel', 'Mappi', 'Asmat'],
    'Papua Tengah': ['Nabire', 'Puncak Jaya', 'Paniai', 'Mimika', 'Puncak', 'Dogiyai', 'Intan Jaya', 'Deiyai'],
    'Papua Pegunungan': ['Jayawijaya', 'Pegunungan Bintang', 'Yahukimo', 'Tolikara',
                         'Mamberamo Tengah', 'Yalimo', 'Lanny Jaya', 'Nduga'],
    'Papua Barat Daya': ['Kota Sorong', 'Sorong', 'Sorong Selatan', 'Raja Ampat', 'Tambrauw', 'Maybrat'],
}
SPLIT_LOOKUP = {k: p for p, ks in PAPUA_SPLIT.items() for k in ks}
SPLIT_LOOKUP['Kepulauan Seribu'] = 'DKI Jakarta'

# source name -> (current official name, former name to show)
RENAME = {
    'Toba Samosir': ('Toba', 'Toba Samosir'),
    'Mamuju Utara': ('Pasangkayu', 'Mamuju Utara'),
    'Maluku Tenggara Barat': ('Kepulauan Tanimbar', 'Maluku Tenggara Barat'),
    'Mahakam Hulu': ('Mahakam Ulu', None),
    'Siau Tagulandang Biaro': ('Kepulauan Siau Tagulandang Biaro', None),
    'Banyu Asin': ('Banyuasin', None),
    'Karang Asem': ('Karangasem', None),
    'Toli-Toli': ('Tolitoli', None),
    'Labuhan Batu': ('Labuhanbatu', None),
    'Labuhan Batu Selatan': ('Labuhanbatu Selatan', None),
    'Labuhan Batu Utara': ('Labuhanbatu Utara', None),
    'Gunung Kidul': ('Gunungkidul', None),
    'Pangkajene Dan Kepulauan': ('Pangkajene dan Kepulauan', None),
    'Kota Baru': ('Kotabaru', None),
    'Kota Banjar Baru': ('Kota Banjarbaru', None),
    'Kota Sawah Lunto': ('Kota Sawahlunto', None),
    'Kota Pangkal Pinang': ('Kota Pangkalpinang', None),
    'Kota Tanjung Pinang': ('Kota Tanjungpinang', None),
    'Kota Tanjung Balai': ('Kota Tanjungbalai', None),
    'Kota Pematang Siantar': ('Kota Pematangsiantar', None),
}
NON_PLAYABLE = {'Danau', 'Danau Toba', 'Hutan', 'Waduk Cirata', 'Wadung Kedungombo'}

adm1 = json.load(open(adm1_path))
provs = [(PROV_ID[f['properties']['shapeName']], shape(f['geometry']).buffer(0)) for f in adm1['features']]

adm2 = json.load(open(adm2_path))
out = []
for f in adm2['features']:
    src = f['properties']['shapeName']
    geom = shape(f['geometry']).buffer(0)
    pt = geom.representative_point()
    hits = [p for p, g in provs if g.contains(pt)]
    if not hits:  # small islands the simplified province outline misses: nearest province
        hits = [min(provs, key=lambda pg: pg[1].distance(geom))[0]]
        print('fallback:', src, '->', hits[0])
    prov = hits[0]
    if src in SPLIT_LOOKUP:
        prov = SPLIT_LOOKUP[src]
    name, alt = RENAME.get(src, (src, None))
    props = {'p': prov}
    if src in NON_PLAYABLE:
        props['w'] = 2 if src == 'Hutan' else 1  # 1 = lake/reservoir, 2 = non-playable land
        props['n'] = src
    else:
        is_kota = name.startswith('Kota ')
        props['t'] = 'kota' if is_kota else 'kab'
        props['n'] = name[5:] if is_kota else name
        if alt:
            props['a'] = alt
    out.append({'type': 'Feature', 'properties': props, 'geometry': f['geometry']})

json.dump({'type': 'FeatureCollection', 'features': out}, open(out_path, 'w'))

# report
from collections import Counter
play = [o['properties'] for o in out if 'w' not in o['properties']]
print('playable', len(play), Counter(p['t'] for p in play))
c = Counter(p['p'] for p in play)
for k in sorted(c):
    print(f'{c[k]:3d} {k}')
print('non-playable', [(o['properties']['n'], o['properties']['p']) for o in out if 'w' in o['properties']])
