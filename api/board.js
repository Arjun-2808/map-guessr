// /api/board?game=idn&kind=setup&g1=..&g2=..&filter=..&rounds=..   or   kind=daily | full
import { send, fail, query } from '../lib/http.js';
import { db, sessionUser, topEntries } from '../lib/store.js';
import { loadGame, normCfg, fullCfg, cfgKey, utcDate } from '../lib/games.js';

export default async function handler(req, res) {
  const r = db();
  if (!r) return fail(res, 503, 'Leaderboards are offline right now.');
  if (req.method !== 'GET') return fail(res, 405, 'Use GET.');
  try {
    const q = query(req);
    const g = await loadGame(q.get('game'));
    if (!g) return fail(res, 400, 'Unknown game.');
    const kind = q.get('kind') || 'setup';
    const limit = Math.max(1, Math.min(50, Number(q.get('limit')) || 50));
    const me = await sessionUser(r, req);
    let key, extra = {};
    if (kind === 'daily') {
      const date = utcDate();
      key = `lb:daily:${g.id}:${date}`;
      const next = new Date(date + 'T00:00:00Z').getTime() + 86400000;
      extra = { date, resetsInMs: next - Date.now() };
      if (me) {
        const done = await r.get(`daily:done:${g.id}:${date}:${me.lower}`);
        extra.played = done ? JSON.parse(done) : null;
      }
    } else {
      const cfg = kind === 'full' ? fullCfg(g) : normCfg(g, { g1: q.get('g1'), g2: q.get('g2'), filter: q.get('filter'), rounds: q.get('rounds') });
      if (!cfg) return fail(res, 400, 'That setup is not valid.');
      key = `lb:${g.id}:${cfgKey(cfg)}`;
      extra = { cfg };
    }
    const out = await topEntries(r, key, limit, me);
    return send(res, 200, { kind, ...extra, ...out, signedIn: !!me });
  } catch (e) {
    console.error('board error', e);
    return fail(res, 500, 'Something went wrong on our side. Try again.');
  }
}
