from flask import Flask, request, jsonify, session
from flask_session import Session
from flask_cors import CORS
import redis, os, tempfile, uuid, ssl, smtplib
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev_secret")

# ---------------- Session Configuration ----------------
redis_url = os.getenv("REDIS_URL")
if redis_url:
    app.config["SESSION_TYPE"] = "redis"
    app.config["SESSION_REDIS"] = redis.from_url(redis_url)
else:
    app.config["SESSION_TYPE"] = "filesystem"
    app.config["SESSION_FILE_DIR"] = tempfile.gettempdir()

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_USE_SIGNER"] = True
app.config["SESSION_KEY_PREFIX"] = "chat:"
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

# ---------------- Debug Logs ----------------
DEBUG_LOGS = []

def add_debug_log(msg):
    DEBUG_LOGS.append(msg)
    if len(DEBUG_LOGS) > 50:
        DEBUG_LOGS.pop(0)

# ---------------- Routes ----------------
@app.route("/", methods=["GET"])
def home():
    return "Ticketing agent backend is running!"

@app.route("/reset", methods=["POST"])
def reset_session():
    session.clear()
    add_debug_log("Session reset")
    return jsonify({"status": "ok"})

@app.route("/ask", methods=["POST"])
def ask():
    # initialize session if not exists
    if "current_index" not in session:
        session["current_index"] = 0
        session["answers"] = []

    idx = session["current_index"]
    answers = session["answers"]

    if idx >= len(questions):
        return jsonify({
            "message": "All questions answered.",
            "done": True,
            "answers": answers
        })

    return jsonify({
        "question": questions[idx],
        "done": False,
        "step": idx,
        "answers_in_session": answers
    })

@app.route("/answer", methods=["POST"])
def answer():
    data = request.get_json(force=True)
    user_answer = (data.get("answer") or "").strip()

    if not user_answer:
        return jsonify({"question": "Please provide a valid answer.", "done": False})

    # initialize session if missing
    if "current_index" not in session:
        session["current_index"] = 0
        session["answers"] = []

    idx = session["current_index"]
    session["answers"].append(user_answer)

    # advance to next question
    idx += 1
    session["current_index"] = idx
    session.modified = True

    if idx >= len(questions):
        return jsonify({
            "message": "All questions completed!",
            "done": True,
            "answers": session["answers"]
        })

    return jsonify({
        "question": questions[idx],
        "done": False,
        "step": idx,
        "answers_in_session": session["answers"]
    })

@app.route("/debug", methods=["GET"])
def debug():
    return jsonify({
        "current_index": session.get("current_index", 0),
        "answers_in_session": session.get("answers", []),
        "debug_logs": DEBUG_LOGS[-50:]
    })

# ---------------- Helper: Ticket PDF ----------------
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

# ---------------- Run App ----------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
