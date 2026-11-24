# RailSync — Smart Railway Management System

A Flask web app for railway operations and passenger access: train search and booking, simulated UPI payment, QR tickets, live train tracking, platform allocation, gate checks, and complaints. Three roles share one app: **Admin**, **Staff**, and **Passenger**.

## Quick start (local demo)

Runs on SQLite — no MySQL server or `.env` needed.

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python seed.py
.\.venv\Scripts\python app.py
```

Open http://127.0.0.1:5000/login. `seed.py` rebuilds `instance/railsync.db` from `schema.sql` with 12 stations, 12 trains, 24 schedules (today and tomorrow), fare rules, platforms, and 3 demo users. It **deletes the existing demo database**, so stop the server first. All demo passwords are `demo123`.

| Role | Email |
|---|---|
| Admin | `admin@railway.test` |
| Staff | `staff@railway.test` |
| Passenger | `passenger@railway.test` |

## Features by role

### Shared

- `/` landing page; logging in redirects to the dashboard for your role.
- `/register` creates a **passenger** account: name, email, phone, password confirmation, minimum 6-character password, basic email/phone validation, and duplicate email/phone checks. Passwords are stored as hashes.
- `/login`, `/logout`; inactive accounts cannot log in.

### Passenger

- **Profile** (`/passenger/profile`) — view your account details.
- **Search trains** (`/passenger/search-trains`) — filter by source, destination, and journey date; shows departure/arrival (estimated times when available) and schedule status. Only active trains and non-cancelled schedules appear, and the boarding stop must come before the destination.
- **Book tickets** (`/passenger/book-ticket`) — pick a schedule, boarding and alighting stops, coach type, and 1–6 passengers with names, ages, and genders. Fare = base fare + per-km rate × journey distance × passenger count, using the fare rule effective on the journey date. Stop order, distance, and passenger data are validated.
- **Payment portal** (`/passenger/create-booking` → `/passenger/payment`) — the pending booking is held in the session and a UPI QR for `saralaya@upi` is generated with the fare and a transaction reference. **Nothing is stored until you click “I have paid — continue”**, which creates the booking, one passenger row and QR token per traveller (valid for 2 hours), a payment record, and a ticket. Payment is simulated; no money moves.
- **My Bookings** (`/passenger/my-bookings`) — all bookings with PNR, train, route, date, fare, payment status, and a QR pass for each passenger. `/passenger/my-qr-ticket` redirects here.
- **Download PDF** (`/passenger/booking/<id>/pdf`) — booking details plus the first passenger's QR; only for bookings with successful payment.
- **Live train tracking** (`/passenger/live-trains`) — today's and tomorrow's active schedules with computed status (`SCHEDULED`, `RUNNING`, `DELAYED`, `COMPLETED`), next stop, and full stop list. Refreshes automatically every 15 seconds, with a manual Refresh button. Admin delay records shift estimated times and change the status.
- **Journey history** (`/passenger/journey-history`) — past bookings ordered by journey date.
- **Submit complaint** (`/passenger/submit-complaint`) — complaint type, description, and optional booking/station references (validated against your own bookings).

### Admin

- **Dashboard** (`/admin/dashboard`) — counts of users, trains, stations, and bookings, with links to every management module.
- **Users** (`/admin/users`) — view all registered accounts.
- **Trains** (`/admin/trains`) — add, edit, and activate/deactivate trains (number, name, type, route, capacity).
- **Stations** (`/admin/stations`) — add, edit, and activate/deactivate stations (code, name, city, state, type).
- **Routes and stops** (`/admin/routes`, `/admin/route-stops`) — manage source/destination and distance; add, edit, and delete intermediate stops. Stops used by a schedule cannot be deleted.
- **Schedules** (`/admin/schedules`) — add schedules for active trains and set status (`SCHEDULED`, `DELAYED`, `CANCELLED`, `COMPLETED`).
- **Schedule stops** (`/admin/schedule-stops`) — set arrival/departure times and platform for each stop.
- **Platform allocations** (`/admin/platform-allocations`) — assign a platform and time window to a schedule stop. Rejects inactive/wrong-station platforms, overlapping allocations, and duplicate allocations; supports editing and cancellation.
- **Platform conflicts** (`/admin/platform-conflicts`) — review recorded conflicts between two allocations and mark them resolved with notes.
- **Delays** (`/admin/delays`, `/admin/delays/add`) — record minutes and reason at a station on that train's route; moves a `SCHEDULED` train to `DELAYED`, which passengers see in live tracking.
- **Complaints** (`/admin/complaints`) — review complaints and set status (`OPEN`, `IN_PROGRESS`, `RESOLVED`, `REJECTED`); resolving stamps the time.

### Staff

- **Dashboard** (`/staff/dashboard`) — counts of verifications, entries, exits, and platform access grants.
- **Verify ticket** (`/staff/verify-ticket`) — look up a passenger QR token; checks the token is active and unexpired and that the booking and passenger are confirmed.
- **Entry / exit** (`/staff/entry`, `/staff/exit`) — scan a token at a station and log `ALLOWED` or `DENIED` with the staff member and station.
- **Platform access** (`/staff/platform-access`) — scan a token against an active platform and log the decision.

All admin and staff routes require login and the matching role, and staff routes additionally require an active staff record; unauthorized requests return 403.

## Configuration

`config.py` reads two optional environment variables:

- `DATABASE_URL` — defaults to `sqlite:///railsync.db` (file at `instance/railsync.db`).
- `SECRET_KEY` — defaults to `local-demo-secret-change-me`; **set a real value outside the demo**.

## Project layout

- `app.py` — Flask app factory, blueprint registration, landing page.
- `config.py`, `extensions.py`, `models/` — config, shared extensions, SQLAlchemy user model.
- `routes/` — `auth.py` (register/login), `users.py` (admin users + passenger portal), `admin.py` (admin management), `staff.py` (gate operations).
- `templates/`, `schema.sql`, `seed.py` — UI, SQLite schema, demo data.
- `tests/smoke.py` — end-to-end check covering registration, login, UPI QR, deferred booking, merged booking/QR page, PDF, complaints, staff verification, live tracking, and delays.

## Check

After seeding:

```powershell
.\.venv\Scripts\python tests\smoke.py
```

## Demo limitations

- Payments are simulated: the UPI QR is generated from the UPI ID and no real transaction or money transfer occurs.
- QR tokens expire 2 hours after confirmation.
- The seeded database is local demo data; `seed.py` overwrites it on every run.
- The landing page advertises crowd monitoring, but no crowd-analytics screen is implemented in this version.
