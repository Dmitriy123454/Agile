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
    if session.get("user"):
        return redirect(url_for("trainer"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
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
                    if user['password_hash'] != hash_password(password):
                        return render_template("login.html", error="Неверный пароль"), 401
                
                # Устанавливаем сессию
                session["user"] = {
                    "id": user['id'],  # Добавляем ID из БД
                    "email": email,
                    "role": user.get('role', 'student')
                }
                
                # Загружаем рекорд из БД вместо сессии
                best_score = db.get_user_best_score(user['id'])
                session["record"] = best_score
                
                return redirect(url_for("trainer"))
                
            except Exception as e:
                print(f"Login error: {e}")
                # Fallback к старой логике при ошибке БД
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
    # Загружаем статистику из БД, если доступно
    user_stats = {}
    try:
        if session.get("user") and session["user"].get("id"):
            user_stats = db.get_user_stats(session["user"]["id"])
    except Exception as e:
        print(f"Stats loading error: {e}")
        user_stats = {}
    
    return render_template("trainer.html", 
                         record=session.get("record", 0),
                         user_stats=user_stats)

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
            
            # Обновляем рекорд в БД и сессии
            if points > session.get("record", 0):
                session["record"] = points
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
@app.route("/teacher/courses/<int:course_id>")
@login_required
@teacher_required
def teacher_course_students(course_id):
    students = db.get_course_students(course_id)
    return render_template(
        "teacher_course.html",
        course_id=course_id,
        students=students
    )

@app.route("/api/courses/<int:course_id>/students/<int:student_id>/delete", methods=["POST"])
@login_required
@teacher_required
def api_delete_student(course_id, student_id):
    try:
        db.remove_student_from_course(student_id, course_id)
        # берём обновлённый список учеников
        students = db.get_course_students(course_id)
        return jsonify({"ok": True, "students": students})
    except Exception as e:
        print(f"Delete student error: {e}")
        return jsonify({"ok": False, "error": "Не удалось удалить ученика"}), 500




# API endpoint for generating a new multiplication task
@app.route("/api/task")
@login_required
def api_task():
    a = random.randint(2, 9)
    b = random.randint(2, 9)
    return jsonify({"a": a, "b": b, "answer": a * b})

if __name__ == "__main__":
    app.run(debug=True)