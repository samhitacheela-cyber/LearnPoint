from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
from werkzeug.security import generate_password_hash
from datetime import datetime
import os

from course_data import COURSES


db = SQLAlchemy()


# ==================================================
# DATABASE MODELS
# ==================================================

class User(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    role = db.Column(
        db.String(20),
        nullable=False,
        default="user"
    )

    created_at = db.Column(
        db.DateTime,
        nullable=True,
        default=datetime.utcnow
    )

    last_login = db.Column(
        db.DateTime,
        nullable=True
    )

    reset_token_hash = db.Column(
        db.String(64),
        nullable=True
    )

    reset_token_expires_at = db.Column(
        db.Integer,
        nullable=True
    )


class Admin(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    username = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )


class Course(db.Model):
    id = db.Column(
        db.String(100),
        primary_key=True
    )

    title = db.Column(
        db.String(150),
        nullable=False
    )

    description = db.Column(
        db.Text,
        nullable=False
    )


class Progress(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    course_id = db.Column(
        db.String(100),
        db.ForeignKey("course.id"),
        nullable=False
    )

    progress = db.Column(
        db.Integer,
        default=0
    )

    completed = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "course_id",
            name="unique_user_course"
        ),
    )


# ==================================================
# DATABASE INITIALIZATION
# ==================================================

def initialize_database():
    db.create_all()

    # Add role column to older databases
    try:
        inspector = inspect(db.engine)

        user_columns = {
            column["name"]
            for column in inspector.get_columns("user")
        }

        if "role" not in user_columns:
            with db.engine.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE user "
                        "ADD COLUMN role VARCHAR(20) "
                        "NOT NULL DEFAULT 'user'"
                    )
                )

    except Exception:
        pass

    # Add password reset fields
    try:
        inspector = inspect(db.engine)

        user_columns = {
            column["name"]
            for column in inspector.get_columns("user")
        }

        with db.engine.begin() as connection:

            if "reset_token_hash" not in user_columns:
                connection.execute(
                    text(
                        "ALTER TABLE user "
                        "ADD COLUMN reset_token_hash VARCHAR(64)"
                    )
                )

            if "reset_token_expires_at" not in user_columns:
                connection.execute(
                    text(
                        "ALTER TABLE user "
                        "ADD COLUMN reset_token_expires_at INTEGER"
                    )
                )

    except Exception:
        pass

    # Add account monitoring fields
    try:
        inspector = inspect(db.engine)

        user_columns = {
            column["name"]
            for column in inspector.get_columns("user")
        }

        with db.engine.begin() as connection:

            if "created_at" not in user_columns:
                connection.execute(
                    text(
                        "ALTER TABLE user "
                        "ADD COLUMN created_at DATETIME"
                    )
                )

            if "last_login" not in user_columns:
                connection.execute(
                    text(
                        "ALTER TABLE user "
                        "ADD COLUMN last_login DATETIME"
                    )
                )

    except Exception:
        pass

    # Add course completion field
    try:
        inspector = inspect(db.engine)

        progress_columns = {
            column["name"]
            for column in inspector.get_columns("progress")
        }

        if "completed" not in progress_columns:

            with db.engine.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE progress "
                        "ADD COLUMN completed "
                        "BOOLEAN NOT NULL DEFAULT FALSE"
                    )
                )

            with db.engine.begin() as connection:
                connection.execute(
                    text(
                        "UPDATE progress "
                        "SET completed = TRUE "
                        "WHERE progress >= 100"
                    )
                )

    except Exception:
        pass

    # Create courses
    for course_id, course_data in COURSES.items():

        existing_course = db.session.get(
            Course,
            course_id
        )

        if existing_course is None:

            course = Course(
                id=course_id,
                title=course_data["title"],
                description=course_data["description"]
            )

            db.session.add(course)

    # Create administrator
    admin_username = os.getenv(
        "ADMIN_USERNAME",
        "admin"
    )

    admin_password = os.getenv(
        "ADMIN_PASSWORD",
        "admin123"
    )

    existing_admin = Admin.query.filter_by(
        username=admin_username
    ).first()

    if existing_admin is None:

        db.session.add(
            Admin(
                username=admin_username,
                password_hash=generate_password_hash(
                    admin_password
                )
            )
        )

    db.session.commit()