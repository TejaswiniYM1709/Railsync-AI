from flask import Flask, render_template_string, redirect, url_for
from flask_login import current_user
from config import Config
from extensions import db, login_manager
from models import User
from routes.auth import auth
from routes.admin import admin
from routes.users import users_bp, passenger_bp
from routes.staff import staff


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    app.register_blueprint(auth)
    app.register_blueprint(admin)
    app.register_blueprint(users_bp)
    app.register_blueprint(passenger_bp)
    app.register_blueprint(staff)

    with app.app_context():
        user_count = User.query.count()
        print("Total registered users:", user_count)

    @app.route("/")
    def home():

        if current_user.is_authenticated:

            if current_user.role == "ADMIN":
                return redirect(url_for("admin.dashboard"))

            elif current_user.role == "PASSENGER":
                return redirect(url_for("passenger.dashboard"))

            elif current_user.role == "STAFF":
                return redirect(url_for("staff.dashboard"))

        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>RailSync - Smart Railway Management</title>

            <style>
                * {
                    box-sizing: border-box;
                }

                body {
                    margin: 0;
                    font-family: Arial, sans-serif;
                    background: #f1f5f9;
                    color: #142b45;
                }

                header {
                    background: #142b45;
                    color: white;
                    padding: 20px 7%;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }

                header h1 {
                    margin: 0;
                }

                header a {
                    color: white;
                    text-decoration: none;
                    background: #2878b5;
                    padding: 12px 25px;
                    border-radius: 6px;
                }

                .hero {
                    text-align: center;
                    padding: 100px 20px;
                    background: linear-gradient(
                        135deg, #142b45, #2878b5
                    );
                    color: white;
                }

                .hero h2 {
                    font-size: 45px;
                    margin-bottom: 15px;
                }

                .hero p {
                    font-size: 19px;
                    line-height: 1.7;
                }

                .hero a {
                    display: inline-block;
                    margin-top: 25px;
                    background: white;
                    color: #142b45;
                    padding: 15px 35px;
                    border-radius: 7px;
                    text-decoration: none;
                    font-weight: bold;
                }

                .features {
                    padding: 55px 8%;
                    text-align: center;
                }

                .feature-grid {
                    display: grid;
                    grid-template-columns:
                        repeat(auto-fit, minmax(220px, 1fr));
                    gap: 25px;
                    margin-top: 35px;
                }

                .feature {
                    background: white;
                    padding: 30px 20px;
                    border-radius: 12px;
                    box-shadow: 0 3px 12px #ddd;
                }

                .feature h3 {
                    color: #2878b5;
                }

                footer {
                    background: #142b45;
                    color: white;
                    text-align: center;
                    padding: 20px;
                }
            </style>
        </head>

        <body>

            <header>
                <h1>🚆 RailSync</h1>
                <a href="/login">Login</a>
            </header>

            <section class="hero">

                <h2>Welcome to RailSync</h2>

                <p>
                    Smart Railway Management &
                    Passenger Access System
                </p>

                <p>
                    Simplifying railway operations through
                    intelligent digital solutions.
                </p>

                <a href="/login">Get Started</a>

            </section>

            <section class="features">

                <h2>Our Features</h2>

                <div class="feature-grid">

                    <div class="feature">
                        <h3>🎫 Smart Ticket Booking</h3>
                        <p>Search trains and book tickets conveniently.</p>
                    </div>

                    <div class="feature">
                        <h3>📱 QR Ticket System</h3>
                        <p>Digital passenger ticket verification.</p>
                    </div>

                    <div class="feature">
                        <h3>🚉 Station Management</h3>
                        <p>Manage stations and platform allocations.</p>
                    </div>

                    <div class="feature">
                        <h3>👥 Crowd Monitoring</h3>
                        <p>Monitor passenger movement and station activity.</p>
                    </div>

                    <div class="feature">
                        <h3>⚠️ Complaint Management</h3>
                        <p>Submit and manage passenger complaints.</p>
                    </div>

                    <div class="feature">
                        <h3>📊 Admin Dashboard</h3>
                        <p>Centralized railway administration.</p>
                    </div>

                </div>

            </section>

            <footer>
                <p>© 2026 RailSync | Smart Railway Management System</p>
            </footer>

        </body>
        </html>
        """)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)