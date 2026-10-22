window.GAME = {
  id: 'ac', nav: 'usa',
  projection: () => d3.geoAlbersUsa(),
  graticule: null,
  levels: __LEVELS__,
  filter: {
    label: 'Which codes', def: 'all',
    opts: [{ key: 'all', label: 'All codes' }, { key: 'base', label: 'Skip overlays' }],
    test: (it, k) => k === 'all' || it.t === 'base'
  },
  count: items => {
    const o = items.filter(i => i.t === 'overlay').length;
    return items.length + (items.length === 1 ? ' area code' : ' area codes') + (o ? ` (${o} ${o === 1 ? 'overlay' : 'overlays'})` : '');
  },
  hint: 'Show state', hitText: 'Spot on.', sea: 'You clicked outside the map.'
};
