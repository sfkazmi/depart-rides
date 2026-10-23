#!/usr/bin/env python3
"""Depart Rides agent portal. Stdlib only (http.server + sqlite3).
Runs on 127.0.0.1:3891 behind Apache (/agents/*). No secrets in this file:
the pepper and public-page slug live in $STATE/secret.json (created on first run)."""
import hashlib, hmac, html, re, json, os, secrets, sqlite3, string, sys, time, threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse, urlencode

STATE = os.environ.get('PORTAL_STATE', '/var/lib/departrides-portal')
DB = os.path.join(STATE, 'portal.db')
PORT = int(os.environ.get('PORTAL_PORT', '3891'))
BASE = '/agents'
PKT = timezone(timedelta(hours=5))
CARS = [('prado', 'Toyota Prado'), ('land-cruiser-v8', 'Land Cruiser V8'), ('haval-h6', 'Haval H6'),
        ('jetour-t2', 'Jetour T2'), ('corolla-xli', 'Corolla XLi')]
CARN = dict(CARS)
SLOTS = [('morning', 'Morning'), ('evening', 'Evening')]
TRIPS = [('local', 'Local'), ('out', 'Out of city')]
DAYS = 14

def load_secret():
    p = os.path.join(STATE, 'secret.json')
    if not os.path.exists(p):
        d = {'pepper': secrets.token_hex(32), 'public_slug': 'availability-' + secrets.token_hex(4)}
        fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as f: json.dump(d, f)
    with open(p) as f: return json.load(f)

def db():
    c = sqlite3.connect(DB, timeout=10); c.row_factory = sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON'); return c

def init_db():
    with db() as c:
        c.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS agents(id INTEGER PRIMARY KEY, name TEXT NOT NULL, username TEXT UNIQUE NOT NULL COLLATE NOCASE,
          pw_hash TEXT NOT NULL, code_hash TEXT UNIQUE NOT NULL, created_at TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS admins(id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, pw_hash TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY, role TEXT NOT NULL, ref_id INTEGER NOT NULL, expires REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS bookings(id INTEGER PRIMARY KEY, agent_id INTEGER NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
          car TEXT NOT NULL, date TEXT NOT NULL, slot TEXT NOT NULL, trip TEXT NOT NULL, amount INTEGER NOT NULL,
          created_at TEXT NOT NULL, cancelled_at TEXT);
        CREATE UNIQUE INDEX IF NOT EXISTS one_booking ON bookings(car, date, slot) WHERE cancelled_at IS NULL;
        ''')
        for t, col in (('sessions', 'as_agent INTEGER'), ('bookings', 'by_admin INTEGER')):
            if col.split()[0] not in [r[1] for r in c.execute(f'PRAGMA table_info({t})')]:
                c.execute(f'ALTER TABLE {t} ADD COLUMN {col}')

def pw_hash(pw, salt=None):
    salt = salt or secrets.token_bytes(16)
    h = hashlib.scrypt(pw.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return salt.hex() + '$' + h.hex()

def pw_check(pw, stored):
    try: s, _ = stored.split('$'); return hmac.compare_digest(pw_hash(pw, bytes.fromhex(s)), stored)
    except Exception: return False

def code_hash(code): return hmac.new(SECRET['pepper'].encode(), b'code:' + code.encode(), 'sha256').hexdigest()
def tok_hash(t): return hashlib.sha256(t.encode()).hexdigest()
def now_pkt(): return datetime.now(PKT)
def today(): return now_pkt().date()

# ---- rate limiting (in memory) ----
LOCK = threading.Lock(); FAILS = {}
LIMITS = {'ip': (10, 900), 'user': (5, 900), 'code-global': (60, 3600), 'admin-ip': (5, 3600)}
def limited(kind, key):
    n, win = LIMITS[kind]; t = time.time()
    with LOCK:
        lst = [x for x in FAILS.get((kind, key), []) if t - x < win]; FAILS[(kind, key)] = lst
        return len(lst) >= n
def fail(kind, key):
    with LOCK: FAILS.setdefault((kind, key), []).append(time.time())

# ---- html ----
CSS = '''@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,600;1,600&family=Outfit:wght@300;400;500;600;700&display=swap');
:root{--bg:#050706;--panel:#101513;--panel2:#161c19;--line:#262e29;--ink:#f4f1e8;--muted:#9aa39b;--lime:#cafa58;--gold:#cbb991;--red:#ff6b5e}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 Outfit,sans-serif}
a{color:var(--lime)}.wrap{max-width:1100px;margin:0 auto;padding:18px}
header{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:14px 18px;border-bottom:1px solid var(--line)}
header img{height:30px}h1,h2{font-family:'Cormorant Garamond',serif;font-weight:600;line-height:1.05;margin:.2em 0}h1{font-size:40px}h2{font-size:30px}
.accent{color:var(--lime);font-style:italic}.muted{color:var(--muted)}.eyebrow{font-size:11px;letter-spacing:.18em;color:var(--gold);text-transform:uppercase}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:18px;margin:16px 0}
label{display:block;font-size:13px;color:var(--muted);margin:10px 0 4px}
input,select{width:100%;padding:12px 14px;border-radius:12px;border:1px solid var(--line);background:var(--panel2);color:var(--ink);font:inherit;font-size:16px}
.btn{display:inline-block;border:0;border-radius:999px;background:var(--lime);color:#071006;font:600 15px Outfit,sans-serif;padding:12px 22px;cursor:pointer;text-decoration:none}
.btn.ghost{background:transparent;color:var(--ink);border:1px solid var(--line)}.btn.sm{padding:7px 14px;font-size:13px}.btn.danger{background:var(--red);color:#fff}
.grid2{display:grid;gap:12px}@media(min-width:720px){.grid2{grid-template-columns:1fr 1fr}}
.msg{padding:12px 14px;border-radius:12px;margin:12px 0;background:#18240f;border:1px solid #3c5a1c}.msg.err{background:#2a1110;border-color:#6b2a25}
.cal{display:grid;gap:10px}@media(min-width:720px){.cal{grid-template-columns:repeat(2,1fr)}}@media(min-width:1000px){.cal{grid-template-columns:repeat(3,1fr)}}
.day{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:12px}.day h3{margin:0 0 8px;font-size:15px;font-weight:600}
.row{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:5px 0;border-top:1px solid var(--line);font-size:13.5px}
.chips{display:flex;gap:6px}.chip{min-width:62px;text-align:center;border-radius:999px;padding:3px 8px;font-size:12px;font-weight:600}
.free{background:#1c2b10;color:var(--lime)}.booked{background:#2a1513;color:#ff9b91}.mine{background:#2a2412;color:var(--gold)}
table{width:100%;border-collapse:collapse;font-size:13.5px}td,th{padding:8px 6px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
.tablewrap{overflow-x:auto}.nav{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:8px 0}.tabs{display:flex;gap:8px;margin:10px 0}
.legend{display:flex;gap:8px;flex-wrap:wrap;font-size:12px;margin:8px 0}
code{background:var(--panel2);padding:2px 6px;border-radius:6px;font-size:15px}'''

def e(s): return html.escape(str(s), quote=True)
def page(title, body, right=''):
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow"><title>{e(title)} · Depart Rides</title><style>{CSS}</style></head><body>
<header><a href="https://departrides.com/"><img src="/assets/logo.svg" alt="Depart Rides"></a><div>{right}</div></header><main class="wrap">{body}</main></body></html>'''

def fmt_day(d): return d.strftime('%a %d %b')
def rs(n): return 'Rs ' + f'{n:,}'

def calendar(start, viewer_agent=None, link_base=None):
    end = start + timedelta(days=DAYS - 1)
    with db() as c:
        rows = c.execute('SELECT car,date,slot,agent_id FROM bookings WHERE cancelled_at IS NULL AND date BETWEEN ? AND ?',
                         (start.isoformat(), end.isoformat())).fetchall()
    taken = {(r['car'], r['date'], r['slot']): r['agent_id'] for r in rows}
    out = ['<div class="legend"><span class="chip free">Available</span><span class="chip booked">Booked</span>' +
           ('<span class="chip mine">Your booking</span>' if viewer_agent else '') + '</div><div class="cal">']
    for i in range(DAYS):
        d = start + timedelta(days=i); ds = d.isoformat()
        out.append(f'<div class="day"><h3>{fmt_day(d)}</h3>')
        for cid, cname in CARS:
            chips = []
            for sid, sname in SLOTS:
                a = taken.get((cid, ds, sid))
                cls, txt = ('free', sname) if a is None else (('mine', sname) if viewer_agent and a == viewer_agent else ('booked', sname))
                chips.append(f'<span class="chip {cls}" title="{e(cname)} {e(sname)}: {"available" if a is None else "booked"}">{txt}</span>')
            out.append(f'<div class="row"><span>{e(cname)}</span><span class="chips">{"".join(chips)}</span></div>')
        out.append('</div>')
    out.append('</div>')
    prev_s, next_s = start - timedelta(days=DAYS), start + timedelta(days=DAYS)
    nav = '<div class="nav">'
    if prev_s >= today() - timedelta(days=DAYS): nav += f'<a class="btn ghost sm" href="{link_base}?from={prev_s}">← Earlier</a>'
    nav += f'<span class="muted">{fmt_day(start)} – {fmt_day(end)}</span><a class="btn ghost sm" href="{link_base}?from={next_s}">Later →</a></div>'
    return nav + ''.join(out)

def parse_start(q):
    try: d = datetime.strptime(q.get('from', [''])[0], '%Y-%m-%d').date()
    except ValueError: d = today()
    lo, hi = today() - timedelta(days=60), today() + timedelta(days=365)
    return min(max(d, lo), hi)

class H(BaseHTTPRequestHandler):
    server_version = 'DRPortal'
    def log_message(self, fmt, *a): sys.stderr.write('%s %s\n' % (self.ip(), fmt % a))
    def ip(self):
        xf = self.headers.get('X-Forwarded-For', '')
        return xf.split(',')[-1].strip() if xf else self.client_address[0]
    def csrf_cookie(self):
        for part in self.headers.get('Cookie', '').split(';'):
            k, _, v = part.strip().partition('=')
            if k == 'dr_c' and len(v) >= 20: return v
    def send(self, body, code=200, headers=()):
        tok = self.csrf_cookie(); headers = list(headers)
        if not tok:
            tok = secrets.token_urlsafe(24)
            headers.append(('Set-Cookie', f'dr_c={tok}; Path={BASE}; Max-Age=2592000; HttpOnly; Secure; SameSite=Strict'))
        body = re.sub(r'(<form [^>]*method="post"[^>]*>)', lambda m: m.group(1) + f'<input type="hidden" name="csrf" value="{tok}">', body)
        b = body.encode(); self.send_response(code)
        self.send_header('Content-Type', 'text/html; charset=utf-8'); self.send_header('Content-Length', str(len(b)))
        self.send_header('Cache-Control', 'no-store'); self.send_header('X-Robots-Tag', 'noindex, nofollow')
        self.send_header('X-Frame-Options', 'DENY'); self.send_header('Referrer-Policy', 'same-origin')
        self.send_header('X-Content-Type-Options', 'nosniff')
        for k, v in headers: self.send_header(k, v)
        self.end_headers(); self.wfile.write(b)
    def redirect(self, loc, headers=()):
        self.send_response(303); self.send_header('Location', loc); self.send_header('Cache-Control', 'no-store')
        for k, v in headers: self.send_header(k, v)
        self.send_header('Content-Length', '0'); self.end_headers()
    def cookie(self):
        for part in self.headers.get('Cookie', '').split(';'):
            k, _, v = part.strip().partition('=')
            if k == 'dr_s': return v
    def session(self, role):
        self.as_admin = None
        t = self.cookie()
        if not t: return None
        with db() as c:
            self.as_admin = None
            r = c.execute('SELECT ref_id FROM sessions WHERE token_hash=? AND role=? AND expires>?', (tok_hash(t), role, time.time())).fetchone()
            if not r and role == 'agent':  # admin viewing as an agent
                r2 = c.execute("SELECT ref_id, as_agent FROM sessions WHERE token_hash=? AND role='admin' AND expires>? AND as_agent IS NOT NULL", (tok_hash(t), time.time())).fetchone()
                if r2:
                    self.as_admin = r2['ref_id']
                    return c.execute('SELECT * FROM agents WHERE id=? AND active=1', (r2['as_agent'],)).fetchone()
            if not r: return None
            if role == 'agent':
                a = c.execute('SELECT * FROM agents WHERE id=? AND active=1', (r['ref_id'],)).fetchone()
                return a
            return c.execute('SELECT * FROM admins WHERE id=?', (r['ref_id'],)).fetchone()
    def new_session(self, role, ref, ttl):
        t = secrets.token_urlsafe(32)
        with db() as c:
            c.execute('DELETE FROM sessions WHERE expires<?', (time.time(),))
            c.execute('INSERT INTO sessions(token_hash,role,ref_id,expires) VALUES(?,?,?,?)', (tok_hash(t), role, ref, time.time() + ttl))
        return ('Set-Cookie', f'dr_s={t}; Path={BASE}; Max-Age={ttl}; HttpOnly; Secure; SameSite=Strict')
    def end_session(self):
        t = self.cookie()
        if t:
            with db() as c: c.execute('DELETE FROM sessions WHERE token_hash=?', (tok_hash(t),))
        return ('Set-Cookie', f'dr_s=; Path={BASE}; Max-Age=0; HttpOnly; Secure; SameSite=Strict')
    def form(self):
        n = min(int(self.headers.get('Content-Length') or 0), 10000)
        return {k: v[0].strip() for k, v in parse_qs(self.rfile.read(n).decode('utf-8', 'replace')).items()}
    def same_origin(self, f):
        ok = ('https://departrides.com', 'https://www.departrides.com')
        o = (self.headers.get('Origin') or '').rstrip('/')
        if o in ok: return True
        r = self.headers.get('Referer') or ''
        if o in ('', 'null') and any(r == x or r.startswith(x + '/') for x in ok): return True
        if o not in ('', 'null'): return False  # a real foreign origin
        c = self.csrf_cookie()  # no usable Origin/Referer: double-submit token + SameSite=Strict
        return bool(c) and hmac.compare_digest(c, f.get('csrf', ''))

    # ---------- GET ----------
    def do_GET(self):
        u = urlparse(self.path); p = u.path.rstrip('/') or '/'; q = parse_qs(u.query)
        msg = q.get('m', [''])[0]; err = q.get('err', [''])[0]
        flash = (f'<div class="msg">{e(msg)}</div>' if msg else '') + (f'<div class="msg err">{e(err)}</div>' if err else '')
        if p == BASE: return self.agent_home(q, flash)
        if p == BASE + '/admin': return self.admin_home(q, flash)
        if p == BASE + '/' + SECRET['public_slug']:
            start = parse_start(q)
            body = (f'<span class="eyebrow">Agent availability</span><h1>Car <span class="accent">availability</span></h1>'
                    f'<p class="muted">Morning and evening slots for the next days. Updated live. To book, log in to the agent portal or call/WhatsApp 0339 9999038.</p>'
                    + calendar(start, None, BASE + '/' + SECRET['public_slug']))
            return self.send(page('Availability', body))
        if p == '/healthz': return self.send('ok')
        self.send(page('Not found', '<h1>Not found</h1>'), 404)

    def agent_home(self, q, flash):
        a = self.session('agent')
        if not a:
            body = f'''<span class="eyebrow">Agent portal</span><h1>Agent <span class="accent">login</span></h1>{flash}
<div class="grid2"><form class="panel" method="post" action="{BASE}/login"><input type="hidden" name="mode" value="pw"><h2>Username</h2>
<label>Username</label><input name="username" autocomplete="username" required maxlength="40" autocapitalize="none">
<label>Password (3 letters)</label><input name="password" type="password" autocomplete="current-password" required maxlength="20">
<p><button class="btn">Log in</button></p></form>
<form class="panel" method="post" action="{BASE}/login"><input type="hidden" name="mode" value="code"><h2>6-digit code</h2>
<label>Your agent code</label><input name="code" inputmode="numeric" pattern="[0-9]{{6}}" maxlength="6" required autocomplete="one-time-code">
<p><button class="btn">Log in with code</button></p></form></div>
<p class="muted">Need access? Contact Depart Rides on 0339 9999038.</p>'''
            return self.send(page('Agent login', body))
        start = parse_start(q); t = today()
        with db() as c:
            mine = c.execute('SELECT * FROM bookings WHERE agent_id=? AND cancelled_at IS NULL AND date>=? ORDER BY date,slot', (a['id'], t.isoformat())).fetchall()
        car_opts = ''.join(f'<option value="{k}">{e(v)}</option>' for k, v in CARS)
        rows = ''.join(f'''<tr><td>{fmt_day(datetime.strptime(b["date"],"%Y-%m-%d"))}</td><td>{e(CARN.get(b["car"],b["car"]))}</td><td>{dict(SLOTS)[b["slot"]]}</td>
<td>{dict(TRIPS)[b["trip"]]}</td><td>{rs(b["amount"])}</td><td><form method="post" action="{BASE}/cancel" onsubmit="return confirm('Cancel this booking?')">
<input type="hidden" name="id" value="{b["id"]}"><button class="btn danger sm">Cancel</button></form></td></tr>''' for b in mine)
        body = f'''<span class="eyebrow">Agent portal</span><h1>Hi, <span class="accent">{e(a["name"])}</span></h1>{flash}
<form class="panel" method="post" action="{BASE}/book"><h2>New booking</h2><div class="grid2">
<div><label>Car</label><select name="car" required>{car_opts}</select></div>
<div><label>Date</label><input type="date" name="date" required min="{t}" max="{t + timedelta(days=365)}" value="{t}"></div>
<div><label>Slot</label><select name="slot">{''.join(f'<option value="{k}">{v}</option>' for k,v in SLOTS)}</select></div>
<div><label>Trip</label><select name="trip">{''.join(f'<option value="{k}">{v}</option>' for k,v in TRIPS)}</select></div>
<div><label>Booking amount (Rs)</label><input name="amount" inputmode="numeric" pattern="[0-9]{{1,7}}" required placeholder="e.g. 25000"></div>
</div><p><button class="btn">Book this slot</button></p></form>
<div class="panel"><h2>Your upcoming bookings</h2>{('<div class="tablewrap"><table><tr><th>Date</th><th>Car</th><th>Slot</th><th>Trip</th><th>Amount</th><th></th></tr>' + rows + '</table></div>') if mine else '<p class="muted">No upcoming bookings.</p>'}</div>
<h2>Availability</h2>{calendar(start, a["id"], BASE)}'''
        right = f'<form method="post" action="{BASE}/logout"><button class="btn ghost sm">Log out</button></form>'
        if self.as_admin:
            right = f'<form method="post" action="{BASE}/admin/stop-as"><button class="btn sm">Back to admin</button></form>'
            body = f'<div class="msg" style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap"><span>Viewing as <b>{e(a["name"])}</b> (admin). Bookings you make are recorded as made by admin on their behalf.</span><form method="post" action="{BASE}/admin/stop-as"><button class="btn sm">Back to admin</button></form></div>' + body
        self.send(page('Agent portal', body, right))

    def admin_home(self, q, flash):
        ad = self.session('admin')
        if not ad:
            body = f'''<span class="eyebrow">Admin</span><h1>Admin <span class="accent">login</span></h1>{flash}
<form class="panel" method="post" action="{BASE}/admin/login" style="max-width:420px"><label>Username</label><input name="username" required autocapitalize="none">
<label>Password</label><input name="password" type="password" required><p><button class="btn">Log in</button></p></form>'''
            return self.send(page('Admin', body))
        show = q.get('show', ['upcoming'])[0]
        with db() as c:
            agents = c.execute('SELECT a.*, (SELECT COUNT(*) FROM bookings b WHERE b.agent_id=a.id AND b.cancelled_at IS NULL) n FROM agents a WHERE active=1 ORDER BY name').fetchall()
            sql = 'SELECT b.*, a.name agent FROM bookings b JOIN agents a ON a.id=b.agent_id WHERE b.cancelled_at IS NULL'
            args = ()
            if show != 'all': sql += ' AND b.date>=?'; args = (today().isoformat(),)
            bks = c.execute(sql + ' ORDER BY b.date, b.slot, b.car', args).fetchall()
        total = sum(b['amount'] for b in bks)
        arows = ''.join(f'''<tr><td>{e(x["name"])}</td><td>{e(x["username"])}</td><td>{x["n"]}</td><td><form method="post" action="{BASE}/admin/agent-del" onsubmit="return confirm('Remove agent {e(x["name"])} and all their bookings?')">
<input type="hidden" name="id" value="{x["id"]}"><button class="btn danger sm">Remove</button></form>
<form method="post" action="{BASE}/admin/login-as" style="margin-top:6px"><input type="hidden" name="id" value="{x["id"]}"><button class="btn sm">Login as agent</button></form></td></tr>''' for x in agents)
        brows = ''.join(f'''<tr><td>{b["date"]}</td><td>{e(CARN.get(b["car"],b["car"]))}</td><td>{dict(SLOTS)[b["slot"]]}</td><td>{dict(TRIPS)[b["trip"]]}</td>
<td>{e(b["agent"])}{' <span class="muted">(by admin)</span>' if b["by_admin"] else ''}</td><td>{rs(b["amount"])}</td><td><form method="post" action="{BASE}/admin/booking-cancel" onsubmit="return confirm('Cancel booking?')"><input type="hidden" name="id" value="{b["id"]}"><button class="btn danger sm">Cancel</button></form></td></tr>''' for b in bks)
        body = f'''<span class="eyebrow">Admin</span><h1>Agent <span class="accent">admin</span></h1>{flash}
<form class="panel" method="post" action="{BASE}/admin/agent-add"><h2>Add agent</h2><div class="grid2">
<div><label>Name</label><input name="name" required maxlength="60"></div><div><label>Username</label><input name="username" required maxlength="40" pattern="[A-Za-z0-9._-]{{3,40}}" autocapitalize="none"></div>
<div><label>Password (3 letters, blank = generate)</label><input name="password" maxlength="3" pattern="[A-Za-z]{{3}}"></div></div>
<p class="muted">A unique 6-digit login code is generated automatically and shown once.</p><p><button class="btn">Add agent</button></p></form>
<div class="panel"><h2>Agents</h2>{('<div class="tablewrap"><table><tr><th>Name</th><th>Username</th><th>Bookings</th><th></th></tr>'+arows+'</table></div>') if agents else '<p class="muted">No agents yet.</p>'}</div>
<div class="panel"><h2>Bookings</h2><div class="tabs"><a class="btn sm {'' if show!='all' else 'ghost'}" href="?show=upcoming">Upcoming</a><a class="btn sm {'' if show=='all' else 'ghost'}" href="?show=all">All</a></div>
{('<div class="tablewrap"><table><tr><th>Date</th><th>Car</th><th>Slot</th><th>Trip</th><th>Agent</th><th>Amount</th><th></th></tr>'+brows+f'</table></div><p><b>Total: {rs(total)}</b> · {len(bks)} bookings</p>') if bks else '<p class="muted">No bookings.</p>'}</div>
<p class="muted">Public availability page (share with agents, not linked on the site): <a href="{BASE}/{SECRET["public_slug"]}">departrides.com{BASE}/{SECRET["public_slug"]}</a></p>'''
        right = f'<form method="post" action="{BASE}/admin/logout"><button class="btn ghost sm">Log out</button></form>'
        self.send(page('Admin', body, right))

    # ---------- POST ----------
    def do_POST(self):
        p = urlparse(self.path).path.rstrip('/')
        f = self.form(); ip = self.ip()
        if not self.same_origin(f):
            back = BASE + ('/admin' if p.startswith(BASE + '/admin') else '/')
            return self.redirect(back + '?' + urlencode({'err': 'Your session form expired. Please try again.'}))
        routes = {BASE + '/login': self.login, BASE + '/logout': lambda f, ip: self.stop_as(f, ip) if (self.session('agent') and self.as_admin) else self.redirect(BASE + '/', [self.end_session()]),
                  BASE + '/book': self.book, BASE + '/cancel': self.cancel, BASE + '/admin/login': self.admin_login,
                  BASE + '/admin/logout': lambda f, ip: self.redirect(BASE + '/admin', [self.end_session()]),
                  BASE + '/admin/agent-add': self.agent_add, BASE + '/admin/agent-del': self.agent_del,
                  BASE + '/admin/booking-cancel': self.admin_cancel, BASE + '/admin/login-as': self.login_as,
                  BASE + '/admin/stop-as': self.stop_as}
        if p not in routes: return self.send('Not found', 404)
        routes[p](f, ip)

    def login(self, f, ip):
        bad = BASE + '/?' + urlencode({'err': 'Login failed. Check your details and try again.'})
        slow = BASE + '/?' + urlencode({'err': 'Too many attempts. Please wait 15 minutes and try again.'})
        if limited('ip', ip): return self.redirect(slow)
        with db() as c:
            if f.get('mode') == 'code':
                code = f.get('code', '')
                if limited('code-global', 'all'): return self.redirect(slow)
                a = c.execute('SELECT * FROM agents WHERE code_hash=? AND active=1', (code_hash(code),)).fetchone() if code.isdigit() and len(code) == 6 else None
                if not a: fail('ip', ip); fail('code-global', 'all'); return self.redirect(bad)
            else:
                un = f.get('username', '').lower()
                if limited('user', un): return self.redirect(slow)
                a = c.execute('SELECT * FROM agents WHERE username=? AND active=1', (un,)).fetchone()
                if not a or not pw_check(f.get('password', '').lower(), a['pw_hash']):
                    if not a: pw_check('xxx', '00$00')
                    fail('ip', ip); fail('user', un); return self.redirect(bad)
        self.redirect(BASE + '/', [self.new_session('agent', a['id'], 7 * 86400)])

    def book(self, f, ip):
        a = self.session('agent')
        if not a: return self.redirect(BASE + '/')
        def err(m): return self.redirect(BASE + '/?' + urlencode({'err': m}))
        car, slot, trip, amt = f.get('car'), f.get('slot'), f.get('trip'), f.get('amount', '').replace(',', '')
        try: d = datetime.strptime(f.get('date', ''), '%Y-%m-%d').date()
        except ValueError: return err('Pick a valid date.')
        if car not in CARN or slot not in dict(SLOTS) or trip not in dict(TRIPS): return err('Invalid choice.')
        if d < today() or d > today() + timedelta(days=365): return err('Date must be from today up to one year ahead.')
        if not amt.isdigit() or not (0 < int(amt) <= 5_000_000): return err('Enter the booking amount in rupees (numbers only).')
        try:
            with db() as c:
                c.execute('INSERT INTO bookings(agent_id,car,date,slot,trip,amount,created_at,by_admin) VALUES(?,?,?,?,?,?,?,?)',
                          (a['id'], car, d.isoformat(), slot, trip, int(amt), now_pkt().isoformat(timespec='seconds'), self.as_admin))
        except sqlite3.IntegrityError:
            return err(f'{CARN[car]} is already booked on {fmt_day(d)} ({dict(SLOTS)[slot]}). Pick another car, date or slot.')
        self.redirect(BASE + '/?' + urlencode({'m': f'Booked: {CARN[car]}, {fmt_day(d)}, {dict(SLOTS)[slot]}, {dict(TRIPS)[trip]}, {rs(int(amt))}.', 'from': d.isoformat() if d >= today() + timedelta(days=DAYS) else ''}))

    def cancel(self, f, ip):
        a = self.session('agent')
        if not a: return self.redirect(BASE + '/')
        with db() as c:
            n = c.execute('UPDATE bookings SET cancelled_at=? WHERE id=? AND agent_id=? AND cancelled_at IS NULL',
                          (now_pkt().isoformat(timespec='seconds'), f.get('id'), a['id'])).rowcount
        self.redirect(BASE + '/?' + urlencode({'m': 'Booking cancelled.'} if n else {'err': 'Booking not found.'}))

    def admin_login(self, f, ip):
        if limited('admin-ip', ip): return self.redirect(BASE + '/admin?' + urlencode({'err': 'Too many attempts. Try again later.'}))
        with db() as c: ad = c.execute('SELECT * FROM admins WHERE username=?', (f.get('username', ''),)).fetchone()
        if not ad or not pw_check(f.get('password', ''), ad['pw_hash']):
            fail('admin-ip', ip); return self.redirect(BASE + '/admin?' + urlencode({'err': 'Login failed.'}))
        self.redirect(BASE + '/admin', [self.new_session('admin', ad['id'], 12 * 3600)])

    def agent_add(self, f, ip):
        if not self.session('admin'): return self.redirect(BASE + '/admin')
        name, un, pw = f.get('name', ''), f.get('username', '').lower(), f.get('password', '').lower()
        err = lambda m: self.redirect(BASE + '/admin?' + urlencode({'err': m}))
        if not name or not un or not all(ch in string.ascii_lowercase + string.digits + '._-' for ch in un) or len(un) < 3: return err('Enter a name and a username (3+ letters/numbers).')
        if pw and not (len(pw) == 3 and pw.isalpha() and pw.isascii()): return err('Password must be exactly 3 letters.')
        pw = pw or ''.join(secrets.choice(string.ascii_lowercase) for _ in range(3))
        with db() as c:
            if c.execute('SELECT 1 FROM agents WHERE username=?', (un,)).fetchone(): return err('That username is taken.')
            for _ in range(50):
                code = f'{secrets.randbelow(900000) + 100000}'
                if not c.execute('SELECT 1 FROM agents WHERE code_hash=?', (code_hash(code),)).fetchone(): break
            c.execute('INSERT INTO agents(name,username,pw_hash,code_hash,created_at) VALUES(?,?,?,?,?)',
                      (name, un, pw_hash(pw), code_hash(code), now_pkt().isoformat(timespec='seconds')))
        body = f'''<span class="eyebrow">Admin</span><h1>Agent <span class="accent">added</span></h1><div class="panel">
<p>Send these to <b>{e(name)}</b>. They are shown only once (stored hashed).</p>
<p>Login page: <code>https://departrides.com{BASE}/</code></p><p>Username: <code>{e(un)}</code> &nbsp; Password: <code>{e(pw)}</code></p>
<p>Or 6-digit code: <code>{code}</code></p></div><p><a class="btn" href="{BASE}/admin">Back to admin</a></p>'''
        self.send(page('Agent added', body))

    def login_as(self, f, ip):
        if not self.session('admin'): return self.redirect(BASE + '/admin')
        with db() as c:
            a = c.execute('SELECT id FROM agents WHERE id=? AND active=1', (f.get('id'),)).fetchone()
            if not a: return self.redirect(BASE + '/admin?' + urlencode({'err': 'Agent not found.'}))
            c.execute("UPDATE sessions SET as_agent=? WHERE token_hash=? AND role='admin'", (a['id'], tok_hash(self.cookie())))
        self.redirect(BASE + '/')

    def stop_as(self, f, ip):
        if self.session('admin'):
            with db() as c: c.execute("UPDATE sessions SET as_agent=NULL WHERE token_hash=? AND role='admin'", (tok_hash(self.cookie()),))
        self.redirect(BASE + '/admin')

    def agent_del(self, f, ip):
        if not self.session('admin'): return self.redirect(BASE + '/admin')
        with db() as c:
            c.execute("DELETE FROM sessions WHERE role='agent' AND ref_id=?", (f.get('id'),))
            c.execute("UPDATE sessions SET as_agent=NULL WHERE as_agent=?", (f.get('id'),))
            n = c.execute('DELETE FROM agents WHERE id=?', (f.get('id'),)).rowcount
        self.redirect(BASE + '/admin?' + urlencode({'m': 'Agent removed with their bookings.'} if n else {'err': 'Agent not found.'}))

    def admin_cancel(self, f, ip):
        if not self.session('admin'): return self.redirect(BASE + '/admin')
        with db() as c: c.execute('UPDATE bookings SET cancelled_at=? WHERE id=? AND cancelled_at IS NULL', (now_pkt().isoformat(timespec='seconds'), f.get('id')))
        self.redirect(BASE + '/admin?' + urlencode({'m': 'Booking cancelled.'}))

def set_admin(username, pw=None):
    pw = pw or secrets.token_urlsafe(12)
    with db() as c:
        c.execute('INSERT INTO admins(username,pw_hash) VALUES(?,?) ON CONFLICT(username) DO UPDATE SET pw_hash=excluded.pw_hash', (username, pw_hash(pw)))
    return pw

if __name__ == '__main__':
    os.makedirs(STATE, exist_ok=True); SECRET = load_secret(); init_db()
    if len(sys.argv) > 1 and sys.argv[1] == 'set-admin':
        print(set_admin(sys.argv[2])); sys.exit()
    if len(sys.argv) > 1 and sys.argv[1] == 'set-admin-stdin':  # password read from stdin, never printed
        pw = sys.stdin.readline().rstrip('\n')
        if len(pw) < 4: sys.exit('password too short')
        set_admin(sys.argv[2], pw); print('ok'); sys.exit()
    if len(sys.argv) > 1 and sys.argv[1] == 'public-slug':
        print(SECRET['public_slug']); sys.exit()
    ThreadingHTTPServer(('127.0.0.1', PORT), H).serve_forever()
