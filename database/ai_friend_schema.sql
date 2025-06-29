-- AI Friend Agent Database Schema
-- Minimal schema since conversations are ephemeral - only stores usage analytics and preferences

-- Enable Row Level Security
ALTER DATABASE postgres SET row_security = on;

-- User Friend Preferences
CREATE TABLE IF NOT EXISTS friend_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    preferred_personalities TEXT[] DEFAULT '{}', -- Array of preferred personality types
    interaction_history JSON DEFAULT '{}', -- Summary stats, not conversation content
    mood_patterns JSON DEFAULT '{}', -- Pattern analysis for better personality matching
    last_interaction_at TIMESTAMP WITH TIME ZONE,
    total_conversations INTEGER DEFAULT 0,
    favorite_personality TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id)
);

-- Conversation Sessions (Ephemeral - minimal data)
CREATE TABLE IF NOT EXISTS friend_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    personality_type TEXT NOT NULL CHECK (personality_type IN ('supportive', 'motivator', 'mentor', 'funny', 'mindful')),
    session_start TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    session_end TIMESTAMP WITH TIME ZONE,
    duration_minutes INTEGER,
    mood_before TEXT,
    mood_after TEXT,
    satisfaction_rating INTEGER CHECK (satisfaction_rating BETWEEN 1 AND 5),
    agent_id TEXT NOT NULL, -- ElevenLabs agent ID used
    conversation_id TEXT, -- ElevenLabs conversation ID
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Personality Usage Analytics
CREATE TABLE IF NOT EXISTS personality_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    personality_type TEXT NOT NULL,
    usage_count INTEGER DEFAULT 1,
    total_duration_minutes INTEGER DEFAULT 0,
    average_satisfaction DECIMAL(3,2),
    last_used_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    effectiveness_score DECIMAL(5,2), -- AI-calculated effectiveness
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, personality_type)
);

-- Mood Tracking (Optional - for personality recommendations)
CREATE TABLE IF NOT EXISTS mood_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    mood_before TEXT,
    mood_after TEXT,
    personality_used TEXT,
    interaction_date DATE DEFAULT CURRENT_DATE,
    mood_improvement_score INTEGER CHECK (mood_improvement_score BETWEEN -5 AND 5),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_friend_preferences_user_id ON friend_preferences(user_id);
CREATE INDEX IF NOT EXISTS idx_friend_sessions_user_id ON friend_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_friend_sessions_personality ON friend_sessions(personality_type);
CREATE INDEX IF NOT EXISTS idx_friend_sessions_start ON friend_sessions(session_start);
CREATE INDEX IF NOT EXISTS idx_personality_analytics_user_id ON personality_analytics(user_id);
CREATE INDEX IF NOT EXISTS idx_mood_tracking_user_id ON mood_tracking(user_id);
CREATE INDEX IF NOT EXISTS idx_mood_tracking_date ON mood_tracking(interaction_date);

-- Row Level Security Policies

-- Friend Preferences RLS
ALTER TABLE friend_preferences ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own friend preferences" ON friend_preferences
    FOR SELECT USING (user_id = current_setting('app.current_user_id', true));

CREATE POLICY "Users can insert own friend preferences" ON friend_preferences
    FOR INSERT WITH CHECK (user_id = current_setting('app.current_user_id', true));

CREATE POLICY "Users can update own friend preferences" ON friend_preferences
    FOR UPDATE USING (user_id = current_setting('app.current_user_id', true));

-- Friend Sessions RLS
ALTER TABLE friend_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own friend sessions" ON friend_sessions
    FOR SELECT USING (user_id = current_setting('app.current_user_id', true));

CREATE POLICY "Users can insert own friend sessions" ON friend_sessions
    FOR INSERT WITH CHECK (user_id = current_setting('app.current_user_id', true));

CREATE POLICY "Users can update own friend sessions" ON friend_sessions
    FOR UPDATE USING (user_id = current_setting('app.current_user_id', true));

-- Personality Analytics RLS
ALTER TABLE personality_analytics ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own personality analytics" ON personality_analytics
    FOR SELECT USING (user_id = current_setting('app.current_user_id', true));

CREATE POLICY "Users can insert own personality analytics" ON personality_analytics
    FOR INSERT WITH CHECK (user_id = current_setting('app.current_user_id', true));

CREATE POLICY "Users can update own personality analytics" ON personality_analytics
    FOR UPDATE USING (user_id = current_setting('app.current_user_id', true));

-- Mood Tracking RLS
ALTER TABLE mood_tracking ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own mood tracking" ON mood_tracking
    FOR SELECT USING (user_id = current_setting('app.current_user_id', true));

CREATE POLICY "Users can insert own mood tracking" ON mood_tracking
    FOR INSERT WITH CHECK (user_id = current_setting('app.current_user_id', true));

-- Triggers for updated_at timestamps
CREATE TRIGGER update_friend_preferences_updated_at BEFORE UPDATE ON friend_preferences
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_personality_analytics_updated_at BEFORE UPDATE ON personality_analytics
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Analytics Views
CREATE OR REPLACE VIEW user_friend_analytics AS
SELECT 
    user_id,
    COUNT(DISTINCT personality_type) as personalities_used,
    COUNT(*) as total_sessions,
    AVG(duration_minutes) as avg_session_duration,
    AVG(satisfaction_rating) as avg_satisfaction,
    MAX(session_start) as last_interaction,
    EXTRACT(DAYS FROM NOW() - MAX(session_start)) as days_since_last_interaction
FROM friend_sessions
WHERE session_end IS NOT NULL
GROUP BY user_id;

CREATE OR REPLACE VIEW personality_effectiveness AS
SELECT 
    personality_type,
    COUNT(*) as total_uses,
    AVG(satisfaction_rating) as avg_satisfaction,
    AVG(duration_minutes) as avg_duration,
    COUNT(CASE WHEN satisfaction_rating >= 4 THEN 1 END)::FLOAT / COUNT(*) as high_satisfaction_rate
FROM friend_sessions
WHERE session_end IS NOT NULL AND satisfaction_rating IS NOT NULL
GROUP BY personality_type;

CREATE OR REPLACE VIEW mood_improvement_trends AS
SELECT 
    user_id,
    personality_used,
    DATE_TRUNC('week', interaction_date) as week,
    AVG(mood_improvement_score) as avg_mood_improvement,
    COUNT(*) as interactions_count
FROM mood_tracking
GROUP BY user_id, personality_used, DATE_TRUNC('week', interaction_date);

-- Function to update personality analytics
CREATE OR REPLACE FUNCTION update_personality_analytics()
RETURNS TRIGGER AS $$
BEGIN
    -- Update or insert personality analytics when session ends
    IF NEW.session_end IS NOT NULL AND OLD.session_end IS NULL THEN
        INSERT INTO personality_analytics 
            (user_id, personality_type, usage_count, total_duration_minutes, last_used_at)
        VALUES 
            (NEW.user_id, NEW.personality_type, 1, NEW.duration_minutes, NEW.session_end)
        ON CONFLICT (user_id, personality_type) 
        DO UPDATE SET
            usage_count = personality_analytics.usage_count + 1,
            total_duration_minutes = personality_analytics.total_duration_minutes + NEW.duration_minutes,
            last_used_at = NEW.session_end,
            updated_at = NOW();
            
        -- Update average satisfaction if rating provided
        IF NEW.satisfaction_rating IS NOT NULL THEN
            UPDATE personality_analytics 
            SET average_satisfaction = (
                SELECT AVG(satisfaction_rating) 
                FROM friend_sessions 
                WHERE user_id = NEW.user_id 
                AND personality_type = NEW.personality_type
                AND satisfaction_rating IS NOT NULL
            )
            WHERE user_id = NEW.user_id AND personality_type = NEW.personality_type;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_personality_analytics_trigger
    AFTER UPDATE ON friend_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_personality_analytics();

-- Function to calculate session duration
CREATE OR REPLACE FUNCTION calculate_session_duration()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.session_end IS NOT NULL AND NEW.session_start IS NOT NULL THEN
        NEW.duration_minutes = EXTRACT(EPOCH FROM (NEW.session_end - NEW.session_start)) / 60;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER calculate_session_duration_trigger
    BEFORE INSERT OR UPDATE ON friend_sessions
    FOR EACH ROW
    EXECUTE FUNCTION calculate_session_duration();

-- Comments for documentation
COMMENT ON TABLE friend_preferences IS 'User preferences for AI friend personalities and interaction patterns';
COMMENT ON TABLE friend_sessions IS 'Minimal session data for analytics - no conversation content stored';
COMMENT ON TABLE personality_analytics IS 'Aggregated analytics for personality effectiveness per user';
COMMENT ON TABLE mood_tracking IS 'Optional mood tracking before/after friend interactions';
COMMENT ON VIEW user_friend_analytics IS 'User-level analytics for friend interactions';
COMMENT ON VIEW personality_effectiveness IS 'Global personality effectiveness metrics';
COMMENT ON VIEW mood_improvement_trends IS 'Mood improvement trends by personality type'; 