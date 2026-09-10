import os
import time

try:
    from google import genai
except ImportError:
    genai = None


def register_ai_routes(app, get_logged_in_user, get_courses):

    from flask import request, jsonify
    from urllib.parse import quote_plus


    client = None

    key = os.getenv("GEMINI_API_KEY")

    if genai and key:
        client = genai.Client(
            api_key=key
        )


    @app.route("/api/ask-ai/<course_id>", methods=["POST"])
    def ask_ai(course_id):

        user = get_logged_in_user()


        if not user:
            return jsonify({
                "error": "Please login first."
            }), 401



        courses = get_courses()


        if course_id not in courses:

            return jsonify({
                "error": "Course not found."
            }), 404



        course = courses.get(course_id)


        if not course:

            return jsonify({
                "error": "Course not found."
            }), 404



        data = request.get_json(
            silent=True
        ) or {}


        question = str(
            data.get("question", "")
        ).strip()



        if not question:

            return jsonify({
                "error": "Please enter a question."
            }), 400



        if len(question) > 2000:

            return jsonify({
                "error": "Question is too long."
            }), 400




        if client is None:

            return jsonify({
                "error": "Gemini AI is not configured."
            }), 503





        lessons = course.get(
            "lessons",
            []
        )


        topics = ", ".join(
            lesson.get("title", "")
            for lesson in lessons
        )



        prompt = f"""

You are LearnPoint AI Assistant.

Course:
{course.get("title")}

Description:
{course.get("description")}

Topics:
{topics}


Student Question:
{question}


Give a simple and clear explanation.
Use examples where useful.
Help the student understand the topic.

"""



        try:

            response = None


            for attempt in range(3):

                try:

                    response = client.models.generate_content(

                        model="gemini-2.0-flash",

                        contents=prompt

                    )

                    break



                except Exception as e:


                    error = str(e)


                    if (
                        "503" in error
                        or
                        "UNAVAILABLE" in error
                    ):

                        time.sleep(3)

                        continue


                    raise e





            if response is None:

                return jsonify({

                    "error":
                    "Gemini service is busy. Please try again."

                }),503





            videos = []


            searches = [

                f"{course.get('title')} {question}",

                question,

                f"{course.get('title')} tutorial"

            ]



            for search in searches:


                videos.append({

                    "title":
                    f"YouTube search: {search}",

                    "url":
                    "https://www.youtube.com/results?search_query="
                    + quote_plus(search)

                })



            return jsonify({

                "answer": response.text,

                "videos": videos

            })






        except Exception as e:


            app.logger.exception(
                "Gemini Error: %s",
                e
            )


            return jsonify({

                "error":
                "The AI assistant is temporarily unavailable. Please try again."

            }),503