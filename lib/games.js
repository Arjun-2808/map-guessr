// Game data, scopes and scoring. The scoring maths mirrors the page engine exactly,
// so the server can re-score a run from the raw click coordinates.
import crypto from 'node:crypto';
import { geoBounds, geoDistance, geoContains } from 'd3-geo';
import { feature } from 'topojson-client';

const LOADERS = {
  idn: () => import('./data/idn.js'),
  phl: () => import('./data/phl.js'),
  usa: () => import('./data/usa.js'),
};
const RULES = {
  idn: { def: 'both', depth: { both: 2, kab: 2, kota: 2 }, test: (it, k) => k === 'both' || it.t === k },
  phl: { def: 'prov', depth: { prov: 2, reg: 1 }, test: (it, k) => it.set === k },
  usa: { def: 'all', depth: { all: 2, base: 2 }, test: (it, k) => k === 'all' || it.t === 'base' },
};
export const ROUNDS = [5, 10, 20, 'all'];
const cache = {};
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

export async function loadGame(id) {
  if (!RULES[id]) return null;
  if (cache[id]) return cache[id];
  const d = (await LOADERS[id]()).default;
  const feats = feature(d.topo, d.topo.objects.k).features;
  const fidx = {};
  feats.forEach((f, i) => { fidx[f.properties.k] = i; });
  const items = d.items.map((it, i) => ({ ...it, id: i, fs: it.f.map(k => fidx[k]).filter(v => v != null) }));
  const g = {
    id, feats, fidx, items, rules: RULES[id],
    l1: new Set(d.levels[0].opts.map(o => o.key)),
    l2: new Map(d.levels[1].opts.map(o => [o.key, o.parent])),
  };
  cache[id] = g;
  return g;
}

// Validate and normalise a setup; returns null if invalid.
export function normCfg(g, c) {
  if (!c || typeof c !== 'object') return null;
  const filter = c.filter ?? g.rules.def;
  if (!(filter in g.rules.depth)) return null;
  const rounds = c.rounds === 'all' ? 'all' : Number(c.rounds);
  if (!ROUNDS.includes(rounds)) return null;
  let g1 = String(c.g1 ?? 'all'), g2 = String(c.g2 ?? 'all');
  if (g1 !== 'all' && !g.l1.has(g1)) return null;
  if (g.rules.depth[filter] < 2) g2 = 'all';
  if (g2 !== 'all') {
    if (!g.l2.has(g2)) return null;
    g1 = g.l2.get(g2);
  }
  return { g1, g2, filter, rounds };
}
export const fullCfg = g => ({ g1: 'all', g2: 'all', filter: g.rules.def, rounds: 10 });
export const cfgKey = c => [c.g1, c.g2, c.filter, c.rounds].join('|');

export function scopeItems(g, c) {
  const deep = g.rules.depth[c.filter] >= 2;
  return g.items.filter(it => g.rules.test(it, c.filter) && (c.g1 === 'all' || it.g1 === c.g1) && (!deep || c.g2 === 'all' || it.g2 === c.g2));
}
function featsOf(items) { const s = new Set(); items.forEach(it => it.fs.forEach(fi => s.add(fi))); return [...s]; }
export function scaleKm(g, items) {
  const [[w, s], [e, n]] = geoBounds({ type: 'FeatureCollection', features: featsOf(items).map(i => g.feats[i]) });
  const spanLon = e >= w ? e - w : e + 360 - w;
  const d = geoDistance([0, s], [Math.min(spanLon, 179), n]) * 6371;
  return clamp(d / 25, 12, 160);
}

// Same edge-distance routine as the page.
function nearest(ll, f) {
  const [lon0, lat0] = ll;
  const kx = 111.32 * Math.cos(lat0 * Math.PI / 180), ky = 110.57;
  const polys = f.geometry.type === 'Polygon' ? [f.geometry.coordinates] : f.geometry.coordinates;
  let best = Infinity, bp = ll;
  for (const poly of polys) for (const ring of poly) for (let i = 0; i < ring.length - 1; i++) {
    let ax = ring[i][0] - lon0, bx = ring[i + 1][0] - lon0;
    if (ax > 180) ax -= 360; if (ax < -180) ax += 360; if (bx > 180) bx -= 360; if (bx < -180) bx += 360;
    ax *= kx; bx *= kx;
    const ay = (ring[i][1] - lat0) * ky, by = (ring[i + 1][1] - lat0) * ky;
    const dx = bx - ax, dy = by - ay, L = dx * dx + dy * dy;
    const t = L ? clamp(-(ax * dx + ay * dy) / L, 0, 1) : 0;
    const px = ax + t * dx, py = ay + t * dy, d = Math.hypot(px, py);
    if (d < best) { best = d; bp = [lon0 + px / kx, lat0 + py / ky]; }
  }
  return { km: best, point: bp };
}

// guess = { lon, lat, k (clicked feature key or null), hint }
export function scoreGuess(g, item, guess, scale) {
  const ok = guess && Number.isFinite(guess.lon) && Number.isFinite(guess.lat) && Math.abs(guess.lat) <= 90 && Math.abs(guess.lon) <= 360;
  if (!ok) return { pts: 0, km: null, hit: false };
  const ll = [guess.lon, guess.lat];
  const fi = guess.k != null ? g.fidx[guess.k] : undefined;
  let hit = false;
  if (fi !== undefined && item.fs.includes(fi)) {
    // the page tests the click against the drawn (simplified) shape; accept it if the point is
    // inside or within a few pixels' worth of that shape at the run's zoom level
    const f = g.feats[fi];
    hit = geoContains(f, ll) || geoDistance(ll, nearest(ll, f).point) * 6371 < Math.max(3, scale * 0.05);
  }
  let km = 0;
  if (!hit) {
    let best = null;
    item.fs.forEach(i => { const r = nearest(ll, g.feats[i]); if (!best || r.km < best.km) best = r; });
    km = geoDistance(ll, best.point) * 6371;
  }
  let pts = hit ? 1000 : Math.round(800 * Math.exp(-km / scale));
  if (guess.hint) pts = Math.round(pts / 2);
  return { pts, km, hit };
}

// Deterministic daily set: same 10 for everyone on a given UTC day.
export function dailyQueue(g, date, salt) {
  const items = scopeItems(g, fullCfg(g));
  let seed = crypto.createHash('sha256').update(`${salt}|${g.id}|${date}`).digest().readUInt32LE(0);
  const rand = () => { seed |= 0; seed = (seed + 0x6D2B79F5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  const ids = items.map(it => it.id);
  for (let i = ids.length - 1; i > 0; i--) { const j = Math.floor(rand() * (i + 1)); [ids[i], ids[j]] = [ids[j], ids[i]]; }
  return ids.slice(0, 10);
}
export const utcDate = (t = Date.now()) => new Date(t).toISOString().slice(0, 10);
export function shuffle(a) {
  a = a.slice();
  for (let i = a.length - 1; i > 0; i--) { const j = crypto.randomInt(i + 1); [a[i], a[j]] = [a[j], a[i]]; }
  return a;
}
