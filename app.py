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

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text, or_
from flask_swagger_ui import get_swaggerui_blueprint

from werkzeug.security import generate_password_hash, check_password_hash

import os
import secrets
import hashlib
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
load_dotenv()

try:
    from google import genai
except ImportError:
    genai = None


# --------------------------------------------------
# FLASK APPLICATION
# --------------------------------------------------

app = Flask(__name__)

app.config["SECRET_KEY"] = "learnpoint-secret-key"

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL",
    "sqlite:///database.db"
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if genai and GEMINI_API_KEY:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
else:
    gemini_client = None


# --------------------------------------------------
# SWAGGER CONFIGURATION
# --------------------------------------------------

SWAGGER_URL = "/swagger"

API_URL = "/static/swagger.json"

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        "app_name": "LearnPoint API"
    }
)

app.register_blueprint(
    swaggerui_blueprint,
    url_prefix=SWAGGER_URL
)


# --------------------------------------------------
# DATABASE MODELS
# --------------------------------------------------

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


# --------------------------------------------------
# COURSE DATA
# --------------------------------------------------

COURSE_DATA = {

    "python": {
        "title": "Python Programming",
        "description": (
            "Learn Python programming from the basics through practical examples."
        ),
        "icon": "🐍",
        "lessons": [
            {"number": 1, "title": "Introduction to Python", "description": "Learn what Python is and where it is used."},
            {"number": 2, "title": "Python Syntax & Basic Concepts", "description": "Learn Python syntax, indentation and basic concepts."},
            {"number": 3, "title": "Variables & Data Types", "description": "Learn variables and common Python data types."},
            {"number": 4, "title": "Operators", "description": "Learn arithmetic, comparison and logical operators."},
            {"number": 5, "title": "Conditional Statements", "description": "Learn if, elif and else statements."},
            {"number": 6, "title": "Loops", "description": "Learn for and while loops."},
            {"number": 7, "title": "Functions", "description": "Learn how to create and use functions."},
            {"number": 8, "title": "Lists, Tuples & Sets", "description": "Learn Python collection data types."},
            {"number": 9, "title": "Dictionaries", "description": "Learn how to work with key-value pairs."},
            {"number": 10, "title": "Strings", "description": "Learn string operations and methods."},
            {"number": 11, "title": "File Handling", "description": "Learn how to read and write files."},
            {"number": 12, "title": "Exception Handling", "description": "Learn how to handle errors using exceptions."},
            {"number": 13, "title": "Object-Oriented Programming", "description": "Learn classes, objects and OOP concepts."},
            {"number": 14, "title": "Modules & Packages", "description": "Learn how to organize and reuse Python code."},
            {"number": 15, "title": "Python Libraries", "description": "Learn how to use external Python libraries."},
            {"number": 16, "title": "NumPy Basics", "description": "Learn the basics of numerical computing with NumPy."},
            {"number": 17, "title": "Pandas Basics", "description": "Learn data manipulation using Pandas."},
            {"number": 18, "title": "Data Analysis with Python", "description": "Learn basic data analysis techniques in Python."},
            {"number": 19, "title": "Mini Project", "description": "Apply Python concepts in a practical project."}
        ]
    },

    "sql": {
        "title": "SQL & Databases",
        "description": "Learn databases and SQL queries from the fundamentals.",
        "icon": "🗄️",
        "lessons": [
            {"number": 1, "title": "Introduction to Databases", "description": "Understand databases, tables, rows and columns."},
            {"number": 2, "title": "Database Design", "description": "Learn tables, relationships, keys and normalization."},
            {"number": 3, "title": "SQL Syntax & Data Types", "description": "Learn SQL syntax and common data types."},
            {"number": 4, "title": "SELECT Queries", "description": "Learn how to retrieve information from tables."},
            {"number": 5, "title": "INSERT, UPDATE & DELETE", "description": "Learn how to add, modify and remove records."},
            {"number": 6, "title": "WHERE & Filtering", "description": "Filter records using conditions."},
            {"number": 7, "title": "ORDER BY & Sorting", "description": "Sort query results using SQL."},
            {"number": 8, "title": "Aggregate Functions", "description": "Use COUNT, SUM, AVG, MIN and MAX."},
            {"number": 9, "title": "GROUP BY & HAVING", "description": "Group data and filter grouped results."},
            {"number": 10, "title": "JOINS", "description": "Combine data from multiple related tables."},
            {"number": 11, "title": "Subqueries", "description": "Use queries inside other SQL queries."},
            {"number": 12, "title": "Views & Indexes", "description": "Learn views and indexes for efficient databases."},
            {"number": 13, "title": "Transactions", "description": "Understand commit, rollback and database transactions."},
            {"number": 14, "title": "SQL with Applications", "description": "Understand how applications interact with databases."},
            {"number": 15, "title": "Database Mini Project", "description": "Apply SQL concepts in a practical project."}
        ]
    },

    "statistics": {
        "title": "Statistics",
        "description": "Build a strong foundation in statistics and data analysis.",
        "icon": "📊",
        "lessons": [
            {"number": 1, "title": "Introduction to Statistics", "description": "Understand data, populations and samples."},
            {"number": 2, "title": "Types of Data", "description": "Learn qualitative, quantitative and categorical data."},
            {"number": 3, "title": "Data Collection", "description": "Learn basic methods of collecting and organizing data."},
            {"number": 4, "title": "Mean, Median & Mode", "description": "Learn measures of central tendency."},
            {"number": 5, "title": "Range & Percentiles", "description": "Understand basic measures for describing data."},
            {"number": 6, "title": "Variance & Standard Deviation", "description": "Understand how data is spread."},
            {"number": 7, "title": "Probability", "description": "Learn the basics of probability."},
            {"number": 8, "title": "Probability Distributions", "description": "Understand common probability distributions."},
            {"number": 9, "title": "Sampling & Sampling Methods", "description": "Learn how samples are selected from populations."},
            {"number": 10, "title": "Hypothesis Testing", "description": "Learn the basics of statistical hypothesis testing."},
            {"number": 11, "title": "Correlation", "description": "Understand relationships between variables."},
            {"number": 12, "title": "Regression", "description": "Learn how regression is used to study relationships."},
            {"number": 13, "title": "Data Interpretation", "description": "Learn how to interpret statistical results."},
            {"number": 14, "title": "Statistics with Python", "description": "Apply statistical concepts using Python."},
            {"number": 15, "title": "Statistics Mini Project", "description": "Apply statistics to a real dataset."}
        ]
    },

    "cybersecurity": {
        "title": "Cybersecurity",
        "description": "Learn the fundamentals of cybersecurity and computer security.",
        "icon": "🔐",
        "lessons": [
            {"number": 1, "title": "Cybersecurity Fundamentals", "description": "Understand threats, vulnerabilities and security."},
            {"number": 2, "title": "CIA Triad", "description": "Learn confidentiality, integrity and availability."},
            {"number": 3, "title": "Computer Networking", "description": "Understand basic networking concepts."},
            {"number": 4, "title": "Network Security", "description": "Learn basic techniques for securing networks."},
            {"number": 5, "title": "Authentication & Authorization", "description": "Understand secure access to systems."},
            {"number": 6, "title": "Passwords & Access Control", "description": "Learn secure password and access practices."},
            {"number": 7, "title": "Common Security Threats", "description": "Learn about common cybersecurity threats."},
            {"number": 8, "title": "Malware", "description": "Understand viruses, worms, trojans and ransomware."},
            {"number": 9, "title": "Phishing & Social Engineering", "description": "Learn how social engineering attacks work."},
            {"number": 10, "title": "Web Application Security", "description": "Understand common web security risks."},
            {"number": 11, "title": "Cryptography Basics", "description": "Learn basic concepts of encryption and hashing."},
            {"number": 12, "title": "Firewalls & Security Tools", "description": "Understand basic security tools and controls."},
            {"number": 13, "title": "Security Best Practices", "description": "Learn practices for safer systems and applications."},
            {"number": 14, "title": "Incident Response", "description": "Understand the basic steps of responding to incidents."},
            {"number": 15, "title": "Cybersecurity Mini Project", "description": "Apply cybersecurity concepts in a practical project."}
        ]
    },

    "machine-learning": {
        "title": "Machine Learning",
        "description": "Learn the foundations of machine learning and intelligent systems.",
        "icon": "🤖",
        "lessons": [
            {"number": 1, "title": "Introduction to Machine Learning", "description": "Understand machine learning and its applications."},
            {"number": 2, "title": "Types of Machine Learning", "description": "Learn supervised, unsupervised and reinforcement learning."},
            {"number": 3, "title": "Data Preparation", "description": "Learn how data is prepared for machine learning."},
            {"number": 4, "title": "Training & Testing", "description": "Learn how datasets are divided for ML."},
            {"number": 5, "title": "Features & Labels", "description": "Understand inputs and outputs used in ML models."},
            {"number": 6, "title": "Linear Regression", "description": "Learn the basics of regression using linear models."},
            {"number": 7, "title": "Classification", "description": "Understand classification problems."},
            {"number": 8, "title": "Decision Trees", "description": "Learn how decision tree models work."},
            {"number": 9, "title": "Clustering", "description": "Learn the basics of grouping similar data points."},
            {"number": 10, "title": "Model Evaluation", "description": "Learn how to evaluate machine learning models."},
            {"number": 11, "title": "Overfitting & Underfitting", "description": "Understand common model performance problems."},
            {"number": 12, "title": "Feature Engineering", "description": "Learn how to create useful features for models."},
            {"number": 13, "title": "Scikit-learn", "description": "Learn how to build ML models using Scikit-learn."},
            {"number": 14, "title": "Machine Learning Workflow", "description": "Understand the end-to-end ML workflow."},
            {"number": 15, "title": "Machine Learning Mini Project", "description": "Apply machine learning concepts to a dataset."}
        ]
    },

    "data-visualization": {
        "title": "Data Visualization",
        "description": "Learn how to turn data into meaningful visualizations.",
        "icon": "📈",
        "lessons": [
            {"number": 1, "title": "Introduction to Data Visualization", "description": "Understand why data visualization is important."},
            {"number": 2, "title": "Types of Charts", "description": "Learn common charts used for data analysis."},
            {"number": 3, "title": "Matplotlib", "description": "Create visualizations using Python and Matplotlib."},
            {"number": 4, "title": "Line Charts", "description": "Create and customize line charts."},
            {"number": 5, "title": "Bar Charts", "description": "Create and customize bar charts."},
            {"number": 6, "title": "Pie Charts", "description": "Create and customize pie charts."},
            {"number": 7, "title": "Scatter Plots", "description": "Visualize relationships between numerical variables."},
            {"number": 8, "title": "Histograms", "description": "Visualize the distribution of numerical data."},
            {"number": 9, "title": "Box Plots", "description": "Visualize data spread and identify outliers."},
            {"number": 10, "title": "Customizing Visualizations", "description": "Improve charts using labels, titles and formatting."},
            {"number": 11, "title": "Subplots", "description": "Display multiple visualizations together."},
            {"number": 12, "title": "Pandas Visualization", "description": "Create charts directly from Pandas data."},
            {"number": 13, "title": "Data Storytelling", "description": "Learn how to communicate insights through visualizations."},
            {"number": 14, "title": "Visualization Best Practices", "description": "Learn how to design clear and effective charts."},
            {"number": 15, "title": "Data Visualization Project", "description": "Apply visualization techniques to a dataset."}
        ]
    },

    "html-css": {
        "title": "HTML & CSS",
        "description": "Learn how to build and style modern web pages with HTML and CSS.",
        "icon": "🌐",
        "lessons": [
            {"number": 1, "title": "Introduction to Web Development", "description": "Understand how websites and web pages work."},
            {"number": 2, "title": "HTML Fundamentals", "description": "Learn the structure of an HTML document."},
            {"number": 3, "title": "HTML Elements & Attributes", "description": "Work with common HTML elements and attributes."},
            {"number": 4, "title": "Links, Images & Media", "description": "Add links, images, audio and video to web pages."},
            {"number": 5, "title": "HTML Forms", "description": "Create forms and collect user input."},
            {"number": 6, "title": "Semantic HTML", "description": "Use meaningful HTML elements for accessible pages."},
            {"number": 7, "title": "CSS Fundamentals", "description": "Learn selectors, properties and basic styling."},
            {"number": 8, "title": "Colors, Fonts & Text", "description": "Style text, colors and typography with CSS."},
            {"number": 9, "title": "Box Model", "description": "Understand margin, padding, borders and sizing."},
            {"number": 10, "title": "Flexbox", "description": "Create flexible page layouts with Flexbox."},
            {"number": 11, "title": "CSS Grid", "description": "Build two-dimensional layouts with CSS Grid."},
            {"number": 12, "title": "Responsive Design", "description": "Make websites work well on different screen sizes."},
            {"number": 13, "title": "Transitions & Effects", "description": "Add simple transitions and visual effects."},
            {"number": 14, "title": "Web Page Project", "description": "Build a complete responsive web page."}
        ]
    },

    "javascript": {
        "title": "JavaScript",
        "description": "Learn JavaScript fundamentals and how to add interactivity to web pages.",
        "icon": "⚡",
        "lessons": [
            {"number": 1, "title": "Introduction to JavaScript", "description": "Understand JavaScript and where it is used."},
            {"number": 2, "title": "Variables & Data Types", "description": "Learn variables and common JavaScript data types."},
            {"number": 3, "title": "Operators & Expressions", "description": "Work with arithmetic, comparison and logical operators."},
            {"number": 4, "title": "Conditional Statements", "description": "Use if, else and switch statements."},
            {"number": 5, "title": "Loops", "description": "Repeat tasks using for, while and related loops."},
            {"number": 6, "title": "Functions", "description": "Create reusable JavaScript functions."},
            {"number": 7, "title": "Arrays", "description": "Store and process collections of values."},
            {"number": 8, "title": "Objects", "description": "Represent structured data using objects."},
            {"number": 9, "title": "String & Array Methods", "description": "Use useful built-in methods for data manipulation."},
            {"number": 10, "title": "DOM Fundamentals", "description": "Select and modify elements on a web page."},
            {"number": 11, "title": "Events", "description": "Respond to clicks, input and other browser events."},
            {"number": 12, "title": "Forms & Validation", "description": "Handle form data and validate user input."},
            {"number": 13, "title": "Fetch API", "description": "Send requests and work with API responses."},
            {"number": 14, "title": "Async JavaScript", "description": "Understand promises and async/await."},
            {"number": 15, "title": "JavaScript Mini Project", "description": "Build an interactive browser-based project."}
        ]
    },

    "web-development": {
        "title": "Web Development",
        "description": "Understand how frontend, backend, APIs and databases work together in web applications.",
        "icon": "💻",
        "lessons": [
            {"number": 1, "title": "How the Web Works", "description": "Understand browsers, servers, requests and responses."},
            {"number": 2, "title": "Frontend & Backend", "description": "Learn the roles of frontend and backend development."},
            {"number": 3, "title": "HTTP & HTTPS", "description": "Understand web protocols and secure communication."},
            {"number": 4, "title": "HTML, CSS & JavaScript", "description": "Understand the core frontend technologies."},
            {"number": 5, "title": "Backend Fundamentals", "description": "Learn how server-side applications process requests."},
            {"number": 6, "title": "Flask Basics", "description": "Build simple web applications using Flask."},
            {"number": 7, "title": "Routes & Templates", "description": "Connect URLs to server logic and HTML templates."},
            {"number": 8, "title": "Forms & User Input", "description": "Handle data submitted by users."},
            {"number": 9, "title": "Databases in Web Apps", "description": "Understand how applications store and retrieve data."},
            {"number": 10, "title": "REST APIs", "description": "Learn how web applications communicate through APIs."},
            {"number": 11, "title": "Authentication", "description": "Understand login, sessions and protected pages."},
            {"number": 12, "title": "Application Security", "description": "Learn basic practices for securing web applications."},
            {"number": 13, "title": "Deployment Basics", "description": "Understand how web applications are deployed online."},
            {"number": 14, "title": "Git & Version Control", "description": "Track and manage application code with Git."},
            {"number": 15, "title": "Full Stack Mini Project", "description": "Build a simple full stack web application."}
        ]
    },

    "git-github": {
        "title": "Git & GitHub",
        "description": "Learn version control and how to collaborate on projects using Git and GitHub.",
        "icon": "🔗",
        "lessons": [
            {"number": 1, "title": "Introduction to Version Control", "description": "Understand why developers use version control."},
            {"number": 2, "title": "Git Installation & Setup", "description": "Set up Git and configure your identity."},
            {"number": 3, "title": "Repositories", "description": "Create and understand Git repositories."},
            {"number": 4, "title": "Git Status & Add", "description": "Track changes and stage files."},
            {"number": 5, "title": "Commits", "description": "Save project changes with meaningful commits."},
            {"number": 6, "title": "Git Log & History", "description": "Review project history and previous commits."},
            {"number": 7, "title": "Branches", "description": "Create and work with independent development branches."},
            {"number": 8, "title": "Merge & Resolve Conflicts", "description": "Combine branches and handle common conflicts."},
            {"number": 9, "title": "GitHub Basics", "description": "Understand repositories and projects on GitHub."},
            {"number": 10, "title": "Push & Pull", "description": "Synchronize local code with a remote repository."},
            {"number": 11, "title": "Clone & Fork", "description": "Copy repositories and work with existing projects."},
            {"number": 12, "title": "Pull Requests", "description": "Propose and review code changes collaboratively."},
            {"number": 13, "title": "Issues & Project Collaboration", "description": "Track tasks and collaborate with other developers."},
            {"number": 14, "title": "Git Best Practices", "description": "Learn practical habits for clean version control."},
            {"number": 15, "title": "GitHub Project", "description": "Publish and manage a project using GitHub."}
        ]
    }
}


# --------------------------------------------------
# CREATE DATABASE AND COURSES
# --------------------------------------------------

def initialize_database():

    db.create_all()

    # Add the role column to an existing database created
    # before role-based authentication was introduced.
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
        # Do not prevent the application from starting if the
        # database engine does not allow the migration statement.
        pass

    # Add password-reset fields to existing databases.
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
        # Existing deployments may use a database engine with
        # different ALTER TABLE limitations.
        pass

    # Add account monitoring fields to existing databases.
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

    # Add explicit course-completion status to existing databases.
    try:
        inspector = inspect(db.engine)
        progress_columns = {column["name"] for column in inspector.get_columns("progress")}
        if "completed" not in progress_columns:
            with db.engine.begin() as connection:
                connection.execute(text(
                    "ALTER TABLE progress ADD COLUMN completed BOOLEAN NOT NULL DEFAULT FALSE"
                ))
            with db.engine.begin() as connection:
                connection.execute(text(
                    "UPDATE progress SET completed = TRUE WHERE progress >= 100"
                ))
    except Exception:
        pass

    for course_id, course_data in COURSE_DATA.items():

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

    # Create a separate administrator account.
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


with app.app_context():

    initialize_database()


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


def _hash_reset_token(token):

    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


def _send_password_reset_email(user, reset_url):

    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM", smtp_username or "")
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

    if not smtp_host or not smtp_username or not smtp_password or not smtp_from:
        return False

    message = EmailMessage()
    message["Subject"] = "LearnPoint Password Reset"
    message["From"] = smtp_from
    message["To"] = user.email
    message.set_content(
        "Hello " + user.name + ",\n\n"
        "We received a request to reset your LearnPoint password.\n\n"
        "Use this link to create a new password:\n"
        + reset_url
        + "\n\nThis link expires in 30 minutes. If you did not request this, you can ignore this email.\n\n"
        "LearnPoint\nLearn. Practice. Grow."
    )

    with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
        if use_tls:
            server.starttls()
        server.login(smtp_username, smtp_password)
        server.send_message(message)

    return True


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
            user.reset_token_hash = _hash_reset_token(token)
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
                sent = _send_password_reset_email(user, reset_url)
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

    token_hash = _hash_reset_token(token)
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
    user.reset_token_hash = _hash_reset_token(token)
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
        sent = _send_password_reset_email(user, reset_url)
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
# GEMINI AI LEARNING ASSISTANT
# --------------------------------------------------

@app.route(
    "/api/ask-ai/<course_id>",
    methods=["POST"]
)
def ask_ai(course_id):

    user = get_logged_in_user()

    if not user:
        return jsonify(
            {
                "error": "Please login first."
            }
        ), 401

    if course_id not in COURSE_DATA:
        return jsonify(
            {
                "error": "Course not found."
            }
        ), 404

    data = request.get_json(
        silent=True
    ) or {}

    question = str(
        data.get("question", "")
    ).strip()

    if not question:
        return jsonify(
            {
                "error": "Please enter a question."
            }
        ), 400

    if len(question) > 2000:
        return jsonify(
            {
                "error": "Question is too long."
            }
        ), 400

    if gemini_client is None:
        return jsonify(
            {
                "error": (
                    "Gemini AI is not configured. "
                    "Add GEMINI_API_KEY to the environment variables."
                )
            }
        ), 503

    course_data = COURSE_DATA[course_id]

    lesson_topics = ", ".join(
        lesson["title"]
        for lesson in course_data["lessons"]
    )

    prompt = f"""
You are the LearnPoint AI Learning Assistant.

The student is currently learning:
Course: {course_data["title"]}
Course description: {course_data["description"]}
Available lesson topics: {lesson_topics}

Student question:
{question}

Answer the student's question clearly and accurately.
Use simple, student-friendly language.
Give examples when useful.
If the question is related to the current course, prioritize
that course context.
If it is unrelated, you may still answer it, but briefly
mention that it is outside the current course.
Do not claim that the answer comes from LearnPoint course
material unless it is actually provided in the context above.
"""

    try:

        response = gemini_client.models.generate_content(
            model="gemini-3.7-flash",
            contents=prompt
        )

        answer = response.text

        # Build reliable reference-search links instead of asking the AI
        # to invent video URLs. These open live Google Video and YouTube
        # search results for the student's exact question and course.
        from urllib.parse import quote_plus

        search_queries = [
            f"{course_data["title"]} {question}",
            question,
            f"{course_data["title"]} tutorial for beginners"
        ]

        videos = []

        for query in search_queries:
            videos.append(
                {
                    "title": f"Search Google Videos: {query}",
                    "url": (
                        "https://www.google.com/search?tbm=vid&q="
                        + quote_plus(query)
                    )
                }
            )
            videos.append(
                {
                    "title": f"Search YouTube: {query}",
                    "url": (
                        "https://www.youtube.com/results?search_query="
                        + quote_plus(query)
                    )
                }
            )

        return jsonify(
            {
                "answer": answer,
                "videos": videos
            }
        ), 200

    except Exception as error:

        app.logger.exception(
            "Gemini request failed"
        )

        return jsonify(
            {
                "error": (
                    "The AI assistant could not answer right now. "
                    "Please try again."
                )
            }
        ), 500


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


# ==================================================
# API - USERS
# ==================================================


# --------------------------------------------------
# GET ALL USERS
# --------------------------------------------------

@app.route(
    "/api/users",
    methods=["GET"]
)
def api_get_users():

    users = User.query.all()

    result = []

    for user in users:

        result.append(
            {
                "id": user.id,
                "name": user.name,
                "email": user.email
            }
        )

    return jsonify(result), 200


# --------------------------------------------------
# CREATE USER
# --------------------------------------------------

@app.route(
    "/api/users",
    methods=["POST"]
)
def api_create_user():

    data = request.get_json(
        force=True
    )

    if not data:

        return jsonify(
            {
                "error": "JSON body is required"
            }
        ), 400

    name = data.get(
        "name"
    )

    email = data.get(
        "email"
    )

    password = data.get(
        "password"
    )

    if not name or not email or not password:

        return jsonify(
            {
                "error": (
                    "name, email and password "
                    "are required"
                )
            }
        ), 400

    email = email.strip().lower()

    existing_user = User.query.filter_by(
        email=email
    ).first()

    if existing_user:

        return jsonify(
            {
                "error": "Email already registered"
            }
        ), 409

    user = User(
        name=name,
        email=email,
        password_hash=generate_password_hash(
            password
        )
    )

    db.session.add(user)

    db.session.commit()

    return jsonify(
        {
            "id": user.id,
            "name": user.name,
            "email": user.email
        }
    ), 201


# --------------------------------------------------
# GET USER
# --------------------------------------------------

@app.route(
    "/api/users/<int:user_id>",
    methods=["GET"]
)
def api_get_user(user_id):

    user = db.session.get(
        User,
        user_id
    )

    if not user:

        return jsonify(
            {
                "error": "User not found"
            }
        ), 404

    return jsonify(
        {
            "id": user.id,
            "name": user.name,
            "email": user.email
        }
    ), 200


# --------------------------------------------------
# UPDATE USER
# --------------------------------------------------

@app.route(
    "/api/users/<int:user_id>",
    methods=["PUT"]
)
def api_update_user(user_id):

    user = db.session.get(
        User,
        user_id
    )

    if not user:

        return jsonify(
            {
                "error": "User not found"
            }
        ), 404

    data = request.get_json(
        silent=True
    )

    if not data:

        return jsonify(
            {
                "error": "JSON body is required"
            }
        ), 400

    if "name" in data:

        user.name = data["name"]

    if "email" in data:

        new_email = data["email"].strip().lower()

        existing_user = User.query.filter(
            User.email == new_email,
            User.id != user_id
        ).first()

        if existing_user:

            return jsonify(
                {
                    "error": "Email already registered"
                }
            ), 409

        user.email = new_email

    if "password" in data:

        user.password_hash = generate_password_hash(
            data["password"]
        )

    db.session.commit()

    return jsonify(
        {
            "id": user.id,
            "name": user.name,
            "email": user.email
        }
    ), 200


# --------------------------------------------------
# DELETE USER
# --------------------------------------------------

@app.route(
    "/api/users/<int:user_id>",
    methods=["DELETE"]
)
def api_delete_user(user_id):

    user = db.session.get(
        User,
        user_id
    )

    if not user:

        return jsonify(
            {
                "error": "User not found"
            }
        ), 404

    Progress.query.filter_by(
        user_id=user_id
    ).delete()

    db.session.delete(user)

    db.session.commit()

    return jsonify(
        {
            "message": "User deleted successfully"
        }
    ), 200


# ==================================================
# API - COURSES
# ==================================================


# --------------------------------------------------
# GET ALL COURSES
# --------------------------------------------------

@app.route(
    "/api/courses",
    methods=["GET"]
)
def api_get_courses():

    courses = Course.query.all()

    result = []

    for course_item in courses:

        result.append(
            {
                "id": course_item.id,
                "title": course_item.title,
                "description": course_item.description
            }
        )

    return jsonify(result), 200


# --------------------------------------------------
# CREATE COURSE
# --------------------------------------------------

@app.route(
    "/api/courses",
    methods=["POST"]
)
def api_create_course():

    data = request.get_json(
        silent=True
    )

    if not data:

        return jsonify(
            {
                "error": "JSON body is required"
            }
        ), 400

    course_id = data.get(
        "id"
    )

    title = data.get(
        "title"
    )

    description = data.get(
        "description"
    )

    if not course_id or not title or not description:

        return jsonify(
            {
                "error": (
                    "id, title and description "
                    "are required"
                )
            }
        ), 400

    existing_course = db.session.get(
        Course,
        course_id
    )

    if existing_course:

        return jsonify(
            {
                "error": "Course already exists"
            }
        ), 409

    course_item = Course(
        id=course_id,
        title=title,
        description=description
    )

    db.session.add(course_item)

    db.session.commit()

    return jsonify(
        {
            "id": course_item.id,
            "title": course_item.title,
            "description": course_item.description
        }
    ), 201


# --------------------------------------------------
# GET COURSE
# --------------------------------------------------

@app.route(
    "/api/courses/<course_id>",
    methods=["GET"]
)
def api_get_course(course_id):

    course_item = db.session.get(
        Course,
        course_id
    )

    if not course_item:

        return jsonify(
            {
                "error": "Course not found"
            }
        ), 404

    return jsonify(
        {
            "id": course_item.id,
            "title": course_item.title,
            "description": course_item.description
        }
    ), 200


# --------------------------------------------------
# UPDATE COURSE
# --------------------------------------------------

@app.route(
    "/api/courses/<course_id>",
    methods=["PUT"]
)
def api_update_course(course_id):

    course_item = db.session.get(
        Course,
        course_id
    )

    if not course_item:

        return jsonify(
            {
                "error": "Course not found"
            }
        ), 404

    data = request.get_json(
        silent=True
    )

    if not data:

        return jsonify(
            {
                "error": "JSON body is required"
            }
        ), 400

    if "title" in data:

        course_item.title = data["title"]

    if "description" in data:

        course_item.description = data[
            "description"
        ]

    db.session.commit()

    return jsonify(
        {
            "id": course_item.id,
            "title": course_item.title,
            "description": course_item.description
        }
    ), 200


# --------------------------------------------------
# DELETE COURSE
# --------------------------------------------------

@app.route(
    "/api/courses/<course_id>",
    methods=["DELETE"]
)
def api_delete_course(course_id):

    course_item = db.session.get(
        Course,
        course_id
    )

    if not course_item:

        return jsonify(
            {
                "error": "Course not found"
            }
        ), 404

    Progress.query.filter_by(
        course_id=course_id
    ).delete()

    db.session.delete(course_item)

    db.session.commit()

    return jsonify(
        {
            "message": "Course deleted successfully"
        }
    ), 200


# ==================================================
# API - PROGRESS
# ==================================================


# --------------------------------------------------
# GET USER PROGRESS
# --------------------------------------------------

@app.route(
    "/api/users/<int:user_id>/progress",
    methods=["GET"]
)
def api_get_progress(user_id):

    user = db.session.get(
        User,
        user_id
    )

    if not user:

        return jsonify(
            {
                "error": "User not found"
            }
        ), 404

    records = Progress.query.filter_by(
        user_id=user_id
    ).all()

    result = []

    for record in records:

        result.append(
            {
                "course_id": record.course_id,
                "progress": record.progress,
                "completed": bool(record.completed)
            }
        )

    for course_id in COURSE_DATA:

        found = False

        for record in result:

            if record["course_id"] == course_id:

                found = True

                break

        if not found:

            result.append(
                {
                    "course_id": course_id,
                    "progress": 0
                }
            )

    return jsonify(result), 200


# --------------------------------------------------
# UPDATE COURSE PROGRESS
# --------------------------------------------------

@app.route(
    "/api/users/<int:user_id>/progress/<course_id>",
    methods=["PUT"]
)
def api_update_progress(
    user_id,
    course_id
):

    user = db.session.get(
        User,
        user_id
    )

    if not user:

        return jsonify(
            {
                "error": "User not found"
            }
        ), 404

    course_item = db.session.get(
        Course,
        course_id
    )

    if not course_item:

        return jsonify(
            {
                "error": "Course not found"
            }
        ), 404

    data = request.get_json(
        silent=True
    )

    if not data or "progress" not in data:

        return jsonify(
            {
                "error": "progress is required"
            }
        ), 400

    progress_value = data["progress"]

    if not isinstance(
        progress_value,
        int
    ):

        return jsonify(
            {
                "error": "progress must be an integer"
            }
        ), 400

    if progress_value < 0 or progress_value > 100:

        return jsonify(
            {
                "error": (
                    "progress must be between "
                    "0 and 100"
                )
            }
        ), 400

    record = Progress.query.filter_by(
        user_id=user_id,
        course_id=course_id
    ).first()

    if record is None:

        record = Progress(
            user_id=user_id,
            course_id=course_id,
            progress=progress_value
        )

        db.session.add(record)

    else:

        record.progress = progress_value

    db.session.commit()

    return jsonify(
        {
            "user_id": user_id,
            "course_id": course_id,
            "progress": record.progress
        }
    ), 200


# --------------------------------------------------
# RUN APPLICATION
# --------------------------------------------------

if __name__ == "__main__":

    app.run(
        debug=True
    )