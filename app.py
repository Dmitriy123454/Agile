from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from datetime import timedelta
import random

app = Flask(__name__)
app.secret_key = "dev-secret-change-me"
app.permanent_session_lifetime = timedelta(days=7)

# -------------------- Helpers --------------------
def login_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

# -------------------- Routes --------------------
@app.route("/", methods=["GET"])
def index():
    if session.get("user"):
        return redirect(url_for("trainer"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        # In a real app: validate and hash password, etc.
        if email and password:
            session["user"] = {"email": email}
            # initialize best record in session store
            session.setdefault("record", 0)
            return redirect(url_for("trainer"))
        else:
            return render_template("login.html", error="Заполните поля"), 400
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/trainer")
@login_required
def trainer():
    # Initial stats for sidebar
    return render_template("trainer.html", record=session.get("record", 0))

@app.route("/result", methods=["POST"])
@login_required
def result():
    data = request.get_json(silent=True) or request.form
    correct = int(data.get("correct", 0))
    wrong = int(data.get("wrong", 0))
    points = int(data.get("points", correct))  # points default to number of correct
    avg_time = float(data.get("avg_time", 0.0))
    total = correct + wrong
    percent = round((correct / total) * 100, 2) if total else 0.0

    # Update record in session
    if points > session.get("record", 0):
        session["record"] = points

    return render_template(
        "result.html",
        points=points,
        correct=correct,
        wrong=wrong,
        avg_time=avg_time,
        percent=percent,
        record=session.get("record", 0),
    )

# API endpoint for generating a new multiplication task
@app.route("/api/task")
@login_required
def api_task():
    a = random.randint(2, 9)
    b = random.randint(2, 9)
    return jsonify({"a": a, "b": b, "answer": a * b})

if __name__ == "__main__":
    app.run(debug=True)