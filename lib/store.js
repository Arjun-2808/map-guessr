// Redis access (Upstash REST) plus accounts and sessions.
import crypto from 'node:crypto';
import { promisify } from 'node:util';
import { Redis } from '@upstash/redis';
import { cookies, sha256, token } from './http.js';

const scrypt = promisify(crypto.scrypt);
let client = null;

export function db() {
  if (globalThis.__mgRedis) return globalThis.__mgRedis; // test hook
  if (client) return client;
  const url = process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL;
  const tok = process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN;
  if (!url || !tok) return null;
  client = new Redis({ url, token: tok, automaticDeserialization: false });
  return client;
}

export const USER_RE = /^[A-Za-z0-9_]{3,20}$/;
const SESSION_DAYS = 30;
const COOKIE = 'mg_sess';

export async function hashPassword(pw, salt = crypto.randomBytes(16).toString('hex')) {
  const key = await scrypt(pw.normalize('NFKC'), salt, 64, { N: 16384, r: 8, p: 1 });
  return { salt, hash: key.toString('hex') };
}
export async function checkPassword(pw, user) {
  const { hash } = await hashPassword(pw, user.salt);
  const a = Buffer.from(hash, 'hex'), b = Buffer.from(user.hash, 'hex');
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

export async function getUser(r, lower) {
  const raw = await r.get('user:' + lower);
  return raw ? JSON.parse(raw) : null;
}
export async function createUser(r, name, pw) {
  const lower = name.toLowerCase();
  const { salt, hash } = await hashPassword(pw);
  const ok = await r.set('user:' + lower, JSON.stringify({ name, salt, hash, created: Date.now() }), { nx: true });
  if (!ok) return false;
  await r.set('name:' + lower, name);
  return true;
}

export async function startSession(r, res, lower) {
  const t = token();
  await r.set('sess:' + sha256(t), lower, { ex: SESSION_DAYS * 86400 });
  res.setHeader('Set-Cookie', `${COOKIE}=${t}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${SESSION_DAYS * 86400}`);
}
export async function endSession(r, req, res) {
  const t = cookies(req)[COOKIE];
  if (t) await r.del('sess:' + sha256(t));
  res.setHeader('Set-Cookie', `${COOKIE}=; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0`);
}
// -> { lower, name } or null
export async function sessionUser(r, req) {
  const t = cookies(req)[COOKIE];
  if (!t || t.length > 100) return null;
  const lower = await r.get('sess:' + sha256(t));
  if (!lower) return null;
  const name = await r.get('name:' + lower);
  return { lower, name: name || lower };
}

// Leaderboard helpers ------------------------------------------------------
export async function topEntries(r, key, limit, me) {
  const flat = await r.zrange(key, 0, limit - 1, { rev: true, withScores: true });
  const rows = [];
  for (let i = 0; i < flat.length; i += 2) rows.push({ lower: String(flat[i]), score: Number(flat[i + 1]) });
  const names = rows.length ? await r.mget(...rows.map(x => 'name:' + x.lower)) : [];
  const total = await r.zcard(key);
  const entries = rows.map((x, i) => ({ rank: i + 1, name: names[i] || x.lower, score: x.score, me: !!me && me.lower === x.lower }));
  let mine = null;
  if (me) {
    const rk = await r.zrevrank(key, me.lower);
    if (rk !== null && rk !== undefined) mine = { rank: Number(rk) + 1, score: Number(await r.zscore(key, me.lower)) };
  }
  return { entries, total: Number(total) || 0, me: mine };
}
