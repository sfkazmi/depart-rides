"""Depart Rides JSON API v1 (/agents/api/v1). Bearer tokens; HTML portal unchanged."""
from __future__ import annotations
import json, re, secrets, sqlite3, string, time
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlparse

# Imported late from app to avoid circular init; handlers receive `app` module helpers.

API = '/agents/api/v1'
SITE = 'https://departrides.com'
FLEET = [
    {
        'id': 'prado', 'name': 'Toyota Prado', 'tag': '2024 · Premium SUV', 'type': 'SUV',
        'year': '2024', 'seats': '7 seats', 'rate': 'On request',
        'rates': [
            {'label': 'Local Jhelum', 'range': 'Rs 15,000 – 18,000', 'note': 'With fuel'},
            {'label': 'Outside city', 'range': 'Rs 14,000 – 17,000', 'note': 'Without fuel'},
            {'label': 'Islamabad & Islamabad Airport', 'range': 'Rs 27,000 – 30,000', 'note': 'With fuel'},
        ],
        'image': f'{SITE}/assets/prado-three-quarter.jpg',
    },
    {
        'id': 'haval-h6', 'name': 'Haval H6', 'tag': '2025 · Modern comfort', 'type': 'SUV',
        'year': '2025', 'seats': '5 seats', 'rate': 'On request',
        'rates': [
            {'label': 'Local Jhelum', 'range': 'Rs 12,000 – 15,000', 'note': 'With fuel'},
            {'label': 'Outside city', 'range': 'Rs 10,000 – 12,000', 'note': 'Without fuel'},
        ],
        'image': f'{SITE}/assets/haval-h6-front.jpg',
    },
    {
        'id': 'jetour-t2', 'name': 'Jetour T2', 'tag': '2026 · White', 'type': 'SUV',
        'year': '2026', 'seats': '5 seats', 'rate': 'Price on demand',
        'image': f'{SITE}/assets/jetour-t2-front.jpg',
    },
    {
        'id': 'corolla-xli', 'name': 'Toyota Corolla XLi', 'tag': '2014 · Black', 'type': 'Sedan',
        'year': '2014', 'seats': '5 seats', 'rate': 'Price on demand',
        'image': f'{SITE}/assets/corolla-xli-front.jpg',
    },
    {
        'id': 'land-cruiser-v8', 'name': 'Toyota Land Cruiser V8', 'tag': '2018 · Actual vehicle',
        'type': 'Luxury', 'year': '2018', 'seats': 'Capacity on request', 'rate': 'On request',
        'rates': [
            {'label': 'Local Jhelum', 'range': 'Rs 20,000 – 25,000', 'note': 'With fuel'},
            {'label': 'Outside city', 'range': 'Rs 18,000 – 22,000', 'note': 'Without fuel'},
            {'label': 'Islamabad & Islamabad Airport', 'range': 'Rs 35,000 – 40,000', 'note': 'With fuel'},
        ],
        'image': f'{SITE}/assets/land-cruiser-side.jpg',
    },
]

TTL = {'customer': 30 * 86400, 'agent': 7 * 86400, 'admin': 12 * 3600}


def ensure_api_tables(c):
    c.execute('''CREATE TABLE IF NOT EXISTS api_tokens(
        token_hash TEXT PRIMARY KEY,
        role TEXT NOT NULL,
        ref_id INTEGER NOT NULL,
        expires REAL NOT NULL,
        admin_id INTEGER,
        created_at TEXT NOT NULL)''')
    c.execute('CREATE INDEX IF NOT EXISTS api_tokens_exp ON api_tokens(expires)')


def iso_exp(expires_ts, pkt):
    return datetime.fromtimestamp(expires_ts, pkt).isoformat(timespec='seconds')


def booking_json(b, carn):
    st = 'cancelled' if b['cancelled_at'] else (b['status'] if 'status' in b.keys() else 'finalized')
    return {
        'id': b['id'],
        'car': b['car'],
        'carName': carn.get(b['car'], b['car']),
        'date': b['date'],
        'slot': b['slot'],
        'trip': b['trip'],
        'status': st,
        'notes': b['notes'] if 'notes' in b.keys() and b['notes'] else '',
        'amount': b['amount'],
        'fuel': b['fuel'] if 'fuel' in b.keys() else 0,
        'driver': bool(b['driver']) if 'driver' in b.keys() else True,
        'agentId': b['agent_id'],
        'customerId': b['customer_id'] if 'customer_id' in b.keys() else None,
        'createdAt': b['created_at'],
        'cancelledAt': b['cancelled_at'],
    }


def totals_json(t):
    return {
        'bookings': t['n'], 'revenue': t['rev'], 'commission': t['com'],
        'driving': t['drv'], 'fuel': t['fuel'], 'net': t['net'],
    }


def period_from_q(q, period_fn):
    """Map API period names onto HTML period() helper."""
    p = (q.get('period') or ['this_month'])[0]
    alias = {'this_month': 'month', 'last_month': 'last', 'all': 'all'}
    if p in ('from',) or (q.get('from') and q.get('to')):
        qq = {
            'period': ['custom'],
            'from_d': [q.get('from', [q.get('from_d', [''])[0]])[0]],
            'to_d': [q.get('to', [q.get('to_d', [''])[0]])[0]],
        }
        return period_fn(qq)
    qq = {'period': [alias.get(p, p)]}
    if p == 'custom':
        qq['from_d'] = q.get('from_d', q.get('from', ['']))
        qq['to_d'] = q.get('to_d', q.get('to', ['']))
    return period_fn(qq)


class Api:
    def __init__(self, app):
        self.app = app

    def handle(self, h, method):
        u = urlparse(h.path)
        path = u.path.rstrip('/') or '/'
        if not path.startswith(API):
            return False
        rel = path[len(API):] or '/'
        if not rel.startswith('/'):
            rel = '/' + rel
        q = parse_qs(u.query)
        if method == 'OPTIONS':
            return self._options(h)
        try:
            body = self._json_body(h) if method in ('POST', 'PUT', 'PATCH') else {}
        except ValueError as e:
            return self._err(h, 400, str(e))
        routes = self._routes()
        key = (method, rel)
        # path params
        handler = routes.get(key)
        params = {}
        if not handler:
            for (m, pat), fn in routes.items():
                if m != method:
                    continue
                mobj = re.fullmatch(pat, rel)
                if mobj:
                    handler = fn
                    params = mobj.groupdict()
                    break
        if not handler:
            return self._err(h, 404, 'Not found')
        return handler(h, q, body, params)

    def _routes(self):
        # patterns use named groups; static paths as exact strings
        R = {}
        def add(method, path, fn):
            R[(method, path)] = fn
        add('GET', '/health', self.health)
        add('GET', '/fleet', self.fleet)
        add('GET', '/availability', self.availability)
        add('POST', '/auth/signup', self.signup)
        add('POST', '/auth/login', self.login)
        add('POST', '/auth/logout', self.logout)
        add('GET', '/me', self.me)
        add('POST', '/requests', self.cust_request)
        add('GET', '/bookings', self.list_bookings)
        add('POST', '/bookings', self.agent_book)
        add('PATCH', r'/bookings/(?P<id>\d+)', self.patch_booking)
        add('POST', r'/bookings/(?P<id>\d+)/cancel', self.cancel_booking)
        add('GET', '/totals', self.agent_totals)
        add('GET', '/admin/requests', self.admin_requests)
        add('POST', r'/admin/requests/(?P<id>\d+)/finalize', self.admin_finalize)
        add('POST', r'/admin/requests/(?P<id>\d+)/reject', self.admin_reject)
        add('GET', '/admin/agents', self.admin_agents)
        add('POST', '/admin/agents', self.admin_agent_add)
        add('DELETE', r'/admin/agents/(?P<id>\d+)', self.admin_agent_del)
        add('POST', r'/admin/agents/(?P<id>\d+)/login-as', self.admin_login_as)
        add('GET', '/admin/bookings', self.admin_bookings)
        add('PATCH', r'/admin/bookings/(?P<id>\d+)', self.admin_patch_booking)
        add('POST', r'/admin/bookings/(?P<id>\d+)/cancel', self.admin_cancel)
        add('GET', '/admin/payouts', self.admin_get_payouts)
        add('PUT', '/admin/payouts', self.admin_put_payouts)
        add('GET', '/admin/totals', self.admin_totals)
        return R

    def _json_body(self, h):
        n = min(int(h.headers.get('Content-Length') or 0), 100_000)
        raw = h.rfile.read(n) if n else b''
        if not raw:
            return {}
        try:
            data = json.loads(raw.decode('utf-8'))
        except Exception:
            raise ValueError('Invalid JSON body')
        if not isinstance(data, dict):
            raise ValueError('JSON body must be an object')
        return data

    def _cors(self):
        return [
            ('Access-Control-Allow-Origin', '*'),
            ('Access-Control-Allow-Headers', 'Authorization, Content-Type'),
            ('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, DELETE, OPTIONS'),
        ]

    def _options(self, h):
        h.send_response(204)
        for k, v in self._cors():
            h.send_header(k, v)
        h.send_header('Content-Length', '0')
        h.send_header('Cache-Control', 'no-store')
        h.end_headers()
        return True

    def _send(self, h, code, obj):
        b = json.dumps(obj, ensure_ascii=False).encode()
        h.send_response(code)
        h.send_header('Content-Type', 'application/json; charset=utf-8')
        h.send_header('Content-Length', str(len(b)))
        h.send_header('Cache-Control', 'no-store')
        h.send_header('X-Content-Type-Options', 'nosniff')
        for k, v in self._cors():
            h.send_header(k, v)
        h.end_headers()
        h.wfile.write(b)
        return True

    def _err(self, h, code, msg):
        return self._send(h, code, {'error': msg})

    def _bearer(self, h):
        auth = h.headers.get('Authorization') or ''
        if not auth.lower().startswith('bearer '):
            return None
        return auth[7:].strip()

    def _auth(self, h, roles=None):
        app = self.app
        tok = self._bearer(h)
        if not tok:
            return None, self._err(h, 401, 'Missing or invalid Authorization Bearer token')
        with app.db() as c:
            c.execute('DELETE FROM api_tokens WHERE expires<?', (time.time(),))
            row = c.execute(
                'SELECT role, ref_id, expires, admin_id FROM api_tokens WHERE token_hash=? AND expires>?',
                (app.tok_hash(tok), time.time())).fetchone()
            if not row:
                return None, self._err(h, 401, 'Invalid or expired token')
            role, ref, exp, admin_id = row['role'], row['ref_id'], row['expires'], row['admin_id']
            if roles and role not in roles:
                return None, self._err(h, 403, 'Forbidden for this role')
            user = None
            if role == 'admin':
                user = c.execute('SELECT * FROM admins WHERE id=?', (ref,)).fetchone()
            elif role == 'agent':
                user = c.execute('SELECT * FROM agents WHERE id=? AND active=1', (ref,)).fetchone()
            elif role == 'customer':
                user = c.execute('SELECT * FROM customers WHERE id=? AND active=1', (ref,)).fetchone()
            if not user:
                return None, self._err(h, 401, 'Account not found or inactive')
            return {
                'role': role, 'ref': ref, 'expires': exp, 'admin_id': admin_id, 'user': user, 'token': tok
            }, None

    def _issue(self, role, ref_id, admin_id=None):
        app = self.app
        ttl = TTL[role]
        raw = secrets.token_urlsafe(32)
        exp = time.time() + ttl
        with app.db() as c:
            c.execute('DELETE FROM api_tokens WHERE expires<?', (time.time(),))
            c.execute(
                'INSERT INTO api_tokens(token_hash,role,ref_id,expires,admin_id,created_at) VALUES(?,?,?,?,?,?)',
                (app.tok_hash(raw), role, ref_id, exp, admin_id, app.now_pkt().isoformat(timespec='seconds')))
        return raw, exp

    def _user_json(self, role, user):
        if role == 'customer':
            return {'id': user['id'], 'name': user['name'], 'phone': user['phone'], 'email': user['email']}
        if role == 'agent':
            return {'id': user['id'], 'name': user['name'], 'username': user['username']}
        return {'id': user['id'], 'username': user['username']}

    def _auth_resp(self, h, code, role, user, token, exp, impersonated=False):
        app = self.app
        body = {
            'token': token,
            'role': role,
            'expiresAt': iso_exp(exp, app.PKT),
            'user': self._user_json(role, user),
        }
        if impersonated:
            body['impersonatedByAdmin'] = True
        return self._send(h, code, body)

    # ---- public ----
    def health(self, h, q, body, params):
        return self._send(h, 200, {'ok': True, 'service': 'departrides-api', 'version': '1'})

    def fleet(self, h, q, body, params):
        return self._send(h, 200, {'cars': FLEET})

    def availability(self, h, q, body, params):
        app = self.app
        start = app.parse_start({'from': q.get('start') or q.get('from') or ['']})
        end = start + timedelta(days=app.DAYS - 1)
        with app.db() as c:
            rows = c.execute(
                "SELECT car,date,slot FROM bookings WHERE cancelled_at IS NULL AND status='finalized' AND date BETWEEN ? AND ?",
                (start.isoformat(), end.isoformat())).fetchall()
        taken = {(r['car'], r['date'], r['slot']) for r in rows}
        slots = []
        for i in range(app.DAYS):
            d = start + timedelta(days=i)
            ds = d.isoformat()
            for cid, _ in app.CARS:
                for sid, _ in app.SLOTS:
                    if (cid, ds, sid) in taken:
                        st = 'booked'
                    elif app.slot_past(d, sid):
                        st = 'past'
                    else:
                        st = 'available'
                    slots.append({'date': ds, 'car': cid, 'slot': sid, 'status': st})
        return self._send(h, 200, {'start': start.isoformat(), 'days': app.DAYS, 'slots': slots})

    # ---- auth ----
    def signup(self, h, q, body, params):
        app = self.app
        name = (body.get('name') or '').strip()
        phone = app.phone_norm(body.get('phone') or '')
        pw = body.get('password') or ''
        email = (body.get('email') or '').strip()
        if not (2 <= len(name) <= 80):
            return self._err(h, 400, 'Enter your name.')
        if not (phone.startswith('03') and len(phone) == 11):
            return self._err(h, 400, 'Enter a valid Pakistani mobile number (03XXXXXXXXX).')
        if not (8 <= len(pw) <= 72):
            return self._err(h, 400, 'Password must be at least 8 characters.')
        if email and ('@' not in email or len(email) > 120):
            return self._err(h, 400, 'Enter a valid email, or omit it.')
        try:
            with app.db() as c:
                c.execute(
                    'INSERT INTO customers(name,phone,email,pw_hash,created_at) VALUES(?,?,?,?,?)',
                    (name, phone, email or None, app.pw_hash(pw), app.now_pkt().isoformat(timespec='seconds')))
                cid = c.execute('SELECT id FROM customers WHERE phone=?', (phone,)).fetchone()['id']
                user = c.execute('SELECT * FROM customers WHERE id=?', (cid,)).fetchone()
        except sqlite3.IntegrityError:
            return self._err(h, 409, 'An account with that phone number already exists.')
        token, exp = self._issue('customer', cid)
        return self._auth_resp(h, 201, 'customer', user, token, exp)

    def login(self, h, q, body, params):
        app = self.app
        ip = h.ip()
        if app.limited('ip', ip):
            return self._err(h, 429, 'Too many attempts. Please wait and try again.')
        code = (body.get('code') or '').strip()
        if code:
            if app.limited('code-global', 'all'):
                return self._err(h, 429, 'Too many attempts. Please wait and try again.')
            if not (code.isdigit() and len(code) == 6):
                app.fail('ip', ip); app.fail('code-global', 'all')
                return self._err(h, 401, 'Login failed.')
            with app.db() as c:
                a = c.execute('SELECT * FROM agents WHERE code_hash=? AND active=1', (app.code_hash(code),)).fetchone()
            if not a:
                app.fail('ip', ip); app.fail('code-global', 'all')
                return self._err(h, 401, 'Login failed.')
            token, exp = self._issue('agent', a['id'])
            return self._auth_resp(h, 200, 'agent', a, token, exp)

        un_raw = (body.get('username') or body.get('phone') or '').strip()
        pw = body.get('password') or ''
        un = un_raw.lower()
        ph = app.phone_norm(un_raw)
        if app.limited('user', un or ph):
            return self._err(h, 429, 'Too many attempts. Please wait and try again.')
        with app.db() as c:
            ad = c.execute('SELECT * FROM admins WHERE username=?', (un_raw,)).fetchone()
            if ad and app.pw_check(pw, ad['pw_hash']):
                token, exp = self._issue('admin', ad['id'])
                return self._auth_resp(h, 200, 'admin', ad, token, exp)
            a = c.execute('SELECT * FROM agents WHERE username=? AND active=1', (un,)).fetchone()
            if a and app.pw_check(pw.lower(), a['pw_hash']):
                token, exp = self._issue('agent', a['id'])
                return self._auth_resp(h, 200, 'agent', a, token, exp)
            cu = c.execute('SELECT * FROM customers WHERE phone=? AND active=1', (ph,)).fetchone() if ph else None
            if cu and app.pw_check(pw, cu['pw_hash']):
                token, exp = self._issue('customer', cu['id'])
                return self._auth_resp(h, 200, 'customer', cu, token, exp)
            app.pw_check('xxx', '00$00')
        app.fail('ip', ip); app.fail('user', un or ph)
        return self._err(h, 401, 'Login failed.')

    def logout(self, h, q, body, params):
        app = self.app
        auth, err = self._auth(h)
        if err:
            return err
        with app.db() as c:
            c.execute('DELETE FROM api_tokens WHERE token_hash=?', (app.tok_hash(auth['token']),))
        return self._send(h, 200, {'ok': True})

    def me(self, h, q, body, params):
        app = self.app
        auth, err = self._auth(h)
        if err:
            return err
        out = {
            'role': auth['role'],
            'user': self._user_json(auth['role'], auth['user']),
            'expiresAt': iso_exp(auth['expires'], app.PKT),
        }
        if auth['admin_id']:
            out['impersonatedByAdmin'] = True
            out['adminId'] = auth['admin_id']
        return self._send(h, 200, out)

    # ---- customer ----
    def cust_request(self, h, q, body, params):
        app = self.app
        auth, err = self._auth(h, roles=['customer'])
        if err:
            return err
        cu = auth['user']
        car, slot, trip = body.get('car'), body.get('slot'), body.get('trip')
        notes = (body.get('notes') or '')[:200]
        try:
            d = datetime.strptime(body.get('date') or '', '%Y-%m-%d').date()
        except ValueError:
            return self._err(h, 400, 'Pick a valid date.')
        if car not in app.CARN or slot not in dict(app.SLOTS) or trip not in dict(app.TRIPS):
            return self._err(h, 400, 'Invalid choice.')
        if not (app.today() <= d <= app.today() + timedelta(days=365)):
            return self._err(h, 400, 'Pick a date from today up to one year ahead.')
        with app.db() as c:
            if c.execute(
                "SELECT 1 FROM bookings WHERE car=? AND date=? AND slot=? AND status='finalized' AND cancelled_at IS NULL",
                (car, d.isoformat(), slot)).fetchone():
                return self._err(h, 409, f'{app.CARN[car]} is already booked on {app.fmt_day(d)} ({dict(app.SLOTS)[slot]}).')
            if c.execute(
                "SELECT 1 FROM bookings WHERE car=? AND date=? AND slot=? AND status='requested' AND cancelled_at IS NULL",
                (car, d.isoformat(), slot)).fetchone():
                return self._err(
                    h, 409,
                    f'A request is already pending for {app.CARN[car]} on {app.fmt_day(d)} ({dict(app.SLOTS)[slot]}). Call 0339 9999038 to join the waitlist.')
            try:
                cur = c.execute(
                    "INSERT INTO bookings(agent_id,customer_id,car,date,slot,trip,amount,created_at,fuel,driver,status,notes) VALUES(NULL,?,?,?,?,?,0,?,0,1,'requested',?)",
                    (cu['id'], car, d.isoformat(), slot, trip, app.now_pkt().isoformat(timespec='seconds'), notes))
                bid = cur.lastrowid
            except sqlite3.IntegrityError:
                return self._err(h, 409, 'Could not submit that request. The slot may have just been taken.')
            b = c.execute('SELECT * FROM bookings WHERE id=?', (bid,)).fetchone()
        return self._send(h, 201, {'booking': booking_json(b, app.CARN)})

    def list_bookings(self, h, q, body, params):
        app = self.app
        auth, err = self._auth(h, roles=['customer', 'agent'])
        if err:
            return err
        with app.db() as c:
            if auth['role'] == 'customer':
                rows = c.execute(
                    'SELECT * FROM bookings WHERE customer_id=? ORDER BY date DESC, slot',
                    (auth['ref'],)).fetchall()
            else:
                pk, lo, hi, _ = period_from_q(q, app.period)
                ps_sql, ps_args = app.period_sql(lo, hi)
                rows = c.execute(
                    "SELECT b.* FROM bookings b WHERE b.agent_id=? AND b.cancelled_at IS NULL AND b.status='finalized'"
                    + ps_sql + ' ORDER BY b.date DESC, b.slot',
                    (auth['ref'],) + ps_args).fetchall()
        return self._send(h, 200, {'bookings': [booking_json(b, app.CARN) for b in rows]})

    def cancel_booking(self, h, q, body, params):
        app = self.app
        auth, err = self._auth(h, roles=['customer', 'agent'])
        if err:
            return err
        bid = int(params['id'])
        with app.db() as c:
            if auth['role'] == 'customer':
                n = c.execute(
                    "UPDATE bookings SET cancelled_at=?, status='cancelled' WHERE id=? AND customer_id=? AND status='requested' AND cancelled_at IS NULL",
                    (app.now_pkt().isoformat(timespec='seconds'), bid, auth['ref'])).rowcount
            else:
                n = c.execute(
                    "UPDATE bookings SET cancelled_at=?, status=CASE WHEN status='requested' THEN 'cancelled' ELSE status END WHERE id=? AND agent_id=? AND cancelled_at IS NULL",
                    (app.now_pkt().isoformat(timespec='seconds'), bid, auth['ref'])).rowcount
            if not n:
                return self._err(h, 404, 'Booking not found or cannot be cancelled.')
            b = c.execute('SELECT * FROM bookings WHERE id=?', (bid,)).fetchone()
        return self._send(h, 200, {'booking': booking_json(b, app.CARN)})

    # ---- agent ----
    def agent_book(self, h, q, body, params):
        app = self.app
        auth, err = self._auth(h, roles=['agent'])
        if err:
            return err
        a = auth['user']
        car, slot, trip = body.get('car'), body.get('slot'), body.get('trip')
        amt = str(body.get('amount', '')).replace(',', '')
        fuel = str(body.get('fuel', 0) if body.get('fuel') is not None else 0).replace(',', '') or '0'
        drv = 1 if body.get('driver', True) in (True, 1, '1', 'true', 'yes') else 0
        try:
            d = datetime.strptime(body.get('date') or '', '%Y-%m-%d').date()
        except ValueError:
            return self._err(h, 400, 'Pick a valid date.')
        if car not in app.CARN or slot not in dict(app.SLOTS) or trip not in dict(app.TRIPS):
            return self._err(h, 400, 'Invalid choice.')
        if not (app.today() - timedelta(days=3650) <= d <= app.today() + timedelta(days=365)):
            return self._err(h, 400, 'Pick a date within the last 10 years or up to one year ahead.')
        if not fuel.isdigit() or int(fuel) > 5_000_000:
            return self._err(h, 400, 'Enter the fuel cost in rupees (numbers only), or 0.')
        if not amt.isdigit() or not (0 < int(amt) <= 5_000_000):
            return self._err(h, 400, 'Enter the booking amount in rupees (numbers only).')
        by_admin = auth['admin_id']
        try:
            with app.db() as c:
                cur = c.execute(
                    "INSERT INTO bookings(agent_id,car,date,slot,trip,amount,created_at,by_admin,fuel,driver,status) VALUES(?,?,?,?,?,?,?,?,?,?, 'finalized')",
                    (a['id'], car, d.isoformat(), slot, trip, int(amt), app.now_pkt().isoformat(timespec='seconds'),
                     by_admin, int(fuel), drv))
                bid = cur.lastrowid
                b = c.execute('SELECT * FROM bookings WHERE id=?', (bid,)).fetchone()
        except sqlite3.IntegrityError:
            return self._err(
                h, 409,
                f'{app.CARN[car]} is already booked on {app.fmt_day(d)} ({dict(app.SLOTS)[slot]}).')
        return self._send(h, 201, {'booking': booking_json(b, app.CARN)})

    def patch_booking(self, h, q, body, params):
        app = self.app
        auth, err = self._auth(h, roles=['agent', 'admin'])
        if err:
            return err
        bid = int(params['id'])
        fuel = body.get('fuel')
        drv = body.get('driver')
        with app.db() as c:
            b = c.execute('SELECT * FROM bookings WHERE id=? AND cancelled_at IS NULL', (bid,)).fetchone()
            if not b:
                return self._err(h, 404, 'Booking not found.')
            if auth['role'] == 'agent' and b['agent_id'] != auth['ref']:
                return self._err(h, 403, 'Not your booking.')
            new_fuel = b['fuel'] if fuel is None else str(fuel).replace(',', '')
            if not str(new_fuel).isdigit() or int(new_fuel) > 5_000_000:
                return self._err(h, 400, 'Fuel cost must be a number in rupees.')
            new_drv = b['driver'] if drv is None else (1 if drv in (True, 1, '1', 'true', 'yes') else 0)
            c.execute('UPDATE bookings SET fuel=?, driver=? WHERE id=?', (int(new_fuel), int(new_drv), bid))
            b = c.execute('SELECT * FROM bookings WHERE id=?', (bid,)).fetchone()
        return self._send(h, 200, {'booking': booking_json(b, app.CARN)})

    def agent_totals(self, h, q, body, params):
        app = self.app
        auth, err = self._auth(h, roles=['agent'])
        if err:
            return err
        pk, lo, hi, label = period_from_q(q, app.period)
        ps_sql, ps_args = app.period_sql(lo, hi)
        with app.db() as c:
            rows = c.execute(
                "SELECT b.* FROM bookings b WHERE b.agent_id=? AND b.cancelled_at IS NULL AND b.status='finalized'"
                + ps_sql,
                (auth['ref'],) + ps_args).fetchall()
            tot = app.totals(rows, app.payouts(c))
        return self._send(h, 200, {
            'period': pk if pk != 'month' else 'this_month',
            'label': label,
            'from': lo.isoformat() if lo else None,
            'to': hi.isoformat() if hi else None,
            'totals': totals_json(tot),
        })

    # ---- admin ----
    def admin_requests(self, h, q, body, params):
        app = self.app
        auth, err = self._auth(h, roles=['admin'])
        if err:
            return err
        with app.db() as c:
            rows = c.execute('''SELECT b.*, cu.name cname, cu.phone cphone, cu.id cid FROM bookings b
                JOIN customers cu ON cu.id=b.customer_id
                WHERE b.status='requested' AND b.cancelled_at IS NULL ORDER BY b.date, b.slot, b.car''').fetchall()
        out = []
        for b in rows:
            o = booking_json(b, app.CARN)
            o['customer'] = {'id': b['cid'], 'name': b['cname'], 'phone': b['cphone']}
            out.append(o)
        return self._send(h, 200, {'requests': out})

    def admin_finalize(self, h, q, body, params):
        app = self.app
        auth, err = self._auth(h, roles=['admin'])
        if err:
            return err
        bid = int(params['id'])
        amt = str(body.get('amount', '')).replace(',', '')
        if not amt.isdigit() or not (0 < int(amt) <= 5_000_000):
            return self._err(h, 400, 'Enter the booking amount in rupees to finalize.')
        with app.db() as c:
            b = c.execute(
                "SELECT * FROM bookings WHERE id=? AND status='requested' AND cancelled_at IS NULL", (bid,)).fetchone()
            if not b:
                return self._err(h, 404, 'Request not found.')
            if c.execute(
                "SELECT 1 FROM bookings WHERE car=? AND date=? AND slot=? AND status='finalized' AND cancelled_at IS NULL AND id!=?",
                (b['car'], b['date'], b['slot'], b['id'])).fetchone():
                return self._err(h, 409, 'That slot is already finalized for someone else.')
            try:
                c.execute("UPDATE bookings SET status='finalized', amount=?, by_admin=1 WHERE id=?", (int(amt), bid))
            except sqlite3.IntegrityError:
                return self._err(h, 409, 'Could not finalize — slot conflict.')
            b = c.execute('SELECT * FROM bookings WHERE id=?', (bid,)).fetchone()
        return self._send(h, 200, {'booking': booking_json(b, app.CARN)})

    def admin_reject(self, h, q, body, params):
        app = self.app
        auth, err = self._auth(h, roles=['admin'])
        if err:
            return err
        bid = int(params['id'])
        with app.db() as c:
            n = c.execute(
                "UPDATE bookings SET status='rejected', cancelled_at=? WHERE id=? AND status='requested'",
                (app.now_pkt().isoformat(timespec='seconds'), bid)).rowcount
            if not n:
                return self._err(h, 404, 'Request not found.')
            b = c.execute('SELECT * FROM bookings WHERE id=?', (bid,)).fetchone()
        return self._send(h, 200, {'booking': booking_json(b, app.CARN)})

    def admin_agents(self, h, q, body, params):
        app = self.app
        auth, err = self._auth(h, roles=['admin'])
        if err:
            return err
        with app.db() as c:
            rows = c.execute(
                """SELECT a.*, (SELECT COUNT(*) FROM bookings b WHERE b.agent_id=a.id AND b.cancelled_at IS NULL AND b.status='finalized') n
                   FROM agents a WHERE active=1 ORDER BY name""").fetchall()
        return self._send(h, 200, {
            'agents': [
                {'id': r['id'], 'name': r['name'], 'username': r['username'], 'bookings': r['n'], 'active': True}
                for r in rows
            ]
        })

    def admin_agent_add(self, h, q, body, params):
        app = self.app
        auth, err = self._auth(h, roles=['admin'])
        if err:
            return err
        name = (body.get('name') or '').strip()
        un = (body.get('username') or '').strip().lower()
        pw = (body.get('password') or '').strip().lower()
        if not name or not un or not all(ch in string.ascii_lowercase + string.digits + '._-' for ch in un) or len(un) < 3:
            return self._err(h, 400, 'Enter a name and a username (3+ letters/numbers).')
        if pw and not (len(pw) == 3 and pw.isalpha() and pw.isascii()):
            return self._err(h, 400, 'Password must be exactly 3 letters.')
        pw = pw or ''.join(secrets.choice(string.ascii_lowercase) for _ in range(3))
        with app.db() as c:
            if c.execute('SELECT 1 FROM agents WHERE username=?', (un,)).fetchone():
                return self._err(h, 409, 'That username is taken.')
            code = None
            for _ in range(50):
                code = f'{secrets.randbelow(900000) + 100000}'
                if not c.execute('SELECT 1 FROM agents WHERE code_hash=?', (app.code_hash(code),)).fetchone():
                    break
            cur = c.execute(
                'INSERT INTO agents(name,username,pw_hash,code_hash,created_at) VALUES(?,?,?,?,?)',
                (name, un, app.pw_hash(pw), app.code_hash(code), app.now_pkt().isoformat(timespec='seconds')))
            aid = cur.lastrowid
        return self._send(h, 201, {
            'agent': {'id': aid, 'name': name, 'username': un, 'bookings': 0, 'active': True},
            'password': pw,
            'code': code,
        })

    def admin_agent_del(self, h, q, body, params):
        app = self.app
        auth, err = self._auth(h, roles=['admin'])
        if err:
            return err
        aid = int(params['id'])
        with app.db() as c:
            c.execute("DELETE FROM sessions WHERE role='agent' AND ref_id=?", (aid,))
            c.execute("UPDATE sessions SET as_agent=NULL WHERE as_agent=?", (aid,))
            c.execute("DELETE FROM api_tokens WHERE role='agent' AND ref_id=?", (aid,))
            n = c.execute('DELETE FROM agents WHERE id=?', (aid,)).rowcount
        if not n:
            return self._err(h, 404, 'Agent not found.')
        return self._send(h, 200, {'ok': True})

    def admin_login_as(self, h, q, body, params):
        app = self.app
        auth, err = self._auth(h, roles=['admin'])
        if err:
            return err
        aid = int(params['id'])
        with app.db() as c:
            a = c.execute('SELECT * FROM agents WHERE id=? AND active=1', (aid,)).fetchone()
        if not a:
            return self._err(h, 404, 'Agent not found.')
        token, exp = self._issue('agent', a['id'], admin_id=auth['ref'])
        return self._auth_resp(h, 200, 'agent', a, token, exp, impersonated=True)

    def admin_bookings(self, h, q, body, params):
        app = self.app
        auth, err = self._auth(h, roles=['admin'])
        if err:
            return err
        pk, lo, hi, _ = period_from_q(q, app.period)
        ps_sql, ps_args = app.period_sql(lo, hi)
        with app.db() as c:
            rows = c.execute(
                '''SELECT b.* FROM bookings b WHERE b.cancelled_at IS NULL AND b.status='finalized' '''
                + ps_sql + ' ORDER BY b.date, b.slot, b.car', ps_args).fetchall()
        return self._send(h, 200, {'bookings': [booking_json(b, app.CARN) for b in rows]})

    def admin_patch_booking(self, h, q, body, params):
        return self.patch_booking(h, q, body, params)

    def admin_cancel(self, h, q, body, params):
        app = self.app
        auth, err = self._auth(h, roles=['admin'])
        if err:
            return err
        bid = int(params['id'])
        with app.db() as c:
            n = c.execute(
                'UPDATE bookings SET cancelled_at=? WHERE id=? AND cancelled_at IS NULL',
                (app.now_pkt().isoformat(timespec='seconds'), bid)).rowcount
            if not n:
                return self._err(h, 404, 'Booking not found.')
            b = c.execute('SELECT * FROM bookings WHERE id=?', (bid,)).fetchone()
        return self._send(h, 200, {'booking': booking_json(b, app.CARN)})

    def admin_get_payouts(self, h, q, body, params):
        app = self.app
        auth, err = self._auth(h, roles=['admin'])
        if err:
            return err
        with app.db() as c:
            po = app.payouts(c)
        return self._send(h, 200, {
            'payouts': [
                {'car': k, 'carName': n, 'commission': po.get(k, (0, 0))[0], 'driving': po.get(k, (0, 0))[1]}
                for k, n in app.CARS
            ]
        })

    def admin_put_payouts(self, h, q, body, params):
        app = self.app
        auth, err = self._auth(h, roles=['admin'])
        if err:
            return err
        items = body.get('payouts') or []
        if not isinstance(items, list) or not items:
            return self._err(h, 400, 'Provide payouts array.')
        vals = []
        for it in items:
            k = it.get('car')
            if k not in app.CARN:
                return self._err(h, 400, f'Unknown car: {k}')
            try:
                cm, dv = int(it['commission']), int(it['driving'])
            except (KeyError, TypeError, ValueError):
                return self._err(h, 400, f'Payouts for {app.CARN[k]} must be numbers.')
            if not (0 <= cm <= 1_000_000 and 0 <= dv <= 1_000_000):
                return self._err(h, 400, f'Payouts for {app.CARN[k]} out of range.')
            vals.append((k, cm, dv))
        with app.db() as c:
            c.executemany(
                'INSERT INTO payouts(car,commission,driving) VALUES(?,?,?) ON CONFLICT(car) DO UPDATE SET commission=excluded.commission, driving=excluded.driving',
                vals)
            po = app.payouts(c)
        return self._send(h, 200, {
            'payouts': [
                {'car': k, 'carName': n, 'commission': po.get(k, (0, 0))[0], 'driving': po.get(k, (0, 0))[1]}
                for k, n in app.CARS
            ]
        })

    def admin_totals(self, h, q, body, params):
        app = self.app
        auth, err = self._auth(h, roles=['admin'])
        if err:
            return err
        pk, lo, hi, label = period_from_q(q, app.period)
        ps_sql, ps_args = app.period_sql(lo, hi)
        with app.db() as c:
            rows = c.execute(
                '''SELECT b.*, a.name aname FROM bookings b LEFT JOIN agents a ON a.id=b.agent_id
                   WHERE b.cancelled_at IS NULL AND b.status='finalized' ''' + ps_sql,
                ps_args).fetchall()
            po = app.payouts(c)
            tot = app.totals(rows, po)
            per = {}
            for b in rows:
                if b['agent_id']:
                    per.setdefault(b['agent_id'], {'name': b['aname'] or '—', 'rows': []})['rows'].append(b)
        by = [
            {'agentId': aid, 'name': v['name'], 'totals': totals_json(app.totals(v['rows'], po))}
            for aid, v in sorted(per.items(), key=lambda x: x[1]['name'] or '')
        ]
        return self._send(h, 200, {
            'period': pk if pk != 'month' else 'this_month',
            'label': label,
            'from': lo.isoformat() if lo else None,
            'to': hi.isoformat() if hi else None,
            'totals': totals_json(tot),
            'byAgent': by,
        })


def attach(app_module):
    """Wire API into HTTP handler class on app module."""
    api = Api(app_module)
    H = app_module.H
    _get, _post = H.do_GET, H.do_POST

    def do_GET(self):
        if urlparse(self.path).path.rstrip('/').startswith(API) or urlparse(self.path).path.startswith(API + '/'):
            return api.handle(self, 'GET')
        return _get(self)

    def do_POST(self):
        p = urlparse(self.path).path.rstrip('/')
        if p.startswith(API):
            return api.handle(self, 'POST')
        return _post(self)

    def do_PUT(self):
        if urlparse(self.path).path.rstrip('/').startswith(API):
            return api.handle(self, 'PUT')
        self.send_error(405)

    def do_PATCH(self):
        if urlparse(self.path).path.rstrip('/').startswith(API):
            return api.handle(self, 'PATCH')
        self.send_error(405)

    def do_DELETE(self):
        if urlparse(self.path).path.rstrip('/').startswith(API):
            return api.handle(self, 'DELETE')
        self.send_error(405)

    def do_OPTIONS(self):
        if urlparse(self.path).path.rstrip('/').startswith(API) or urlparse(self.path).path.startswith(API + '/'):
            return api.handle(self, 'OPTIONS')
        self.send_error(405)

    H.do_GET = do_GET
    H.do_POST = do_POST
    H.do_PUT = do_PUT
    H.do_PATCH = do_PATCH
    H.do_DELETE = do_DELETE
    H.do_OPTIONS = do_OPTIONS
    return api
