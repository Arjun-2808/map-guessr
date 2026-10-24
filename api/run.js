// /api/run?action=start | finish   (ranked score runs and the daily challenge)
import { send, fail, query, readJson, postGuard, rateLimit, token } from '../lib/http.js';
import { db, sessionUser } from '../lib/store.js';
import { loadGame, normCfg, fullCfg, cfgKey, scopeItems, scaleKm, scoreGuess, dailyQueue, utcDate, shuffle } from '../lib/games.js';

const RUN_TTL = 3 * 3600;
const MIN_MS_PER_ROUND = 600;

async function dailySalt(r) {
  let s = await r.get('daily:salt');
  if (!s) { await r.set('daily:salt', token(24), { nx: true }); s = await r.get('daily:salt'); }
  return s;
}

export default async function handler(req, res) {
  const r = db();
  if (!r) return fail(res, 503, 'Leaderboards are offline right now.');
  if (!postGuard(req, res)) return;
  try {
    const me = await sessionUser(r, req);
    if (!me) return fail(res, 401, 'Sign in to play ranked runs.');
    const action = query(req).get('action');
    const body = (await readJson(req)) || {};

    if (action === 'start') {
      if (!(await rateLimit(r, 'start:' + me.lower, 300, 3600))) return fail(res, 429, 'Slow down a little and try again soon.');
      const g = await loadGame(String(body.game));
      if (!g) return fail(res, 400, 'Unknown game.');
      let cfg, queue, date = null;
      if (body.daily) {
        date = utcDate();
        cfg = fullCfg(g);
        const doneKey = `daily:done:${g.id}:${date}:${me.lower}`;
        const fresh = await r.set(doneKey, JSON.stringify({ started: Date.now() }), { nx: true, ex: 3 * 86400 });
        if (!fresh) {
          const prev = JSON.parse((await r.get(doneKey)) || '{}');
          return fail(res, 409, "You've already played today's daily.", { played: prev });
        }
        queue = dailyQueue(g, date, await dailySalt(r));
      } else {
        cfg = normCfg(g, body.cfg);
        if (!cfg) return fail(res, 400, 'That setup is not valid.');
        const ids = scopeItems(g, cfg).map(it => it.id);
        if (!ids.length) return fail(res, 400, 'Nothing to find in that setup.');
        queue = shuffle(ids);
        if (cfg.rounds !== 'all') queue = queue.slice(0, cfg.rounds);
      }
      const runId = token(18);
      await r.set('run:' + runId, JSON.stringify({ user: me.lower, game: g.id, cfg, queue, daily: !!body.daily, date, t0: Date.now() }), { ex: RUN_TTL });
      return send(res, 200, { runId, queue, cfg, daily: !!body.daily, date });
    }

    if (action === 'finish') {
      const runId = String(body.runId || '');
      const raw = runId && (await r.get('run:' + runId));
      if (!raw) return fail(res, 404, 'This run has expired. Start a new one.');
      const run = JSON.parse(raw);
      if (run.user !== me.lower) return fail(res, 403, 'This run belongs to someone else.');
      await r.del('run:' + runId); // one submission per run
      const guesses = Array.isArray(body.guesses) ? body.guesses : [];
      if (guesses.length !== run.queue.length) return fail(res, 400, 'That run is incomplete.');
      if (Date.now() - run.t0 < MIN_MS_PER_ROUND * run.queue.length) return fail(res, 400, 'That was too fast to count.');

      const g = await loadGame(run.game);
      const scale = scaleKm(g, scopeItems(g, run.cfg));
      const rounds = run.queue.map((id, i) => scoreGuess(g, g.items[id], guesses[i], scale));
      const score = rounds.reduce((s, x) => s + x.pts, 0);

      const key = run.daily ? `lb:daily:${g.id}:${run.date}` : `lb:${g.id}:${cfgKey(run.cfg)}`;
      const prev = await r.zscore(key, me.lower);
      await r.zadd(key, { gt: true }, { score, member: me.lower });
      if (run.daily) {
        await r.expire(key, 40 * 86400);
        await r.set(`daily:done:${g.id}:${run.date}:${me.lower}`, JSON.stringify({ score }), { ex: 3 * 86400 });
      }
      const rank = Number(await r.zrevrank(key, me.lower)) + 1;
      const total = Number(await r.zcard(key));
      const best = Math.max(score, prev == null ? 0 : Number(prev));
      return send(res, 200, {
        score, rank, total, best, isBest: prev == null || score > Number(prev), daily: run.daily, date: run.date,
        rounds: rounds.map(x => ({ pts: x.pts, km: x.km == null ? null : Math.round(x.km * 10) / 10 })),
      });
    }
    return fail(res, 400, 'Unknown action.');
  } catch (e) {
    console.error('run error', e);
    return fail(res, 500, 'Something went wrong on our side. Try again.');
  }
}
