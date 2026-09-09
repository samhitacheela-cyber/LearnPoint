import hashlib
import os
import smtplib
from email.message import EmailMessage

def hash_reset_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def send_password_reset_email(user, reset_url):
    host=os.getenv("SMTP_HOST")
    port=int(os.getenv("SMTP_PORT", "587"))
    username=os.getenv("SMTP_USERNAME")
    password=os.getenv("SMTP_PASSWORD")
    sender=os.getenv("SMTP_FROM", username or "")
    if not host or not username or not password or not sender:
        return False
    message=EmailMessage()
    message["Subject"]="LearnPoint Password Reset"
    message["From"]=sender
    message["To"]=user.email
    message.set_content(f"Hello {user.name},\n\nWe received a request to reset your LearnPoint password.\n\nUse this link to create a new password:\n{reset_url}\n\nThis link expires in 30 minutes.\n\nLearnPoint\nLearn. Practice. Grow.")
    with smtplib.SMTP(host, port, timeout=15) as server:
        if os.getenv("SMTP_USE_TLS", "true").lower() == "true": server.starttls()
        server.login(username, password)
        server.send_message(message)
    return True
