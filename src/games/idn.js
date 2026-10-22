window.GAME = {
  id: 'kg', nav: 'idn',
  projection: () => d3.geoMercator(),
  graticule: {
    ext: [[50, -45], [180, 40]], step: 5, equator: true, labelLon: 100, labelLat: 0,
    lats: [5, 0, -5, -10], latLabel: v => (v === 0 ? 'Khatulistiwa 0°' : Math.abs(v) + '° ' + (v > 0 ? 'LU' : 'LS')),
    lons: [95, 140], lonLabel: v => v + '° BT'
  },
  levels: __LEVELS__,
  filter: {
    label: 'Which names', def: 'both',
    opts: [{ key: 'both', label: 'Both' }, { key: 'kab', label: 'Kabupaten' }, { key: 'kota', label: 'Kota' }],
    test: (it, k) => k === 'both' || it.t === k
  },
  count: items => {
    const kab = items.filter(i => i.t === 'kab').length, kota = items.length - kab;
    return [kab ? kab + ' kabupaten' : '', kota ? kota + ' kota' : ''].filter(Boolean).join(' · ');
  },
  short: it => (it.t === 'kota' ? 'Kota ' : 'Kab. ') + it.n,
  hint: 'Show province', hitText: 'Tepat! Spot on.', sea: 'You clicked the sea.'
};
