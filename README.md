# LearnPoint

Code Learning Website

## Step 1 features

- User registration and login
- User profile page
- Edit name and email
- Change password
- Forgot password / password reset by email
- Delete account with password confirmation
- Existing course progress and Gemini AI features retained
- Separate administrator login/dashboard retained

## Project structure

```text
LearnPoint/
├── app.py
├── requirements.txt
├── vercel.json
├── .env.example
├── .gitignore
├── static/
│   ├── style.css
│   ├── favicon.ico
│   ├── logo.png
│   └── swagger.json
└── templates/
    ├── admin_dashboard.html
    ├── admin_login.html
    ├── course.html
    ├── dashboard.html
    ├── forgot_password.html
    ├── lesson.html
    ├── login.html
    ├── profile.html
    ├── register.html
    └── reset_password.html
```

## Local setup

1. Create a virtual environment.
2. Install packages from `requirements.txt`.
3. Copy `.env.example` to `.env` if you want environment variables locally.
4. Set `GEMINI_API_KEY` to enable the AI assistant.
5. Configure SMTP variables to enable password-reset emails.
6. Run `python app.py`.

The app uses SQLite automatically when `DATABASE_URL` is not set. For deployment, use a persistent MySQL database and set `DATABASE_URL` in Vercel.

## Important security notes

- User passwords are stored as secure hashes; the application never displays the old password.
- Admins should reset a user's password rather than viewing it.
- Never commit `.env`, API keys, SMTP passwords, or database credentials to GitHub.

## AI Reference Videos

The course AI assistant provides the Gemini explanation and live reference-search links for the question. The links open Google Video Search and YouTube search results for the course/topic, so LearnPoint does not have to invent or store video URLs.

