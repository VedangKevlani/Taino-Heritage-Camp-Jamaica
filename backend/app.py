# backend/app.py
from flask import Flask, request, jsonify, session, make_response
from flask_session import Session
import os, tempfile, uuid, ssl, smtplib
from dotenv import load_dotenv
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter

load_dotenv()

app = Flask(__name__)

# ---------------- CONFIG ----------------
# Secret (set in Render env var SECRET_KEY in production)
app.secret_key = os.getenv("SECRET_KEY", "dev_local_secret_please_change")

# Session backend (filesystem for now; change to redis for multi-instance)
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = tempfile.gettempdir()
app.config["SESSION_PERMANENT"] = False

# Cookie attributes for cross-site cookies:
# - When deployed, set SESSION_COOKIE_SECURE="True" in env to use Secure cookies.
# - For local testing over http, set SESSION_COOKIE_SECURE="False".
secure_cookie = os.getenv("SESSION_COOKIE_SECURE", "True").lower() == "true"
app.config["SESSION_COOKIE_SAMESITE"] = "None"  # required for cross-site cookies
app.config["SESSION_COOKIE_SECURE"] = secure_cookie
app.config["SESSION_COOKIE_HTTPONLY"] = True

Session(app)

# ---------------- Allowed origins ----------------
# Replace/add your exact Netlify domain(s) here if different.
ALLOWED_ORIGINS = {
    "https://tainoheritagecamp.netlify.app",
    "https://taino-heritage-camp.netlify.app",
    "http://localhost:5173",
    "http://localhost:5500"
}

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

# ---------------- Debug logs ----------------
DEBUG_LOGS = []
def add_debug_log(msg):
    DEBUG_LOGS.append(msg)
    if len(DEBUG_LOGS) > 300:
        DEBUG_LOGS.pop(0)

# ---------------- CORS / preflight handling ----------------
# We set Access-Control-Allow-Origin dynamically (echo the Origin) so browsers accept cookies.
@app.after_request
def set_cors_headers(response):
    origin = request.headers.get("Origin")
    if origin and origin in ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
    # else: do not set allow-origin (or set to none) — prevents accidental open CORS.
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    return response

@app.before_request
def handle_options_requests():
    # For CORS preflight
    if request.method == "OPTIONS":
        resp = make_response()
        resp.status_code = 200
        return resp

# ---------------- Error handler (JSON) ----------------
@app.errorhandler(Exception)
def handle_exception(e):
    add_debug_log(f"Unhandled exception: {repr(e)}")
    return jsonify({"error": "internal_server_error", "message": str(e)}), 500

# ---------------- Routes ----------------
@app.route("/", methods=["GET"])
def test():
    return "Ticketing agent backend is running."

@app.route("/reset", methods=["POST"])
def reset_session():
    session.clear()
    add_debug_log("Session reset")
    return jsonify({"status": "ok"})

@app.route("/ask", methods=["GET"])
def ask():
    # init session keys if missing
    if "step" not in session or "answers" not in session:
        session["step"] = 0
        session["answers"] = []
        add_debug_log("Initialized session keys")

    step = int(session.get("step", 0))
    answers = session.get("answers", [])

    if step >= len(questions):
        add_debug_log("Asked after completion")
        return jsonify({"message": "All questions answered.", "done": True, "answers": answers})

    add_debug_log(f"Asking question {step}: {questions[step]}")
    return jsonify({
        "question": questions[step],
        "done": False,
        "step": step,
        "answers": answers
    })

@app.route("/answer", methods=["POST"])
def answer():
    data = request.get_json(force=True) or {}
    user_answer = (data.get("answer") or "").strip()

    if user_answer == "":
        add_debug_log("Empty answer received")
        return jsonify({"error": "empty_answer", "message": "Please provide a valid answer."}), 400

    # ensure session initialized
    if "step" not in session or "answers" not in session:
        session["step"] = 0
        session["answers"] = []
        add_debug_log("Session auto-initialized on /answer")

    step = int(session.get("step", 0))
    answers = session.get("answers", [])

    # Append answer only if still within questions length
    if step < len(questions):
        answers.append(user_answer)
        session["answers"] = answers
        add_debug_log(f"Answer recorded for step {step}: {user_answer}")
    else:
        add_debug_log(f"Received answer but step {step} already >= questions length")

    # Advance step
    step += 1
    session["step"] = step
    session.modified = True

    # Completed flow
    if step >= len(questions):
        add_debug_log("All questions answered; returning done")
        return jsonify({"message": "All done! Thank you.", "done": True, "answers": session.get("answers", [])})

    # Otherwise return next question (safe index)
    next_q = questions[step]
    add_debug_log(f"Asking next question {step}: {next_q}")
    return jsonify({
        "question": next_q,
        "done": False,
        "step": step,
        "answers": session.get("answers", [])
    })

@app.route("/debug", methods=["GET"])
def debug():
    return jsonify({
        "step_in_session": session.get("step", 0),
        "answers_in_session": session.get("answers", []),
        "debug_logs": DEBUG_LOGS[-100:]
    })

# ---------------- Ticket/email helpers (unchanged) ----------------
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
    password = os.getenv("EMAIL_PASS")

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

# ---------------- Run (local) ----------------
if __name__ == "__main__":
    host = "0.0.0.0"
    port = int(os.getenv("PORT", 5000))
    app.run(host=host, port=port, debug=False)
