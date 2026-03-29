-- US 7.2: Usage event tracking table
-- Records user interactions for DAU and resume metrics

CREATE TABLE IF NOT EXISTS usage_events (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id) ON DELETE SET NULL,
    event       TEXT NOT NULL,
    metadata    JSONB NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_usage_events_user_id    ON usage_events(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_events_event      ON usage_events(event);
CREATE INDEX IF NOT EXISTS idx_usage_events_created_at ON usage_events(created_at);
