from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash
from database import db, User, Course, Progress

api_bp=Blueprint("api", __name__)

@api_bp.route("/api/users",methods=["GET"])
def get_users(): return jsonify([{"id":u.id,"name":u.name,"email":u.email} for u in User.query.all()])

@api_bp.route("/api/users",methods=["POST"])
def create_user():
    d=request.get_json(silent=True) or {}
    if not all(d.get(x) for x in ("name","email","password")): return jsonify({"error":"name, email and password are required"}),400
    email=d["email"].strip().lower()
    if User.query.filter_by(email=email).first(): return jsonify({"error":"Email already registered"}),409
    u=User(name=d["name"],email=email,password_hash=generate_password_hash(d["password"])); db.session.add(u); db.session.commit()
    return jsonify({"id":u.id,"name":u.name,"email":u.email}),201

@api_bp.route("/api/users/<int:user_id>",methods=["GET"])
def get_user(user_id):
    u=db.session.get(User,user_id)
    if not u:return jsonify({"error":"User not found"}),404
    return jsonify({"id":u.id,"name":u.name,"email":u.email})

@api_bp.route("/api/users/<int:user_id>",methods=["PUT"])
def update_user(user_id):
    u=db.session.get(User,user_id); d=request.get_json(silent=True) or {}
    if not u:return jsonify({"error":"User not found"}),404
    if "name" in d:u.name=d["name"]
    if "email" in d:
        email=d["email"].strip().lower()
        if User.query.filter(User.email==email,User.id!=user_id).first():return jsonify({"error":"Email already registered"}),409
        u.email=email
    if "password" in d:u.password_hash=generate_password_hash(d["password"])
    db.session.commit(); return jsonify({"id":u.id,"name":u.name,"email":u.email})

@api_bp.route("/api/users/<int:user_id>",methods=["DELETE"])
def delete_user(user_id):
    u=db.session.get(User,user_id)
    if not u:return jsonify({"error":"User not found"}),404
    Progress.query.filter_by(user_id=user_id).delete(synchronize_session=False); db.session.delete(u); db.session.commit()
    return jsonify({"message":"User deleted successfully"})

@api_bp.route("/api/courses",methods=["GET"])
def get_courses(): return jsonify([{"id":c.id,"title":c.title,"description":c.description} for c in Course.query.all()])

@api_bp.route("/api/courses",methods=["POST"])
def create_course():
    d=request.get_json(silent=True) or {}
    if not all(d.get(x) for x in ("id","title","description")):return jsonify({"error":"id, title and description are required"}),400
    if db.session.get(Course,d["id"]):return jsonify({"error":"Course already exists"}),409
    c=Course(id=d["id"],title=d["title"],description=d["description"]);db.session.add(c);db.session.commit()
    return jsonify({"id":c.id,"title":c.title,"description":c.description}),201

@api_bp.route("/api/courses/<course_id>",methods=["GET"])
def get_course(course_id):
    c=db.session.get(Course,course_id)
    if not c:return jsonify({"error":"Course not found"}),404
    return jsonify({"id":c.id,"title":c.title,"description":c.description})

@api_bp.route("/api/courses/<course_id>",methods=["PUT"])
def update_course(course_id):
    c=db.session.get(Course,course_id);d=request.get_json(silent=True) or {}
    if not c:return jsonify({"error":"Course not found"}),404
    if "title" in d:c.title=d["title"]
    if "description" in d:c.description=d["description"]
    db.session.commit();return jsonify({"id":c.id,"title":c.title,"description":c.description})

@api_bp.route("/api/courses/<course_id>",methods=["DELETE"])
def delete_course(course_id):
    c=db.session.get(Course,course_id)
    if not c:return jsonify({"error":"Course not found"}),404
    Progress.query.filter_by(course_id=course_id).delete(synchronize_session=False);db.session.delete(c);db.session.commit()
    return jsonify({"message":"Course deleted successfully"})

@api_bp.route("/api/users/<int:user_id>/progress",methods=["GET"])
def get_progress(user_id):
    if not db.session.get(User,user_id):return jsonify({"error":"User not found"}),404
    rows=Progress.query.filter_by(user_id=user_id).all()
    return jsonify([{"course_id":r.course_id,"progress":r.progress,"completed":bool(r.completed)} for r in rows])

@api_bp.route("/api/users/<int:user_id>/progress/<course_id>",methods=["PUT"])
def update_progress(user_id,course_id):
    if not db.session.get(User,user_id):return jsonify({"error":"User not found"}),404
    if not db.session.get(Course,course_id):return jsonify({"error":"Course not found"}),404
    d=request.get_json(silent=True) or {}; value=d.get("progress")
    if not isinstance(value,int) or not 0<=value<=100:return jsonify({"error":"progress must be an integer between 0 and 100"}),400
    r=Progress.query.filter_by(user_id=user_id,course_id=course_id).first()
    if not r:r=Progress(user_id=user_id,course_id=course_id);db.session.add(r)
    r.progress=value;r.completed=value>=100;db.session.commit()
    return jsonify({"user_id":user_id,"course_id":course_id,"progress":r.progress,"completed":bool(r.completed)})
