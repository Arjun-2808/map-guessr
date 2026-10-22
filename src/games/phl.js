window.GAME = {
  id: 'ph', nav: 'phl',
  projection: () => d3.geoMercator(),
  graticule: {
    ext: [[100, -10], [150, 35]], step: 5, labelLon: 120, labelLat: 10,
    lats: [5, 10, 15, 20], latLabel: v => v + '° N',
    lons: [115, 130], lonLabel: v => v + '° E'
  },
  levels: __LEVELS__,
  filter: {
    label: 'Find', def: 'prov',
    opts: [{ key: 'prov', label: 'Provinces' }, { key: 'reg', label: 'Regions', depth: 1, noSub: true }],
    test: (it, k) => it.set === k
  },
  count: (items, c) => {
    if (c.filter === 'reg') return items.length + (items.length === 1 ? ' region' : ' regions');
    const mm = items.some(i => i.kind !== 'Province'), n = items.length - (mm ? 1 : 0);
    return [n ? n + (n === 1 ? ' province' : ' provinces') : '', mm ? 'Metro Manila' : ''].filter(Boolean).join(' + ');
  },
  hint: 'Show region', hitText: 'Tama! Spot on.', sea: 'You clicked the sea.'
};
