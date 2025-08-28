from flask import Flask, request, jsonify, session
from flask_session import Session
from flask_cors import CORS
import redis
import tempfile
import uuid, os, smtplib, ssl
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev_secret")

# Redis config (works locally and in Render if REDIS_URL is set)
redis_url = os.getenv("REDIS_URL")
if redis_url:
    app.config["SESSION_TYPE"] = "redis"
    app.config["SESSION_REDIS"] = redis.from_url(redis_url)
else:
    # fallback to filesystem (for local testing)
    app.config["SESSION_TYPE"] = "filesystem"

# ---------------- Session Configuration ----------------
# app.config["SESSION_TYPE"] = "redis"
# app.config["SESSION_REDIS"] = redis.from_url(os.environ.get("REDIS_URL"))
# app.config["SESSION_FILE_DIR"] = tempfile.gettempdir()
# app.config["SESSION_PERMANENT"] = False
# app.config["SESSION_USE_SIGNER"] = True
# app.config["SESSION_KEY_PREFIX"] = "chat:"
Session(app)

# ---------------- CORS ----------------
CORS(app, supports_credentials=True, origins=[
    "https://tainoheritagecamp.netlify.app"
])

# ---------------- Questions ----------------
questions = [
    "Welcome guest! What is your full name?",
    "How many tickets are you purchasing?",
    "Are you with a group? If so, please provide the group name.",
    "What is your phone number?",
    "Are you booking the full experience or just the basic package?",
    "What date would you like to visit?",
    "What is your email address? Once you enter a valid email, a ticket will be sent."
]

# ---------------- In-Memory Debug Log ----------------
DEBUG_LOGS = []

def add_debug_log(msg):
    DEBUG_LOGS.append(msg)
    if len(DEBUG_LOGS) > 50:
        DEBUG_LOGS.pop(0)

# ---------------- Routes ----------------
@app.route("/reset", methods=["POST"])
def reset_session():
    session.clear()
    add_debug_log("Session reset")
    return jsonify({"status": "ok"})

@app.route("/ask", methods=["POST"])
def ask():
    step = session.get("step", 0)
    answers = session.get("answers", [])

    if step >= len(questions):
        return jsonify({
            "message": "All questions answered.",
            "done": True,
            "answers": answers
        })

    return jsonify({
        "question": questions[step],
        "done": False,
        "step": step,
        "answers": answers
    })


@app.route("/answer", methods=["POST"])
def answer():
    data = request.get_json(force=True)
    user_answer = data.get("answer")

    # Initialize session if new
    if "answers" not in session:
        session["answers"] = []
        session["current_index"] = 0

    # Record answer if not first question
    idx = session.get("current_index", 0)
    if idx > 0:
        session["answers"].append(user_answer)

    # Advance to next question
    if idx < len(questions) - 1:
        idx += 1
        session["current_index"] = idx
        session.modified = True
        return jsonify({
            "question": questions[idx],
            "step": idx,
            "answers_in_session": session["answers"]
        })
    else:
        return jsonify({
            "message": "All questions completed!",
            "answers": session["answers"]
        })


@app.route("/debug", methods=["GET"])
def debug():
    return jsonify({
        "current_index": session.get("current_index"),
        "answers_in_session": session.get("answers")
    })

@app.route("/")
def home():
    return "Ticketing agent backend is running!"

# ---------------- Helper Functions ----------------
def generate_ticket(answers):
    pdf_filename = f"ticket_{uuid.uuid4().hex}.pdf"
    qa_map = {q: a for q, a in zip(questions, answers)}

    doc = SimpleDocTemplate(pdf_filename, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Taino Heritage Camp Ticket", styles['Title']))
    story.append(Spacer(1, 12))

    for q_label in ["What is your full name?", "How many tickets are you purchasing?", "What is your email address?"]:
        if q_label in qa_map:
            story.append(Paragraph(f"{q_label.split('?')[0]}: {qa_map[q_label]}", styles['Normal']))

    story.append(Spacer(1, 12))
    story.append(Paragraph("Full Q&A:", styles['Heading2']))
    for q, a in qa_map.items():
        story.append(Paragraph(f"<b>{q}</b> {a}", styles['Normal']))

    doc.build(story)
    return pdf_filename

def email_ticket(receiver_email, pdf_file):
    port = 465
    smtp_server = "smtp.gmail.com"
    sender_email = "tainoheritagecamp@gmail.com"
    password = os.environ.get("EMAIL_PASS")

    from email.message import EmailMessage
    msg = EmailMessage()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = "Your Taino Heritage Camp Ticket"
    msg.set_content("Hello! Thank you for booking with Taino Heritage Camp.\nPlease find your ticket attached.")

    with open(pdf_file, 'rb') as f:
        msg.add_attachment(f.read(), maintype='application', subtype='pdf', filename=os.path.basename(pdf_file))

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
            server.login(sender_email, password)
            server.send_message(msg)
        add_debug_log(f"Ticket sent to {receiver_email}")
        return True
    except smtplib.SMTPException as e:
        add_debug_log(f"SMTP error: {e}")
        return False

# ---------------- Run App ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
