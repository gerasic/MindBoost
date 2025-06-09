CREATE INDEX IF NOT EXISTS idx_user_achievements_user_id
  ON user_achievements (user_id);

CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX IF NOT EXISTS idx_users_nickname_trgm
  ON users USING gin (nickname gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_user_favorites_syllabus_id
  ON user_favorites (syllabus_id);

