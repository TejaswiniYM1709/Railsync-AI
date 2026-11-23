import uuid

from flask import Blueprint, render_template, abort, request, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import text

from extensions import db
from models import User


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

        # Generate booking references

        pnr = "RS" + uuid.uuid4().hex[:10].upper()

        transaction_ref = (
            "TXN" + uuid.uuid4().hex[:12].upper()
        )

        ticket_ref = (
            "TKT" + uuid.uuid4().hex[:12].upper()
        )

        # Insert booking

        result = db.session.execute(text("""
            INSERT INTO bookings
            (
                pnr_number,
                user_id,
                schedule_id,
                boarding_schedule_stop_id,
                alighting_schedule_stop_id,
                total_passengers,
                total_fare,
                booking_status
            )

            VALUES
            (
                :pnr,
                :user_id,
                :schedule_id,
                :boarding,
                :alighting,
                :count,
                :fare,
                'CONFIRMED'
            )

        """), {
            "pnr": pnr,
            "user_id": current_user.user_id,
            "schedule_id": schedule_id,
            "boarding": boarding_id,
            "alighting": alighting_id,
            "count": len(names),
            "fare": total_fare
        })

        booking_id = result.lastrowid

        # Insert passengers

        for name, age, gender in zip(names, ages, genders):

            db.session.execute(text("""
                INSERT INTO booking_passengers
                (
                    booking_id,
                    passenger_name,
                    age,
                    gender,
                    passenger_status
                )

                VALUES
                (
                    :booking_id,
                    :name,
                    :age,
                    :gender,
                    'CONFIRMED'
                )

            """), {
                "booking_id": booking_id,
                "name": name.strip(),
                "age": int(age),
                "gender": gender
            })

        # Insert simulated successful payment

        db.session.execute(text("""
            INSERT INTO payments
            (
                booking_id,
                transaction_reference,
                payment_method,
                amount,
                payment_status
            )

            VALUES
            (
                :booking_id,
                :reference,
                'UPI',
                :amount,
                'SUCCESS'
            )

        """), {
            "booking_id": booking_id,
            "reference": transaction_ref,
            "amount": total_fare
        })

        # Generate ticket record

        db.session.execute(text("""
            INSERT INTO tickets
            (
                booking_id,
                ticket_reference,
                ticket_status
            )

            VALUES
            (
                :booking_id,
                :reference,
                'ACTIVE'
            )

        """), {
            "booking_id": booking_id,
            "reference": ticket_ref
        })

        db.session.commit()

        return render_template(
            "booking_confirmation.html",
            pnr=pnr,
            ticket_ref=ticket_ref,
            total_fare=total_fare,
            names=names
        )

    except Exception as e:

        db.session.rollback()

        flash(str(e), "danger")

        return redirect(url_for("passenger.book_ticket"))


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

        WHERE b.user_id = :user_id

        ORDER BY b.booking_date DESC

    """), {
        "user_id": current_user.user_id
    }).mappings().all()

    return render_template(
        "my_bookings.html",
        bookings=bookings
    )
# ==========================================
# MY QR TICKET
# ==========================================

@passenger_bp.route("/my-qr-ticket")
@login_required
def my_qr_ticket():

    if current_user.role != "PASSENGER":
        abort(403)

    tickets = db.session.execute(text("""
        SELECT
            qt.token_reference,
            qt.issued_at,
            qt.expiry_time,
            qt.token_status,
            bp.passenger_name,
            bp.age,
            b.pnr_number,
            b.booking_status,
            t.train_number,
            t.train_name,
            s.journey_date

        FROM qr_tokens qt

        JOIN booking_passengers bp
            ON qt.booking_passenger_id = bp.booking_passenger_id

        JOIN bookings b
            ON bp.booking_id = b.booking_id

        JOIN schedules s
            ON b.schedule_id = s.schedule_id

        JOIN trains t
            ON s.train_id = t.train_id

        WHERE b.user_id = :user_id

        ORDER BY qt.issued_at DESC

    """), {
        "user_id": current_user.user_id
    }).mappings().all()

    return render_template(
        "my_qr_ticket.html",
        tickets=tickets
    )
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