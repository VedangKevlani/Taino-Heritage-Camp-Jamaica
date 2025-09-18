# backend/app.py
from flask import Flask, request, jsonify, session, make_response
from flask_session import Session
import os, tempfile, uuid
from dotenv import load_dotenv
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
import logging

load_dotenv()
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ---------------- CONFIG ----------------
app.secret_key = os.getenv("SECRET_KEY", "dev_local_secret")
app.api_key = os.getenv("GRAPHHOPPER_API_KEY")
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = tempfile.gettempdir()
app.config["SESSION_PERMANENT"] = False

# Cookie settings for cross-site
secure_cookie = os.getenv("SESSION_COOKIE_SECURE", "False").lower() == "true"
app.config["SESSION_COOKIE_SAMESITE"] = "None"
app.config["SESSION_COOKIE_SECURE"] = secure_cookie
app.config["SESSION_COOKIE_HTTPONLY"] = True

Session(app)

# Allowed origins
ALLOWED_ORIGINS = {
    "https://tainoheritagecamp.netlify.app",
    "https://taino-heritage-camp.netlify.app",
    "http://localhost:5173",
    "http://localhost:5500"
}

# Questions
questions = [
    "Welcome guest! What is your full name?",
    "How many tickets are you purchasing?",
    "Are you with a group? If so, please provide the group name.",
    "What is your phone number?",
    "Are you booking the full experience or just the basic package?",
    "What date would you like to visit?",
    "What is your email address? Once you enter a valid email, a ticket will be sent."
]

DEBUG_LOGS = []
def add_debug_log(msg):
    DEBUG_LOGS.append(msg)
    if len(DEBUG_LOGS) > 300:
        DEBUG_LOGS.pop(0)

# ---------------- CORS ----------------
@app.after_request
def set_cors_headers(response):
    origin = request.headers.get("Origin")
    if origin and origin in ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    return response

@app.before_request
def handle_options_requests():
    if request.method == "OPTIONS":
        resp = make_response()
        resp.status_code = 200
        return resp

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
    # Ensure session is initialized
    if "step" not in session:
        session["step"] = 0
        session["answers"] = []
        add_debug_log("Initialized session keys")

    step = session.get("step", 0)
    answers = session.get("answers", [])

    if step >= len(questions):
        return jsonify({"message": "All questions answered.", "done": True, "answers": answers})

    return jsonify({"question": questions[step], "done": False, "step": step, "answers": answers})

@app.route("/answer", methods=["POST"])
def answer():
    data = request.get_json(force=True) or {}
    user_answer = (data.get("answer") or "").strip()
    if user_answer == "":
        add_debug_log("Empty answer received")
        return jsonify({"error": "empty_answer", "message": "Please provide a valid answer."}), 400

    # Initialize session if missing
    if "step" not in session:
        session["step"] = 0
        session["answers"] = []

    step = session.get("step", 0)
    answers = session.get("answers", [])

    if step < len(questions):
        answers.append(user_answer)
        session["answers"] = answers
        add_debug_log(f"Answer recorded for step {step}: {user_answer}")

    step += 1
    session["step"] = step
    session.modified = True

    # If done with all questions, generate PDF and send email
    if step >= len(questions):
        pdf_file, sent = send_ticket_confirmation(answers)
        if not pdf_file:
            return jsonify({"message": "All done! Ticket generation failed.", "done": True, "answers": answers})
        if not sent:
            return jsonify({"message": "All done! Ticket generated, but email NOT sent.", "done": True, "answers": answers})
        return jsonify({"message": "All done! Your ticket has been emailed.", "done": True, "answers": answers})

    # Return next question
    return jsonify({"question": questions[step], "done": False, "step": step, "answers": answers})

@app.route("/debug", methods=["GET"])
def debug():
    return jsonify({
        "step_in_session": session.get("step", 0),
        "answers_in_session": session.get("answers", []),
        "debug_logs": DEBUG_LOGS[-100:]
    })

# ---------------- PDF + Email Helpers ----------------
def generate_ticket_pdf_canvas(answers, logo_path="html/images/Taino_Heritage_Camps.png", out_dir="/tmp"):
    try:
        pdf_filename = os.path.join(out_dir, f"ticket_{uuid.uuid4().hex}.pdf")
        width, height = (8.5*inch, 5.5*inch)
        c = canvas.Canvas(pdf_filename, pagesize=(width, height))

        # Simple theme
        park_green = colors.HexColor("#2E7D32")
        park_yellow = colors.HexColor("#FFD54F")
        dark_text = colors.HexColor("#0B3D0B")

        # Background
        c.setFillColor(park_green)
        c.rect(0, height-90, width, 90, fill=1)
        c.setFillColor(park_yellow)
        c.rect(0, height-100, width, 10, fill=1)

        # Header
        if logo_path and os.path.exists(logo_path):
            try:
                img = ImageReader(logo_path)
                iw, ih = img.getSize()
                aspect = ih / float(iw)
                logo_h = 60
                logo_w = logo_h / aspect
                c.drawImage(img, 20, height-80-30, width=logo_w, height=logo_h, mask='auto')
            except Exception:
                pass
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 24)
        c.drawString(120, height-50, "Taino Heritage Camp")

        # Answers
        left_x = 20+20
        cur_y = height-140
        c.setFont("Helvetica", 10)
        for i, label in enumerate(["Full name","Tickets","Group","Phone","Package","Visit date","Email"]):
            val = answers[i] if i < len(answers) else ""
            c.setFillColor(park_green)
            c.drawString(left_x, cur_y, f"{label}:")
            c.setFillColor(dark_text)
            c.drawString(left_x+90, cur_y, val)
            cur_y -= 18

        c.showPage()
        c.save()
        add_debug_log(f"Generated PDF: {pdf_filename}")
        return pdf_filename
    except Exception as e:
        add_debug_log(f"PDF generation error: {e}")
        return None

def email_ticket_multi(recipients, pdf_file, subject="Your Ticket", body="Thank you for booking."):
    try:
        api_key = os.getenv("SENDGRID_API_KEY")
        if not api_key:
            add_debug_log("SENDGRID_API_KEY not set")
            return False
        import base64
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition

        with open(pdf_file, "rb") as f:
            encoded_file = base64.b64encode(f.read()).decode()

        message = Mail(
            from_email="tainoheritagecamp@gmail.com",
            to_emails=recipients,
            subject=subject,
            plain_text_content=body
        )
        attachment = Attachment(FileContent(encoded_file), FileName(os.path.basename(pdf_file)), FileType("application/pdf"), Disposition("attachment"))
        message.attachment = attachment

        sg = SendGridAPIClient(api_key)
        sg.send(message)
        add_debug_log(f"Sent ticket to {recipients}")
        return True
    except Exception as e:
        add_debug_log(f"Email error: {e}")
        return False

def send_ticket_confirmation(answers):
    recipient_email = next((a for a in reversed(answers) if "@" in a and "." in a), None)
    if not recipient_email:
        add_debug_log("No valid recipient email found")
        return None, False
    pdf_file = generate_ticket_pdf_canvas(answers)
    if not pdf_file:
        return None, False
    recipients = [recipient_email, "tainoheritagecamp@gmail.com"]
    sent = email_ticket_multi(recipients, pdf_file)
    return pdf_file, sent

# ---------------- Run ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)
