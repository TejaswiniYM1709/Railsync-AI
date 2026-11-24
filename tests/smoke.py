"""Small end-to-end check: python tests/smoke.py (run seed.py first)."""
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import app

DB = Path(__file__).resolve().parents[1] / "instance" / "railsync.db"


def count(table):
    with sqlite3.connect(DB) as con:
        return con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def main():
    client = app.test_client()

    assert client.get("/login").status_code == 200
    assert client.get("/register").status_code == 200
    assert client.post("/login", data={}).status_code == 200

    response = client.post(
        "/register",
        data={
            "full_name": "Smoke Test",
            "email": "smoke@railway.test",
            "password": "secret123",
            "confirm_password": "secret123",
        },
        follow_redirects=True,
    )
    assert b"Registration successful" in response.data
    duplicate = client.post(
        "/register",
        data={
            "full_name": "Smoke Test",
            "email": "smoke@railway.test",
            "password": "secret123",
            "confirm_password": "secret123",
        },
        follow_redirects=True,
    )
    assert b"already exists" in duplicate.data

    assert client.post(
        "/login",
        data={"email": "Passenger@Railway.Test", "password": "demo123"},
        follow_redirects=True,
    ).status_code == 200
    assert b"Live Train Tracking" in client.get("/passenger/dashboard").data
    live = client.get("/passenger/live-trains")
    assert live.status_code == 200
    assert live.data.count(b"<tr>") >= 12
    assert b"Refresh" in live.data

    with sqlite3.connect(DB) as con:
        schedule_id = con.execute("SELECT schedule_id FROM schedules LIMIT 1").fetchone()[0]
        stops = [
            row[0]
            for row in con.execute(
                "SELECT schedule_stop_id FROM schedule_stops WHERE schedule_id = ? ORDER BY schedule_stop_id",
                (schedule_id,),
            )
        ]

    before = count("bookings")
    for coach_type in ("SLEEPER", "AC", "CHAIR_CAR", "GENERAL"):
        payment = client.post(
            "/passenger/create-booking",
            data={
                "schedule_id": schedule_id,
                "boarding_stop_id": stops[0],
                "alighting_stop_id": stops[-1],
                "coach_type": coach_type,
                "passenger_name[]": "Smoke Passenger",
                "age[]": "25",
                "gender[]": "M",
            },
        )
        assert payment.status_code == 200, f"coach type {coach_type} failed"
        assert b"saralaya@upi" in payment.data
        assert b"data:image/png;base64" in payment.data
        assert count("bookings") == before, "booking created before payment confirmation"

    confirmation = client.post("/passenger/confirm-payment")
    assert b"Payment Status: SUCCESS" in confirmation.data
    assert b"View Booking & QR" in confirmation.data
    assert b"Download PDF" in confirmation.data
    assert count("bookings") == before + 1
    assert count("qr_tokens") >= 1

    with sqlite3.connect(DB) as con:
        booking_id = con.execute("SELECT MAX(booking_id) FROM bookings").fetchone()[0]
        token_reference = con.execute(
            """
            SELECT qt.token_reference
            FROM qr_tokens qt
            JOIN booking_passengers bp
                ON qt.booking_passenger_id = bp.booking_passenger_id
            WHERE bp.booking_id = ?
            ORDER BY qt.token_id DESC
            LIMIT 1
            """,
            (booking_id,),
        ).fetchone()[0]

    ticket_page = client.get("/passenger/my-qr-ticket")
    assert ticket_page.status_code == 302
    assert "/passenger/my-bookings" in ticket_page.headers["Location"]

    bookings_page = client.get("/passenger/my-bookings")
    assert b"Passenger QR Tickets" in bookings_page.data
    assert b"Download PDF" in bookings_page.data
    assert b"Copy token" in bookings_page.data
    assert b"data:image/png;base64" in bookings_page.data
    assert token_reference.encode() in bookings_page.data

    pdf = client.get(f"/passenger/booking/{booking_id}/pdf")
    assert pdf.status_code == 200
    assert pdf.data.startswith(b"%PDF")
    assert b"/Subtype /Image" in pdf.data
    assert "application/pdf" in pdf.headers["Content-Type"]

    other = app.test_client()
    assert other.post(
        "/login",
        data={"email": "smoke@railway.test", "password": "secret123"},
        follow_redirects=True,
    ).status_code == 200
    assert other.get(f"/passenger/booking/{booking_id}/pdf").status_code == 403

    complaints_before = count("complaints")
    complaint = client.post(
        "/passenger/submit-complaint",
        data={
            "complaint_type": "Train Delay",
            "description": "Smoke test complaint",
            "booking_id": booking_id,
            "station_id": 1,
        },
        follow_redirects=True,
    )
    assert b"Complaint submitted successfully!" in complaint.data
    assert b"Unable to submit complaint" not in complaint.data
    assert count("complaints") == complaints_before + 1

    client.get("/logout")
    assert client.post(
        "/login",
        data={"email": "staff@railway.test", "password": "demo123"},
        follow_redirects=True,
    ).status_code == 200
    verified = client.post(
        "/staff/verify-ticket",
        data={"qr_token": token_reference},
        follow_redirects=True,
    )
    assert b"Ticket verified successfully!" in verified.data

    with sqlite3.connect(DB) as con:
        delayed_schedule = con.execute(
            "SELECT schedule_id FROM schedules ORDER BY journey_date DESC LIMIT 1"
        ).fetchone()[0]
        delayed_station = con.execute(
            """
            SELECT rs.station_id
            FROM schedule_stops ss
            JOIN route_stops rs ON ss.route_stop_id = rs.route_stop_id
            WHERE ss.schedule_id = ?
            ORDER BY rs.stop_number
            LIMIT 1
            """,
            (delayed_schedule,),
        ).fetchone()[0]

    client.get("/logout")
    assert client.post(
        "/login",
        data={"email": "admin@railway.test", "password": "demo123"},
        follow_redirects=True,
    ).status_code == 200
    delay_page = client.post(
        "/admin/delays/add",
        data={
            "schedule_id": delayed_schedule,
            "station_id": delayed_station,
            "delay_minutes": 20,
            "reason": "Smoke test",
        },
        follow_redirects=True,
    )
    assert b"delay recorded successfully" in delay_page.data

    client.get("/logout")
    assert client.post(
        "/login",
        data={"email": "passenger@railway.test", "password": "demo123"},
        follow_redirects=True,
    ).status_code == 200
    live_after_delay = client.get("/passenger/live-trains")
    assert b"+20 min" in live_after_delay.data

    print("smoke ok: registration, login, UPI QR, deferred booking, merged booking/QR, PDF with QR, complaint, staff verify, live tracking, delay")


if __name__ == "__main__":
    main()
