from flask_login import UserMixin
from extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(15), unique=True)
    role = db.Column(
        db.Enum("ADMIN", "PASSENGER", "STAFF"),
        nullable=False
    )
    account_status = db.Column(
        db.Enum("ACTIVE", "INACTIVE", "BLOCKED"),
        default="ACTIVE"
    )
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())
    updated_at = db.Column(
        db.TIMESTAMP,
        server_default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp()
    )

    def get_id(self):
        return str(self.user_id)