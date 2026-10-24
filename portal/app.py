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
DEFAULT_PAYOUTS = [('prado', 1000, 2000), ('land-cruiser-v8', 2000, 2000), ('haval-h6', 1000, 1500),
                   ('jetour-t2', 2000, 2500), ('corolla-xli', 0, 0)]

def payouts(c): return {r['car']: (r['commission'], r['driving']) for r in c.execute('SELECT * FROM payouts')}

def period(q):
    t = today(); p = q.get('period', ['month'])[0]
    first = t.replace(day=1)
    if p == 'last':
        hi = first - timedelta(days=1); return p, hi.replace(day=1), hi, 'Last month'
    if p == 'all': return p, None, None, 'All time'
    if p == 'custom':
        try:
            lo = datetime.strptime(q.get('from_d', [''])[0], '%Y-%m-%d').date(); hi = datetime.strptime(q.get('to_d', [''])[0], '%Y-%m-%d').date()
            if lo <= hi: return p, lo, hi, f'{fmt_day(lo)} – {fmt_day(hi)}'
        except ValueError: pass
    return 'month', first, (first + timedelta(days=32)).replace(day=1) - timedelta(days=1), 'This month'

def period_sql(lo, hi):
    return ((' AND b.date>=? AND b.date<=?', (lo.isoformat(), hi.isoformat())) if lo else ('', ()))

def totals(bks, po):
    t = {'n': 0, 'rev': 0, 'com': 0, 'drv': 0, 'fuel': 0}
    for b in bks:
        if b['cancelled_at'] or (b['status'] if 'status' in b.keys() else 'finalized') != 'finalized':
            continue
        cm, dv = po.get(b['car'], (0, 0)) if b['agent_id'] else (0, 0)
        t['n'] += 1; t['rev'] += b['amount']; t['com'] += cm; t['drv'] += (dv if b['driver'] else 0); t['fuel'] += b['fuel']
    t['net'] = t['rev'] - t['com'] - t['drv'] - t['fuel']; return t

def stat_cards(t, net=False):
    items = [('Bookings', str(t['n'])), ('Revenue', rs(t['rev'])), ('Commission', rs(t['com'])), ('Driving', rs(t['drv'])), ('Fuel cost', rs(t['fuel']))]
    if net: items.append(('Net', rs(t['net'])))
    return '<div class="stats">' + ''.join(f'<div class="stat"><span>{k}</span><b>{v}</b></div>' for k, v in items) + '</div>'

def period_bar(pk, q, extra=''):
    tabs = ''.join(f'<a class="btn sm {"" if pk == k else "ghost"}" href="?period={k}{extra}">{v}</a>' for k, v in (('month', 'This month'), ('last', 'Last month'), ('all', 'All time')))
    return (f'<div class="tabs">{tabs}</div><form method="get" class="tabs" style="align-items:end"><input type="hidden" name="period" value="custom">'
            f'<div><label>From</label><input type="date" name="from_d" required value="{e(q.get("from_d", [""])[0])}"></div>'
            f'<div><label>To</label><input type="date" name="to_d" required value="{e(q.get("to_d", [""])[0])}"></div><button class="btn sm {"" if pk == "custom" else "ghost"}">Custom range</button></form>')

def phone_norm(p):
    d = ''.join(ch for ch in (p or '') if ch.isdigit())
    if d.startswith('92') and len(d) == 12: d = '0' + d[2:]
    return d

def status_badge(st):
    lab = {'requested': ('Requested', 'badge-req'), 'finalized': ('Finalized', 'badge-ok'),
           'rejected': ('Rejected', 'badge-no'), 'cancelled': ('Cancelled', 'badge-no')}.get(st, (st, 'badge-no'))
    return f'<span class="chip {lab[1]}">{lab[0]}</span>'

def edit_cell(b, action):
    return (f'<form method="post" action="{action}" class="tabs" style="margin:0"><input type="hidden" name="id" value="{b["id"]}">'
            f'<input name="fuel" inputmode="numeric" pattern="[0-9]{{0,7}}" value="{b["fuel"]}" style="width:90px" aria-label="Fuel cost (Rs)">'
            f'<select name="driver" aria-label="With driver"><option value="1"{" selected" if b["driver"] else ""}>Driver</option><option value="0"{"" if b["driver"] else " selected"}>No driver</option></select>'
            f'<button class="btn sm ghost">Save</button></form>')

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
        c.execute('CREATE TABLE IF NOT EXISTS payouts(car TEXT PRIMARY KEY, commission INTEGER NOT NULL DEFAULT 0, driving INTEGER NOT NULL DEFAULT 0)')
        c.executemany('INSERT OR IGNORE INTO payouts(car,commission,driving) VALUES(?,?,?)', DEFAULT_PAYOUTS)
        c.execute('''CREATE TABLE IF NOT EXISTS customers(
            id INTEGER PRIMARY KEY, name TEXT NOT NULL, phone TEXT UNIQUE NOT NULL,
            email TEXT, pw_hash TEXT NOT NULL, created_at TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1)''')
        for t, col in (('sessions', 'as_agent INTEGER'), ('bookings', 'by_admin INTEGER'),
                       ('bookings', 'fuel INTEGER NOT NULL DEFAULT 0'), ('bookings', 'driver INTEGER NOT NULL DEFAULT 1'),
                       ('bookings', "status TEXT NOT NULL DEFAULT 'finalized'"),
                       ('bookings', "notes TEXT NOT NULL DEFAULT ''"),
                       ('bookings', 'customer_id INTEGER')):
            if col.split()[0] not in [r[1] for r in c.execute(f'PRAGMA table_info({t})')]:
                c.execute(f'ALTER TABLE {t} ADD COLUMN {col}')
        # Rebuild bookings once so agent_id can be NULL (customer requests).
        cols = {r[1]: r for r in c.execute('PRAGMA table_info(bookings)')}
        if cols.get('agent_id') and cols['agent_id'][3]:  # notnull=1
            c.executescript('''
            CREATE TABLE bookings_mig(
              id INTEGER PRIMARY KEY, agent_id INTEGER REFERENCES agents(id) ON DELETE CASCADE,
              customer_id INTEGER REFERENCES customers(id) ON DELETE CASCADE,
              car TEXT NOT NULL, date TEXT NOT NULL, slot TEXT NOT NULL, trip TEXT NOT NULL,
              amount INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, cancelled_at TEXT,
              by_admin INTEGER, fuel INTEGER NOT NULL DEFAULT 0, driver INTEGER NOT NULL DEFAULT 1,
              status TEXT NOT NULL DEFAULT 'finalized', notes TEXT NOT NULL DEFAULT '');
            INSERT INTO bookings_mig(id,agent_id,customer_id,car,date,slot,trip,amount,created_at,cancelled_at,by_admin,fuel,driver,status,notes)
              SELECT id,agent_id,customer_id,car,date,slot,trip,amount,created_at,cancelled_at,by_admin,fuel,driver,
                     COALESCE(NULLIF(status,''),'finalized'), COALESCE(notes,'') FROM bookings;
            DROP TABLE bookings; ALTER TABLE bookings_mig RENAME TO bookings;
            ''')
        c.execute("UPDATE bookings SET status='finalized' WHERE status IS NULL OR status=''")
        c.execute('DROP INDEX IF EXISTS one_booking')
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS one_finalized ON bookings(car, date, slot) WHERE status='finalized' AND cancelled_at IS NULL")
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS one_pending ON bookings(car, date, slot) WHERE status='requested' AND cancelled_at IS NULL")

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
def slot_past(d, slot):
    t = today()
    return d < t or (d == t and slot == 'morning' and now_pkt().hour >= 12)

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
.free{background:#1c2b10;color:var(--lime);text-decoration:none}a.free:hover{outline:1px solid var(--lime)}.past{background:#1a1d1b;color:#5d655f}.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin:10px 0}.stat{background:#151815;border:1px solid #263026;border-radius:10px;padding:10px}.stat span{display:block;font-size:12px;color:#8a948c}.stat b{font-size:18px}.day.isp{opacity:.55}.booked{background:#2a1513;color:#ff9b91}.mine{background:#2a2412;color:var(--gold)}.badge-req{background:#2a2412;color:var(--gold)}.badge-ok{background:#1c2b10;color:var(--lime)}.badge-no{background:#1a1d1b;color:#8a948c}
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

def calendar(start, viewer_agent=None, link_base=None, viewer_customer=None):
    end = start + timedelta(days=DAYS - 1)
    with db() as c:
        rows = c.execute("SELECT car,date,slot,agent_id,customer_id FROM bookings WHERE cancelled_at IS NULL AND status='finalized' AND date BETWEEN ? AND ?",
                         (start.isoformat(), end.isoformat())).fetchall()
    taken = {(r['car'], r['date'], r['slot']): (r['agent_id'], r['customer_id']) for r in rows}
    show_mine = viewer_agent or viewer_customer
    out = ['<div class="legend"><span class="chip free">Available</span><span class="chip booked">Booked</span>' +
           ('<span class="chip mine">Your booking</span>' if show_mine else '') + ('' if show_mine else '<span class="chip past">Past</span>') + '</div><div class="cal">']
    for i in range(DAYS):
        d = start + timedelta(days=i); ds = d.isoformat()
        dp = d < today()
        out.append(f'<div class="day{" isp" if dp else ""}"><h3>{fmt_day(d)}{" · Past" if dp else ""}</h3>')
        for cid, cname in CARS:
            chips = []
            for sid, sname in SLOTS:
                own = taken.get((cid, ds, sid))
                a = None if own is None else own[0]
                is_mine = bool(own and ((viewer_agent and a == viewer_agent) or (viewer_customer and own[1] == viewer_customer)))
                cls, txt = ('free', sname) if own is None else (('mine', sname) if is_mine else ('booked', sname))
                if cls == 'free' and slot_past(d, sid) and not show_mine:
                    chips.append(f'<span class="chip past" title="Past">{sname}</span>'); continue
                if cls == 'free' and show_mine:
                    chips.append(f'<a class="chip free" href="{BASE}/?{urlencode({"car": cid, "date": ds, "slot": sid})}#book" title="Book {e(cname)} {e(sname)}">{txt}</a>'); continue
                chips.append(f'<span class="chip {cls}" title="{e(cname)} {e(sname)}: {"available" if own is None else "booked"}">{txt}</span>')
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
                return c.execute('SELECT * FROM agents WHERE id=? AND active=1', (r['ref_id'],)).fetchone()
            if role == 'customer':
                return c.execute('SELECT * FROM customers WHERE id=? AND active=1', (r['ref_id'],)).fetchone()
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
        if p == BASE + '/signup': return self.signup_page(flash)
        if p == BASE:
            if self.session('agent'): return self.agent_home(q, flash)  # includes admin Login-as
            if self.session('admin'): return self.redirect(BASE + '/admin')
            if self.session('customer'): return self.customer_home(q, flash)
            return self.login_page(flash)
        if p == BASE + '/admin':
            if self.session('admin'): return self.admin_home(q, flash)
            return self.redirect(BASE + '/?' + urlencode({'m': 'Log in with your admin account.'}))
        if p == BASE + '/' + SECRET['public_slug']:
            start = parse_start(q)
            body = (f'<span class="eyebrow">Agent availability</span><h1>Car <span class="accent">availability</span></h1>'
                    f'<p class="muted">Morning and evening slots for the next days. Updated live. To book, log in to the agent portal or call/WhatsApp 0339 9999038.</p>'
                    + calendar(start, None, BASE + '/' + SECRET['public_slug']))
            return self.send(page('Availability', body))
        if p == '/healthz': return self.send('ok')
        self.send(page('Not found', '<h1>Not found</h1>'), 404)

    def login_page(self, flash):
        body = f'''<span class="eyebrow">Depart Rides</span><h1>Welcome <span class="accent">back</span></h1>{flash}
<p class="muted">One login for customers, agents and admin. New here? <a href="{BASE}/signup">Create a customer account</a>.</p>
<div class="grid2">
<form class="panel" method="post" action="{BASE}/login"><input type="hidden" name="mode" value="pw"><h2>Username or phone</h2>
<label>Username / phone</label><input name="username" autocomplete="username" required maxlength="40" autocapitalize="none" placeholder="agent name or 03XX…">
<label>Password</label><input name="password" type="password" autocomplete="current-password" required maxlength="72">
<p><button class="btn">Log in</button></p></form>
<form class="panel" method="post" action="{BASE}/login"><input type="hidden" name="mode" value="code"><h2>Agent code</h2>
<label>6-digit agent code</label><input name="code" inputmode="numeric" pattern="[0-9]{{6}}" maxlength="6" required autocomplete="one-time-code">
<p><button class="btn">Log in with code</button></p>
<p class="muted" style="font-size:13px;margin-top:8px">Agents can also use username + 3-letter password above.</p></form>
</div>'''
        return self.send(page('Login', body))

    def signup_page(self, flash):
        if self.session('customer') or self.session('agent') or self.session('admin'):
            return self.redirect(BASE + '/')
        body = f'''<span class="eyebrow">Customers</span><h1>Create your <span class="accent">account</span></h1>{flash}
<form class="panel" method="post" action="{BASE}/signup" style="max-width:520px"><div class="grid2">
<div><label>Full name</label><input name="name" required maxlength="80" autocomplete="name"></div>
<div><label>Phone (WhatsApp)</label><input name="phone" required maxlength="20" inputmode="tel" placeholder="03XXXXXXXXX" autocomplete="tel"></div>
<div><label>Password (8+ characters)</label><input name="password" type="password" required minlength="8" maxlength="72" autocomplete="new-password"></div>
<div><label>Email (optional)</label><input name="email" type="email" maxlength="120" autocomplete="email"></div>
</div><p><button class="btn">Sign up</button></p>
<p class="muted">Already have an account? <a href="{BASE}/">Log in</a>.</p></form>'''
        return self.send(page('Sign up', body))

    def agent_home(self, q, flash):
        a = self.session('agent')
        if not a: return self.redirect(BASE + '/')
        start = parse_start(q); t = today()
        with db() as c:
            pk, lo, hi, plabel = period(q); ps_sql, ps_args = period_sql(lo, hi)
            mine = c.execute("SELECT b.* FROM bookings b WHERE b.agent_id=? AND b.cancelled_at IS NULL AND b.status='finalized'" + ps_sql + ' ORDER BY b.date DESC,b.slot', (a['id'],) + ps_args).fetchall()
            tot = totals(mine, payouts(c))
        pc, pd, ps = q.get('car', [''])[0], q.get('date', [''])[0], q.get('slot', [''])[0]
        car_opts = ''.join(f'<option value="{k}"{" selected" if k == pc else ""}>{e(v)}</option>' for k, v in CARS)
        try: dval = datetime.strptime(pd, '%Y-%m-%d').date().isoformat()
        except ValueError: dval = t.isoformat()
        def _crow(b):
            st = 'cancelled' if b['cancelled_at'] else b['status']
            cancel = ''
            if not b['cancelled_at'] and b['status'] == 'requested':
                cancel = (f'<form method="post" action="{BASE}/cancel" onsubmit="return confirm(&quot;Cancel this request?&quot;)">'
                          f'<input type="hidden" name="id" value="{b["id"]}"><button class="btn danger sm">Cancel</button></form>')
            return (f'<tr><td>{fmt_day(datetime.strptime(b["date"],"%Y-%m-%d"))}</td><td>{e(CARN.get(b["car"],b["car"]))}</td>'
                    f'<td>{dict(SLOTS)[b["slot"]]}</td><td>{dict(TRIPS)[b["trip"]]}</td><td>{status_badge(st)}</td>'
                    f'<td>{e(b["notes"]) or "—"}</td><td>{cancel}</td></tr>')
        rows = ''.join(_crow(b) for b in mine)
        body = f'''<span class="eyebrow">Agent portal</span><h1>Hi, <span class="accent">{e(a["name"])}</span></h1>{flash}
<form class="panel" id="book" method="post" action="{BASE}/book"><h2>New booking</h2><div class="grid2">
<div><label>Car</label><select name="car" required>{car_opts}</select></div>
<div><label>Date</label><input type="date" name="date" required max="{t + timedelta(days=365)}" value="{dval}"></div>
<div><label>Slot</label><select name="slot">{''.join(f'<option value="{k}"{" selected" if k == ps else ""}>{v}</option>' for k,v in SLOTS)}</select></div>
<div><label>Trip</label><select name="trip">{''.join(f'<option value="{k}">{v}</option>' for k,v in TRIPS)}</select></div>
<div><label>Booking amount (Rs)</label><input name="amount" inputmode="numeric" pattern="[0-9]{{1,7}}" required placeholder="e.g. 25000"></div>
<div><label>Fuel cost (Rs, optional)</label><input name="fuel" inputmode="numeric" pattern="[0-9]{{0,7}}" value="0"></div>
<div><label>With driver</label><select name="driver"><option value="1" selected>Yes</option><option value="0">No</option></select></div>
</div><p><button class="btn">Book this slot</button></p></form>
<div class="panel"><h2>Your totals · {plabel}</h2>{period_bar(pk, q)}{stat_cards(tot)}
<h2>Your bookings · {plabel}</h2>{('<div class="tablewrap"><table><tr><th>Date</th><th>Car</th><th>Slot</th><th>Trip</th><th>Amount</th><th>Fuel (Rs) / Driver</th><th></th></tr>' + rows + '</table></div>') if mine else '<p class="muted">No bookings in this period.</p>'}</div>
<h2>Availability</h2>{calendar(start, a["id"], BASE)}'''
        right = f'<form method="post" action="{BASE}/logout"><button class="btn ghost sm">Log out</button></form>'
        if self.as_admin:
            right = f'<form method="post" action="{BASE}/admin/stop-as"><button class="btn sm">Back to admin</button></form>'
            body = f'<div class="msg" style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap"><span>Viewing as <b>{e(a["name"])}</b> (admin). Bookings you make are recorded as made by admin on their behalf.</span><form method="post" action="{BASE}/admin/stop-as"><button class="btn sm">Back to admin</button></form></div>' + body
        self.send(page('Agent portal', body, right))

    def admin_home(self, q, flash):
        ad = self.session('admin')
        if not ad: return self.redirect(BASE + '/')
        with db() as c:
            agents = c.execute("SELECT a.*, (SELECT COUNT(*) FROM bookings b WHERE b.agent_id=a.id AND b.cancelled_at IS NULL AND b.status='finalized') n FROM agents a WHERE active=1 ORDER BY name").fetchall()
            pk, lo, hi, plabel = period(q); ps_sql, ps_args = period_sql(lo, hi)
            bks = c.execute('''SELECT b.*, COALESCE(a.name, cu.name) agent, CASE WHEN b.customer_id IS NOT NULL THEN 1 ELSE 0 END is_cust
                FROM bookings b LEFT JOIN agents a ON a.id=b.agent_id LEFT JOIN customers cu ON cu.id=b.customer_id
                WHERE b.cancelled_at IS NULL AND b.status='finalized''' + ps_sql + ' ORDER BY b.date, b.slot, b.car', ps_args).fetchall()
            pending = c.execute('''SELECT b.*, cu.name cname, cu.phone cphone FROM bookings b JOIN customers cu ON cu.id=b.customer_id
                WHERE b.status='requested' AND b.cancelled_at IS NULL ORDER BY b.date, b.slot, b.car''').fetchall()
            po = payouts(c)
        total = sum(b['amount'] for b in bks); tot = totals(bks, po)
        per = {}
        for b in bks:
            if b['agent_id']: per.setdefault(b['agent'], []).append(b)
        prow = ''.join(f'<tr><td>{e(n)}</td><td>{x["n"]}</td><td>{rs(x["rev"])}</td><td>{rs(x["com"])}</td><td>{rs(x["drv"])}</td><td>{rs(x["fuel"])}</td><td>{rs(x["net"])}</td></tr>'
                       for n, x in sorted((n, totals(v, po)) for n, v in per.items()))
        porow = ''.join(f'<tr><td>{e(n)}</td><td><input name="c_{k}" inputmode="numeric" pattern="[0-9]{{1,7}}" value="{po.get(k,(0,0))[0]}" style="width:100px"></td><td><input name="d_{k}" inputmode="numeric" pattern="[0-9]{{1,7}}" value="{po.get(k,(0,0))[1]}" style="width:100px"></td></tr>' for k, n in CARS)
        arows = ''.join(f'''<tr><td>{e(x["name"])}</td><td>{e(x["username"])}</td><td>{x["n"]}</td><td><form method="post" action="{BASE}/admin/agent-del" onsubmit="return confirm('Remove agent {e(x["name"])} and all their bookings?')">
<input type="hidden" name="id" value="{x["id"]}"><button class="btn danger sm">Remove</button></form>
<form method="post" action="{BASE}/admin/login-as" style="margin-top:6px"><input type="hidden" name="id" value="{x["id"]}"><button class="btn sm">Login as agent</button></form></td></tr>''' for x in agents)
        def _who(b):
            tag = ' <span class="muted">(customer)</span>' if b['is_cust'] else ''
            tag += ' <span class="muted">(by admin)</span>' if b['by_admin'] else ''
            return e(b['agent'] or '—') + tag
        brows = ''.join(f'''<tr><td>{b["date"]}</td><td>{e(CARN.get(b["car"],b["car"]))}</td><td>{dict(SLOTS)[b["slot"]]}</td><td>{dict(TRIPS)[b["trip"]]}</td>
<td>{_who(b)}</td><td>{rs(b["amount"])}</td><td>{edit_cell(b, BASE + "/admin/booking-edit")}</td><td><form method="post" action="{BASE}/admin/booking-cancel" onsubmit="return confirm('Cancel booking?')"><input type="hidden" name="id" value="{b["id"]}"><button class="btn danger sm">Cancel</button></form></td></tr>''' for b in bks)
        prows = ''.join(f'''<tr><td>{b["date"]}</td><td>{e(CARN.get(b["car"],b["car"]))}</td><td>{dict(SLOTS)[b["slot"]]}</td><td>{dict(TRIPS)[b["trip"]]}</td>
<td>{e(b["cname"])}<br><span class="muted">{e(b["cphone"])}</span></td><td>{e(b["notes"]) or "—"}</td>
<td><form method="post" action="{BASE}/admin/finalize" class="tabs" style="margin:0"><input type="hidden" name="id" value="{b["id"]}">
<input name="amount" inputmode="numeric" pattern="[0-9]{{1,7}}" placeholder="Amount Rs" style="width:110px" required>
<button class="btn sm">Finalize</button></form>
<form method="post" action="{BASE}/admin/reject" style="margin-top:6px" onsubmit="return confirm('Reject this request?')"><input type="hidden" name="id" value="{b["id"]}"><button class="btn danger sm">Reject</button></form></td></tr>''' for b in pending)
        body = f'''<span class="eyebrow">Admin</span><h1>Depart <span class="accent">admin</span></h1>{flash}
<div class="panel"><h2>Customer requests</h2>
{('<div class="tablewrap"><table><tr><th>Date</th><th>Car</th><th>Slot</th><th>Trip</th><th>Customer</th><th>Notes</th><th></th></tr>'+prows+'</table></div>') if pending else '<p class="muted">No pending requests.</p>'}</div>
<form class="panel" method="post" action="{BASE}/admin/agent-add"><h2>Add agent</h2><div class="grid2">
<div><label>Name</label><input name="name" required maxlength="60"></div><div><label>Username</label><input name="username" required maxlength="40" pattern="[A-Za-z0-9._-]{{3,40}}" autocapitalize="none"></div>
<div><label>Password (3 letters, blank = generate)</label><input name="password" maxlength="3" pattern="[A-Za-z]{{3}}"></div></div>
<p class="muted">A unique 6-digit login code is generated automatically and shown once.</p><p><button class="btn">Add agent</button></p></form>
<div class="panel"><h2>Agents</h2>{('<div class="tablewrap"><table><tr><th>Name</th><th>Username</th><th>Bookings</th><th></th></tr>'+arows+'</table></div>') if agents else '<p class="muted">No agents yet.</p>'}</div>
<div class="panel"><h2>Totals · {plabel}</h2>{period_bar(pk, q)}{stat_cards(tot, True)}
<p class="muted">Net = revenue − commission − driving − fuel. Driving counts only bookings with a driver. Cancelled bookings are excluded.</p>
{('<h2>Per agent</h2><div class="tablewrap"><table><tr><th>Agent</th><th>Bookings</th><th>Revenue</th><th>Commission</th><th>Driving</th><th>Fuel</th><th>Net</th></tr>' + prow + '</table></div>') if per else ''}</div>
<div class="panel"><h2>Bookings · {plabel}</h2>
{('<div class="tablewrap"><table><tr><th>Date</th><th>Car</th><th>Slot</th><th>Trip</th><th>Agent</th><th>Amount</th><th>Fuel (Rs) / Driver</th><th></th></tr>'+brows+f'</table></div><p><b>Total: {rs(total)}</b> · {len(bks)} bookings</p>') if bks else '<p class="muted">No bookings.</p>'}</div>
<form class="panel" method="post" action="{BASE}/admin/payouts"><h2>Per-car payouts (Rs per booking)</h2><div class="tablewrap"><table><tr><th>Car</th><th>Commission</th><th>Driving</th></tr>{porow}</table></div><p><button class="btn sm">Save payouts</button></p></form>
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
        routes = {BASE + '/login': self.login, BASE + '/signup': self.signup,
                  BASE + '/logout': lambda f, ip: self.stop_as(f, ip) if (self.session('agent') and self.as_admin) else self.redirect(BASE + '/', [self.end_session()]),
                  BASE + '/book': self.book, BASE + '/request': self.cust_request, BASE + '/cancel': self.cancel,
                  BASE + '/admin/login': self.admin_login,
                  BASE + '/admin/logout': lambda f, ip: self.redirect(BASE + '/', [self.end_session()]),
                  BASE + '/admin/agent-add': self.agent_add, BASE + '/admin/agent-del': self.agent_del,
                  BASE + '/admin/booking-cancel': self.admin_cancel, BASE + '/admin/login-as': self.login_as,
                  BASE + '/admin/stop-as': self.stop_as, BASE + '/edit': self.edit, BASE + '/admin/booking-edit': self.admin_edit,
                  BASE + '/admin/payouts': self.set_payouts, BASE + '/admin/finalize': self.finalize,
                  BASE + '/admin/reject': self.reject_req}
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
                return self.redirect(BASE + '/', [self.new_session('agent', a['id'], 7 * 86400)])
            un_raw = f.get('username', '').strip(); pw = f.get('password', '')
            un = un_raw.lower(); ph = phone_norm(un_raw)
            if limited('user', un or ph): return self.redirect(slow)
            ad = c.execute('SELECT * FROM admins WHERE username=?', (un_raw,)).fetchone()
            if ad and pw_check(pw, ad['pw_hash']):
                return self.redirect(BASE + '/admin', [self.new_session('admin', ad['id'], 12 * 3600)])
            a = c.execute('SELECT * FROM agents WHERE username=? AND active=1', (un,)).fetchone()
            if a and pw_check(pw.lower(), a['pw_hash']):
                return self.redirect(BASE + '/', [self.new_session('agent', a['id'], 7 * 86400)])
            cu = c.execute('SELECT * FROM customers WHERE phone=? AND active=1', (ph,)).fetchone() if ph else None
            if cu and pw_check(pw, cu['pw_hash']):
                return self.redirect(BASE + '/', [self.new_session('customer', cu['id'], 30 * 86400)])
            pw_check('xxx', '00$00')
            fail('ip', ip); fail('user', un or ph); return self.redirect(bad)

    def book(self, f, ip):
        a = self.session('agent')
        if not a: return self.redirect(BASE + '/')
        def err(m): return self.redirect(BASE + '/?' + urlencode({'err': m}))
        car, slot, trip, amt = f.get('car'), f.get('slot'), f.get('trip'), f.get('amount', '').replace(',', '')
        try: d = datetime.strptime(f.get('date', ''), '%Y-%m-%d').date()
        except ValueError: return err('Pick a valid date.')
        if car not in CARN or slot not in dict(SLOTS) or trip not in dict(TRIPS): return err('Invalid choice.')
        if not (today() - timedelta(days=3650) <= d <= today() + timedelta(days=365)): return err('Pick a date within the last 10 years or up to one year ahead.')
        fuel = f.get('fuel', '').replace(',', '').strip() or '0'; drv = 0 if f.get('driver') == '0' else 1
        if not fuel.isdigit() or int(fuel) > 5_000_000: return err('Enter the fuel cost in rupees (numbers only), or leave it as 0.')
        if not amt.isdigit() or not (0 < int(amt) <= 5_000_000): return err('Enter the booking amount in rupees (numbers only).')
        try:
            with db() as c:
                c.execute("INSERT INTO bookings(agent_id,car,date,slot,trip,amount,created_at,by_admin,fuel,driver,status) VALUES(?,?,?,?,?,?,?,?,?,?, 'finalized')",
                          (a['id'], car, d.isoformat(), slot, trip, int(amt), now_pkt().isoformat(timespec='seconds'), self.as_admin, int(fuel), drv))
        except sqlite3.IntegrityError:
            return err(f'{CARN[car]} is already booked on {fmt_day(d)} ({dict(SLOTS)[slot]}). Pick another car, date or slot.')
        self.redirect(BASE + '/?' + urlencode({'m': f'Booked: {CARN[car]}, {fmt_day(d)}, {dict(SLOTS)[slot]}, {dict(TRIPS)[trip]}, {rs(int(amt))}.', 'from': d.isoformat() if d >= today() + timedelta(days=DAYS) else ''}))

    def _edit(self, f, back, agent_id=None):
        fuel = f.get('fuel', '').replace(',', '').strip() or '0'; drv = 0 if f.get('driver') == '0' else 1
        if not fuel.isdigit() or int(fuel) > 5_000_000: return self.redirect(back + '?' + urlencode({'err': 'Fuel cost must be a number in rupees.'}))
        with db() as c:
            sql, args = 'UPDATE bookings SET fuel=?, driver=? WHERE id=? AND cancelled_at IS NULL', [int(fuel), drv, f.get('id')]
            if agent_id is not None: sql += ' AND agent_id=?'; args.append(agent_id)
            n = c.execute(sql, args).rowcount
        self.redirect(back + '?' + urlencode({'m': 'Booking updated.'} if n else {'err': 'Booking not found.'}))

    def edit(self, f, ip):
        a = self.session('agent')
        if not a: return self.redirect(BASE + '/')
        self._edit(f, BASE + '/', a['id'])

    def admin_edit(self, f, ip):
        if not self.session('admin'): return self.redirect(BASE + '/admin')
        self._edit(f, BASE + '/admin')

    def set_payouts(self, f, ip):
        if not self.session('admin'): return self.redirect(BASE + '/admin')
        vals = []
        for k, n in CARS:
            cm, dv = f.get('c_' + k, '').replace(',', ''), f.get('d_' + k, '').replace(',', '')
            if not (cm.isdigit() and dv.isdigit() and int(cm) <= 1_000_000 and int(dv) <= 1_000_000):
                return self.redirect(BASE + '/admin?' + urlencode({'err': f'Payouts for {n} must be numbers in rupees.'}))
            vals.append((k, int(cm), int(dv)))
        with db() as c:
            c.executemany('INSERT INTO payouts(car,commission,driving) VALUES(?,?,?) ON CONFLICT(car) DO UPDATE SET commission=excluded.commission, driving=excluded.driving', vals)
        self.redirect(BASE + '/admin?' + urlencode({'m': 'Payouts saved.'}))

    def cancel(self, f, ip):
        a = self.session('agent'); cu = self.session('customer')
        if not a and not cu: return self.redirect(BASE + '/')
        with db() as c:
            if a:
                n = c.execute("UPDATE bookings SET cancelled_at=?, status=CASE WHEN status='requested' THEN 'cancelled' ELSE status END WHERE id=? AND agent_id=? AND cancelled_at IS NULL",
                              (now_pkt().isoformat(timespec='seconds'), f.get('id'), a['id'])).rowcount
            else:
                n = c.execute("UPDATE bookings SET cancelled_at=?, status='cancelled' WHERE id=? AND customer_id=? AND status='requested' AND cancelled_at IS NULL",
                              (now_pkt().isoformat(timespec='seconds'), f.get('id'), cu['id'])).rowcount
        self.redirect(BASE + '/?' + urlencode({'m': 'Cancelled.'} if n else {'err': 'Booking not found.'}))

    def admin_login(self, f, ip):
        f = dict(f); f['mode'] = 'pw'
        self.login(f, ip)

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

    def signup(self, f, ip):
        def err(m): return self.redirect(BASE + '/signup?' + urlencode({'err': m}))
        name, phone, pw, email = f.get('name', ''), phone_norm(f.get('phone', '')), f.get('password', ''), f.get('email', '').strip()
        if not (2 <= len(name) <= 80): return err('Enter your name.')
        if not (phone.startswith('03') and len(phone) == 11): return err('Enter a valid Pakistani mobile number (03XXXXXXXXX).')
        if not (8 <= len(pw) <= 72): return err('Password must be at least 8 characters.')
        if email and ('@' not in email or len(email) > 120): return err('Enter a valid email, or leave it blank.')
        try:
            with db() as c:
                c.execute('INSERT INTO customers(name,phone,email,pw_hash,created_at) VALUES(?,?,?,?,?)',
                          (name, phone, email or None, pw_hash(pw), now_pkt().isoformat(timespec='seconds')))
                cid = c.execute('SELECT id FROM customers WHERE phone=?', (phone,)).fetchone()['id']
        except sqlite3.IntegrityError:
            return err('An account with that phone number already exists. Please log in.')
        self.redirect(BASE + '/?' + urlencode({'m': 'Account created. You can request a booking below.'}),
                      [self.new_session('customer', cid, 30 * 86400)])

    def customer_home(self, q, flash):
        cu = self.session('customer')
        if not cu: return self.redirect(BASE + '/')
        start = parse_start(q); t = today()
        with db() as c:
            mine = c.execute('SELECT * FROM bookings WHERE customer_id=? ORDER BY date DESC, slot', (cu['id'],)).fetchall()
        pc, pd, ps = q.get('car', [''])[0], q.get('date', [''])[0], q.get('slot', [''])[0]
        car_opts = ''.join(f'<option value="{k}"{" selected" if k == pc else ""}>{e(v)}</option>' for k, v in CARS)
        try: dval = datetime.strptime(pd, '%Y-%m-%d').date().isoformat()
        except ValueError: dval = t.isoformat()
        rows = ''.join(f'''<tr><td>{fmt_day(datetime.strptime(b["date"],"%Y-%m-%d"))}</td><td>{e(CARN.get(b["car"],b["car"]))}</td>
<td>{dict(SLOTS)[b["slot"]]}</td><td>{dict(TRIPS)[b["trip"]]}</td><td>{status_badge(b["status"] if not b["cancelled_at"] else "cancelled")}</td>
<td>{e(b["notes"]) or "—"}</td>
<td>{"" if b["cancelled_at"] or b["status"] != "requested" else f'<form method="post" action="{BASE}/cancel" onsubmit="return confirm(\'Cancel this request?\')"><input type="hidden" name="id" value="{b["id"]}"><button class="btn danger sm">Cancel</button></form>'}</td></tr>''' for b in mine)
        body = f'''<span class="eyebrow">My bookings</span><h1>Hi, <span class="accent">{e(cu["name"])}</span></h1>{flash}
<form class="panel" id="book" method="post" action="{BASE}/request"><h2>Request a booking</h2>
<p class="muted">Your request is reviewed by Depart Rides. Once finalized, the slot is confirmed and you will see it here.</p>
<div class="grid2">
<div><label>Car</label><select name="car" required>{car_opts}</select></div>
<div><label>Date</label><input type="date" name="date" required min="{t}" max="{t + timedelta(days=365)}" value="{dval}"></div>
<div><label>Slot</label><select name="slot">{''.join(f'<option value="{k}"{" selected" if k == ps else ""}>{v}</option>' for k,v in SLOTS)}</select></div>
<div><label>Trip</label><select name="trip">{''.join(f'<option value="{k}">{v}</option>' for k,v in TRIPS)}</select></div>
<div style="grid-column:1/-1"><label>Notes (optional)</label><input name="notes" maxlength="200" placeholder="Pickup area, occasion, etc."></div>
</div><p><button class="btn">Submit request</button></p></form>
<div class="panel"><h2>Your bookings</h2>
{('<div class="tablewrap"><table><tr><th>Date</th><th>Car</th><th>Slot</th><th>Trip</th><th>Status</th><th>Notes</th><th></th></tr>'+rows+'</table></div>') if mine else '<p class="muted">No bookings yet.</p>'}</div>
<h2>Availability</h2>{calendar(start, None, BASE, viewer_customer=cu["id"])}'''
        right = f'<form method="post" action="{BASE}/logout"><button class="btn ghost sm">Log out</button></form>'
        self.send(page('My bookings', body, right))

    def cust_request(self, f, ip):
        cu = self.session('customer')
        if not cu: return self.redirect(BASE + '/')
        def err(m): return self.redirect(BASE + '/?' + urlencode({'err': m}))
        car, slot, trip, notes = f.get('car'), f.get('slot'), f.get('trip'), f.get('notes', '')[:200]
        try: d = datetime.strptime(f.get('date', ''), '%Y-%m-%d').date()
        except ValueError: return err('Pick a valid date.')
        if car not in CARN or slot not in dict(SLOTS) or trip not in dict(TRIPS): return err('Invalid choice.')
        if not (today() <= d <= today() + timedelta(days=365)): return err('Pick a date from today up to one year ahead.')
        with db() as c:
            if c.execute("SELECT 1 FROM bookings WHERE car=? AND date=? AND slot=? AND status='finalized' AND cancelled_at IS NULL",
                         (car, d.isoformat(), slot)).fetchone():
                return err(f'{CARN[car]} is already booked on {fmt_day(d)} ({dict(SLOTS)[slot]}). Pick another slot.')
            if c.execute("SELECT 1 FROM bookings WHERE car=? AND date=? AND slot=? AND status='requested' AND cancelled_at IS NULL",
                         (car, d.isoformat(), slot)).fetchone():
                return err(f'A request is already pending for {CARN[car]} on {fmt_day(d)} ({dict(SLOTS)[slot]}). Call 0339 9999038 to join the waitlist.')
            try:
                c.execute("INSERT INTO bookings(agent_id,customer_id,car,date,slot,trip,amount,created_at,fuel,driver,status,notes) VALUES(NULL,?,?,?,?,?,0,?,0,1,'requested',?)",
                          (cu['id'], car, d.isoformat(), slot, trip, now_pkt().isoformat(timespec='seconds'), notes))
            except sqlite3.IntegrityError:
                return err('Could not submit that request. The slot may have just been taken.')
        self.redirect(BASE + '/?' + urlencode({'m': f'Request submitted for {CARN[car]}, {fmt_day(d)}, {dict(SLOTS)[slot]}. We will confirm shortly.'}))

    def finalize(self, f, ip):
        if not self.session('admin'): return self.redirect(BASE + '/')
        amt = f.get('amount', '').replace(',', '')
        if not amt.isdigit() or not (0 < int(amt) <= 5_000_000):
            return self.redirect(BASE + '/admin?' + urlencode({'err': 'Enter the booking amount in rupees to finalize.'}))
        with db() as c:
            b = c.execute("SELECT * FROM bookings WHERE id=? AND status='requested' AND cancelled_at IS NULL", (f.get('id'),)).fetchone()
            if not b: return self.redirect(BASE + '/admin?' + urlencode({'err': 'Request not found.'}))
            if c.execute("SELECT 1 FROM bookings WHERE car=? AND date=? AND slot=? AND status='finalized' AND cancelled_at IS NULL AND id!=?",
                         (b['car'], b['date'], b['slot'], b['id'])).fetchone():
                return self.redirect(BASE + '/admin?' + urlencode({'err': 'That slot is already finalized for someone else.'}))
            try:
                c.execute("UPDATE bookings SET status='finalized', amount=?, by_admin=1 WHERE id=?", (int(amt), b['id']))
            except sqlite3.IntegrityError:
                return self.redirect(BASE + '/admin?' + urlencode({'err': 'Could not finalize — slot conflict.'}))
        self.redirect(BASE + '/admin?' + urlencode({'m': 'Booking finalized. The customer can see it as Finalized.'}))

    def reject_req(self, f, ip):
        if not self.session('admin'): return self.redirect(BASE + '/')
        with db() as c:
            n = c.execute("UPDATE bookings SET status='rejected', cancelled_at=? WHERE id=? AND status='requested'",
                          (now_pkt().isoformat(timespec='seconds'), f.get('id'))).rowcount
        self.redirect(BASE + '/admin?' + urlencode({'m': 'Request rejected.'} if n else {'err': 'Request not found.'}))

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
