// /api/auth?action=me | signup | login | logout
import { send, fail, query, readJson, postGuard, clientIp, rateLimit } from '../lib/http.js';
import { db, USER_RE, getUser, createUser, checkPassword, startSession, endSession, sessionUser } from '../lib/store.js';

export default async function handler(req, res) {
  const r = db();
  if (!r) return fail(res, 503, 'Accounts are offline right now.');
  const action = query(req).get('action');
  try {
    if (action === 'me') {
      const u = await sessionUser(r, req);
      return send(res, 200, { user: u ? { name: u.name } : null });
    }
    if (!postGuard(req, res)) return;
    const body = (await readJson(req)) || {};
    const ip = clientIp(req);

    if (action === 'logout') {
      await endSession(r, req, res);
      return send(res, 200, { user: null });
    }

    const name = String(body.username || '').trim();
    const pw = String(body.password || '');
    if (!USER_RE.test(name)) return fail(res, 400, 'Usernames are 3 to 20 letters, numbers or underscores.');
    if (pw.length < 8 || pw.length > 200) return fail(res, 400, 'Passwords need at least 8 characters.');
    const lower = name.toLowerCase();

    if (action === 'signup') {
      if (!(await rateLimit(r, 'signup:' + ip, 10, 3600))) return fail(res, 429, 'Too many new accounts from here. Try again in an hour.');
      if (!(await createUser(r, name, pw))) return fail(res, 409, 'That username is taken.');
      await startSession(r, res, lower);
      return send(res, 200, { user: { name } });
    }
    if (action === 'login') {
      const okIp = await rateLimit(r, 'login-ip:' + ip, 30, 600);
      const okUser = await rateLimit(r, 'login-user:' + lower, 10, 600);
      if (!okIp || !okUser) return fail(res, 429, 'Too many attempts. Wait 10 minutes and try again.');
      const u = await getUser(r, lower);
      if (!u || !(await checkPassword(pw, u))) return fail(res, 401, 'Wrong username or password.');
      await startSession(r, res, lower);
      return send(res, 200, { user: { name: u.name } });
    }
    return fail(res, 400, 'Unknown action.');
  } catch (e) {
    console.error('auth error', e);
    return fail(res, 500, 'Something went wrong on our side. Try again.');
  }
}
