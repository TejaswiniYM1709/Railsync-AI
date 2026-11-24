import base64
import io
import uuid
from datetime import date, datetime, time, timedelta

import qrcode
from flask import Blueprint, render_template, abort, request, redirect, url_for, flash, session, send_file
from flask_login import login_required, current_user
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from sqlalchemy import text

from extensions import db
from models import User

UPI_ID = "saralaya@upi"
UPI_NAME = "Saralaya"


def _qr_png(value):
    image = qrcode.make(value)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def _qr_image(value):
    return "data:image/png;base64," + base64.b64encode(_qr_png(value).getvalue()).decode()


def _upi_qr(amount, reference):
    uri = (
        f"upi://pay?pa={UPI_ID}&pn={UPI_NAME}"
        f"&am={float(amount):.2f}&cu=INR&tn={reference}"
    )
    return _qr_image(uri)


# ==========================================
# ADMIN USER MANAGEMENT
# ==========================================

users_bp = Blueprint("users", __name__, url_prefix="/admin/users")


@users_bp.route("/")
@login_required
def list_users():

    if current_user.role != "ADMIN":
        abort(403)

    all_users = User.query.order_by(User.user_id).all()

    return render_template("users.html", users=all_users)


# ==========================================
# PASSENGER PORTAL
# ==========================================

passenger_bp = Blueprint(
    "passenger",
    __name__,
    url_prefix="/passenger"
)


# ==========================================
# PASSENGER DASHBOARD
# ==========================================

@passenger_bp.route("/dashboard")
@login_required
def dashboard():

    if current_user.role != "PASSENGER":
        abort(403)

    return render_template("passenger_dashboard.html")


# ==========================================
# PASSENGER PROFILE
# ==========================================

@passenger_bp.route("/profile")
@login_required
def profile():

    if current_user.role != "PASSENGER":
        abort(403)

    return render_template("profile.html")


# ==========================================
# SEARCH TRAINS
# ==========================================

@passenger_bp.route("/search-trains", methods=["GET", "POST"])
@login_required
def search_trains():

    if current_user.role != "PASSENGER":
        abort(403)

    stations = db.session.execute(text("""
        SELECT station_id, station_name
        FROM stations
        WHERE is_active = 1
        ORDER BY station_name
    """)).mappings().all()

    trains = []
    searched = False

    if request.method == "POST":

        source = request.form.get("source")
        destination = request.form.get("destination")
        journey_date = request.form.get("journey_date")

        searched = True

        if source and destination and journey_date and source != destination:

            trains = db.session.execute(text("""
                SELECT
                    t.train_number,
                    t.train_name,
                    s.journey_date,
                    COALESCE(
                        ss1.estimated_departure,
                        ss1.scheduled_departure
                    ) AS departure,
                    COALESCE(
                        ss2.estimated_arrival,
                        ss2.scheduled_arrival
                    ) AS arrival,
                    s.schedule_status

                FROM schedules s

                JOIN trains t
                    ON s.train_id = t.train_id

                JOIN schedule_stops ss1
                    ON s.schedule_id = ss1.schedule_id

                JOIN route_stops rs1
                    ON ss1.route_stop_id = rs1.route_stop_id

                JOIN schedule_stops ss2
                    ON s.schedule_id = ss2.schedule_id

                JOIN route_stops rs2
                    ON ss2.route_stop_id = rs2.route_stop_id

                WHERE rs1.station_id = :source
                  AND rs2.station_id = :destination
                  AND rs1.stop_number < rs2.stop_number
                  AND s.journey_date = :journey_date
                  AND s.schedule_status != 'CANCELLED'
                  AND t.operating_status = 'ACTIVE'

                ORDER BY departure

            """), {
                "source": source,
                "destination": destination,
                "journey_date": journey_date
            }).mappings().all()

    return render_template(
        "search_trains.html",
        stations=stations,
        trains=trains,
        searched=searched
    )


# ==========================================
# BOOK TICKET
# ==========================================

@passenger_bp.route("/book-ticket")
@login_required
def book_ticket():

    if current_user.role != "PASSENGER":
        abort(403)

    schedules = db.session.execute(text("""
        SELECT
            s.schedule_id,
            s.journey_date,
            t.train_number,
            t.train_name,
            t.train_type

        FROM schedules s

        JOIN trains t
            ON s.train_id = t.train_id

        WHERE s.schedule_status IN ('SCHEDULED', 'DELAYED')
          AND t.operating_status = 'ACTIVE'

        ORDER BY s.journey_date

    """)).mappings().all()

    stops = db.session.execute(text("""
        SELECT
            ss.schedule_stop_id,
            ss.schedule_id,
            st.station_name,
            rs.stop_number,
            rs.distance_from_source

        FROM schedule_stops ss

        JOIN route_stops rs
            ON ss.route_stop_id = rs.route_stop_id

        JOIN stations st
            ON rs.station_id = st.station_id

        ORDER BY ss.schedule_id, rs.stop_number

    """)).mappings().all()

    return render_template(
        "book_ticket.html",
        schedules=schedules,
        stops=stops
    )


# ==========================================
# CREATE BOOKING
# ==========================================

@passenger_bp.route("/create-booking", methods=["POST"])
@login_required
def create_booking():

    if current_user.role != "PASSENGER":
        abort(403)

    try:

        schedule_id = int(request.form.get("schedule_id"))
        boarding_id = int(request.form.get("boarding_stop_id"))
        alighting_id = int(request.form.get("alighting_stop_id"))

        coach_type = request.form.get("coach_type")

        names = request.form.getlist("passenger_name[]")
        ages = request.form.getlist("age[]")
        genders = request.form.getlist("gender[]")

        if not names or len(names) > 6:
            raise ValueError("Enter between 1 and 6 passengers.")

        if not (len(names) == len(ages) == len(genders)):
            raise ValueError("Passenger details are incomplete.")

        if any(not name.strip() for name in names):
            raise ValueError("Passenger names cannot be empty.")

        if any(
            not age.isdigit() or not 1 <= int(age) <= 120
            for age in ages
        ):
            raise ValueError("Enter valid passenger ages.")

        # Fetch selected schedule stops

        stops = db.session.execute(text("""
            SELECT
                ss.schedule_stop_id,
                ss.schedule_id,
                rs.stop_number,
                rs.distance_from_source,
                t.train_type,
                s.journey_date

            FROM schedule_stops ss

            JOIN route_stops rs
                ON ss.route_stop_id = rs.route_stop_id

            JOIN schedules s
                ON ss.schedule_id = s.schedule_id

            JOIN trains t
                ON s.train_id = t.train_id

            WHERE ss.schedule_id = :schedule_id
              AND ss.schedule_stop_id IN (:boarding, :alighting)

        """), {
            "schedule_id": schedule_id,
            "boarding": boarding_id,
            "alighting": alighting_id
        }).mappings().all()

        if len(stops) != 2:
            raise ValueError("Invalid boarding or destination station.")

        # Identify boarding and destination stops

        boarding = next(
            s for s in stops
            if s["schedule_stop_id"] == boarding_id
        )

        destination = next(
            s for s in stops
            if s["schedule_stop_id"] == alighting_id
        )

        if boarding["stop_number"] >= destination["stop_number"]:
            raise ValueError(
                "Boarding station must come before destination."
            )

        # Calculate journey distance

        distance = (
            float(destination["distance_from_source"])
            - float(boarding["distance_from_source"])
        )

        if distance <= 0:
            raise ValueError("Invalid journey distance.")

        # Fetch fare rules

        fare = db.session.execute(text("""
            SELECT
                base_fare,
                fare_per_km

            FROM fare_rules

            WHERE train_type = :train_type
              AND coach_type = :coach_type
              AND effective_from <= :journey_date
              AND (
                  effective_to IS NULL
                  OR effective_to >= :journey_date
              )

            LIMIT 1

        """), {
            "train_type": boarding["train_type"],
            "coach_type": coach_type,
            "journey_date": boarding["journey_date"]
        }).mappings().first()

        if not fare:
            raise ValueError(
                "Fare is unavailable for this coach type."
            )

        total_fare = (
            float(fare["base_fare"])
            + float(fare["fare_per_km"]) * distance
        ) * len(names)

        transaction_ref = "TXN" + uuid.uuid4().hex[:12].upper()
        session["pending_booking"] = {
            "schedule_id": schedule_id,
            "boarding": boarding_id,
            "alighting": alighting_id,
            "names": names,
            "ages": ages,
            "genders": genders,
            "fare": float(total_fare),
            "reference": transaction_ref,
        }

        return render_template(
            "payment.html",
            amount=total_fare,
            reference=transaction_ref,
            qr_data=_upi_qr(total_fare, transaction_ref),
        )

    except Exception as e:

        db.session.rollback()

        flash(str(e), "danger")

        return redirect(url_for("passenger.book_ticket"))


@passenger_bp.route("/confirm-payment", methods=["POST"])
@login_required
def confirm_payment():

    if current_user.role != "PASSENGER":
        abort(403)

    data = session.get("pending_booking")
    if not data:
        flash("Payment session expired. Please start your booking again.", "warning")
        return redirect(url_for("passenger.book_ticket"))

    try:
        pnr = "RS" + uuid.uuid4().hex[:10].upper()
        ticket_ref = "TKT" + uuid.uuid4().hex[:12].upper()

        result = db.session.execute(text("""
            INSERT INTO bookings
            (
                pnr_number, user_id, schedule_id,
                boarding_schedule_stop_id, alighting_schedule_stop_id,
                total_passengers, total_fare, booking_status
            )
            VALUES
            (
                :pnr, :user_id, :schedule_id, :boarding, :alighting,
                :count, :fare, 'CONFIRMED'
            )
        """), {
            "pnr": pnr,
            "user_id": current_user.user_id,
            "schedule_id": data["schedule_id"],
            "boarding": data["boarding"],
            "alighting": data["alighting"],
            "count": len(data["names"]),
            "fare": data["fare"],
        })
        booking_id = result.lastrowid

        for name, age, gender in zip(data["names"], data["ages"], data["genders"]):
            passenger = db.session.execute(text("""
                INSERT INTO booking_passengers
                (booking_id, passenger_name, age, gender, passenger_status)
                VALUES (:booking_id, :name, :age, :gender, 'CONFIRMED')
            """), {
                "booking_id": booking_id,
                "name": name.strip(),
                "age": int(age),
                "gender": gender,
            })
            db.session.execute(text("""
                INSERT INTO qr_tokens
                (booking_passenger_id, token_reference, expiry_time, token_status)
                VALUES (:passenger, :reference, :expiry, 'ACTIVE')
            """), {
                "passenger": passenger.lastrowid,
                "reference": "QRT" + uuid.uuid4().hex[:12].upper(),
                "expiry": datetime.now() + timedelta(hours=2),
            })

        db.session.execute(text("""
            INSERT INTO payments
            (booking_id, transaction_reference, payment_method, amount, payment_status)
            VALUES (:booking_id, :reference, 'UPI', :amount, 'SUCCESS')
        """), {
            "booking_id": booking_id,
            "reference": data["reference"],
            "amount": data["fare"],
        })

        db.session.execute(text("""
            INSERT INTO tickets
            (booking_id, ticket_reference, ticket_status)
            VALUES (:booking_id, :reference, 'ACTIVE')
        """), {
            "booking_id": booking_id,
            "reference": ticket_ref,
        })

        db.session.commit()
        session.pop("pending_booking", None)

        return render_template(
            "booking_confirmation.html",
            booking_id=booking_id,
            pnr=pnr,
            ticket_ref=ticket_ref,
            total_fare=data["fare"],
            names=data["names"],
        )

    except Exception as e:

        db.session.rollback()

        flash(str(e), "danger")

        return redirect(url_for("passenger.book_ticket"))


def _at(journey_date, clock, delay=0):
    if not clock:
        return None
    try:
        parsed_time = time.fromisoformat(str(clock)[:8])
        parsed_date = date.fromisoformat(str(journey_date)[:10])
    except ValueError:
        return None
    return datetime.combine(parsed_date, parsed_time) + timedelta(minutes=delay)


@passenger_bp.route("/live-trains")
@login_required
def live_trains():

    if current_user.role != "PASSENGER":
        abort(403)

    today = date.today()
    rows = db.session.execute(text("""
        SELECT
            s.schedule_id,
            t.train_number,
            t.train_name,
            s.journey_date,
            s.schedule_status,
            (
                SELECT MAX(d.delay_minutes)
                FROM delay_records d
                WHERE d.schedule_id = s.schedule_id
            ) AS delay_minutes
        FROM schedules s
        JOIN trains t ON s.train_id = t.train_id
        WHERE t.operating_status = 'ACTIVE'
          AND s.journey_date BETWEEN :today AND :tomorrow
        ORDER BY s.journey_date, t.train_number
    """), {
        "today": today.isoformat(),
        "tomorrow": (today + timedelta(days=1)).isoformat(),
    }).mappings().all()

    now = datetime.now()
    trains = []

    for row in rows:
        stops = db.session.execute(text("""
            SELECT
                st.station_name,
                ss.scheduled_arrival,
                ss.scheduled_departure
            FROM schedule_stops ss
            JOIN route_stops rs ON ss.route_stop_id = rs.route_stop_id
            JOIN stations st ON rs.station_id = st.station_id
            WHERE ss.schedule_id = :schedule_id
            ORDER BY rs.stop_number
        """), {"schedule_id": row["schedule_id"]}).mappings().all()

        delay = int(row["delay_minutes"] or 0)
        times = [
            (
                stop["station_name"],
                _at(row["journey_date"], stop["scheduled_arrival"], delay),
                _at(row["journey_date"], stop["scheduled_departure"], delay),
            )
            for stop in stops
        ]
        future = [item for item in times if item[2] and item[2] > now]
        if delay and times and (times[-1][1] is None or now < times[-1][1]):
            status = "DELAYED"
        elif times and times[-1][1] and now > times[-1][1]:
            status = "COMPLETED"
        elif times and now >= times[0][2]:
            status = "RUNNING"
        else:
            status = "SCHEDULED"

        trains.append({
            "train_number": row["train_number"],
            "train_name": row["train_name"],
            "journey_date": row["journey_date"],
            "status": status,
            "delay": delay,
            "next_stop": future[0][0] if future else "—",
            "stops": " → ".join(stop["station_name"] for stop in stops),
        })

    return render_template("live_trains.html", trains=trains, updated=now)


# ==========================================
# MY BOOKINGS
# ==========================================

@passenger_bp.route("/my-bookings")
@login_required
def my_bookings():

    if current_user.role != "PASSENGER":
        abort(403)

    bookings = db.session.execute(text("""
        SELECT
            b.booking_id,
            b.pnr_number,
            b.booking_date,
            b.total_passengers,
            b.total_fare,
            b.booking_status,
            p.payment_status,

            t.train_number,
            t.train_name,

            s.journey_date,

            st1.station_name AS source_station,
            st2.station_name AS destination_station

        FROM bookings b

        JOIN schedules s
            ON b.schedule_id = s.schedule_id

        JOIN trains t
            ON s.train_id = t.train_id

        JOIN schedule_stops ss1
            ON b.boarding_schedule_stop_id = ss1.schedule_stop_id

        JOIN route_stops rs1
            ON ss1.route_stop_id = rs1.route_stop_id

        JOIN stations st1
            ON rs1.station_id = st1.station_id

        JOIN schedule_stops ss2
            ON b.alighting_schedule_stop_id = ss2.schedule_stop_id

        JOIN route_stops rs2
            ON ss2.route_stop_id = rs2.route_stop_id

        JOIN stations st2
            ON rs2.station_id = st2.station_id

        LEFT JOIN payments p
            ON p.booking_id = b.booking_id

        WHERE b.user_id = :user_id

        ORDER BY b.booking_date DESC

    """), {
        "user_id": current_user.user_id
    }).mappings().all()

    tickets = db.session.execute(text("""
        SELECT
            bp.booking_id,
            bp.passenger_name,
            bp.age,
            bp.gender,
            qt.token_reference,
            qt.expiry_time,
            qt.token_status

        FROM booking_passengers bp

        JOIN bookings b
            ON bp.booking_id = b.booking_id

        JOIN qr_tokens qt
            ON qt.booking_passenger_id = bp.booking_passenger_id

        WHERE b.user_id = :user_id

        ORDER BY bp.booking_passenger_id

    """), {
        "user_id": current_user.user_id
    }).mappings().all()

    tickets_by_booking = {}
    for ticket in tickets:
        row = dict(ticket)
        row["qr_data"] = _qr_image(row["token_reference"])
        tickets_by_booking.setdefault(row["booking_id"], []).append(row)

    return render_template(
        "my_bookings.html",
        bookings=bookings,
        tickets_by_booking=tickets_by_booking
    )


@passenger_bp.route("/booking/<int:booking_id>/pdf")
@login_required
def download_booking_pdf(booking_id):

    if current_user.role != "PASSENGER":
        abort(403)

    booking = db.session.execute(text("""
        SELECT
            b.pnr_number,
            b.booking_date,
            b.total_passengers,
            b.total_fare,
            b.booking_status,

            t.train_number,
            t.train_name,
            s.journey_date,

            st1.station_name AS boarding_station,
            st2.station_name AS destination_station,

            p.transaction_reference,
            p.payment_status,
            ti.ticket_reference

        FROM bookings b

        JOIN schedules s
            ON b.schedule_id = s.schedule_id

        JOIN trains t
            ON s.train_id = t.train_id

        JOIN schedule_stops ss1
            ON b.boarding_schedule_stop_id = ss1.schedule_stop_id

        JOIN route_stops rs1
            ON ss1.route_stop_id = rs1.route_stop_id

        JOIN stations st1
            ON rs1.station_id = st1.station_id

        JOIN schedule_stops ss2
            ON b.alighting_schedule_stop_id = ss2.schedule_stop_id

        JOIN route_stops rs2
            ON ss2.route_stop_id = rs2.route_stop_id

        JOIN stations st2
            ON rs2.station_id = st2.station_id

        LEFT JOIN payments p
            ON p.booking_id = b.booking_id

        LEFT JOIN tickets ti
            ON ti.booking_id = b.booking_id

        WHERE b.booking_id = :booking_id
          AND b.user_id = :user_id

        LIMIT 1
    """), {
        "booking_id": booking_id,
        "user_id": current_user.user_id
    }).mappings().first()

    if not booking or booking["payment_status"] != "SUCCESS":
        abort(403)

    passengers = db.session.execute(text("""
        SELECT
            bp.passenger_name,
            bp.age,
            bp.gender,
            qt.token_reference
        FROM booking_passengers bp
        LEFT JOIN qr_tokens qt
            ON qt.booking_passenger_id = bp.booking_passenger_id
        WHERE bp.booking_id = :booking_id
        ORDER BY bp.booking_passenger_id
    """), {"booking_id": booking_id}).mappings().all()

    output = io.BytesIO()
    pdf = canvas.Canvas(output, pagesize=A4)
    height = A4[1]
    y = height - 60

    def line(label, value):
        nonlocal y
        if y < 60:
            pdf.showPage()
            y = height - 60
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(55, y, f"{label}:")
        pdf.setFont("Helvetica", 10)
        pdf.drawString(160, y, str(value))
        y -= 18

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(55, y, "RailSync - Booking Details")

    first_token = next(
        (passenger["token_reference"] for passenger in passengers if passenger["token_reference"]),
        None,
    )
    if first_token:
        pdf.drawImage(ImageReader(_qr_png(first_token)), 440, height - 180, 90, 90)
        pdf.setFont("Helvetica", 8)
        pdf.drawCentredString(485, height - 192, "Scan at gate")

    y -= 34

    for label, value in (
        ("PNR", booking["pnr_number"]),
        ("Train", f"{booking['train_number']} - {booking['train_name']}"),
        ("Journey date", booking["journey_date"]),
        ("From", booking["boarding_station"]),
        ("To", booking["destination_station"]),
        ("Passengers", booking["total_passengers"]),
        ("Fare", f"INR {float(booking['total_fare']):.2f}"),
        ("Payment", f"{booking['payment_status']} ({booking['transaction_reference']})"),
        ("Ticket reference", booking["ticket_reference"]),
        ("Booking status", booking["booking_status"]),
        ("Booked at", booking["booking_date"]),
    ):
        line(label, value)

    y -= 10
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(55, y, "Passengers")
    y -= 22

    for index, passenger in enumerate(passengers, 1):
        line(
            f"{index}. {passenger['passenger_name']}",
            f"{passenger['age']} / {passenger['gender']} / {passenger['token_reference'] or '-'}",
        )

    pdf.save()
    output.seek(0)

    return send_file(
        output,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"RailSync_{booking['pnr_number']}.pdf",
    )


# ==========================================
# MY QR TICKET
# ==========================================

@passenger_bp.route("/my-qr-ticket")
@login_required
def my_qr_ticket():

    if current_user.role != "PASSENGER":
        abort(403)

    return redirect(url_for("passenger.my_bookings"))


@passenger_bp.route("/journey-history")
@login_required
def journey_history():

    if current_user.role != "PASSENGER":
        abort(403)

    journeys = db.session.execute(text("""
        SELECT
            b.pnr_number,
            t.train_number,
            t.train_name,
            s.journey_date,
            origin.station_name AS from_station,
            destination.station_name AS to_station,
            b.total_passengers,
            b.total_fare,
            b.booking_status
        FROM bookings b
        JOIN schedules s
            ON b.schedule_id = s.schedule_id
        JOIN trains t
            ON s.train_id = t.train_id
        JOIN schedule_stops boarding
            ON b.boarding_schedule_stop_id = boarding.schedule_stop_id
        JOIN route_stops origin_route
            ON boarding.route_stop_id = origin_route.route_stop_id
        JOIN stations origin
            ON origin_route.station_id = origin.station_id
        JOIN schedule_stops alighting
            ON b.alighting_schedule_stop_id = alighting.schedule_stop_id
        JOIN route_stops destination_route
            ON alighting.route_stop_id = destination_route.route_stop_id
        JOIN stations destination
            ON destination_route.station_id = destination.station_id
        WHERE b.user_id = :user_id
        ORDER BY s.journey_date DESC
    """), {"user_id": current_user.user_id}).mappings().all()

    return render_template(
        "journey_history.html",
        journeys=journeys
    )
@passenger_bp.route("/submit-complaint", methods=["GET", "POST"])
@login_required
def submit_complaint():

    if current_user.role != "PASSENGER":
        abort(403)

    if request.method == "POST":
        complaint_type = request.form.get("complaint_type", "").strip()
        description = request.form.get("description", "").strip()
        booking_id = request.form.get("booking_id") or None
        station_id = request.form.get("station_id") or None

        if not complaint_type or not description:
            flash("Please fill in all required fields.")
            return redirect(url_for("passenger.submit_complaint"))

        if booking_id:
            booking = db.session.execute(text("""
                SELECT booking_id
                FROM bookings
                WHERE booking_id = :booking_id
                  AND user_id = :user_id
            """), {
                "booking_id": booking_id,
                "user_id": current_user.user_id
            }).first()

            if not booking:
                flash("Invalid booking selected.")
                return redirect(url_for("passenger.submit_complaint"))

        if station_id:
            station = db.session.execute(text("""
                SELECT station_id
                FROM stations
                WHERE station_id = :station_id
            """), {"station_id": station_id}).first()

            if not station:
                flash("Invalid station selected.")
                return redirect(url_for("passenger.submit_complaint"))

        try:
            db.session.execute(text("""
                INSERT INTO complaints
                (user_id, booking_id, station_id,
                 complaint_type, description)
                VALUES
                (:user_id, :booking_id, :station_id,
                 :complaint_type, :description)
            """), {
                "user_id": current_user.user_id,
                "booking_id": booking_id,
                "station_id": station_id,
                "complaint_type": complaint_type,
                "description": description
            })

            db.session.commit()

            flash("Complaint submitted successfully!")
            return redirect(url_for("passenger.submit_complaint"))

        except Exception as e:
            db.session.rollback()
            flash("Unable to submit complaint. Please try again.")
            print("Complaint Error:", e)

    bookings = db.session.execute(text("""
        SELECT booking_id, pnr_number
        FROM bookings
        WHERE user_id = :user_id
        ORDER BY booking_date DESC
    """), {"user_id": current_user.user_id}).mappings().all()

    stations = db.session.execute(text("""
        SELECT station_id, station_name
        FROM stations
        WHERE is_active = 1
        ORDER BY station_name
    """)).mappings().all()

    return render_template(
        "submit_complaint.html",
        bookings=bookings,
        stations=stations
    )