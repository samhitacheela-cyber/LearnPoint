from datetime import datetime
import os
from sqlalchemy import inspect, text
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
from course_data import COURSES

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user")
    created_at = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    reset_token_hash = db.Column(db.String(64), nullable=True)
    reset_token_expires_at = db.Column(db.Integer, nullable=True)

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

class Course(db.Model):
    id = db.Column(db.String(100), primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)

class Progress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    course_id = db.Column(db.String(100), db.ForeignKey("course.id"), nullable=False)
    progress = db.Column(db.Integer, default=0)
    completed = db.Column(db.Boolean, default=False, nullable=False)
    __table_args__ = (db.UniqueConstraint("user_id", "course_id", name="unique_user_course"),)

def _add_column(table, column, definition):
    try:
        inspector = inspect(db.engine)
        columns = {c["name"] for c in inspector.get_columns(table)}
        if column not in columns:
            with db.engine.begin() as connection:
                connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))
    except Exception:
        pass

def initialize_database():
    db.create_all()
    _add_column("user", "role", "VARCHAR(20) NOT NULL DEFAULT 'user'")
    _add_column("user", "reset_token_hash", "VARCHAR(64)")
    _add_column("user", "reset_token_expires_at", "INTEGER")
    _add_column("user", "created_at", "DATETIME")
    _add_column("user", "last_login", "DATETIME")
    _add_column("progress", "completed", "BOOLEAN NOT NULL DEFAULT FALSE")
    try:
        with db.engine.begin() as connection:
            connection.execute(text("UPDATE progress SET completed = TRUE WHERE progress >= 100"))
    except Exception:
        pass
    for course_id, data in COURSES.items():
        if db.session.get(Course, course_id) is None:
            db.session.add(Course(id=course_id, title=data["title"], description=data["description"]))
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
    if Admin.query.filter_by(username=admin_username).first() is None:
        db.session.add(Admin(username=admin_username, password_hash=generate_password_hash(admin_password)))
    db.session.commit()
