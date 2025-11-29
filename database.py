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

    def save_exercise_result(self, user_id, exercise_data):
        """Сохранение результатов упражнения (одной тренировки)"""
        correct = int(exercise_data.get('correct', 0))
        wrong = int(exercise_data.get('wrong', 0))
        points = int(exercise_data.get('points', correct))
        avg_time = float(exercise_data.get('avg_time', 0.0))
        exercise_type = exercise_data.get('exercise_type', 'multiplication_basic')

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO exercise_results 
                    (user_id, exercise_type, correct_count, wrong_count, total_points, average_time, best_score)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    user_id,
                    exercise_type,
                    correct,
                    wrong,
                    points,
                    avg_time,
                    points,  # результат этой попытки как best_score именно для неё
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
        Получение статистики пользователя + данные для графика.
        last_attempts — 10 последних тренировок (для графика).
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Агрегированная статистика (на будущее, вдруг пригодится)
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

                # 10 последних тренировок
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

        # Для графика слева → самая старая попытка
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


# Глобальный экземпляр
db = DatabaseManager()
