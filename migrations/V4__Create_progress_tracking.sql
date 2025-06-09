CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS user_progresses (
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    syllabus_id UUID NOT NULL REFERENCES syllabuses(syllabus_id) ON DELETE CASCADE,
    completed_levels INT NOT NULL DEFAULT 0,
    total_levels INT NOT NULL,
    score INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, syllabus_id)
);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'score_grade') THEN
        CREATE TYPE score_grade AS ENUM ('A', 'B', 'C');
    END IF;
END
$$;

CREATE TABLE IF NOT EXISTS user_scores (
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    task_id UUID NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
    score score_grade,
    attempts INT NOT NULL DEFAULT 1,
    PRIMARY KEY (user_id, task_id)
);

CREATE TABLE IF NOT EXISTS user_favorites (
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    syllabus_id UUID NOT NULL REFERENCES syllabuses(syllabus_id) ON DELETE CASCADE,
    added_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, syllabus_id)
);

CREATE TABLE IF NOT EXISTS syllabus_reviews (
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    syllabus_id UUID NOT NULL REFERENCES syllabuses(syllabus_id) ON DELETE CASCADE,
    review TEXT,
    rating INT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, syllabus_id)
);
