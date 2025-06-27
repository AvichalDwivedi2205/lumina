-- Enable required extensions first
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Enhanced Journal entries table with encryption and row-level security
-- Supports both legacy and new enhanced journaling agent formats
CREATE TABLE IF NOT EXISTS journal_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entry_id TEXT UNIQUE NOT NULL, -- Agent-generated entry ID
    user_id TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Encrypted sensitive data
    encrypted_raw_text TEXT NOT NULL,
    encrypted_normalized_text TEXT NOT NULL,
    encrypted_insights TEXT NOT NULL, -- Can store either legacy multi-insights or new unified insight
    
    -- Structured analysis data (not encrypted for querying)
    emotions JSONB NOT NULL, -- 6-emotion framework: joy, sadness, anger, fear, disgust, surprise
    patterns JSONB NOT NULL,
    
    -- Enhanced crisis detection
    crisis_detected BOOLEAN DEFAULT FALSE, -- Backward compatibility (derived from crisis_level >= 3)
    crisis_level INTEGER DEFAULT 1 CHECK (crisis_level >= 1 AND crisis_level <= 5), -- 1=No crisis, 5=Imminent danger
    crisis_indicators JSONB DEFAULT '[]'::jsonb, -- Specific indicators found
    crisis_reasoning TEXT, -- LLM explanation of assessment
    
    -- Embedding vector for similarity search
    embedding_vector VECTOR(768), -- all-mpnet-base-v2 dimension
    
    -- Optional metadata
    tags JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb, -- Includes agent_version, emotion_framework, etc.
    
    -- Constraints
    CONSTRAINT journal_entries_user_id_check CHECK (user_id != ''),
    CONSTRAINT journal_entries_entry_id_check CHECK (entry_id != ''),
    CONSTRAINT journal_entries_raw_text_check CHECK (encrypted_raw_text != ''),
    CONSTRAINT journal_entries_normalized_text_check CHECK (encrypted_normalized_text != '')
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_journal_entries_entry_id ON journal_entries(entry_id);
CREATE INDEX IF NOT EXISTS idx_journal_entries_user_id ON journal_entries(user_id);
CREATE INDEX IF NOT EXISTS idx_journal_entries_created_at ON journal_entries(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_journal_entries_user_created ON journal_entries(user_id, created_at DESC);

-- Crisis-specific indexes
CREATE INDEX IF NOT EXISTS idx_journal_entries_crisis_detected ON journal_entries(crisis_detected) WHERE crisis_detected = true;
CREATE INDEX IF NOT EXISTS idx_journal_entries_crisis_level ON journal_entries(crisis_level) WHERE crisis_level >= 3;
CREATE INDEX IF NOT EXISTS idx_journal_entries_user_crisis ON journal_entries(user_id, crisis_level) WHERE crisis_level >= 3;

-- JSONB indexes for better performance (fixed GIN operators)
CREATE INDEX IF NOT EXISTS idx_journal_entries_emotions ON journal_entries USING GIN (emotions);
CREATE INDEX IF NOT EXISTS idx_journal_entries_patterns ON journal_entries USING GIN (patterns);
CREATE INDEX IF NOT EXISTS idx_journal_entries_crisis_indicators ON journal_entries USING GIN (crisis_indicators);
CREATE INDEX IF NOT EXISTS idx_journal_entries_metadata ON journal_entries USING GIN (metadata);

-- Vector similarity search index (requires pgvector extension)
CREATE INDEX IF NOT EXISTS idx_journal_entries_embedding ON journal_entries 
USING ivfflat (embedding_vector vector_cosine_ops) WITH (lists = 100);

-- Enable Row Level Security
ALTER TABLE journal_entries ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Users can only access their own journal entries
CREATE POLICY "Users can only access their own journal entries" ON journal_entries
    FOR ALL USING (user_id = auth.uid()::text);

-- RLS Policy: Users can insert their own journal entries
CREATE POLICY "Users can insert their own journal entries" ON journal_entries
    FOR INSERT WITH CHECK (user_id = auth.uid()::text);

-- RLS Policy: Users can update their own journal entries
CREATE POLICY "Users can update their own journal entries" ON journal_entries
    FOR UPDATE USING (user_id = auth.uid()::text);

-- RLS Policy: Users can delete their own journal entries
CREATE POLICY "Users can delete their own journal entries" ON journal_entries
    FOR DELETE USING (user_id = auth.uid()::text);

-- Function to automatically update updated_at timestamp and crisis_detected flag
CREATE OR REPLACE FUNCTION update_journal_entry_metadata()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    -- Automatically set crisis_detected based on crisis_level for backward compatibility
    NEW.crisis_detected = (NEW.crisis_level >= 3);
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to automatically update metadata
CREATE TRIGGER update_journal_entries_metadata
    BEFORE INSERT OR UPDATE ON journal_entries
    FOR EACH ROW
    EXECUTE FUNCTION update_journal_entry_metadata();

-- Enhanced view for easier querying (without encrypted data)
CREATE OR REPLACE VIEW journal_entries_summary AS
SELECT 
    id,
    entry_id,
    user_id,
    created_at,
    updated_at,
    emotions,
    patterns,
    crisis_detected,
    crisis_level,
    crisis_indicators,
    crisis_reasoning,
    tags,
    metadata,
    (CASE WHEN embedding_vector IS NOT NULL THEN true ELSE false END) as has_embedding,
    -- Emotion analysis helpers
    (emotions->>'primary') as primary_emotion,
    (emotions->'analysis'->>'joy')::int as joy_level,
    (emotions->'analysis'->>'sadness')::int as sadness_level,
    (emotions->'analysis'->>'anger')::int as anger_level,
    (emotions->'analysis'->>'fear')::int as fear_level,
    (emotions->'analysis'->>'disgust')::int as disgust_level,
    (emotions->'analysis'->>'surprise')::int as surprise_level
FROM journal_entries;

-- Crisis monitoring view for healthcare providers (if needed)
CREATE OR REPLACE VIEW crisis_entries AS
SELECT 
    entry_id,
    user_id,
    created_at,
    crisis_level,
    crisis_indicators,
    crisis_reasoning,
    primary_emotion,
    patterns
FROM journal_entries_summary
WHERE crisis_level >= 3
ORDER BY crisis_level DESC, created_at DESC;

-- Grant permissions for authenticated users
GRANT ALL ON journal_entries TO authenticated;
GRANT SELECT ON journal_entries_summary TO authenticated;
GRANT SELECT ON crisis_entries TO authenticated;

-- Enhanced documentation
COMMENT ON TABLE journal_entries IS 'Enhanced encrypted journal entries with therapeutic analysis and crisis assessment';
COMMENT ON COLUMN journal_entries.entry_id IS 'Agent-generated unique entry identifier';
COMMENT ON COLUMN journal_entries.encrypted_raw_text IS 'AES-256 encrypted original journal text';
COMMENT ON COLUMN journal_entries.encrypted_normalized_text IS 'AES-256 encrypted normalized journal text';
COMMENT ON COLUMN journal_entries.encrypted_insights IS 'AES-256 encrypted therapeutic insights (legacy multi-modal or new unified)';
COMMENT ON COLUMN journal_entries.emotions IS 'Structured emotional analysis using 6-emotion framework (joy, sadness, anger, fear, disgust, surprise)';
COMMENT ON COLUMN journal_entries.patterns IS 'Identified cognitive and behavioral patterns';
COMMENT ON COLUMN journal_entries.crisis_detected IS 'Boolean flag for crisis detection (derived from crisis_level >= 3)';
COMMENT ON COLUMN journal_entries.crisis_level IS 'LLM-assessed crisis level: 1=No crisis, 5=Imminent danger';
COMMENT ON COLUMN journal_entries.crisis_indicators IS 'Specific crisis indicators identified by LLM';
COMMENT ON COLUMN journal_entries.crisis_reasoning IS 'LLM explanation of crisis assessment';
COMMENT ON COLUMN journal_entries.embedding_vector IS 'Vector embedding for similarity search using all-mpnet-base-v2';

-- Test the schema with a simple query
SELECT 'Enhanced Lumina Mental Health Schema Created Successfully!' as status;
