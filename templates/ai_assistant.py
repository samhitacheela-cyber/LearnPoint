import os
try:
    from google import genai
except ImportError:
    genai = None

def register_ai_routes(app, get_logged_in_user, courses):
    from flask import request, jsonify
    from urllib.parse import quote_plus
    client = None
    key = os.getenv("GEMINI_API_KEY")
    if genai and key:
        client = genai.Client(api_key=key)

    @app.route("/api/ask-ai/<course_id>", methods=["POST"])
    def ask_ai(course_id):
        user=get_logged_in_user()
        if not user: return jsonify({"error":"Please login first."}),401
        if course_id not in courses: return jsonify({"error":"Course not found."}),404
        data=request.get_json(silent=True) or {}
        question=str(data.get("question","")).strip()
        if not question: return jsonify({"error":"Please enter a question."}),400
        if len(question)>2000: return jsonify({"error":"Question is too long."}),400
        if client is None: return jsonify({"error":"Gemini AI is not configured. Add GEMINI_API_KEY to the environment variables."}),503
        course=courses[course_id]
        topics=", ".join(x["title"] for x in course.get("lessons",[]))
        prompt=f"""You are the LearnPoint AI Learning Assistant.

Course: {course["title"]}
Description: {course["description"]}
Lesson topics: {topics}

Student question:
{question}

Answer clearly and accurately in simple, student-friendly language. Give examples when useful. Prioritize the current course context."""
        try:
            response=client.models.generate_content(model="gemini-3.7-flash", contents=prompt)
            queries=[f"{course['title']} {question}",question,f"{course['title']} tutorial for beginners"]
            videos=[]
            for q in queries:
                videos.append({"title":f"Search Google Videos: {q}","url":"https://www.google.com/search?tbm=vid&q="+quote_plus(q)})
                videos.append({"title":f"Search YouTube: {q}","url":"https://www.youtube.com/results?search_query="+quote_plus(q)})
            return jsonify({"answer":response.text,"videos":videos}),200
        except Exception:
            app.logger.exception("Gemini request failed")
            return jsonify({"error":"The AI assistant could not answer right now. Please try again."}),500
