from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from datetime import timedelta
import random
import hashlib
from database import db
from functools import wraps

app = Flask(__name__)
app.secret_key = "dev-secret-change-me"
app.permanent_session_lifetime = timedelta(days=7)

# -------------------- Helpers --------------------
def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def teacher_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = session.get("user")
        if not user or user.get("role") != "teacher":
            return redirect(url_for("trainer"))
        return fn(*args, **kwargs)
    return wrapper

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# -------------------- Routes --------------------
@app.route("/", methods=["GET"])
def index():
    # Если пользователь уже вошёл — ведём на тренажёр, иначе на логин
    if session.get("user"):
        return redirect(url_for("trainer"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    # Не показываем форму логина, если пользователь уже авторизован
    if request.method == "GET" and session.get("user"):
        return redirect(url_for("trainer"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if email and password:
            try:
                user = db.get_user_by_email(email)
                if not user:
                    # Авторегистрация нового пользователя
                    user_id = db.create_user(email, hash_password(password))
                    user = {'id': user_id, 'email': email}
                else:
                    # Проверяем пароль (упрощенно)
                    if user.get('password_hash') != hash_password(password):
                        return render_template("login.html", error="Неверный пароль"), 401

                # Устанавливаем сессию
                session.permanent = True
                session["user"] = {
                    "id": user['id'],            # ID из БД
                    "email": email,
                    "role": user.get('role', 'student')
                }

                # Загружаем рекорд из БД
                best_score = db.get_user_best_score(user['id'])
                session["record"] = best_score or 0

                return redirect(url_for("trainer"))

            except Exception as e:
                print(f"Login error: {e}")
                # Fallback к старой логике при ошибке БД
                session.permanent = True
                session["user"] = {"email": email}
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
    return render_template(
        "trainer.html",
        record=session.get("record", 0)
    )

@app.route("/result", methods=["POST"])
@login_required
def result():
    data = request.get_json(silent=True) or request.form
    correct = int(data.get("correct", 0))
    wrong = int(data.get("wrong", 0))
    points = int(data.get("points", correct))
    avg_time = float(data.get("avg_time", 0.0))
    total = correct + wrong
    percent = round((correct / total) * 100, 2) if total else 0.0

    try:
        # Сохраняем в БД, если есть ID пользователя
        if session.get("user") and session["user"].get("id"):
            db.save_exercise_result(session["user"]["id"], {
                "correct": correct,
                "wrong": wrong,
                "points": points,
                "avg_time": avg_time,
                "exercise_type": "multiplication_basic"
            })

            # Обновляем рекорд в сессии (и, при желании, можно обновлять в БД)
            if points > session.get("record", 0):
                session["record"] = points
                # Если есть метод обновления лучшего результата, можно раскомментировать:
                # db.update_user_best_score(session["user"]["id"], points)

    except Exception as e:
        print(f"Result saving error: {e}")
        # Fallback: сохраняем только в сессии
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

# ----- Teacher area -----
@app.route("/teacher/courses/<int:course_id>")
@login_required
@teacher_required
def teacher_course_students(course_id):
    q = request.args.get("q", "").strip() or None
    date_from = request.args.get("from") or None   # формат YYYY-MM-DD
    date_to   = request.args.get("to") or None     # формат YYYY-MM-DD (исключающая верхняя граница)
    sort      = request.args.get("sort") or "percent_desc"

    try:
        students = db.get_course_students_stats(course_id, q, date_from, date_to, sort)
    except Exception as e:
        print(f"teacher_course_students error: {e}")
        students = []

    return render_template(
        "teacher_course.html",
        course_id=course_id,
        students=students,
        q=(q or ""),
        date_from=date_from or "",
        date_to=date_to or "",
        sort=sort
    )

@app.route("/api/courses/<int:course_id>/students/<int:student_id>/delete", methods=["POST"])
@login_required
@teacher_required
def api_delete_student(course_id, student_id):
    try:
        # порядок аргументов как в твоём database.py
        db.remove_student_from_course(student_id, course_id)
        students = db.get_course_students(course_id)  # обновлённый список
        return jsonify({"ok": True, "students": students})
    except Exception as e:
        print(f"Delete student error: {e}")
        return jsonify({"ok": False, "error": "Не удалось удалить ученика"}), 500

# ----- API: задачи умножения -----
@app.route("/api/task")
@login_required
def api_task():
    a = random.randint(2, 9)
    b = random.randint(2, 9)
    return jsonify({"a": a, "b": b, "answer": a * b})

# ----- Личный кабинет -----
@app.route("/profile")
@login_required
def profile():
    user = session.get("user", {})
    email = user.get("email", "")
    record = session.get("record", 0)

    user_stats = []
    try:
        raw = None
        if user.get("id"):
            raw = db.get_user_stats(user["id"])
        if isinstance(raw, dict):
            user_stats = [raw]
        elif isinstance(raw, list):
            user_stats = [x for x in raw if isinstance(x, dict)]
        else:
            user_stats = []
    except Exception as e:
        print(f"Profile stats error: {e}")
        user_stats = []

    # ↓↓↓ ДОБАВЬ ЭТО ↓↓↓
    last_results = []
    try:
        if user.get("id"):
            # ожидается метод в database.py; limit=10
            last_results = db.get_last_results(user["id"], limit=10)
    except Exception as e:
        print(f"Profile last_results error: {e}")
        last_results = []
    # ↑↑↑ ДОБАВЬ ЭТО ↑↑↑

    return render_template(
        "profile.html",
        email=email,
        record=record,
        user_stats=user_stats,
        last_results=last_results,   # ← ВАЖНО: передаём в шаблон
    )

if __name__ == "__main__":
    app.run(debug=True)
