CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS subscriptions (
    subscriber_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    target_id     UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (subscriber_id, target_id),
    CONSTRAINT no_self_subscription CHECK (subscriber_id <> target_id)
);

CREATE TABLE IF NOT EXISTS user_rankings (
    user_id      UUID   NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    period       CHAR(7) NOT NULL CHECK (period ~ '^\d{4}-\d{2}$'),
    xp_earned    INT    NOT NULL DEFAULT 0,
    last_updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, period)
);

ALTER TABLE user_rankings
  ALTER COLUMN period
  SET DEFAULT to_char(CURRENT_DATE, 'YYYY-MM');
