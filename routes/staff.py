from datetime import datetime

from flask import Blueprint, render_template, abort, request, flash, redirect
from flask_login import login_required, current_user
from sqlalchemy import text
from extensions import db

staff = Blueprint("staff", __name__, url_prefix="/staff")


# GET ACTIVE STAFF ID
def get_staff_id():
    return db.session.execute(
        text("""
            SELECT staff_id
            FROM staff
            WHERE user_id = :user_id
            AND employment_status = 'ACTIVE'
        """),
        {"user_id": current_user.user_id}
    ).scalar()


# STAFF DASHBOARD
@staff.route("/dashboard")
@login_required
def dashboard():

    if current_user.role != "STAFF":
        abort(403)

    if not get_staff_id():
        abort(403)

    stats = {
        "verifications": db.session.execute(
            text("SELECT COUNT(*) FROM ticket_verifications")
        ).scalar() or 0,

        "entries": db.session.execute(
            text("SELECT COUNT(*) FROM entry_logs")
        ).scalar() or 0,

        "exits": db.session.execute(
            text("SELECT COUNT(*) FROM exit_logs")
        ).scalar() or 0,

        "platform_access": db.session.execute(
            text("SELECT COUNT(*) FROM platform_access_logs")
        ).scalar() or 0
    }

    return render_template("staff_dashboard.html", stats=stats)


# QR TICKET VERIFICATION
@staff.route("/verify-ticket", methods=["GET", "POST"])
@login_required
def verify_ticket():

    if current_user.role != "STAFF":
        abort(403)

    if not get_staff_id():
        abort(403)

    verified_passenger = None

    if request.method == "POST":

        token = request.form.get("qr_token", "").strip()

        result = db.session.execute(
            text("""
                SELECT
                    qt.token_id,
                    qt.token_status,
                    (qt.expiry_time > :now) AS is_valid_time,
                    bp.passenger_name,
                    bp.passenger_status,
                    b.pnr_number,
                    b.booking_status
                FROM qr_tokens qt
                JOIN booking_passengers bp
                    ON qt.booking_passenger_id = bp.booking_passenger_id
                JOIN bookings b
                    ON bp.booking_id = b.booking_id
                WHERE qt.token_reference = :token
            """),
            {"token": token, "now": datetime.now()}
        ).mappings().first()

        if not result:
            flash("Invalid QR ticket.", "danger")

        elif result["token_status"] != "ACTIVE":
            flash("QR ticket is not active.", "danger")

        elif not result["is_valid_time"]:
            flash("QR ticket has expired.", "danger")

        elif result["booking_status"] != "CONFIRMED":
            flash("Booking is not confirmed.", "danger")

        elif result["passenger_status"] != "CONFIRMED":
            flash("Passenger is not confirmed.", "danger")

        else:
            verified_passenger = result
            flash("Ticket verified successfully!", "success")

    return render_template(
        "verify_ticket.html",
        passenger=verified_passenger
    )


# PASSENGER ENTRY
@staff.route("/entry", methods=["GET", "POST"])
@login_required
def passenger_entry():

    if current_user.role != "STAFF":
        abort(403)

    staff_id = get_staff_id()

    if not staff_id:
        abort(403)

    if request.method == "POST":

        token = request.form.get("qr_token", "").strip()

        try:
            station_id = int(request.form.get("station_id"))
        except (ValueError, TypeError):
            flash("Please select a valid station.", "danger")
            return redirect(request.url)

        station = db.session.execute(
            text("""
                SELECT station_id
                FROM stations
                WHERE station_id = :id
                AND is_active = 1
            """),
            {"id": station_id}
        ).first()

        if not station:
            flash("Invalid or inactive station.", "danger")
            return redirect(request.url)

        result = db.session.execute(
            text("""
                SELECT
                    qt.token_id,
                    qt.token_status,
                    (qt.expiry_time > :now) AS is_valid_time,
                    bp.passenger_status,
                    b.booking_status
                FROM qr_tokens qt
                JOIN booking_passengers bp
                    ON qt.booking_passenger_id = bp.booking_passenger_id
                JOIN bookings b
                    ON bp.booking_id = b.booking_id
                WHERE qt.token_reference = :token
            """),
            {"token": token, "now": datetime.now()}
        ).mappings().first()

        if result:

            allowed = (
                result["token_status"] == "ACTIVE"
                and result["is_valid_time"]
                and result["booking_status"] == "CONFIRMED"
                and result["passenger_status"] == "CONFIRMED"
            )

            status = "ALLOWED" if allowed else "DENIED"

            db.session.execute(
                text("""
                    INSERT INTO entry_logs
                    (token_id, station_id, staff_id, entry_status)
                    VALUES (:token_id, :station_id, :staff_id, :status)
                """),
                {
                    "token_id": result["token_id"],
                    "station_id": station_id,
                    "staff_id": staff_id,
                    "status": status
                }
            )

            db.session.commit()

            if allowed:
                flash("Passenger entry recorded successfully!", "success")
            else:
                flash("Entry denied. QR ticket is invalid or inactive.", "danger")

        else:
            flash("Invalid QR ticket. Entry denied.", "danger")

    stations = db.session.execute(
        text("""
            SELECT station_id, station_name
            FROM stations
            WHERE is_active = 1
        """)
    ).mappings().all()

    return render_template(
        "staff_entry.html",
        stations=stations
    )


# PASSENGER EXIT
@staff.route("/exit", methods=["GET", "POST"])
@login_required
def passenger_exit():

    if current_user.role != "STAFF":
        abort(403)

    staff_id = get_staff_id()

    if not staff_id:
        abort(403)

    if request.method == "POST":

        token = request.form.get("qr_token", "").strip()

        try:
            station_id = int(request.form.get("station_id"))
        except (ValueError, TypeError):
            flash("Please select a valid station.", "danger")
            return redirect(request.url)

        station = db.session.execute(
            text("""
                SELECT station_id
                FROM stations
                WHERE station_id = :id
            """),
            {"id": station_id}
        ).first()

        if not station:
            flash("Invalid station selected.", "danger")
            return redirect(request.url)

        result = db.session.execute(
            text("""
                SELECT
                    qt.token_id,
                    qt.token_status,
                    (qt.expiry_time > :now) AS is_valid_time,
                    bp.passenger_status,
                    b.booking_status
                FROM qr_tokens qt
                JOIN booking_passengers bp
                    ON qt.booking_passenger_id = bp.booking_passenger_id
                JOIN bookings b
                    ON bp.booking_id = b.booking_id
                WHERE qt.token_reference = :token
            """),
            {"token": token, "now": datetime.now()}
        ).mappings().first()

        if result:

            allowed = (
                result["token_status"] == "ACTIVE"
                and result["is_valid_time"]
                and result["booking_status"] == "CONFIRMED"
                and result["passenger_status"] == "CONFIRMED"
            )

            status = "ALLOWED" if allowed else "DENIED"

            db.session.execute(
                text("""
                    INSERT INTO exit_logs
                    (token_id, station_id, staff_id, exit_status)
                    VALUES (:token_id, :station_id, :staff_id, :status)
                """),
                {
                    "token_id": result["token_id"],
                    "station_id": station_id,
                    "staff_id": staff_id,
                    "status": status
                }
            )

            db.session.commit()

            if allowed:
                flash("Passenger exit recorded successfully!", "success")
            else:
                flash("Exit denied. QR ticket is invalid or inactive.", "danger")

        else:
            flash("Invalid QR ticket. Exit denied.", "danger")

    stations = db.session.execute(
        text("""
            SELECT station_id, station_name
            FROM stations
        """)
    ).mappings().all()

    return render_template(
        "staff_exit.html",
        stations=stations
    )


# PLATFORM ACCESS MANAGEMENT
@staff.route("/platform-access", methods=["GET", "POST"])
@login_required
def platform_access():

    if current_user.role != "STAFF":
        abort(403)

    staff_id = get_staff_id()

    if not staff_id:
        abort(403)

    if request.method == "POST":

        token = request.form.get("qr_token", "").strip()

        try:
            platform_id = int(request.form.get("platform_id"))
        except (ValueError, TypeError):
            flash("Please select a valid platform.", "danger")
            return redirect(request.url)

        token_result = db.session.execute(
            text("""
                SELECT
                    qt.token_id,
                    qt.token_status,
                    (qt.expiry_time > :now) AS is_valid_time,
                    bp.passenger_status,
                    b.booking_status
                FROM qr_tokens qt
                JOIN booking_passengers bp
                    ON qt.booking_passenger_id = bp.booking_passenger_id
                JOIN bookings b
                    ON bp.booking_id = b.booking_id
                WHERE qt.token_reference = :token
            """),
            {"token": token, "now": datetime.now()}
        ).mappings().first()

        platform_result = db.session.execute(
            text("""
                SELECT platform_id
                FROM platforms
                WHERE platform_id = :platform_id
                AND platform_status = 'ACTIVE'
            """),
            {"platform_id": platform_id}
        ).first()

        if token_result:

            allowed = (
                token_result["token_status"] == "ACTIVE"
                and token_result["is_valid_time"]
                and token_result["booking_status"] == "CONFIRMED"
                and token_result["passenger_status"] == "CONFIRMED"
                and platform_result is not None
            )

            status = "ALLOWED" if allowed else "DENIED"

            db.session.execute(
                text("""
                    INSERT INTO platform_access_logs
                    (token_id, platform_id, staff_id, access_status)
                    VALUES (:token_id, :platform_id, :staff_id, :status)
                """),
                {
                    "token_id": token_result["token_id"],
                    "platform_id": platform_id,
                    "staff_id": staff_id,
                    "status": status
                }
            )

            db.session.commit()

            if allowed:
                flash("Platform access granted!", "success")
            else:
                flash("Platform access denied.", "danger")

        else:
            flash("Invalid QR ticket. Access denied.", "danger")

    platforms = db.session.execute(
        text("""
            SELECT
                p.platform_id,
                p.platform_number,
                s.station_name
            FROM platforms p
            JOIN stations s
                ON p.station_id = s.station_id
            WHERE p.platform_status = 'ACTIVE'
            ORDER BY s.station_name, p.platform_number
        """)
    ).mappings().all()

    return render_template(
        "platform_access.html",
        platforms=platforms
    )