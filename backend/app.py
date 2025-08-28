# backend/app.py
from flask import Flask, request, jsonify, session, make_response
from flask_session import Session
import os, tempfile, uuid, ssl, smtplib
from dotenv import load_dotenv
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import mm, inch
from reportlab.lib.utils import ImageReader
from email.message import EmailMessage
import mimetypes
import logging

logger = logging.getLogger(__name__)

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
        pdf_file, success = send_ticket_confirmation(answers)
    
        if not success:
            add_debug_log("Failed to send ticket to guest or host")
            return jsonify({"error": "ticket_error", "message": "Ticket generation or email failed."}), 500
        
        add_debug_log(f"Ticket successfully sent; PDF: {pdf_file}")
        return jsonify({"message": "All done! Your ticket has been emailed.", "done": True, "answers": answers})

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
def generate_ticket_pdf_canvas(answers, logo_path="html/images/Taino_Heritage_Camps.png", out_dir="/tmp"):
    """
    Generate a styled ticket PDF using reportlab.canvas.
    - answers: list of strings (same order as questions)
    - logo_path: optional path to a logo image to include
    - out_dir: directory to write the PDF into (Render: /tmp works)
    Returns full filepath to the generated PDF.
    """
    try:
        # File name
        pdf_filename = os.path.join(out_dir, f"ticket_{uuid.uuid4().hex}.pdf")

        # Canvas setup
        width, height = (8.5 * inch, 5.5 * inch)  # landscape-ish ticket size
        c = canvas.Canvas(pdf_filename, pagesize=(width, height))

        # Theme colors (park green / yellow)
        park_green = colors.HexColor("#2E7D32")   # deep green
        park_yellow = colors.HexColor("#FFD54F")  # warm yellow
        dark_text = colors.HexColor("#0B3D0B")    # dark green for text

        # Background band
        c.setFillColor(park_green)
        c.rect(0, height - 90, width, 90, fill=1, stroke=0)

        # Decorative yellow stripe
        c.setFillColor(park_yellow)
        c.rect(0, height - 100, width, 10, fill=1, stroke=0)

        # Logo (if available) — left side of header
        logo_x = 20
        logo_y = height - 80
        logo_h = 60
        if logo_path and os.path.exists(logo_path):
            try:
                img = ImageReader(logo_path)
                iw, ih = img.getSize()
                aspect = ih / float(iw)
                logo_w = logo_h / aspect
                c.drawImage(img, logo_x, logo_y - logo_h/2, width=logo_w, height=logo_h, mask='auto')
            except Exception as e:
                logger.exception("Failed drawing logo: %s", e)

        # Header text (park name)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 24)
        c.drawString(120, height - 50, "Taino Heritage Camp")

        # Subheader / tagline
        c.setFont("Helvetica", 10)
        c.drawString(120, height - 68, "Experience Jamaica's history, nature, and culture")

        # Ticket box
        margin = 20
        box_y = 40
        box_h = height - 160
        c.setFillColor(colors.white)
        c.roundRect(margin, box_y, width - 2*margin, box_h, 8, fill=1, stroke=0)

        # Horizontal dividing line
        c.setStrokeColor(park_green)
        c.setLineWidth(1)
        c.line(margin + 10, box_y + box_h - 30, width - margin - 10, box_y + box_h - 30)

        # Draw key fields on the left (name, tickets, date, phone)
        left_x = margin + 20
        cur_y = box_y + box_h - 50
        c.setFillColor(dark_text)
        c.setFont("Helvetica-Bold", 12)
        # labels with values from answers — be defensive with indexes
        label_font = "Helvetica-Bold"
        value_font = "Helvetica"
        fields = [
            ("Full name", answers[0] if len(answers) > 0 else ""),
            ("Tickets", answers[1] if len(answers) > 1 else ""),
            ("Group", answers[2] if len(answers) > 2 else ""),
            ("Phone", answers[3] if len(answers) > 3 else ""),
            ("Package", answers[4] if len(answers) > 4 else ""),
            ("Visit date", answers[5] if len(answers) > 5 else ""),
            ("Email", answers[6] if len(answers) > 6 else "")
        ]

        for label, value in fields:
            c.setFont(label_font, 9)
            c.setFillColor(park_green)
            c.drawString(left_x, cur_y, f"{label}:")
            c.setFont(value_font, 10)
            c.setFillColor(dark_text)
            c.drawString(left_x + 90, cur_y, str(value))
            cur_y -= 18

        # Right side: ticket details / barcode-like box
        right_x = width - margin - 220
        right_y = box_y + box_h - 40
        c.setFont("Helvetica-Bold", 18)
        c.setFillColor(park_green)
        c.drawString(right_x, right_y, "Admission Ticket")
        c.setFont("Helvetica", 10)
        c.setFillColor(dark_text)
        c.drawString(right_x, right_y - 22, "Taino Heritage Camp · Jamaica")

        # Simple perforation / decorative barcode block
        barcode_x = right_x
        barcode_y = right_y - 70
        c.setFillColor(park_yellow)
        c.rect(barcode_x, barcode_y, 200, 40, fill=1, stroke=0)
        c.setFillColor(dark_text)
        c.setFont("Courier-Bold", 12)
        # create a pseudo ticket code
        ticket_code = f"THC-{uuid.uuid4().hex[:8].upper()}"
        c.drawString(barcode_x + 10, barcode_y + 12, ticket_code)

        # Footer: small terms
        foot_y = box_y + 10
        c.setFont("Helvetica-Oblique", 8)
        c.setFillColor(colors.grey)
        c.drawString(margin + 20, foot_y, "Please bring this ticket on the day of your visit. Non-transferable. Subject to park rules.")

        # Decorative plant icon (green circle)
        c.setFillColor(park_green)
        c.circle(width - margin - 30, foot_y + 8, 8, fill=1, stroke=0)

        # finalize
        c.showPage()
        c.save()
        add_debug_log(f"Generated PDF: {pdf_filename}")
        return pdf_filename

    except Exception as exc:
        logger.exception("generate_ticket_pdf_canvas failed: %s", exc)
        add_debug_log(f"PDF generation error: {exc}")

def email_ticket_multi(recipients, pdf_file, subject="Your Taino Heritage Camp Ticket", body="Thank you for booking with Taino Heritage Camp. See attached ticket."):
    """
    Send the given pdf_file to the list of recipients.
    recipients: list of email addresses
    """
    try:
        port = 465
        smtp_server = "smtp.gmail.com"
        sender_email = "vibranzmagazine@gmail.com"
        password = os.getenv("EMAIL_PASS")  # must be set

        if not password:
            add_debug_log("EMAIL_PASS env var not set; cannot send email")
            raise RuntimeError("EMAIL_PASS not set")

        # build message
        msg = EmailMessage()
        msg["From"] = sender_email
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = subject
        msg.set_content(body)

        # attach PDF
        with open(pdf_file, "rb") as f:
            data = f.read()
            maintype, subtype = ("application", "pdf")
            msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=os.path.basename(pdf_file))

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
            server.login(sender_email, password)
            # send to all recipients explicitly
            server.send_message(msg, from_addr=sender_email, to_addrs=recipients)

        add_debug_log(f"Sent ticket to: {recipients}")
        return True

    except Exception as e:
        logger.exception("Failed to send email: %s", e)
        add_debug_log(f"Email error: {e}")
        return False
    
def send_ticket_confirmation(answers, logo_path=None):
    """
    Convenience wrapper:
    - generates the PDF
    - emails it to the booking email (assumed last answer) and host
    Returns tuple (pdf_file, success_bool)
    """
    try:
        # defensive: ensure answers exist
        if not answers or len(answers) == 0:
            add_debug_log("send_ticket_confirmation called with empty answers")
            return None, False

        # assume email is the last item (index 6 if full flow)
        recipient_email = None
        # try the last non-empty value that looks like an email
        for a in reversed(answers):
            if isinstance(a, str) and "@" in a and "." in a:
                recipient_email = a.strip()
                break

        if not recipient_email:
            add_debug_log("No recipient email found in answers; aborting send")
            return None, False

        pdf_file = generate_ticket_pdf_canvas(answers, logo_path=logo_path)

        recipients = [recipient_email, "tainoheritagecamp@gmail.com"]
        subject = "Taino Heritage Camp — Your Ticket"
        body = f"Hello,\n\nThank you for booking with Taino Heritage Camp. Your ticket is attached.\n\nSee you soon!\nTaino Heritage Camp"

        sent = email_ticket_multi(recipients, pdf_file, subject=subject, body=body)
        return pdf_file, sent

    except Exception as exc:
        logger.exception("send_ticket_confirmation failed: %s", exc)
        return None, False

# ---------------- Run (local) ----------------
if __name__ == "__main__":
    host = "0.0.0.0"
    port = int(os.getenv("PORT", 5000))
    app.run(host=host, port=port, debug=False)
