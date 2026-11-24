from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from extensions import db
from models import User

auth = Blueprint("auth", __name__)


@auth.route("/register", methods=["GET", "POST"])
def register():

    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not (full_name and email and password):
            flash("Fill in your name, email and password.", "danger")
        elif "@" not in email or "." not in email.split("@")[-1]:
            flash("Enter a valid email address.", "danger")
        elif password != confirm:
            flash("Passwords do not match.", "danger")
        elif len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
        elif phone and (not phone.isdigit() or not 10 <= len(phone) <= 15):
            flash("Enter a valid phone number.", "danger")
        elif User.query.filter_by(email=email).first():
            flash("An account with this email already exists.", "danger")
        elif phone and User.query.filter_by(phone=phone).first():
            flash("An account with this phone already exists.", "danger")
        else:
            user = User(
                full_name=full_name,
                email=email,
                password_hash=generate_password_hash(password),
                phone=phone or None,
                role="PASSENGER",
                account_status="ACTIVE",
            )
            db.session.add(user)
            db.session.commit()
            flash("Registration successful. Please log in.", "success")
            return redirect(url_for("auth.login"))

    return render_template("register.html")


@auth.route("/login", methods=["GET", "POST"])
def login():

    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):

            if user.account_status != "ACTIVE":
                flash("Your account is not active.", "warning")
                return redirect(url_for("auth.login"))

            login_user(user)
            flash("Login successful!", "success")

            return redirect(url_for("home"))

        flash("Invalid email or password.", "danger")

    return render_template("login.html")


@auth.route("/logout")
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))