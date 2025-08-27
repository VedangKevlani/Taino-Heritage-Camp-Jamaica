from flask import Flask, request, jsonify, session
# import redis
from flask_session import Session
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
import uuid
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
import qrcode, smtplib, ssl, os
from flask_cors import CORS
import tempfile
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = "sUp3Rs3cr3tK3y"
# Use Redis for session storage
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_FILE_DIR"] = tempfile.gettempdir()
app.config["SESSION_USE_SIGNER"] = True
app.config["SESSION_KEY_PREFIX"] = "chat:"
Session(app)

# ✅ Proper CORS for Netlify frontend
CORS(app, supports_credentials=True, origins=[
    "https://tainoheritagecamp.netlify.app"
])


@app.route("/", methods=["GET"])
def test():
    return "This is working sir"

@app.route("/reset", methods=["POST"])
def reset_session():
    session.clear()
    return jsonify({"status": "ok"})

questions = [
    "Welcome guest! What is your full name?",
    "How many tickets are you purchasing?",
    "Are you with a group? If so, please provide the group name.",
    "What is your phone number?",
    "Are you booking the full experience or just the basic package?",
    "What date would you like to visit?",
    "What is your email address? Once you enter a valid email, a ticket will be sent."
]

@app.route("/ask", methods=["GET"])
def ask():
    step = session.get("step", 0)
    answers = session.get("answers", [])

    if step >= len(questions):
        return jsonify({"message": "All questions answered.", "done": True, "answers": answers})

    return jsonify({
        "question": questions[step],
        "done": False,
        "step": step,
        "answers": answers
    })

@app.route("/answer", methods=["POST"])
def answer():
    data = request.get_json()
    user_answer = data.get("answer", "").strip()
    if not user_answer:
        return jsonify({"question": "Please provide a valid answer.", "done": False})

    # Pull session
    step = session.get("step", 0)
    answers = session.get("answers", [])

    # Append answer only once
    if len(answers) == step:
        answers.append(user_answer)
        session["answers"] = answers

    step += 1
    session["step"] = step

    if step >= len(questions):
        session.clear()
        return jsonify({"question": "All done! Your ticket has been sent to your email.", "done": True})

    return jsonify({
        "question": questions[step],
        "done": False,
        "step": step,
        "answers": answers
    })

@app.route("/debug", methods=["GET", "POST"])
def debug():
    # Show current session info
    step = session.get("step", 0)
    answers = session.get("answers", [])

    # If POST, show the incoming data too
    incoming = {}
    if request.method == "POST":
        incoming = request.get_json() or {}

    debug_info = {
        "step_in_session": step,
        "answers_in_session": answers,
        "incoming_post_data": incoming
    }

    print("DEBUG:", debug_info)  # this will show in your server logs
    return jsonify(debug_info)

# Keep a simple in-memory log for debugging
DEBUG_LOGS = []

def add_debug_log(msg):
    """Add a message to the in-memory debug log."""
    DEBUG_LOGS.append(msg)
    # Keep only last 50 logs to avoid memory issues
    if len(DEBUG_LOGS) > 50:
        DEBUG_LOGS.pop(0)

# ----------------- Helper Functions -----------------
def generate_ticket(answers):
    pdf_filename = f"ticket_{uuid.uuid4().hex}.pdf"

    # Map answers to their corresponding questions
    qa_map = {}
    for q, a in zip(questions, answers):
        qa_map[q] = a

    doc = SimpleDocTemplate(pdf_filename, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Taino Heritage Camp Ticket", styles['Title']))
    story.append(Spacer(1, 12))

    # Now you can pull answers by question label
    if "What is your full name?" in qa_map:
        story.append(Paragraph(f"Name: {qa_map['What is your full name?']}", styles['Normal']))
    if "How many tickets are you purchasing?" in qa_map:
        story.append(Paragraph(f"Tickets: {qa_map['How many tickets are you purchasing?']}", styles['Normal']))
    if "What is your email address?" in qa_map:
        story.append(Paragraph(f"Email: {qa_map['What is your email address?']}", styles['Normal']))

    # ✅ Add all answers in case you want a full transcript
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
        print(f"Ticket sent to {receiver_email}")
        return True
    except smtplib.SMTPException as e:
        print("SMTP error:", e)
        return False

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)