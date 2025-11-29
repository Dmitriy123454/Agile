-- Полная схема БД для математического тренажера

-- 1. Пользователи системы
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'student' CHECK (role IN ('student', 'teacher', 'parent')),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Связь ученик-родитель
CREATE TABLE IF NOT EXISTS student_parents (
    student_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    parent_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    PRIMARY KEY (student_id, parent_id)
);

-- 3. Связь ученик-учитель  
CREATE TABLE IF NOT EXISTS student_teachers (
    student_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    teacher_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    PRIMARY KEY (student_id, teacher_id)
);

-- 4. Сессии пользователей (для замены Flask session storage)
CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Типы упражнений
CREATE TABLE IF NOT EXISTS exercise_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    parameters JSONB, -- {min: 2, max: 9, operators: ['*']}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Курсы
CREATE TABLE IF NOT EXISTS courses (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    subject VARCHAR(50) NOT NULL CHECK (subject IN ('arithmetic', 'multiplication')),
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. Назначенные курсы ученикам
CREATE TABLE IF NOT EXISTS assigned_courses (
    id SERIAL PRIMARY KEY,
    student_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    course_id INTEGER REFERENCES courses(id) ON DELETE CASCADE,
    assigned_by INTEGER REFERENCES users(id),
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(student_id, course_id)
);

-- 8. Результаты выполнения упражнений (сводка по сессии)
CREATE TABLE IF NOT EXISTS exercise_results (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    exercise_type VARCHAR(100) NOT NULL,
    correct_count INTEGER DEFAULT 0,
    wrong_count INTEGER DEFAULT 0,
    total_points INTEGER DEFAULT 0,
    average_time FLOAT DEFAULT 0.0,
    best_score INTEGER DEFAULT 0,
    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 9. Детализация по каждому заданию
CREATE TABLE IF NOT EXISTS exercise_attempts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    exercise_type VARCHAR(100) NOT NULL,
    task_data JSONB NOT NULL, -- {a: 5, b: 3, answer: 15}
    user_answer INTEGER,
    is_correct BOOLEAN,
    time_spent FLOAT, -- seconds
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создаем индексы для ускорения запросов
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON user_sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_exercise_results_user_id ON exercise_results(user_id);
CREATE INDEX IF NOT EXISTS idx_exercise_results_completed_at ON exercise_results(completed_at);
CREATE INDEX IF NOT EXISTS idx_exercise_attempts_user_id ON exercise_attempts(user_id);
CREATE INDEX IF NOT EXISTS idx_exercise_attempts_created_at ON exercise_attempts(created_at);
CREATE INDEX IF NOT EXISTS idx_student_parents_student ON student_parents(student_id);
CREATE INDEX IF NOT EXISTS idx_student_parents_parent ON student_parents(parent_id);
CREATE INDEX IF NOT EXISTS idx_student_teachers_student ON student_teachers(student_id);
CREATE INDEX IF NOT EXISTS idx_student_teachers_teacher ON student_teachers(teacher_id);

-- Заполняем базовые типы упражнений
INSERT INTO exercise_types (name, description, parameters) VALUES
('multiplication_basic', 'Базовое умножение', '{"min": 2, "max": 9, "operators": ["*"]}'),
('multiplication_advanced', 'Продвинутое умножение', '{"min": 10, "max": 99, "operators": ["*"]}'),
('arithmetic_basic', 'Базовая арифметика', '{"min": 1, "max": 20, "operators": ["+", "-"]}'),
('arithmetic_advanced', 'Продвинутая арифметика', '{"min": 10, "max": 100, "operators": ["+", "-", "*"]}')
ON CONFLICT (name) DO NOTHING;

-- Создаем тестового учителя (если нужно)
INSERT INTO users (email, password_hash, role, first_name, last_name) VALUES
('teacher@school.ru', 'hashed_password_123', 'teacher', 'Мария', 'Иванова')
ON CONFLICT (email) DO NOTHING;