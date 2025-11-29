import psycopg2
import os
from contextlib import contextmanager
from config import Config


class DatabaseManager:
    @contextmanager
    def get_connection(self):
        """Контекстный менеджер для подключения к БД"""
        conn = psycopg2.connect(Config.DATABASE_URL)
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Database error: {e}")
            raise e
        finally:
            conn.close()

    def create_user(self, email, password_hash, role='student', first_name='', last_name=''):
        """Создание нового пользователя"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO users (email, password_hash, role, first_name, last_name)
                    VALUES (%s, %s, %s, %s, %s) RETURNING id
                """, (email, password_hash, role, first_name, last_name))
                return cur.fetchone()[0]

    def get_user_by_email(self, email):
        """Получение пользователя по email"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, email, password_hash, role, first_name, last_name 
                    FROM users WHERE email = %s
                """, (email,))
                result = cur.fetchone()
                if result:
                    return {
                        'id': result[0],
                        'email': result[1],
                        'password_hash': result[2],
                        'role': result[3],
                        'first_name': result[4],
                        'last_name': result[5]
                    }
                return None

    def save_exercise_result(self, user_id: int, payload: dict):
        """
        payload = {
            correct: int,
            wrong: int,
            points: int,       # -> total_points
            avg_time: float,   # -> average_time
            exercise_type: str
        }
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO exercise_results
                        (user_id, exercise_type, correct_count, wrong_count, total_points, average_time, completed_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                """, (
                    user_id,
                    payload.get("exercise_type", "multiplication_basic"),
                    int(payload.get("correct", 0)),
                    int(payload.get("wrong", 0)),
                    int(payload.get("points", 0)),         # <-- total_points
                    float(payload.get("avg_time", 0.0)),   # <-- average_time
                ))

    def get_user_best_score(self, user_id, exercise_type='multiplication_basic'):
        """Получение лучшего результата пользователя (максимум очков)"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COALESCE(MAX(total_points), 0)
                    FROM exercise_results 
                    WHERE user_id = %s AND exercise_type = %s
                """, (user_id, exercise_type))
                result = cur.fetchone()
                return result[0] or 0

    def get_user_stats(self, user_id, exercise_type='multiplication_basic'):
        """
        Получение общей статистики (и последние 10 попыток — будет удобно, если понадобятся).
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        COUNT(*) AS total_sessions,
                        COALESCE(SUM(correct_count), 0) AS total_correct,
                        COALESCE(SUM(wrong_count), 0) AS total_wrong,
                        COALESCE(MAX(total_points), 0) AS overall_best
                    FROM exercise_results 
                    WHERE user_id = %s AND exercise_type = %s
                """, (user_id, exercise_type))
                row = cur.fetchone()
                total_sessions = row[0] or 0
                total_correct = row[1] or 0
                total_wrong = row[2] or 0
                overall_best = row[3] or 0

                cur.execute("""
                    SELECT 
                        completed_at,
                        correct_count,
                        wrong_count,
                        total_points,
                        average_time
                    FROM exercise_results
                    WHERE user_id = %s AND exercise_type = %s
                    ORDER BY completed_at DESC
                    LIMIT 10
                """, (user_id, exercise_type))
                rows = cur.fetchall()

        rows = list(reversed(rows))
        last_attempts = []
        for completed_at, correct, wrong, points, avg_time in rows:
            total = (correct or 0) + (wrong or 0)
            percent = (correct / total * 100.0) if total else 0.0
            last_attempts.append({
                'label': completed_at.strftime('%d.%m'),
                'points': int(points or 0),
                'correct': int(correct or 0),
                'wrong': int(wrong or 0),
                'percent': round(percent, 1),
                'avg_time': float(avg_time or 0.0),
            })

        return {
            'total_sessions': total_sessions,
            'total_correct': total_correct,
            'total_wrong': total_wrong,
            'overall_best': overall_best,
            'last_attempts': last_attempts,
        }

    def get_course_students(self, course_id: int):
        """Возвращает список студентов, прикрепленных к курсу."""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        u.id,
                        u.email,
                        COALESCE(u.first_name, '') AS first_name,
                        COALESCE(u.last_name, '')  AS last_name,
                        ac.assigned_at
                    FROM assigned_courses ac
                    JOIN users u ON u.id = ac.student_id
                    WHERE ac.course_id = %s
                    ORDER BY u.last_name NULLS LAST, u.first_name NULLS LAST, u.email;
                """, (course_id,))
                cols = [desc[0] for desc in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]

    def remove_student_from_course(self, student_id, course_id):
        """Удалить ученика с курса (запись в assigned_courses)"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM assigned_courses
                    WHERE student_id = %s AND course_id = %s
                """, (student_id, course_id))

    def get_course_students_stats(self, course_id: int, query: str | None = None,
                                  date_from: str | None = None, date_to: str | None = None,
                                  sort: str | None = None):
        """
        Агрегированная статистика учеников курса с поиском/датами/сортировкой.
        Даты фильтруем по exercise_results.completed_at.
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                params = [course_id]
                date_sql = []
                if date_from:
                    date_sql.append("er.completed_at >= %s")  # <-- fixed
                    params.append(date_from)
                if date_to:
                    date_sql.append("er.completed_at < %s")   # <-- fixed
                    params.append(date_to)

                search_sql = ""
                if query:
                    params.extend([f"%{query}%", f"%{query}%"])
                    search_sql = "AND ((COALESCE(u.first_name,'') || ' ' || COALESCE(u.last_name,'')) ILIKE %s OR u.email ILIKE %s)"

                sort_map = {
                    "percent_desc": "percent_correct DESC NULLS LAST",
                    "percent_asc":  "percent_correct ASC NULLS LAST",
                    "avg_time_desc":"avg_time DESC NULLS LAST",
                    "avg_time_asc": "avg_time ASC NULLS LAST",
                    "attempts_desc":"attempts DESC, percent_correct DESC",
                    "attempts_asc": "attempts ASC, percent_correct DESC",
                }
                order_by = sort_map.get(sort or "percent_desc", "percent_correct DESC NULLS LAST")

                cur.execute(f"""
                    SELECT
                        u.id,
                        u.email,
                        COALESCE(u.first_name,'') AS first_name,
                        COALESCE(u.last_name,'')  AS last_name,
                        COUNT(er.id)                              AS attempts,
                        COALESCE(SUM(er.correct_count),0)         AS total_correct,
                        COALESCE(SUM(er.wrong_count),0)           AS total_wrong,
                        CASE
                          WHEN COALESCE(SUM(er.correct_count)+SUM(er.wrong_count),0) > 0
                          THEN ROUND( (SUM(er.correct_count)::decimal * 100.0) /
                                     (SUM(er.correct_count)+SUM(er.wrong_count)), 2)
                          ELSE 0
                        END AS percent_correct,
                        ROUND(AVG(NULLIF(er.average_time,0))::numeric, 2) AS avg_time
                    FROM assigned_courses ac
                    JOIN users u ON u.id = ac.student_id
                    LEFT JOIN exercise_results er
                      ON er.user_id = u.id
                     {('AND ' + ' AND '.join(date_sql)) if date_sql else ''}
                    WHERE ac.course_id = %s
                    {search_sql}
                    GROUP BY u.id, u.email, u.first_name, u.last_name
                    ORDER BY {order_by};
                """, params)

                cols = [d[0] for d in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]

    def get_last_results(self, user_id: int, limit: int = 10):
        """Последние попытки для графиков в профиле ученика."""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        completed_at AS created_at,          -- <-- fixed alias
                        COALESCE(total_points, 0)  AS points,  -- <-- fixed alias
                        COALESCE(correct_count, 0) AS correct,
                        COALESCE(wrong_count, 0)   AS wrong,
                        COALESCE(average_time, 0)  AS avg_time
                    FROM exercise_results
                    WHERE user_id = %s
                    ORDER BY completed_at DESC
                    LIMIT %s
                """, (user_id, limit))
                cols = [d[0] for d in cur.description]
                return [dict(zip(cols, r)) for r in cur.fetchall()]


# Глобальный экземпляр
db = DatabaseManager()
