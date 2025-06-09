CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS syllabuses (
    syllabus_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    description TEXT,
    author_user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS levels (
    level_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    syllabus_id UUID NOT NULL REFERENCES syllabuses(syllabus_id) ON DELETE CASCADE,
    title VARCHAR(100) NOT NULL,
    description TEXT,
    "order" INT NOT NULL,
    CONSTRAINT unique_level_order_per_syllabus UNIQUE (syllabus_id, "order")
);

CREATE TABLE IF NOT EXISTS theories (
    theory_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    level_id UUID NOT NULL REFERENCES levels(level_id) ON DELETE CASCADE,
    content TEXT NOT NULL
);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'task_type') THEN
        CREATE TYPE task_type AS ENUM ('classic', 'interactive', 'practical', 'gamified');
    END IF;
END
$$;

CREATE TABLE IF NOT EXISTS tasks (
    task_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    level_id UUID NOT NULL REFERENCES levels(level_id) ON DELETE CASCADE,
    type task_type NOT NULL,
    content TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS exams (
    exam_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    level_id UUID NOT NULL REFERENCES levels(level_id) ON DELETE CASCADE,
    content TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS exam_tasks (
    exam_id UUID NOT NULL REFERENCES exams(exam_id) ON DELETE CASCADE,
    task_id UUID NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
    PRIMARY KEY (exam_id, task_id)
);
