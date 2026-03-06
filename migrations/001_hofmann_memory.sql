-- Hofmann Agent Memory Schema
-- Run in Supabase SQL editor

-- Conversations: stores full chat history per session
CREATE TABLE IF NOT EXISTS hofmann_conversations (
  id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  session_id  TEXT NOT NULL,
  role        TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
  content     TEXT NOT NULL,
  dimensions  INTEGER[] NOT NULL DEFAULT '{1}',
  dose        TEXT NOT NULL DEFAULT 'common',
  language    TEXT NOT NULL DEFAULT 'nl',
  mode        TEXT NOT NULL DEFAULT 'text',
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_hof_conv_session ON hofmann_conversations (session_id);
CREATE INDEX IF NOT EXISTS idx_hof_conv_created ON hofmann_conversations (created_at);

-- Session metadata: tracks session state and user preferences
CREATE TABLE IF NOT EXISTS hofmann_sessions (
  session_id      TEXT PRIMARY KEY,
  preferred_dims  INTEGER[] DEFAULT '{1}',
  preferred_dose  TEXT DEFAULT 'common',
  preferred_lang  TEXT DEFAULT 'nl',
  message_count   INTEGER DEFAULT 0,
  first_seen      TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_active     TIMESTAMPTZ NOT NULL DEFAULT now(),
  metadata        JSONB DEFAULT '{}'
);

-- Learned insights: agent extracts and stores learnings from conversations
CREATE TABLE IF NOT EXISTS hofmann_insights (
  id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  session_id    TEXT NOT NULL,
  dimension     INTEGER NOT NULL CHECK (dimension BETWEEN 1 AND 9),
  substance     TEXT NOT NULL,
  insight_type  TEXT NOT NULL CHECK (insight_type IN ('question_pattern', 'user_interest', 'effective_response', 'topic_depth', 'cross_dim_resonance')),
  content       TEXT NOT NULL,
  relevance     REAL DEFAULT 0.5 CHECK (relevance BETWEEN 0 AND 1),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_hof_insights_dim ON hofmann_insights (dimension);
CREATE INDEX IF NOT EXISTS idx_hof_insights_type ON hofmann_insights (insight_type);

-- Enable RLS
ALTER TABLE hofmann_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE hofmann_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE hofmann_insights ENABLE ROW LEVEL SECURITY;

-- Service role full access
CREATE POLICY "Service role access" ON hofmann_conversations FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role access" ON hofmann_sessions FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role access" ON hofmann_insights FOR ALL USING (true) WITH CHECK (true);
