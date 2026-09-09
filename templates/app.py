from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    jsonify,
    flash
)

from sqlalchemy import or_
from flask_swagger_ui import get_swaggerui_blueprint
from werkzeug.security import generate_password_hash, check_password_hash

import os
import secrets
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
load_dotenv()

from database import db, User, Admin, Course, Progress, initialize_database
from course_data import COURSES
from email_utils import hash_reset_token, send_password_reset_email
from api_routes import api_bp
from ai_assistant import register_ai_routes


# --------------------------------------------------
# FLASK APPLICATION
# --------------------------------------------------

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "learnpoint-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///database.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

with app.app_context():
    initialize_database()


# --------------------------------------------------
# SWAGGER CONFIGURATION
# --------------------------------------------------

SWAGGER_URL = "/swagger"
API_URL = "/static/swagger.json"
swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={"app_name": "LearnPoint API"}
)
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)
app.register_blueprint(api_bp)

# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def get_logged_in_user():

    user_id = session.get("user_id")

    if not user_id:
        return None

    return db.session.get(
        User,
        user_id
    )


def get_course_progress(user_id):

    progress_records = Progress.query.filter_by(
        user_id=user_id
    ).all()

    progress_dict = {}

    for record in progress_records:

        progress_dict[
            record.course_id
        ] = record.progress

    for course_id in COURSE_DATA:

        if course_id not in progress_dict:

            progress_dict[course_id] = 0

    return progress_dict


def get_user_course_progress(
    user_id,
    course_id
):

    record = Progress.query.filter_by(
        user_id=user_id,
        course_id=course_id
    ).first()

    if record:

        return record.progress

    return 0


# --------------------------------------------------
# HOME
# --------------------------------------------------

@app.route("/")
def home():

    if session.get("admin_id"):
        return redirect(
            url_for("admin_dashboard")
        )

    if session.get("user_id"):
        return redirect(
            url_for("dashboard")
        )

    return redirect(
        url_for("login")
    )


# --------------------------------------------------
# REGISTER
# --------------------------------------------------

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        if not username or not email or not password or not confirm_password:

            flash(
                "Please fill in all fields.",
                "error"
            )

            return redirect(
                url_for("register")
            )

        if password != confirm_password:

            flash(
                "Passwords do not match.",
                "error"
            )

            return redirect(
                url_for("register")
            )

        existing_user = User.query.filter_by(
            email=email
        ).first()

        if existing_user:

            flash(
                "Email is already registered.",
                "error"
            )

            return redirect(
                url_for("register")
            )

        new_user = User(
            name=username,
            email=email,
            password_hash=generate_password_hash(
                password
            ),
            role="user"
        )

        db.session.add(
            new_user
        )

        db.session.commit()

        flash(
            "Registration successful. Please login.",
            "success"
        )

        return redirect(
            url_for("login")
        )

    return render_template(
        "register.html"
    )
# --------------------------------------------------
# LOGIN
# --------------------------------------------------

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        user = User.query.filter_by(
            name=username
        ).first()

        if user and check_password_hash(
            user.password_hash,
            password
        ):

            session["user_id"] = user.id
            user.last_login = datetime.utcnow()
            db.session.commit()

            return redirect(
                url_for("dashboard")
            )

        flash(
            "Invalid username or password.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    return render_template(
        "login.html"
    )
# --------------------------------------------------
# FORGOT PASSWORD
# --------------------------------------------------

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        user = User.query.filter_by(email=email).first()

        # Always show the same response so the page does not reveal
        # whether an email address is registered.
        if user:
            token = secrets.token_urlsafe(32)
            user.reset_token_hash = hash_reset_token(token)
            user.reset_token_expires_at = int(
                (datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp()
            )
            db.session.commit()

            reset_url = url_for(
                "reset_password",
                token=token,
                _external=True
            )

            try:
                sent = send_password_reset_email(user, reset_url)
            except Exception:
                app.logger.exception("Password reset email failed")
                sent = False

            if not sent:
                app.logger.warning(
                    "Password reset email is not configured. Reset URL: %s",
                    reset_url
                )

        flash(
            "If an account with that email exists, a password reset link has been sent.",
            "success"
        )
        return redirect(url_for("forgot_password"))

    return render_template("forgot_password.html")


# --------------------------------------------------
# RESET PASSWORD
# --------------------------------------------------

@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):

    token_hash = hash_reset_token(token)
    user = User.query.filter_by(
        reset_token_hash=token_hash
    ).first()

    now = int(datetime.now(timezone.utc).timestamp())

    if not user or not user.reset_token_expires_at or user.reset_token_expires_at < now:
        flash("This password reset link is invalid or has expired.", "error")
        return redirect(url_for("forgot_password"))

    if request.method == "POST":

        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if len(password) < 8:
            flash("Password must be at least 8 characters long.", "error")
            return redirect(url_for("reset_password", token=token))

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for("reset_password", token=token))

        user.password_hash = generate_password_hash(password)
        user.reset_token_hash = None
        user.reset_token_expires_at = None
        db.session.commit()

        flash("Password reset successful. Please login.", "success")
        return redirect(url_for("login"))

    return render_template("reset_password.html")


# --------------------------------------------------
# USER PROFILE
# --------------------------------------------------

@app.route("/profile", methods=["GET", "POST"])
def profile():

    user = get_logged_in_user()

    if not user:
        return redirect(url_for("login"))

    if request.method == "POST":

        action = request.form.get("action", "")

        if action == "update_profile":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()

            if not name or not email:
                flash("Name and email are required.", "error")
                return redirect(url_for("profile"))

            existing_user = User.query.filter(
                User.email == email,
                User.id != user.id
            ).first()

            if existing_user:
                flash("That email is already registered.", "error")
                return redirect(url_for("profile"))

            user.name = name
            user.email = email
            db.session.commit()
            flash("Profile updated successfully.", "success")

        elif action == "change_password":
            current_password = request.form.get("current_password", "")
            new_password = request.form.get("new_password", "")
            confirm_password = request.form.get("confirm_password", "")

            if not check_password_hash(user.password_hash, current_password):
                flash("Current password is incorrect.", "error")
                return redirect(url_for("profile"))

            if len(new_password) < 8:
                flash("New password must be at least 8 characters long.", "error")
                return redirect(url_for("profile"))

            if new_password != confirm_password:
                flash("New passwords do not match.", "error")
                return redirect(url_for("profile"))

            user.password_hash = generate_password_hash(new_password)
            db.session.commit()
            flash("Password changed successfully.", "success")

        elif action == "delete_account":
            password = request.form.get("password", "")

            if not check_password_hash(user.password_hash, password):
                flash("Incorrect password. Your account was not deleted.", "error")
                return redirect(url_for("profile"))

            Progress.query.filter_by(user_id=user.id).delete(
                synchronize_session=False
            )
            db.session.delete(user)
            db.session.commit()
            session.clear()
            flash("Your LearnPoint account has been deleted.", "success")
            return redirect(url_for("login"))

        return redirect(url_for("profile"))

    progress_records = Progress.query.filter_by(user_id=user.id).all()
    completion_map = {record.course_id: bool(record.completed) for record in progress_records}

    completed_course_items = []
    for course_id, course_data in COURSE_DATA.items():
        if completion_map.get(course_id, False):
            completed_course_items.append({
                "title": course_data["title"],
                "course_id": course_id
            })

    completed_courses = len(completed_course_items)

    return render_template(
        "profile.html",
        user=user,
        completed_courses=completed_courses,
        completed_course_items=completed_course_items,
        total_courses=len(COURSE_DATA)
    )


# --------------------------------------------------
# ADMIN LOGIN
# --------------------------------------------------

@app.route(
    "/admin/login",
    methods=["GET", "POST"]
)
def admin_login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        admin = Admin.query.filter_by(
            username=username
        ).first()

        if admin and check_password_hash(
            admin.password_hash,
            password
        ):

            session["admin_id"] = admin.id
            session.pop("user_id", None)

            return redirect(
                url_for("admin_dashboard")
            )

        flash(
            "Invalid administrator username or password.",
            "error"
        )

        return redirect(
            url_for("admin_login")
        )

    return render_template(
        "admin_login.html"
    )


# --------------------------------------------------
# ADMIN DASHBOARD
# --------------------------------------------------

@app.route("/admin")
def admin_dashboard():

    admin_id = session.get("admin_id")

    if not admin_id:
        return redirect(url_for("admin_login"))

    admin = db.session.get(Admin, admin_id)

    if not admin:
        session.pop("admin_id", None)
        return redirect(url_for("admin_login"))

    search = request.args.get("search", "").strip()

    query = User.query

    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                User.name.ilike(like),
                User.email.ilike(like)
            )
        )

    users = query.order_by(User.id.desc()).all()

    courses = Course.query.order_by(Course.id).all()

    progress_records = Progress.query.all()
    progress_map = {}
    completion_map = {}
    for record in progress_records:
        progress_map[(record.user_id, record.course_id)] = record.progress
        completion_map[(record.user_id, record.course_id)] = bool(record.completed)

    user_rows = []
    for user in users:
        completed = sum(
            1
            for course_id in COURSE_DATA
            if completion_map.get((user.id, course_id), False)
        )
        progress_values = [
            progress_map.get((user.id, course_id), 0)
            for course_id in COURSE_DATA
        ]
        overall_progress = round(
            sum(progress_values) / len(progress_values)
        ) if progress_values else 0

        user_rows.append({
            "user": user,
            "completed_courses": completed,
            "overall_progress": overall_progress
        })

    total_users = User.query.count()
    active_users = User.query.filter(User.last_login.isnot(None)).count()
    completed_courses_total = sum(
        1
        for row in user_rows
        if row["completed_courses"] == len(COURSE_DATA) and len(COURSE_DATA) > 0
    )

    return render_template(
        "admin_dashboard.html",
        admin=admin,
        users=user_rows,
        courses=courses,
        search=search,
        total_users=total_users,
        active_users=active_users,
        completed_users=completed_courses_total
    )


@app.route("/admin/users/<int:user_id>")
def admin_user_detail(user_id):

    if not session.get("admin_id"):
        return redirect(url_for("admin_login"))

    admin = db.session.get(Admin, session["admin_id"])
    user = db.session.get(User, user_id)

    if not admin:
        session.pop("admin_id", None)
        return redirect(url_for("admin_login"))

    if not user:
        flash("User not found.", "error")
        return redirect(url_for("admin_dashboard"))

    progress_records = Progress.query.filter_by(user_id=user.id).all()
    progress_map = {record.course_id: record.progress for record in progress_records}
    completion_map = {record.course_id: bool(record.completed) for record in progress_records}

    user_courses = []
    for course_id, course_data in COURSE_DATA.items():
        user_courses.append({
            "title": course_data["title"],
            "course_id": course_id,
            "progress": progress_map.get(course_id, 0),
            "completed": completion_map.get(course_id, False)
        })

    completed_courses = sum(
        1 for item in user_courses if item["completed"]
    )

    overall_progress = round(
        sum(item["progress"] for item in user_courses) / len(user_courses)
    ) if user_courses else 0

    return render_template(
        "admin_user.html",
        admin=admin,
        user=user,
        user_courses=user_courses,
        completed_courses=completed_courses,
        overall_progress=overall_progress
    )


@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
def admin_delete_user(user_id):

    if not session.get("admin_id"):
        return redirect(url_for("admin_login"))

    user = db.session.get(User, user_id)

    if not user:
        flash("User not found.", "error")
        return redirect(url_for("admin_dashboard"))

    Progress.query.filter_by(user_id=user_id).delete(
        synchronize_session=False
    )
    db.session.delete(user)
    db.session.commit()

    flash("User account deleted successfully.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/users/<int:user_id>/reset-password", methods=["POST"])
def admin_reset_user_password(user_id):

    if not session.get("admin_id"):
        return redirect(url_for("admin_login"))

    user = db.session.get(User, user_id)

    if not user:
        flash("User not found.", "error")
        return redirect(url_for("admin_dashboard"))

    token = secrets.token_urlsafe(32)
    user.reset_token_hash = hash_reset_token(token)
    user.reset_token_expires_at = int(
        (datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp()
    )
    db.session.commit()

    reset_url = url_for(
        "reset_password",
        token=token,
        _external=True
    )

    try:
        sent = send_password_reset_email(user, reset_url)
    except Exception:
        app.logger.exception("Admin password reset email failed")
        sent = False

    if sent:
        flash("Password reset link sent to the user's registered email.", "success")
    else:
        flash(
            "Email is not configured. Copy this temporary reset link (valid for 30 minutes): " + reset_url,
            "success"
        )

    return redirect(url_for("admin_user_detail", user_id=user_id))


# --------------------------------------------------
# ADMIN LOGOUT
# --------------------------------------------------

@app.route("/admin/logout")
def admin_logout():

    session.pop("admin_id", None)

    return redirect(
        url_for("admin_login")
    )


# --------------------------------------------------
# LOGOUT
# --------------------------------------------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------

@app.route("/dashboard")
def dashboard():

    user = get_logged_in_user()

    if not user:

        return redirect(
            url_for("login")
        )

    course_progress = get_course_progress(
        user.id
    )

    courses = []

    for course_id, course_data in COURSE_DATA.items():

        courses.append(
            {
                "id": course_id,
                "title": course_data["title"],
                "description": course_data["description"],
                "icon": course_data["icon"],
                "progress": course_progress.get(
                    course_id,
                    0
                )
            }
        )

    return render_template(
        "dashboard.html",
        user=user,
        courses=courses,
        course_progress=course_progress
    )


# --------------------------------------------------
# COURSE PAGE
# --------------------------------------------------

@app.route(
    "/course/<course_id>"
)
def course(course_id):

    user = get_logged_in_user()

    if not user:

        return redirect(
            url_for("login")
        )

    if course_id not in COURSE_DATA:

        return "Course not found", 404

    course_data = COURSE_DATA[
        course_id
    ]

    progress_record = Progress.query.filter_by(
        user_id=user.id,
        course_id=course_id
    ).first()

    progress = progress_record.progress if progress_record else 0
    completed = bool(progress_record.completed) if progress_record else False

    return render_template(
        "course.html",
        course_id=course_id,
        course=course_data,
        progress=progress,
        completed=completed,
        lessons=course_data["lessons"]
    )


# --------------------------------------------------
# MARK COURSE AS COMPLETED
# --------------------------------------------------

@app.route(
    "/course/<course_id>/complete",
    methods=["POST"]
)
def complete_course(course_id):

    user = get_logged_in_user()

    if not user:
        return redirect(url_for("login"))

    if course_id not in COURSE_DATA:
        return "Course not found", 404

    progress_record = Progress.query.filter_by(
        user_id=user.id,
        course_id=course_id
    ).first()

    if progress_record is None or progress_record.progress < 100:
        flash("Complete all lessons before marking this course as completed.", "error")
        return redirect(url_for("course", course_id=course_id))

    progress_record.completed = True
    db.session.commit()

    flash("Course marked as completed! ✓", "success")
    return redirect(url_for("course", course_id=course_id))


# --------------------------------------------------
# LESSON PAGE
# --------------------------------------------------

@app.route(
    "/lesson/<course_id>/<int:lesson_number>"
)
def lesson(
    course_id,
    lesson_number
):

    user = get_logged_in_user()

    if not user:

        return redirect(
            url_for("login")
        )

    if course_id not in COURSE_DATA:

        return "Course not found", 404

    course_data = COURSE_DATA[
        course_id
    ]

    lesson_data = None

    for lesson_item in course_data["lessons"]:

        if lesson_item["number"] == lesson_number:

            lesson_data = lesson_item

            break

    if lesson_data is None:

        return "Lesson not found", 404

    progress = get_user_course_progress(
        user.id,
        course_id
    )

    return render_template(
        "lesson.html",
        course_id=course_id,
        course=course_data,
        lesson=lesson_data,
        progress=progress
    )


# --------------------------------------------------
# MARK LESSON AS COMPLETE
# --------------------------------------------------

@app.route(
    "/lesson/<course_id>/<int:lesson_number>/complete",
    methods=["POST"]
)
def complete_lesson(
    course_id,
    lesson_number
):

    user = get_logged_in_user()

    if not user:

        return redirect(
            url_for("login")
        )

    if course_id not in COURSE_DATA:

        return "Course not found", 404

    lessons = COURSE_DATA[
        course_id
    ]["lessons"]

    total_lessons = len(lessons)

    if lesson_number < 1 or lesson_number > total_lessons:

        return "Lesson not found", 404

    progress_record = Progress.query.filter_by(
        user_id=user.id,
        course_id=course_id
    ).first()

    if progress_record is None:

        progress_record = Progress(
            user_id=user.id,
            course_id=course_id,
            progress=0
        )

        db.session.add(progress_record)

    completed_lessons = round(
        progress_record.progress
        * total_lessons
        / 100
    )

    if lesson_number > completed_lessons:

        completed_lessons += 1

    new_progress = round(
        completed_lessons
        / total_lessons
        * 100
    )

    if new_progress > 100:

        new_progress = 100

    progress_record.progress = new_progress

    db.session.commit()

    return redirect(
        url_for(
            "lesson",
            course_id=course_id,
            lesson_number=lesson_number
        )
    )


register_ai_routes(app, get_logged_in_user, COURSES)


# --------------------------------------------------
# RUN APPLICATION
# --------------------------------------------------

if __name__ == "__main__":

    app.run(
        debug=True
    )