// Small request/response helpers shared by the API functions.
import crypto from 'node:crypto';

export function send(res, status, body) {
  res.statusCode = status;
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.setHeader('Cache-Control', 'no-store');
  res.end(JSON.stringify(body));
}
export const fail = (res, status, error, extra = {}) => send(res, status, { error, ...extra });

export function query(req) {
  return new URL(req.url, 'http://local').searchParams;
}

export async function readJson(req) {
  // Vercel's Node runtime may have parsed the body already.
  try { if (req.body !== undefined && req.body !== null) return typeof req.body === 'string' ? JSON.parse(req.body) : req.body; } catch (e) { return null; }
  let size = 0;
  const chunks = [];
  for await (const c of req) {
    size += c.length;
    if (size > 256 * 1024) return null;
    chunks.push(c);
  }
  try { return JSON.parse(Buffer.concat(chunks).toString('utf8') || '{}'); } catch (e) { return null; }
}

// State-changing calls must be same-origin JSON POSTs (blocks cross-site form posts).
export function postGuard(req, res) {
  if (req.method !== 'POST') { fail(res, 405, 'Use POST.'); return false; }
  if (!String(req.headers['content-type'] || '').includes('application/json')) { fail(res, 415, 'Send JSON.'); return false; }
  const origin = req.headers.origin;
  if (origin) {
    let host = '';
    try { host = new URL(origin).host; } catch (e) {}
    if (host !== req.headers.host) { fail(res, 403, 'Cross-site request blocked.'); return false; }
  }
  return true;
}

export function clientIp(req) {
  return String(req.headers['x-real-ip'] || req.headers['x-forwarded-for'] || '').split(',')[0].trim() || 'unknown';
}

export async function rateLimit(r, key, limit, windowSec) {
  const n = await r.incr('rl:' + key);
  if (n === 1) await r.expire('rl:' + key, windowSec);
  return n <= limit;
}

export function cookies(req) {
  const out = {};
  String(req.headers.cookie || '').split(';').forEach(p => {
    const i = p.indexOf('=');
    if (i > 0) out[p.slice(0, i).trim()] = decodeURIComponent(p.slice(i + 1).trim());
  });
  return out;
}

export const sha256 = s => crypto.createHash('sha256').update(s).digest('hex');
export const token = (n = 32) => crypto.randomBytes(n).toString('base64url');
