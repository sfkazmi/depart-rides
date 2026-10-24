# Depart Rides API v1

Base URL (production): `https://departrides.com/agents/api/v1`

Flutter app: **Depart Rides** · package `pk.departrides.app`

Auth: `Authorization: Bearer <token>` on protected routes.  
Content-Type: `application/json`  
Errors: `{ "error": "human-readable message" }` with suitable HTTP status (400/401/403/404/409/429).

Tokens are opaque; store hashed server-side. Login response always includes `token`, `role`, `expiresAt` (ISO-8601 UTC), and `user`.

Roles: `customer` | `agent` | `admin`

Period query (where noted): `period=this_month|last_month|all` or `from=YYYY-MM-DD&to=YYYY-MM-DD`.

---

## Public

### GET /health
```json
{ "ok": true, "version": "1" }
```

### GET /fleet
```json
{
  "cars": [
    {
      "id": "prado",
      "name": "Toyota Prado 2024",
      "rates": {
        "localJhelum": { "min": 15000, "max": 18000, "fuelIncluded": true },
        "outsideCity": { "min": 14000, "max": 17000, "fuelIncluded": false },
        "islamabadWithFuel": { "min": 27000, "max": 30000 }
      }
    }
  ],
  "packageDiscountPercent": 10,
  "contactPhone": "03399999038"
}
```
Car ids: `prado` | `haval` | `v8` | `jetour` | `corolla`. Islamabad rates only where published (prado, v8).

### GET /availability?start=YYYY-MM-DD
Public calendar (finalized occupancy only). Optional `start` (defaults today PKT). Returns ~14 days.
```json
{
  "start": "2026-10-24",
  "days": [
    {
      "date": "2026-10-24",
      "cars": [
        {
          "car": "prado",
          "morning": "available",
          "evening": "booked"
        }
      ]
    }
  ]
}
```
Slot status: `available` | `booked`.

---

## Auth

### POST /auth/signup
Customer only.
```json
// request
{ "name": "Ali Khan", "phone": "03001234567", "password": "secret123", "email": "ali@example.com" }
// response 201
{
  "token": "...",
  "role": "customer",
  "expiresAt": "2026-11-23T18:00:00Z",
  "user": { "id": 1, "name": "Ali Khan", "phone": "03001234567", "email": "ali@example.com" }
}
```

### POST /auth/login
Either password login or agent code:
```json
// A) username/phone + password (customer, agent, or admin)
{ "username": "03001234567", "password": "secret123" }
// B) agent 6-digit code
{ "code": "123456" }
// response 200
{
  "token": "...",
  "role": "agent",
  "expiresAt": "2026-11-23T18:00:00Z",
  "user": { "id": 2, "name": "Ibrahim", "username": "ibrahim" }
}
```
Admin `user` shape: `{ "id": "admin", "username": "syed-admin", "name": "Admin" }`.

### POST /auth/logout
Bearer required. Revokes current token. `204` empty or `{ "ok": true }`.

### GET /me
Bearer required.
```json
{ "role": "customer", "user": { "id": 1, "name": "Ali Khan", "phone": "03001234567", "email": null } }
```

---

## Customer (Bearer `customer`)

### POST /requests
```json
// request
{ "car": "prado", "date": "2026-11-01", "slot": "morning", "trip": "local", "notes": "Airport pickup" }
// response 201
{
  "booking": {
    "id": 10,
    "car": "prado",
    "date": "2026-11-01",
    "slot": "morning",
    "trip": "local",
    "status": "requested",
    "notes": "Airport pickup",
    "amount": null,
    "fuel": 0,
    "driver": true
  }
}
```
`slot`: `morning` | `evening`. `trip`: `local` | `out`.  
409 if a pending request already exists for that car/date/slot.

### GET /bookings
```json
{ "bookings": [ /* Booking */ ] }
```

### POST /bookings/{id}/cancel
Cancel own `requested` booking. `200` `{ "booking": { ... "status": "cancelled" } }` or `204`.

---

## Agent (Bearer `agent`)

### POST /bookings
Creates **finalized** booking.
```json
{
  "car": "v8",
  "date": "2026-10-05",
  "slot": "evening",
  "trip": "out",
  "amount": 25000,
  "fuel": 500,
  "driver": true
}
```
Past dates allowed. 409 if slot already finalized.

### PATCH /bookings/{id}
Own booking: `{ "fuel": 800, "driver": false }`

### POST /bookings/{id}/cancel
Cancel own finalized booking (same rules as web).

### GET /bookings?period=this_month
### GET /totals?period=this_month
```json
{
  "period": { "key": "this_month", "from": "2026-10-01", "to": "2026-10-31", "label": "This month" },
  "totals": {
    "bookings": 3,
    "revenue": 75000,
    "commission": 5000,
    "driving": 6000,
    "fuel": 1200,
    "net": null
  }
}
```
`net` is null for agents (admin-only).

---

## Admin (Bearer `admin`)

### GET /admin/requests
Pending customer requests (`status=requested`).

### POST /admin/requests/{id}/finalize
`{ "amount": 18000 }` → booking becomes `finalized`.

### POST /admin/requests/{id}/reject
Reject/cancel pending request.

### GET /admin/agents
### POST /admin/agents
```json
// request
{ "name": "Sara", "username": "sara", "password": "abc" }
// password optional 3 letters; blank = generate
// response 201 (credentials shown once)
{
  "agent": { "id": 3, "name": "Sara", "username": "sara" },
  "password": "abc",
  "code": "482910"
}
```
### DELETE /admin/agents/{id}

### POST /admin/agents/{id}/login-as
Returns an **agent** token for impersonation (bookings marked by admin):
```json
{
  "token": "...",
  "role": "agent",
  "expiresAt": "2026-11-23T18:00:00Z",
  "user": { "id": 3, "name": "Sara", "username": "sara" },
  "impersonatedByAdmin": true
}
```

### GET /admin/bookings?period=this_month
Finalized bookings (all agents/customers).

### POST /admin/bookings/{id}/cancel
### PATCH /admin/bookings/{id}
`{ "fuel", "driver", "amount?" }`

### GET /admin/payouts
### PUT /admin/payouts
```json
{
  "payouts": [
    { "car": "prado", "commission": 1000, "driving": 2000 },
    { "car": "v8", "commission": 2000, "driving": 2000 },
    { "car": "haval", "commission": 1000, "driving": 1500 },
    { "car": "jetour", "commission": 2000, "driving": 2500 },
    { "car": "corolla", "commission": 0, "driving": 0 }
  ]
}
```

### GET /admin/totals?period=this_month
Same totals object as agent plus `net` = revenue − commission − driving − fuel, and optional `perAgent` array.

---

## Booking object
```json
{
  "id": 1,
  "car": "prado",
  "date": "2026-11-01",
  "slot": "morning",
  "trip": "local",
  "status": "requested",
  "amount": 18000,
  "fuel": 0,
  "driver": true,
  "notes": "",
  "byAdmin": false,
  "agentId": null,
  "customerId": 1,
  "agentName": null,
  "customerName": "Ali Khan",
  "customerPhone": "03001234567",
  "cancelledAt": null
}
```
`status`: `requested` | `finalized` | `cancelled`

---

## Status codes
| Code | Meaning |
|------|---------|
| 200/201/204 | Success |
| 400 | Validation |
| 401 | Missing/invalid token or bad login |
| 403 | Wrong role |
| 404 | Not found |
| 409 | Slot conflict / duplicate pending |
| 429 | Rate limited |

Contract may gain fields; treat unknown JSON fields as ignorable. Breaking changes → v2.
