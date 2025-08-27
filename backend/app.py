from flask import Flask, request, jsonify, session
from flask_session import Session
from reportlab.pdfgen import canvas
import smtplib, ssl, os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
import qrcode
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()
password = os.environ.get("EMAIL_PASS")

app = Flask(__name__)
app.secret_key = "sUp3Rs3cr3tK3y" 
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

CORS(app, supports_credentials=True, origins=[
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "https://tainoheritagecamp.netlify.app/"
])

questions = [
    "Welcome guest! What is your full name?",
    "How many tickets are you purchasing?",
    "Are you with a group? If so, please provide the group name.",
    "What is your phone number?",
    "Are you booking the full experience or just the basic package?",
    "What date would you like to visit?",
    "What is your email address? Once you enter a valid email, a ticket will be sent."
]

@app.route("/", methods=["GET"])
def hello():
    return "Hello from Flask"

# ----------------- Routes -----------------
@app.route("/reset", methods=["POST"])
def reset_session():
    session.clear()
    return jsonify({"status": "ok"})

@app.route("/ask", methods=["GET"])
def get_question():
    # Initialize session if missing
    if "current_index" not in session or "answers" not in session:
        session["current_index"] = 0
        session["answers"] = []

    idx = session["current_index"]
    print("DEBUG /ask - session:", dict(session))  # Show session contents
    print("DEBUG /ask - idx:", idx)

    if idx >= len(questions):
        return jsonify({"question": "All done! Your ticket has been sent to your email.", "done": True})

    return jsonify({"question": questions[idx], "done": False})

@app.route("/answer", methods=["POST"])
def answer():
    data = request.get_json()
    user_answer = data.get("answer", "").strip()
    if not user_answer:
        return jsonify({"question": "Please provide a valid answer.", "done": False})

    idx = session.get("current_index", 0)
    answers = session.get("answers", [])
    answers.append(user_answer)
    session["answers"] = answers
    idx += 1
    session["current_index"] = idx

    # If more questions, return next one
    if idx < len(questions):
        return jsonify({"question": questions[idx], "done": False})

    # Last question answered → generate ticket & email
    try:
        pdf_filename = generate_ticket(answers)
        email_ticket(answers[-1], pdf_filename)
    except Exception as e:
        print(f"Error generating/emailing ticket: {e}")
        session.clear()
        return jsonify({"question": "An error occurred while generating your ticket.", "done": True})

    # Clear session for next user
    session.clear()
    return jsonify({"question": "All done! Your ticket has been sent to your email.", "done": True})

# ----------------- Helper Functions -----------------
def generate_ticket(answers):
    safe_name = answers[1].replace(" ", "_")
    filename = f"Taino_HCGuest_Ticket_{safe_name}.pdf"

    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4

    # Header
    c.setFillColor(colors.black)
    c.rect(0, height - 100, width, 100, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(width / 2, height - 60, "Taino Heritage Camp Ticket")

    # Info box
    c.setFillColor(colors.lightgrey)
    c.rect(50, height - 500, width - 100, 350, fill=1)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 14)

    labels = [
        ("Name", answers[1]),
        ("Tickets", answers[2]),
        ("Group", answers[3]),
        ("Phone", answers[4]),
        ("Package", answers[5]),
        ("Date", answers[6]),
        ("Email", answers[7]),
    ]
    y = height - 120
    for label, value in labels:
        c.drawString(70, y, f"{label}: {value}")
        y -= 40

    # QR Code
    qr_data = f"Name: {answers[1]} | Tickets: {answers[2]} | Date: {answers[6]}"
    qr = qrcode.make(qr_data)
    qr_file = f"{safe_name}_qr.png"
    qr.save(qr_file)
    c.drawImage(qr_file, width - 150, height - 450, width=100, height=100)
    os.remove(qr_file)

    # Footer
    c.setFont("Helvetica-Oblique", 12)
    c.drawCentredString(width / 2, 50, "Thank you for booking with Taino Heritage Camp!")
    c.drawCentredString(width / 2, 30, "Please bring this ticket with you on arrival.")
    c.save()
    return filename

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
    app.run(port=5000, debug=True, use_reloader=True)
