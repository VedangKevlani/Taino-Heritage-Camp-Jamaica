from flask import Flask, request, jsonify, session
from flask_session import Session
from flask_cors import CORS
import tempfile
import uuid, os, smtplib, ssl
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
# app.secret_key = os.environ.get("SECRET_KEY", "devkey")

# # ---------------- Session Configuration ----------------
# app.config["SESSION_TYPE"] = "filesystem"
# app.config["SESSION_FILE_DIR"] = tempfile.gettempdir()
# app.config["SESSION_PERMANENT"] = False
# app.config["SESSION_USE_SIGNER"] = True
# app.config["SESSION_KEY_PREFIX"] = "chat:"
# Session(app)

# # ---------------- CORS ----------------
# # Add your Netlify domain and localhost for testing
# CORS(app, supports_credentials=True, origins=[
#     "https://tainoheritagecamp.netlify.app",
#     "http://localhost:5173",
#     "http://localhost:5500"
# ])

# Secret key for sessions
app.secret_key = "sUp3Rs3cr3tK3y"

# Configure server-side session
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_COOKIE_SAMESITE"] = "None"   # Important for cross-origin
app.config["SESSION_COOKIE_SECURE"] = True       # Render uses HTTPS

Session(app)

# Allow frontend domain to send cookies
CORS(app, supports_credentials=True, origins=["https://taino-heritage-camp.netlify.app"])

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
    if len(DEBUG_LOGS) > 200:
        DEBUG_LOGS.pop(0)

# ---------------- Error handler (returns JSON instead of HTML) ----------------
@app.errorhandler(Exception)
def handle_exception(e):
    add_debug_log(f"Unhandled exception: {repr(e)}")
    # Return JSON for easier frontend parsing
    return jsonify({"error": "internal_server_error", "message": str(e)}), 500

# ---------------- Routes ----------------
@app.route("/", methods=["GET"])
def test():
    return "This is working sir"

@app.route("/reset", methods=["POST"])
def reset_session():
    session.clear()
    add_debug_log("Session reset")
    return jsonify({"status": "ok"})

@app.route("/ask", methods=["GET"])
def ask():
    # If new session, start at question 0
    if "index" not in session:
        session["index"] = 0
    idx = session["index"]
    return jsonify({"question": questions[idx]})

@app.route("/answer", methods=["POST"])
def answer():
    data = request.json
    if "answers" not in session:
        session["answers"] = []

    # Store answer
    session["answers"].append(data.get("answer", ""))
    session.modified = True

    # Move to next question
    session["index"] += 1
    idx = session["index"]

    if idx >= len(questions):
        return jsonify({"done": True, "answers": session["answers"]})

    return jsonify({"question": questions[idx], "done": False})

@app.route("/")
def home():
    return "Backend is running!"

@app.route("/debug", methods=["GET"])
def debug():
    return jsonify({
        "step_in_session": session.get("step", 0),
        "answers_in_session": session.get("answers", []),
        "debug_logs": DEBUG_LOGS[-50:]
    })

# ---------------- Helper Functions (ticket/email) ----------------
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

# ---------------- Run App (local) ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
