# RailSync local demo

Run the app locally with SQLite. No MySQL install or `.env` is needed.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python seed.py
```

`seed.py` recreates `instance/railsync.db` with:

- 12 trains, 12 stations, 24 schedules (today and tomorrow)
- fares, platforms and 3 demo users
- password for all demo users: `demo123`

## Run

```powershell
.\.venv\Scripts\python app.py
```

Open http://127.0.0.1:5000/login.

Demo accounts:

| Role | Email |
|---|---|
| Admin | `admin@railway.test` |
| Staff | `staff@railway.test` |
| Passenger | `passenger@railway.test` |

## Demo the features

1. **Register:** open `/register`, create a passenger account, then log in.
2. **Payment portal:** as a passenger, book a ticket. The QR page shows `saralaya@upi`, the fare and a transaction reference. Click **I have paid — continue** to finish the booking. No booking is stored before that click.
3. **Live tracking:** open **Live Train Tracking** from the passenger dashboard. It auto-refreshes every 15 seconds, or press **Refresh**. As admin, add a delay at `/admin/delays/add`; the tracking page then shows the delay.
4. **Ticket QR:** open **My Bookings**. Each paid booking shows passenger QR passes encoding their token references; staff can verify them at `/staff/verify-ticket`.
5. **PDF:** use **Download PDF** on any paid booking. The PDF includes the booking details and the first passenger QR.

The payment QR is generated from the UPI ID, so no QR image file is needed. The payment is simulated; no money moves.

## Check

```powershell
.\.venv\Scripts\python tests\smoke.py
```
