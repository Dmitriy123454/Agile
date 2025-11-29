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
        """Сохранение результатов упражнения"""
        pass
    
    def get_user_best_score(self, user_id, exercise_type='multiplication_basic'):
        """Получение лучшего результата пользователя"""
        pass

    def get_user_stats(self, user_id):
        """Получение статистики пользователя"""
        pass

# Глобальный экземпляр
db = DatabaseManager()