from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash

from database import db, User, Course, Progress


api_bp = Blueprint("api", __name__)


# -------------------------
# USERS API
# -------------------------

@api_bp.route("/api/users", methods=["GET"])
def get_users():
    users = User.query.all()

    return jsonify([
        {
            "id": u.id,
            "name": u.name,
            "email": u.email
        }
        for u in users
    ])


@api_bp.route("/api/users", methods=["POST"])
def create_user():

    data = request.get_json(silent=True) or {}

    if not all(data.get(x) for x in ("name", "email", "password")):
        return jsonify({
            "error": "name, email and password are required"
        }), 400


    email = data["email"].strip().lower()


    if User.query.filter_by(email=email).first():
        return jsonify({
            "error": "Email already registered"
        }), 409


    user = User(
        name=data["name"],
        email=email,
        password_hash=generate_password_hash(data["password"])
    )


    db.session.add(user)
    db.session.commit()


    return jsonify({
        "id": user.id,
        "name": user.name,
        "email": user.email
    }), 201



@api_bp.route("/api/users/<int:user_id>", methods=["GET"])
def get_user(user_id):

    user = db.session.get(User, user_id)


    if not user:
        return jsonify({
            "error": "User not found"
        }), 404


    return jsonify({
        "id": user.id,
        "name": user.name,
        "email": user.email
    })



@api_bp.route("/api/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):

    user = db.session.get(User, user_id)

    data = request.get_json(silent=True) or {}


    if not user:
        return jsonify({
            "error": "User not found"
        }), 404


    if "name" in data:
        user.name = data["name"]


    if "email" in data:

        email = data["email"].strip().lower()

        exists = User.query.filter(
            User.email == email,
            User.id != user_id
        ).first()


        if exists:
            return jsonify({
                "error": "Email already registered"
            }), 409


        user.email = email


    if "password" in data:
        user.password_hash = generate_password_hash(
            data["password"]
        )


    db.session.commit()


    return jsonify({
        "id": user.id,
        "name": user.name,
        "email": user.email
    })



@api_bp.route("/api/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):

    user = db.session.get(User, user_id)


    if not user:
        return jsonify({
            "error": "User not found"
        }),404


    Progress.query.filter_by(
        user_id=user_id
    ).delete(
        synchronize_session=False
    )


    db.session.delete(user)
    db.session.commit()


    return jsonify({
        "message": "User deleted successfully"
    })



# -------------------------
# COURSES API
# -------------------------

@api_bp.route("/api/courses", methods=["GET"])
def get_courses():

    courses = Course.query.all()


    return jsonify([
        {
            "id": c.id,
            "title": c.title,
            "description": c.description,
            "category": getattr(c, "category", None)
        }

        for c in courses
    ])




@api_bp.route("/api/courses", methods=["POST"])
def create_course():

    data = request.get_json(silent=True) or {}


    if not all(
        data.get(x)
        for x in ("id", "title", "description")
    ):
        return jsonify({
            "error": "id, title and description are required"
        }),400



    if db.session.get(Course, data["id"]):

        return jsonify({
            "error": "Course already exists"
        }),409



    course = Course(
        id=data["id"],
        title=data["title"],
        description=data["description"]
    )


    if hasattr(course, "category"):
        course.category = data.get("category","General")


    db.session.add(course)
    db.session.commit()


    return jsonify({
        "id": course.id,
        "title": course.title,
        "description": course.description
    }),201




@api_bp.route("/api/courses/<course_id>", methods=["GET"])
def get_course(course_id):

    course = db.session.get(
        Course,
        course_id
    )


    if not course:
        return jsonify({
            "error":"Course not found"
        }),404



    return jsonify({
        "id":course.id,
        "title":course.title,
        "description":course.description
    })




@api_bp.route("/api/courses/<course_id>", methods=["PUT"])
def update_course(course_id):

    course = db.session.get(
        Course,
        course_id
    )


    data=request.get_json(silent=True) or {}


    if not course:
        return jsonify({
            "error":"Course not found"
        }),404



    if "title" in data:
        course.title=data["title"]


    if "description" in data:
        course.description=data["description"]


    if hasattr(course,"category") and "category" in data:
        course.category=data["category"]



    db.session.commit()


    return jsonify({
        "message":"Course updated successfully"
    })




@api_bp.route("/api/courses/<course_id>", methods=["DELETE"])
def delete_course(course_id):

    course=db.session.get(
        Course,
        course_id
    )


    if not course:
        return jsonify({
            "error":"Course not found"
        }),404



    Progress.query.filter_by(
        course_id=course_id
    ).delete(
        synchronize_session=False
    )


    db.session.delete(course)
    db.session.commit()


    return jsonify({
        "message":"Course deleted successfully"
    })




# -------------------------
# PROGRESS API
# -------------------------

@api_bp.route(
    "/api/users/<int:user_id>/progress",
    methods=["GET"]
)
def get_progress(user_id):

    if not db.session.get(User,user_id):

        return jsonify({
            "error":"User not found"
        }),404



    progress = Progress.query.filter_by(
        user_id=user_id
    ).all()



    return jsonify([

        {
            "course_id":p.course_id,
            "progress":p.progress,
            "completed":bool(p.completed)
        }

        for p in progress

    ])




@api_bp.route(
    "/api/users/<int:user_id>/progress/<course_id>",
    methods=["PUT"]
)
def update_progress(user_id,course_id):

    if not db.session.get(User,user_id):
        return jsonify({
            "error":"User not found"
        }),404



    if not db.session.get(Course,course_id):
        return jsonify({
            "error":"Course not found"
        }),404



    data=request.get_json(silent=True) or {}

    value=data.get("progress")



    if not isinstance(value,int) or not 0 <= value <= 100:

        return jsonify({
            "error":"progress must be between 0 and 100"
        }),400




    progress=Progress.query.filter_by(
        user_id=user_id,
        course_id=course_id
    ).first()



    if not progress:

        progress=Progress(
            user_id=user_id,
            course_id=course_id
        )

        db.session.add(progress)



    progress.progress=value
    progress.completed=value>=100


    db.session.commit()



    return jsonify({
        "user_id":user_id,
        "course_id":course_id,
        "progress":progress.progress,
        "completed":bool(progress.completed)
    })