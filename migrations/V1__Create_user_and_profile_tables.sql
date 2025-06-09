CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nickname VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS profile_frames (
    profile_frame_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    image_url TEXT NOT NULL,
    unlock_condition TEXT
);

CREATE TABLE IF NOT EXISTS profile_backgrounds (
    profile_background_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    image_url TEXT NOT NULL,
    unlock_condition TEXT,
    is_premium BOOLEAN NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS user_profiles (
    user_id UUID PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    avatar_url TEXT,
    bio TEXT,
    profile_frame_id UUID REFERENCES profile_frames(profile_frame_id) ON DELETE SET NULL,
    profile_background_id UUID REFERENCES profile_backgrounds(profile_background_id) ON DELETE SET NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
