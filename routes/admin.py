from flask import Blueprint, render_template, abort, request, redirect, url_for, flash
from sqlalchemy import text
from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user
from extensions import db
from sqlalchemy import text

admin = Blueprint("admin", __name__, url_prefix="/admin")


@admin.route("/dashboard")
@login_required
def dashboard():

    if current_user.role != "ADMIN":
        abort(403)

    stats = {}

    tables = ["users", "trains", "stations", "bookings"]

    for table in tables:
        result = db.session.execute(
            text(f"SELECT COUNT(*) FROM {table}")
        )
        stats[table] = result.scalar()

    return render_template(
        "admin_dashboard.html",
        stats=stats
    )
@admin.route("/trains")
@login_required
def manage_trains():

    if current_user.role != "ADMIN":
        abort(403)

    trains = db.session.execute(
        text("""
            SELECT train_id, train_number, train_name,
                   train_type, operating_status
            FROM trains
            ORDER BY train_id
        """)
    ).mappings().all()

    return render_template(
        "trains.html",
        trains=trains
    )
@admin.route("/trains/add", methods=["GET", "POST"])
@login_required
def add_train():

    if current_user.role != "ADMIN":
        abort(403)

    if request.method == "POST":
        train_number = request.form.get("train_number")
        train_name = request.form.get("train_name")
        train_type = request.form.get("train_type")
        route_id = request.form.get("route_id")
        total_capacity = request.form.get("total_capacity")

        try:
            db.session.execute(
                text("""
                    INSERT INTO trains
                    (train_number, train_name, train_type,
                     route_id, total_capacity)
                    VALUES
                    (:number, :name, :type, :route, :capacity)
                """),
                {
                    "number": train_number,
                    "name": train_name,
                    "type": train_type,
                    "route": route_id,
                    "capacity": total_capacity
                }
            )

            db.session.commit()
            flash("Train added successfully!", "success")
            return redirect(url_for("admin.manage_trains"))

        except Exception:
            db.session.rollback()
            flash("Unable to add train. Check the details.", "danger")

    routes = db.session.execute(
        text("SELECT route_id, route_name FROM routes")
    ).mappings().all()

    return render_template("add_train.html", routes=routes)
@admin.route("/trains/edit/<int:train_id>", methods=["GET", "POST"])
@login_required
def edit_train(train_id):

    if current_user.role != "ADMIN":
        abort(403)

    train = db.session.execute(
        text("""
            SELECT * FROM trains
            WHERE train_id = :id
        """),
        {"id": train_id}
    ).mappings().first()

    if not train:
        abort(404)

    if request.method == "POST":

        try:
            db.session.execute(
                text("""
                    UPDATE trains
                    SET train_number = :number,
                        train_name = :name,
                        train_type = :type,
                        route_id = :route,
                        total_capacity = :capacity
                    WHERE train_id = :id
                """),
                {
                    "number": request.form.get("train_number"),
                    "name": request.form.get("train_name"),
                    "type": request.form.get("train_type"),
                    "route": request.form.get("route_id"),
                    "capacity": request.form.get("total_capacity"),
                    "id": train_id
                }
            )

            db.session.commit()
            flash("Train updated successfully!", "success")
            return redirect(url_for("admin.manage_trains"))

        except Exception:
            db.session.rollback()
            flash("Unable to update train. Check the details.", "danger")

    routes = db.session.execute(
        text("SELECT route_id, route_name FROM routes")
    ).mappings().all()

    return render_template(
        "edit_train.html",
        train=train,
        routes=routes
    )
@admin.route("/trains/status/<int:train_id>", methods=["POST"])
@login_required
def toggle_train_status(train_id):

    if current_user.role != "ADMIN":
        abort(403)

    new_status = request.form.get("status")

    if new_status not in ["ACTIVE", "INACTIVE"]:
        abort(400)

    result = db.session.execute(
        text("""
            UPDATE trains
            SET operating_status = :status
            WHERE train_id = :id
        """),
        {
            "status": new_status,
            "id": train_id
        }
    )

    if result.rowcount == 0:
        db.session.rollback()
        abort(404)

    db.session.commit()

    flash(f"Train status changed to {new_status}!", "success")

    return redirect(url_for("admin.manage_trains"))
@admin.route("/stations")
@login_required
def manage_stations():

    if current_user.role != "ADMIN":
        abort(403)

    stations = db.session.execute(
        text("""
            SELECT station_id, station_code, station_name,
                   city, state, station_type, is_active
            FROM stations
            ORDER BY station_id
        """)
    ).mappings().all()

    return render_template(
        "stations.html",
        stations=stations
    )
@admin.route("/stations/status/<int:station_id>", methods=["POST"])
@login_required
def toggle_station_status(station_id):

    if current_user.role != "ADMIN":
        abort(403)

    new_status = request.form.get("status")

    if new_status not in ["0", "1"]:
        abort(400)

    result = db.session.execute(
        text("""
            UPDATE stations
            SET is_active = :status
            WHERE station_id = :id
        """),
        {
            "status": int(new_status),
            "id": station_id
        }
    )

    if result.rowcount == 0:
        db.session.rollback()
        abort(404)

    db.session.commit()

    flash("Station status updated successfully!", "success")

    return redirect(url_for("admin.manage_stations"))
@admin.route("/stations/add", methods=["GET", "POST"])
@login_required
def add_station():

    if current_user.role != "ADMIN":
        abort(403)

    if request.method == "POST":

        station_code = request.form.get("station_code")
        station_name = request.form.get("station_name")
        city = request.form.get("city")
        state = request.form.get("state")
        station_type = request.form.get("station_type")

        try:
            db.session.execute(
                text("""
                    INSERT INTO stations
                    (station_code, station_name, city, state, station_type)
                    VALUES
                    (:code, :name, :city, :state, :type)
                """),
                {
                    "code": station_code,
                    "name": station_name,
                    "city": city,
                    "state": state,
                    "type": station_type
                }
            )

            db.session.commit()

            flash("Station added successfully!", "success")
            return redirect(url_for("admin.manage_stations"))

        except Exception:
            db.session.rollback()
            flash("Unable to add station. Check the details.", "danger")

    return render_template("add_station.html")
@admin.route("/stations/edit/<int:station_id>", methods=["GET", "POST"])
@login_required
def edit_station(station_id):

    if current_user.role != "ADMIN":
        abort(403)

    station = db.session.execute(
        text("""
            SELECT * FROM stations
            WHERE station_id = :id
        """),
        {"id": station_id}
    ).mappings().first()

    if not station:
        abort(404)

    if request.method == "POST":

        try:
            db.session.execute(
                text("""
                    UPDATE stations
                    SET station_code = :code,
                        station_name = :name,
                        city = :city,
                        state = :state,
                        station_type = :type
                    WHERE station_id = :id
                """),
                {
                    "code": request.form.get("station_code"),
                    "name": request.form.get("station_name"),
                    "city": request.form.get("city"),
                    "state": request.form.get("state"),
                    "type": request.form.get("station_type"),
                    "id": station_id
                }
            )

            db.session.commit()

            flash("Station updated successfully!", "success")
            return redirect(url_for("admin.manage_stations"))

        except Exception:
            db.session.rollback()
            flash("Unable to update station. Check the details.", "danger")

    return render_template(
        "edit_station.html",
        station=station
    )
@admin.route("/routes")
@login_required
def manage_routes():

    if current_user.role != "ADMIN":
        abort(403)

    routes = db.session.execute(
        text("""
            SELECT
                r.route_id,
                r.route_name,
                s1.station_name AS source_station,
                s2.station_name AS destination_station,
                r.distance_km
            FROM routes r
            JOIN stations s1
                ON r.source_station_id = s1.station_id
            JOIN stations s2
                ON r.destination_station_id = s2.station_id
            ORDER BY r.route_id
        """)
    ).mappings().all()

    return render_template(
        "routes.html",
        routes=routes
    )
@admin.route("/routes/add", methods=["GET", "POST"])
@login_required
def add_route():

    if current_user.role != "ADMIN":
        abort(403)

    if request.method == "POST":

        route_name = request.form.get("route_name")
        source_station_id = request.form.get("source_station_id")
        destination_station_id = request.form.get("destination_station_id")
        distance_km = request.form.get("distance_km")

        try:
            db.session.execute(
                text("""
                    INSERT INTO routes
                    (route_name, source_station_id,
                     destination_station_id, distance_km)
                    VALUES
                    (:name, :source, :destination, :distance)
                """),
                {
                    "name": route_name,
                    "source": source_station_id,
                    "destination": destination_station_id,
                    "distance": distance_km
                }
            )

            db.session.commit()

            flash("Route added successfully!", "success")
            return redirect(url_for("admin.manage_routes"))

        except Exception:
            db.session.rollback()
            flash("Unable to add route. Check the details.", "danger")

    stations = db.session.execute(
        text("""
            SELECT station_id, station_name
            FROM stations
            WHERE is_active = 1
            ORDER BY station_name
        """)
    ).mappings().all()

    return render_template("add_route.html", stations=stations)
@admin.route("/routes/edit/<int:route_id>", methods=["GET", "POST"])
@login_required
def edit_route(route_id):

    if current_user.role != "ADMIN":
        abort(403)

    route = db.session.execute(
        text("""
            SELECT * FROM routes
            WHERE route_id = :id
        """),
        {"id": route_id}
    ).mappings().first()

    if not route:
        abort(404)

    if request.method == "POST":

        try:
            db.session.execute(
                text("""
                    UPDATE routes
                    SET route_name = :name,
                        source_station_id = :source,
                        destination_station_id = :destination,
                        distance_km = :distance
                    WHERE route_id = :id
                """),
                {
                    "name": request.form.get("route_name"),
                    "source": request.form.get("source_station_id"),
                    "destination": request.form.get("destination_station_id"),
                    "distance": request.form.get("distance_km"),
                    "id": route_id
                }
            )

            db.session.commit()

            flash("Route updated successfully!", "success")
            return redirect(url_for("admin.manage_routes"))

        except Exception:
            db.session.rollback()
            flash("Unable to update route. Check the details.", "danger")

    stations = db.session.execute(
        text("""
            SELECT station_id, station_name
            FROM stations
            WHERE is_active = 1
            ORDER BY station_name
        """)
    ).mappings().all()

    return render_template(
        "edit_route.html",
        route=route,
        stations=stations
    )
@admin.route("/route-stops")
@login_required
def manage_route_stops():

    if current_user.role != "ADMIN":
        abort(403)

    route_stops = db.session.execute(
        text("""
            SELECT
                rs.route_stop_id,
                r.route_name,
                s.station_name,
                rs.stop_number,
                rs.distance_from_source
            FROM route_stops rs
            JOIN routes r
                ON rs.route_id = r.route_id
            JOIN stations s
                ON rs.station_id = s.station_id
            ORDER BY r.route_id, rs.stop_number
        """)
    ).mappings().all()

    return render_template(
        "route_stops.html",
        route_stops=route_stops
    )
@admin.route("/route-stops/add", methods=["GET", "POST"])
@login_required
def add_route_stop():

    if current_user.role != "ADMIN":
        abort(403)

    if request.method == "POST":

        try:
            route_id = int(request.form.get("route_id"))
            station_id = int(request.form.get("station_id"))
            stop_number = int(request.form.get("stop_number"))
            distance = float(request.form.get("distance_from_source"))

            if stop_number <= 0 or distance < 0:
                raise ValueError("Invalid stop details.")

            db.session.execute(
                text("""
                    INSERT INTO route_stops
                    (route_id, station_id, stop_number, distance_from_source)
                    VALUES
                    (:route_id, :station_id, :stop_number, :distance)
                """),
                {
                    "route_id": route_id,
                    "station_id": station_id,
                    "stop_number": stop_number,
                    "distance": distance
                }
            )

            db.session.commit()
            flash("Route stop added successfully!", "success")
            return redirect(url_for("admin.manage_route_stops"))

        except Exception:
            db.session.rollback()
            flash("Unable to add route stop. Check the details and avoid duplicate stops.", "danger")

    routes = db.session.execute(
        text("SELECT route_id, route_name FROM routes ORDER BY route_id")
    ).mappings().all()

    stations = db.session.execute(
        text("SELECT station_id, station_name FROM stations WHERE is_active = 1 ORDER BY station_name")
    ).mappings().all()

    return render_template(
        "add_route_stop.html",
        routes=routes,
        stations=stations
    )
@admin.route("/route-stops/edit/<int:stop_id>", methods=["GET", "POST"])
@login_required
def edit_route_stop(stop_id):

    if current_user.role != "ADMIN":
        abort(403)

    stop = db.session.execute(
        text("""
            SELECT * FROM route_stops
            WHERE route_stop_id = :id
        """),
        {"id": stop_id}
    ).mappings().first()

    if not stop:
        abort(404)

    if request.method == "POST":
        try:
            db.session.execute(
                text("""
                    UPDATE route_stops
                    SET station_id = :station,
                        stop_number = :number,
                        distance_from_source = :distance
                    WHERE route_stop_id = :id
                """),
                {
                    "station": int(request.form.get("station_id")),
                    "number": int(request.form.get("stop_number")),
                    "distance": float(request.form.get("distance_from_source")),
                    "id": stop_id
                }
            )

            db.session.commit()
            flash("Route stop updated successfully!", "success")
            return redirect(url_for("admin.manage_route_stops"))

        except Exception:
            db.session.rollback()
            flash("Unable to update route stop. Check the details.", "danger")

    stations = db.session.execute(
        text("""
            SELECT station_id, station_name
            FROM stations
            WHERE is_active = 1
            ORDER BY station_name
        """)
    ).mappings().all()

    return render_template(
        "edit_route_stop.html",
        stop=stop,
        stations=stations
    )
@admin.route("/route-stops/delete/<int:stop_id>", methods=["POST"])
@login_required
def delete_route_stop(stop_id):

    if current_user.role != "ADMIN":
        abort(403)

    stop = db.session.execute(
        text("""
            SELECT route_stop_id
            FROM route_stops
            WHERE route_stop_id = :id
        """),
        {"id": stop_id}
    ).first()

    if not stop:
        abort(404)

    # Prevent deletion if a schedule already uses this stop
    used = db.session.execute(
        text("""
            SELECT schedule_stop_id
            FROM schedule_stops
            WHERE route_stop_id = :id
            LIMIT 1
        """),
        {"id": stop_id}
    ).first()

    if used:
        flash("Cannot delete this stop because it is used in a train schedule.", "warning")
        return redirect(url_for("admin.manage_route_stops"))

    try:
        db.session.execute(
            text("""
                DELETE FROM route_stops
                WHERE route_stop_id = :id
            """),
            {"id": stop_id}
        )

        db.session.commit()
        flash("Route stop deleted successfully!", "success")

    except Exception:
        db.session.rollback()
        flash("Unable to delete route stop.", "danger")

    return redirect(url_for("admin.manage_route_stops"))
@admin.route("/schedules")
@login_required
def manage_schedules():

    if current_user.role != "ADMIN":
        abort(403)

    schedules = db.session.execute(
        text("""
            SELECT
                s.schedule_id,
                t.train_number,
                t.train_name,
                s.journey_date,
                s.schedule_status
            FROM schedules s
            JOIN trains t
                ON s.train_id = t.train_id
            ORDER BY s.journey_date, s.schedule_id
        """)
    ).mappings().all()

    return render_template(
        "schedules.html",
        schedules=schedules
    )
@admin.route("/schedules/add", methods=["GET", "POST"])
@login_required
def add_schedule():

    if current_user.role != "ADMIN":
        abort(403)

    if request.method == "POST":

        try:
            train_id = int(request.form.get("train_id"))
            journey_date = request.form.get("journey_date")

            if not journey_date:
                raise ValueError("Journey date is required.")

            db.session.execute(
                text("""
                    INSERT INTO schedules
                    (train_id, journey_date, schedule_status)
                    VALUES
                    (:train_id, :journey_date, 'SCHEDULED')
                """),
                {
                    "train_id": train_id,
                    "journey_date": journey_date
                }
            )

            db.session.commit()
            flash("Train schedule added successfully!", "success")
            return redirect(url_for("admin.manage_schedules"))

        except Exception:
            db.session.rollback()
            flash("Unable to add schedule. Check the train and journey date. A schedule may already exist for this train on that date.", "danger")

    trains = db.session.execute(
        text("""
            SELECT train_id, train_number, train_name
            FROM trains
            WHERE operating_status = 'ACTIVE'
            ORDER BY train_number
        """)
    ).mappings().all()

    return render_template(
        "add_schedule.html",
        trains=trains
    )
@admin.route("/schedules/edit/<int:schedule_id>", methods=["GET", "POST"])
@login_required
def edit_schedule(schedule_id):

    if current_user.role != "ADMIN":
        abort(403)

    schedule = db.session.execute(
        text("""
            SELECT *
            FROM schedules
            WHERE schedule_id = :id
        """),
        {"id": schedule_id}
    ).mappings().first()

    if not schedule:
        abort(404)

    if request.method == "POST":

        try:
            journey_date = request.form.get("journey_date")
            schedule_status = request.form.get("schedule_status")

            if schedule_status not in [
                "SCHEDULED", "DELAYED", "CANCELLED", "COMPLETED"
            ]:
                raise ValueError("Invalid schedule status.")

            db.session.execute(
                text("""
                    UPDATE schedules
                    SET journey_date = :journey_date,
                        schedule_status = :status
                    WHERE schedule_id = :id
                """),
                {
                    "journey_date": journey_date,
                    "status": schedule_status,
                    "id": schedule_id
                }
            )

            db.session.commit()
            flash("Schedule updated successfully!", "success")
            return redirect(url_for("admin.manage_schedules"))

        except Exception:
            db.session.rollback()
            flash("Unable to update schedule. Check the details.", "danger")

    return render_template(
        "edit_schedule.html",
        schedule=schedule
    )
@admin.route("/schedule-stops")
@login_required
def manage_schedule_stops():

    if current_user.role != "ADMIN":
        abort(403)

    schedule_stops = db.session.execute(
        text("""
            SELECT
                ss.schedule_stop_id,
                t.train_number,
                t.train_name,
                s.journey_date,
                st.station_name,
                rs.stop_number,
                ss.scheduled_arrival,
                ss.scheduled_departure,
                p.platform_number
            FROM schedule_stops ss
            JOIN schedules s
                ON ss.schedule_id = s.schedule_id
            JOIN trains t
                ON s.train_id = t.train_id
            JOIN route_stops rs
                ON ss.route_stop_id = rs.route_stop_id
            JOIN stations st
                ON rs.station_id = st.station_id
            LEFT JOIN platforms p
                ON ss.platform_id = p.platform_id
            ORDER BY s.journey_date, t.train_number, rs.stop_number
        """)
    ).mappings().all()

    return render_template(
        "schedule_stops.html",
        schedule_stops=schedule_stops
    )
@admin.route("/schedule-stops/edit/<int:stop_id>", methods=["GET", "POST"])
@login_required
def edit_schedule_stop(stop_id):

    if current_user.role != "ADMIN":
        abort(403)

    stop = db.session.execute(
        text("""
            SELECT
                ss.*,
                st.station_name,
                t.train_number,
                t.train_name,
                s.journey_date
            FROM schedule_stops ss
            JOIN schedules s ON ss.schedule_id = s.schedule_id
            JOIN trains t ON s.train_id = t.train_id
            JOIN route_stops rs ON ss.route_stop_id = rs.route_stop_id
            JOIN stations st ON rs.station_id = st.station_id
            WHERE ss.schedule_stop_id = :id
        """),
        {"id": stop_id}
    ).mappings().first()

    if not stop:
        abort(404)

    if request.method == "POST":
        try:
            arrival = request.form.get("scheduled_arrival") or None
            departure = request.form.get("scheduled_departure") or None
            platform_id = request.form.get("platform_id") or None

            db.session.execute(
                text("""
                    UPDATE schedule_stops
                    SET scheduled_arrival = :arrival,
                      scheduled_departure = :departure,
                      platform_id = :platform
                    WHERE schedule_stop_id = :id
                """),
                {
                    "arrival": arrival,
                    "departure": departure,
                    "platform": int(platform_id) if platform_id else None,
                    "id": stop_id
                }
            )

            db.session.commit()
            flash("Schedule stop updated successfully!", "success")

            return redirect(url_for("admin.manage_schedule_stops"))

        except Exception:
            db.session.rollback()
            flash("Unable to update schedule stop. Check the details.", "danger")

    platforms = db.session.execute(
        text("""
            SELECT platform_id, platform_number
            FROM platforms
            WHERE station_id = (
                SELECT station_id
                FROM route_stops
                WHERE route_stop_id = :route_stop_id
            )
            AND platform_status = 'ACTIVE'
            ORDER BY platform_number
        """),
        {"route_stop_id": stop["route_stop_id"]}
    ).mappings().all()

    return render_template(
        "edit_schedule_stop.html",
        stop=stop,
        platforms=platforms
    )
@admin.route("/platform-allocations")
@login_required
def manage_platform_allocations():

    if current_user.role != "ADMIN":
        abort(403)

    allocations = db.session.execute(
        text("""
            SELECT
                pa.allocation_id,
                t.train_number,
                t.train_name,
                s.journey_date,
                st.station_name,
                rs.stop_number,
                p.platform_number,
                pa.arrival_time,
                pa.departure_time,
                pa.allocation_status
            FROM platform_allocations pa
            JOIN schedule_stops ss
                ON pa.schedule_stop_id = ss.schedule_stop_id
            JOIN schedules s
                ON ss.schedule_id = s.schedule_id
            JOIN trains t
                ON s.train_id = t.train_id
            JOIN route_stops rs
                ON ss.route_stop_id = rs.route_stop_id
            JOIN stations st
                ON rs.station_id = st.station_id
            JOIN platforms p
                ON pa.platform_id = p.platform_id
            ORDER BY s.journey_date, pa.arrival_time
        """)
    ).mappings().all()

    return render_template(
        "platform_allocations.html",
        allocations=allocations
    )
@admin.route("/platform-allocations/add", methods=["GET", "POST"])
@login_required
def add_platform_allocation():

    if current_user.role != "ADMIN":
        abort(403)

    if request.method == "POST":
        try:
            schedule_stop_id = int(request.form.get("schedule_stop_id"))
            platform_id = int(request.form.get("platform_id"))
            arrival = request.form.get("arrival_time")
            departure = request.form.get("departure_time")

            if not arrival or not departure or arrival >= departure:
                raise ValueError("Invalid arrival or departure time.")

            stop = db.session.execute(
                text("""
                    SELECT
                        ss.schedule_stop_id,
                        rs.station_id
                    FROM schedule_stops ss
                    JOIN route_stops rs
                        ON ss.route_stop_id = rs.route_stop_id
                    WHERE ss.schedule_stop_id = :id
                """),
                {"id": schedule_stop_id}
            ).mappings().first()

            if not stop:
                raise ValueError("Schedule stop not found.")

            platform = db.session.execute(
                text("""
                    SELECT platform_id
                    FROM platforms
                    WHERE platform_id = :platform
                      AND station_id = :station
                      AND platform_status = 'ACTIVE'
                """),
                {
                    "platform": platform_id,
                    "station": stop["station_id"]
                }
            ).first()

            if not platform:
                raise ValueError("Select a valid platform for this station.")

            existing = db.session.execute(
                text("""
                    SELECT allocation_id
                    FROM platform_allocations
                    WHERE schedule_stop_id = :stop
                      AND allocation_status != 'CANCELLED'
                """),
                {"stop": schedule_stop_id}
            ).first()

            if existing:
                raise ValueError("This schedule stop already has an allocation.")

            conflict = db.session.execute(
                text("""
                    SELECT allocation_id
                    FROM platform_allocations
                    WHERE platform_id = :platform
                      AND allocation_status != 'CANCELLED'
                      AND arrival_time < :departure
                      AND departure_time > :arrival
                    LIMIT 1
                """),
                {
                    "platform": platform_id,
                    "arrival": arrival,
                    "departure": departure
                }
            ).first()

            if conflict:
                raise ValueError("Platform conflict! Another train is assigned during this time.")

            db.session.execute(
                text("""
                    INSERT INTO platform_allocations
                    (schedule_stop_id, platform_id, arrival_time, departure_time)
                    VALUES
                    (:stop, :platform, :arrival, :departure)
                """),
                {
                    "stop": schedule_stop_id,
                    "platform": platform_id,
                    "arrival": arrival,
                    "departure": departure
                }
            )

            db.session.execute(
                text("""
                    UPDATE schedule_stops
                    SET platform_id = :platform
                    WHERE schedule_stop_id = :stop
                """),
                {
                    "platform": platform_id,
                    "stop": schedule_stop_id
                }
            )

            db.session.commit()
            flash("Platform allocated successfully!", "success")
            return redirect(url_for("admin.manage_platform_allocations"))

        except ValueError as error:
            db.session.rollback()
            flash(str(error), "danger")

        except Exception:
            db.session.rollback()
            flash("Unable to allocate platform. Please check the details.", "danger")

    schedule_stops = db.session.execute(
        text("""
            SELECT
                ss.schedule_stop_id,
                t.train_number,
                t.train_name,
                s.journey_date,
                st.station_name,
                rs.station_id
            FROM schedule_stops ss
            JOIN schedules s ON ss.schedule_id = s.schedule_id
            JOIN trains t ON s.train_id = t.train_id
            JOIN route_stops rs ON ss.route_stop_id = rs.route_stop_id
            JOIN stations st ON rs.station_id = st.station_id
            WHERE s.schedule_status IN ('SCHEDULED', 'DELAYED')
            ORDER BY s.journey_date, t.train_number, rs.stop_number
        """)
    ).mappings().all()

    platforms = db.session.execute(
        text("""
            SELECT platform_id, station_id, platform_number
            FROM platforms
            WHERE platform_status = 'ACTIVE'
            ORDER BY station_id, platform_number
        """)
    ).mappings().all()

    return render_template(
        "add_platform_allocation.html",
        schedule_stops=schedule_stops,
        platforms=platforms
    )
@admin.route("/platform-allocations/edit/<int:allocation_id>", methods=["GET", "POST"])
@login_required
def edit_platform_allocation(allocation_id):

    if current_user.role != "ADMIN":
        abort(403)

    allocation = db.session.execute(
        text("""
            SELECT
                pa.*,
                ss.schedule_stop_id,
                rs.station_id,
                st.station_name
            FROM platform_allocations pa
            JOIN schedule_stops ss
                ON pa.schedule_stop_id = ss.schedule_stop_id
            JOIN route_stops rs
                ON ss.route_stop_id = rs.route_stop_id
            JOIN stations st
                ON rs.station_id = st.station_id
            WHERE pa.allocation_id = :id
        """),
        {"id": allocation_id}
    ).mappings().first()

    if not allocation:
        abort(404)

    if request.method == "POST":
        try:
            platform_id = int(request.form.get("platform_id"))
            arrival = request.form.get("arrival_time")
            departure = request.form.get("departure_time")

            if not arrival or not departure or arrival >= departure:
                raise ValueError("Invalid arrival or departure time.")

            platform = db.session.execute(
                text("""
                    SELECT platform_id
                    FROM platforms
                    WHERE platform_id = :platform
                      AND station_id = :station
                      AND platform_status = 'ACTIVE'
                """),
                {
                    "platform": platform_id,
                    "station": allocation["station_id"]
                }
            ).first()

            if not platform:
                raise ValueError("Select a valid platform for this station.")

            conflict = db.session.execute(
                text("""
                    SELECT allocation_id
                    FROM platform_allocations
                    WHERE platform_id = :platform
                      AND allocation_id != :id
                      AND allocation_status != 'CANCELLED'
                      AND arrival_time < :departure
                      AND departure_time > :arrival
                    LIMIT 1
                """),
                {
                    "platform": platform_id,
                    "id": allocation_id,
                    "arrival": arrival,
                    "departure": departure
                }
            ).first()

            if conflict:
                raise ValueError("Platform conflict! Another train is assigned during this time.")

            db.session.execute(
                text("""
                    UPDATE platform_allocations
                    SET platform_id = :platform,
                        arrival_time = :arrival,
                        departure_time = :departure
                    WHERE allocation_id = :id
                """),
                {
                    "platform": platform_id,
                    "arrival": arrival,
                    "departure": departure,
                    "id": allocation_id
                }
            )

            db.session.execute(
                text("""
                    UPDATE schedule_stops
                    SET platform_id = :platform
                    WHERE schedule_stop_id = :stop
                """),
                {
                    "platform": platform_id,
                    "stop": allocation["schedule_stop_id"]
                }
            )

            db.session.commit()
            flash("Platform allocation updated successfully!", "success")
            return redirect(url_for("admin.manage_platform_allocations"))

        except ValueError as error:
            db.session.rollback()
            flash(str(error), "danger")

        except Exception:
            db.session.rollback()
            flash("Unable to update platform allocation.", "danger")

    platforms = db.session.execute(
        text("""
            SELECT platform_id, platform_number
            FROM platforms
            WHERE station_id = :station
              AND platform_status = 'ACTIVE'
            ORDER BY platform_number
        """),
        {"station": allocation["station_id"]}
    ).mappings().all()

    return render_template(
        "edit_platform_allocation.html",
        allocation=allocation,
        platforms=platforms
    )
@admin.route("/platform-allocations/cancel/<int:allocation_id>", methods=["POST"])
@login_required
def cancel_platform_allocation(allocation_id):

    if current_user.role != "ADMIN":
        abort(403)

    allocation = db.session.execute(
        text("""
            SELECT allocation_id, schedule_stop_id
            FROM platform_allocations
            WHERE allocation_id = :id
              AND allocation_status != 'CANCELLED'
        """),
        {"id": allocation_id}
    ).mappings().first()

    if not allocation:
        flash("Allocation not found or already cancelled.", "warning")
        return redirect(url_for("admin.manage_platform_allocations"))

    try:
        db.session.execute(
            text("""
                UPDATE platform_allocations
                SET allocation_status = 'CANCELLED'
                WHERE allocation_id = :id
            """),
            {"id": allocation_id}
        )

        db.session.execute(
            text("""
                UPDATE schedule_stops
                SET platform_id = NULL
                WHERE schedule_stop_id = :stop
            """),
            {"stop": allocation["schedule_stop_id"]}
        )

        db.session.commit()
        flash("Platform allocation cancelled successfully!", "success")

    except Exception:
        db.session.rollback()
        flash("Unable to cancel platform allocation.", "danger")

    return redirect(url_for("admin.manage_platform_allocations"))
@admin.route("/platform-conflicts")
@login_required
def manage_platform_conflicts():

    if current_user.role != "ADMIN":
        abort(403)

    conflicts = db.session.execute(
        text("""
            SELECT
                pc.conflict_id,
                pc.conflict_time,
                pc.resolution_status,
                pc.resolution_notes,

                st.station_name,
                p.platform_number,

                t1.train_number AS train1_number,
                t1.train_name AS train1_name,
                pa1.arrival_time AS train1_arrival,
                pa1.departure_time AS train1_departure,

                t2.train_number AS train2_number,
                t2.train_name AS train2_name,
                pa2.arrival_time AS train2_arrival,
                pa2.departure_time AS train2_departure

            FROM platform_conflicts pc

            JOIN platforms p
                ON pc.platform_id = p.platform_id

            JOIN stations st
                ON p.station_id = st.station_id

            JOIN platform_allocations pa1
                ON pc.allocation_id_1 = pa1.allocation_id

            JOIN platform_allocations pa2
                ON pc.allocation_id_2 = pa2.allocation_id

            JOIN schedule_stops ss1
                ON pa1.schedule_stop_id = ss1.schedule_stop_id

            JOIN schedule_stops ss2
                ON pa2.schedule_stop_id = ss2.schedule_stop_id

            JOIN schedules s1
                ON ss1.schedule_id = s1.schedule_id

            JOIN schedules s2
                ON ss2.schedule_id = s2.schedule_id

            JOIN trains t1
                ON s1.train_id = t1.train_id

            JOIN trains t2
                ON s2.train_id = t2.train_id

            ORDER BY pc.conflict_time DESC
        """)
    ).mappings().all()

    return render_template(
        "platform_conflicts.html",
        conflicts=conflicts
    )
@admin.route("/platform-conflicts/resolve/<int:conflict_id>", methods=["POST"])
@login_required
def resolve_platform_conflict(conflict_id):

    if current_user.role != "ADMIN":
        abort(403)

    notes = request.form.get("resolution_notes", "").strip()

    conflict = db.session.execute(
        text("""
            SELECT conflict_id, resolution_status
            FROM platform_conflicts
            WHERE conflict_id = :id
        """),
        {"id": conflict_id}
    ).mappings().first()

    if not conflict:
        abort(404)

    if conflict["resolution_status"] == "RESOLVED":
        flash("Conflict is already resolved.", "warning")
        return redirect(url_for("admin.manage_platform_conflicts"))

    if not notes:
        flash("Please enter resolution notes.", "warning")
        return redirect(url_for("admin.manage_platform_conflicts"))

    try:
        db.session.execute(
            text("""
                UPDATE platform_conflicts
                SET resolution_status = 'RESOLVED',
                    resolution_notes = :notes
                WHERE conflict_id = :id
            """),
            {"notes": notes, "id": conflict_id}
        )

        db.session.commit()
        flash("Platform conflict resolved successfully!", "success")

    except Exception:
        db.session.rollback()
        flash("Unable to resolve platform conflict.", "danger")

    return redirect(url_for("admin.manage_platform_conflicts"))
@admin.route("/delays")
@login_required
def manage_delays():

    if current_user.role != "ADMIN":
        abort(403)

    delays = db.session.execute(
        text("""
            SELECT
                d.delay_id,
                t.train_number,
                t.train_name,
                s.journey_date,
                st.station_name,
                d.delay_minutes,
                d.reason,
                d.recorded_at
            FROM delay_records d
            JOIN schedules s
                ON d.schedule_id = s.schedule_id
            JOIN trains t
                ON s.train_id = t.train_id
            JOIN stations st
                ON d.station_id = st.station_id
            ORDER BY d.recorded_at DESC
        """)
    ).mappings().all()

    return render_template(
        "delays.html",
        delays=delays
    )
@admin.route("/delays/add", methods=["GET", "POST"])
@login_required
def add_delay():

    if current_user.role != "ADMIN":
        abort(403)

    if request.method == "POST":
        try:
            schedule_id = int(request.form.get("schedule_id"))
            station_id = int(request.form.get("station_id"))
            delay_minutes = int(request.form.get("delay_minutes"))
            reason = request.form.get("reason", "").strip()

            if delay_minutes < 0:
                raise ValueError("Delay cannot be negative.")

            valid_stop = db.session.execute(
                text("""
                    SELECT ss.schedule_stop_id
                    FROM schedule_stops ss
                    JOIN route_stops rs
                        ON ss.route_stop_id = rs.route_stop_id
                    WHERE ss.schedule_id = :schedule
                      AND rs.station_id = :station
                """),
                {
                    "schedule": schedule_id,
                    "station": station_id
                }
            ).first()

            if not valid_stop:
                raise ValueError("Selected station is not on this train route.")

            db.session.execute(
                text("""
                    INSERT INTO delay_records
                    (schedule_id, station_id, delay_minutes, reason)
                    VALUES
                    (:schedule, :station, :minutes, :reason)
                """),
                {
                    "schedule": schedule_id,
                    "station": station_id,
                    "minutes": delay_minutes,
                    "reason": reason
                }
            )

            db.session.execute(
                text("""
                    UPDATE schedules
                    SET schedule_status = 'DELAYED'
                    WHERE schedule_id = :schedule
                      AND schedule_status = 'SCHEDULED'
                """),
                {"schedule": schedule_id}
            )

            db.session.commit()
            flash("Train delay recorded successfully!", "success")
            return redirect(url_for("admin.manage_delays"))

        except ValueError as error:
            db.session.rollback()
            flash(str(error), "danger")

        except Exception:
            db.session.rollback()
            flash("Unable to record train delay.", "danger")

    schedules = db.session.execute(
        text("""
            SELECT s.schedule_id, t.train_number, t.train_name,
                   s.journey_date
            FROM schedules s
            JOIN trains t ON s.train_id = t.train_id
            WHERE s.schedule_status IN ('SCHEDULED', 'DELAYED')
            ORDER BY s.journey_date
        """)
    ).mappings().all()

    stations = db.session.execute(
        text("""
            SELECT station_id, station_name
            FROM stations
            WHERE is_active = 1
            ORDER BY station_name
        """)
    ).mappings().all()

    return render_template(
        "add_delay.html",
        schedules=schedules,
        stations=stations
    )
@admin.route("/complaints")
@login_required
def manage_complaints():

    if current_user.role != "ADMIN":
        abort(403)

    complaints = db.session.execute(text("""
        SELECT
            c.complaint_id,
            c.complaint_type,
            c.description,
            c.complaint_status,
            c.created_at,
            u.full_name,
            b.pnr_number,
            s.station_name
        FROM complaints c
        JOIN users u
            ON c.user_id = u.user_id
        LEFT JOIN bookings b
            ON c.booking_id = b.booking_id
        LEFT JOIN stations s
            ON c.station_id = s.station_id
        ORDER BY c.created_at DESC
    """)).mappings().all()

    return render_template(
        "admin_complaints.html",
        complaints=complaints
    )
@admin.route("/complaints/update/<int:complaint_id>", methods=["POST"])
@login_required
def update_complaint(complaint_id):

    if current_user.role != "ADMIN":
        abort(403)

    new_status = request.form.get("complaint_status")

    allowed_statuses = [
        "OPEN",
        "IN_PROGRESS",
        "RESOLVED",
        "REJECTED"
    ]

    if new_status not in allowed_statuses:
        abort(400)

    db.session.execute(text("""
        UPDATE complaints
        SET complaint_status = :status,
            resolved_at = CASE
                WHEN :status = 'RESOLVED' THEN NOW()
                ELSE NULL
            END
        WHERE complaint_id = :complaint_id
    """), {
        "status": new_status,
        "complaint_id": complaint_id
    })

    db.session.commit()

    flash("Complaint status updated successfully!")

    return redirect(url_for("admin.manage_complaints"))