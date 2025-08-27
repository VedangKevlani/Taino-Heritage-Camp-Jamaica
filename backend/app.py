from flask import Flask, request, jsonify, session
import redis
from flask_session import Session
from flask_cors import CORS
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "SuperSecretKey123")

# ----------------- Redis Session Setup -----------------
app.config["SESSION_TYPE"] = "redis"
app.config["SESSION_REDIS"] = redis.from_url(os.environ.get("REDIS_URL"))
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_USE_SIGNER"] = True
app.config["SESSION_KEY_PREFIX"] = "chat:"
Session(app)

# ----------------- CORS for frontend -----------------
CORS(app, supports_credentials=True, origins=[
    "https://tainoheritagecamp.netlify.app"
])

# ----------------- Questions -----------------
questions = [
    "Welcome guest! What is your full name?",
    "How many tickets are you purchasing?",
    "Are you with a group? If so, please provide the group name.",
    "What is your phone number?",
    "Are you booking the full experience or just the basic package?",
    "What date would you like to visit?",
    "What is your email address? Once you enter a valid email, a ticket will be sent."
]

# ----------------- Routes -----------------
@app.route("/reset", methods=["POST"])
def reset_session():
    session.clear()
    return jsonify({"status": "ok"})

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

    # ----------------- Pull session -----------------
    step = session.get("step", 0)
    answers = session.get("answers", [])

    # Append answer only if step matches answers length
    if len(answers) == step:
        answers.append(user_answer)
        session["answers"] = answers

    step += 1
    session["step"] = step

    # If finished
    if step >= len(questions):
        session.clear()
        return jsonify({"question": "All done! Your ticket has been sent to your email.", "done": True})

    return jsonify({
        "question": questions[step],
        "done": False,
        "step": step,
        "answers": answers
    })

# Debug endpoint to check session
@app.route("/debug")
def debug():
    return jsonify({
        "step": session.get("step", 0),
        "answers": session.get("answers", [])
    })

# ----------------- Run -----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
