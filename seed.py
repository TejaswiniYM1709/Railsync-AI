"""Build a fresh local SQLite demo database: python seed.py"""
import sqlite3
from datetime import date, timedelta
from pathlib import Path

from werkzeug.security import generate_password_hash

ROOT = Path(__file__).resolve().parent
DB = ROOT / "instance" / "railsync.db"
DB.parent.mkdir(parents=True, exist_ok=True)
try:
    DB.unlink(missing_ok=True)  # local demo database only
except PermissionError:
    raise SystemExit("Stop the Flask server before running seed.py.")

con = sqlite3.connect(DB)
con.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))

stations = [
    ("NDLS", "New Delhi", "Delhi", "Delhi", "JUNCTION"),
    ("JP", "Jaipur Junction", "Jaipur", "Rajasthan", "JUNCTION"),
    ("ADI", "Ahmedabad Junction", "Ahmedabad", "Gujarat", "JUNCTION"),
    ("MMT", "Mumbai Central", "Mumbai", "Maharashtra", "TERMINAL"),
    ("PNBE", "Patna Junction", "Patna", "Bihar", "JUNCTION"),
    ("HWH", "Howrah Junction", "Kolkata", "West Bengal", "JUNCTION"),
    ("BBS", "Bhubaneswar", "Bhubaneswar", "Odisha", "STATION"),
    ("MAS", "Chennai Central", "Chennai", "Tamil Nadu", "TERMINAL"),
    ("SBC", "KSR Bengaluru", "Bengaluru", "Karnataka", "TERMINAL"),
    ("ERS", "Ernakulam Junction", "Kochi", "Kerala", "JUNCTION"),
    ("PUNE", "Pune Junction", "Pune", "Maharashtra", "JUNCTION"),
    ("AGC", "Agra Cantt", "Agra", "Uttar Pradesh", "JUNCTION"),
]
con.executemany(
    "INSERT INTO stations (station_code, station_name, city, state, station_type) VALUES (?,?,?,?,?)",
    stations,
)

trains = [
    ("12001", "Shatabdi Express", "SUPERFAST"),
    ("12951", "Mumbai Rajdhani", "SUPERFAST"),
    ("12301", "Howrah Rajdhani", "SUPERFAST"),
    ("12621", "Tamil Nadu Express", "SUPERFAST"),
    ("12213", "Deccan Queen", "SUPERFAST"),
    ("12471", "Swaraj Express", "EXPRESS"),
    ("12137", "Punjab Mail", "EXPRESS"),
    ("12809", "Mumbai Mail", "EXPRESS"),
    ("12627", "Karnataka Express", "EXPRESS"),
    ("12217", "Kerala Sampark", "SUPERFAST"),
    ("19019", "Dehradun Express", "EXPRESS"),
    ("12009", "Shatabdi Local", "LOCAL"),
]

today = date.today()
for i, (number, name, ttype) in enumerate(trains):
    stops = [i % len(stations), (i + 2) % len(stations), (i + 5) % len(stations), (i + 8) % len(stations)]
    station_ids = [s + 1 for s in stops]
    distance = 420 + i * 35
    cur = con.execute(
        "INSERT INTO routes (route_name, source_station_id, destination_station_id, distance_km) VALUES (?,?,?,?)",
        (f"{name} Route", station_ids[0], station_ids[-1], distance),
    )
    route_id = cur.lastrowid
    for n, sid in enumerate(station_ids):
        con.execute(
            "INSERT INTO route_stops (route_id, station_id, stop_number, distance_from_source) VALUES (?,?,?,?)",
            (route_id, sid, n + 1, round(distance * n / (len(station_ids) - 1), 2)),
        )
    con.execute(
        "INSERT INTO trains (train_number, train_name, train_type, route_id, total_capacity, operating_status) VALUES (?,?,?,?,?,?)",
        (number, name, ttype, route_id, 1000, "ACTIVE"),
    )

for train_id in range(1, len(trains) + 1):
    for offset in (0, 1):
        journey = today + timedelta(days=offset)
        cur = con.execute(
            "INSERT INTO schedules (train_id, journey_date, schedule_status) VALUES (?,?,?)",
            (train_id, journey.isoformat(), "SCHEDULED"),
        )
        schedule_id = cur.lastrowid
        stop_rows = con.execute(
            "SELECT route_stop_id FROM route_stops WHERE route_id = (SELECT route_id FROM trains WHERE train_id = ?) ORDER BY stop_number",
            (train_id,),
        ).fetchall()
        for n, (route_stop_id,) in enumerate(stop_rows):
            hour = 6 + (n * 2 + train_id) % 14
            departure = f"{hour:02d}:{15 * (train_id % 4):02d}:00"
            arrival = f"{hour:02d}:{(15 * (train_id % 4) + 55) % 60:02d}:00"
            con.execute(
                "INSERT INTO schedule_stops (schedule_id, route_stop_id, scheduled_arrival, scheduled_departure) VALUES (?,?,?,?)",
                (schedule_id, route_stop_id, arrival, departure),
            )

for ttype, base in (("SUPERFAST", 120), ("EXPRESS", 90), ("LOCAL", 40)):
    for coach, extra in (("GENERAL", 0), ("SLEEPER", 50), ("AC", 350), ("CHAIR_CAR", 650)):
        con.execute(
            "INSERT INTO fare_rules (train_type, coach_type, base_fare, fare_per_km, effective_from) VALUES (?,?,?,?,?)",
            (ttype, coach, base + extra, 0.65 if ttype != "LOCAL" else 0.4, "2025-01-01"),
        )

for name, email, phone, role in [
    ("Demo Admin", "admin@railway.test", "9000000001", "ADMIN"),
    ("Demo Staff", "staff@railway.test", "9000000002", "STAFF"),
    ("Demo Passenger", "passenger@railway.test", "9000000003", "PASSENGER"),
]:
    cur = con.execute(
        "INSERT INTO users (full_name, email, password_hash, phone, role, account_status) VALUES (?,?,?,?,?,?)",
        (name, email, generate_password_hash("demo123"), phone, role, "ACTIVE"),
    )
    if role == "STAFF":
        con.execute(
            "INSERT INTO staff (user_id, station_id, employment_status) VALUES (?,?,?)",
            (cur.lastrowid, 1, "ACTIVE"),
        )

for sid in range(1, len(stations) + 1):
    for n in (1, 2):
        con.execute(
            "INSERT INTO platforms (station_id, platform_number, platform_status) VALUES (?,?,?)",
            (sid, str(n), "ACTIVE"),
        )

con.commit()
print(
    f"Seeded {DB}: {len(stations)} stations, {len(trains)} trains, "
    f"{len(trains) * 2} schedules, 3 users (password: demo123)"
)
con.close()
