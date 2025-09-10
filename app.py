import csv
import os
from flask import Flask, render_template, request, redirect, url_for, session, abort, flash

# --------------------------
# Config
# --------------------------
app = Flask(__name__, static_folder="static", template_folder="templates")
# Use a strong secret key in production (e.g., from env var)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-me")

QUESTIONS_CSV = os.environ.get("QUESTIONS_CSV", "questions.csv")


# --------------------------
# Data loading
# --------------------------
def load_questions(csv_path):
    questions = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        # Expected columns: id,question,option_A,option_B,option_C,option_D,correct
        for row in reader:
            q = {
                "id": row.get("id", "").strip(),
                "question": row.get("question", "").strip(),
                "options": {
                    "A": row.get("option_A", "").strip(),
                    "B": row.get("option_B", "").strip(),
                    "C": row.get("option_C", "").strip(),
                    "D": row.get("option_D", "").strip(),
                },
                "correct": row.get("correct", "").strip().upper(),
            }
            # Basic validation
            if not q["question"] or q["correct"] not in {"A", "B", "C", "D"}:
                continue
            questions.append(q)
    if not questions:
        raise RuntimeError("No valid questions loaded from CSV.")
    return questions


# Cache questions in memory on startup
try:
    QUESTIONS = load_questions(QUESTIONS_CSV)
except Exception as e:
    print(f"ERROR loading questions: {e}")
    QUESTIONS = []


# --------------------------
# Helpers
# --------------------------
def init_quiz_state():
    session["current_index"] = 0
    session["score"] = 0
    session["answers"] = []  # list of dicts: {id, selected, correct}


def require_login():
    if "username" not in session:
        return False
    return True


# --------------------------
# Routes
# --------------------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        if not username:
            flash("Please enter your name to continue.")
            return render_template("login.html")
        session["username"] = username
        init_quiz_state()
        return redirect(url_for("quiz"))
    return render_template("login.html")


@app.route("/start")
def start():
    if not require_login():
        return redirect(url_for("login"))
    init_quiz_state()
    return redirect(url_for("quiz"))


@app.route("/quiz", methods=["GET"])
def quiz():
    if not require_login():
        return redirect(url_for("login"))
    idx = session.get("current_index", 0)
    if idx >= len(QUESTIONS):
        return redirect(url_for("result"))
    q = QUESTIONS[idx]
    return render_template(
        "quiz.html",
        question=q["question"],
        options=q["options"],
        qnum=idx + 1,
        total=len(QUESTIONS),
    )


@app.route("/answer", methods=["POST"])
def answer():
    if not require_login():
        return redirect(url_for("login"))
    choice = request.form.get("choice", "").upper()
    idx = session.get("current_index", 0)
    if idx >= len(QUESTIONS):
        return redirect(url_for("result"))

    q = QUESTIONS[idx]
    correct = q["correct"]

    # Save answer
    answers = session.get("answers", [])
    answers.append({
        "id": q["id"],
        "question": q["question"],
        "selected": choice,
        "correct": correct,
        "is_correct": choice == correct
    })
    session["answers"] = answers

    # Update score
    if choice == correct:
        session["score"] = session.get("score", 0) + 1

    # Next question
    session["current_index"] = idx + 1

    # If finished, go to result
    if session["current_index"] >= len(QUESTIONS):
        return redirect(url_for("result"))
    return redirect(url_for("quiz"))


@app.route("/result")
def result():
    if not require_login():
        return redirect(url_for("login"))
    total = len(QUESTIONS)
    score = session.get("score", 0)
    answers = session.get("answers", [])
    return render_template("result.html", total=total, score=score, answers=answers)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# --------------------------
# Entry
# --------------------------
if __name__ == "__main__":
    if not QUESTIONS:
        raise SystemExit("No questions loaded. Check your CSV file and restart.")
    # Run on localhost:5000
    app.run(debug=True)
