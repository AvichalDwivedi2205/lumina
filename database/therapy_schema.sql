-- Therapy Sessions Table
CREATE TABLE IF NOT EXISTS therapy_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    therapist_type VARCHAR(20) NOT NULL CHECK (therapist_type IN ('male', 'female')),
    session_mode VARCHAR(20) NOT NULL CHECK (session_mode IN ('voice', 'video')),
    session_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    duration_minutes INTEGER DEFAULT 45,
    mood_rating INTEGER CHECK (mood_rating >= 1 AND mood_rating <= 10),
    encrypted_notes TEXT, -- Fernet encrypted therapy notes
    session_summary TEXT,
    exercises_recommended JSONB DEFAULT '[]'::jsonb,
    reflection_questions JSONB DEFAULT '[]'::jsonb,
    crisis_indicators JSONB DEFAULT '[]'::jsonb,
    agent_config JSONB,
    tavus_conversation_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Mental Exercises Table  
CREATE TABLE IF NOT EXISTS mental_exercises (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    exercise_type VARCHAR(50) NOT NULL CHECK (exercise_type IN ('mindfulness', 'cbt_tools', 'behavioral_activation', 'self_compassion')),
    session_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    duration_minutes INTEGER DEFAULT 10,
    completion_status VARCHAR(20) DEFAULT 'started' CHECK (completion_status IN ('started', 'completed', 'interrupted')),
    mood_before INTEGER CHECK (mood_before >= 1 AND mood_before <= 10),
    mood_after INTEGER CHECK (mood_after >= 1 AND mood_after <= 10),
    notes TEXT, -- Encrypted exercise data
    exercise_notes TEXT, -- User's own notes about the exercise
    agent_config JSONB,
    personalization_data JSONB,
    effectiveness_analysis JSONB,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for better performance
CREATE INDEX IF NOT EXISTS idx_therapy_sessions_user_id ON therapy_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_therapy_sessions_created_at ON therapy_sessions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_therapy_sessions_user_created ON therapy_sessions(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_mental_exercises_user_id ON mental_exercises(user_id);
CREATE INDEX IF NOT EXISTS idx_mental_exercises_type ON mental_exercises(exercise_type);
CREATE INDEX IF NOT EXISTS idx_mental_exercises_user_type ON mental_exercises(user_id, exercise_type);
CREATE INDEX IF NOT EXISTS idx_mental_exercises_created_at ON mental_exercises(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_mental_exercises_completion ON mental_exercises(completion_status);

-- Therapy Session Analytics View
CREATE OR REPLACE VIEW therapy_session_analytics AS
SELECT 
    user_id,
    COUNT(*) as total_sessions,
    COUNT(CASE WHEN mood_rating IS NOT NULL THEN 1 END) as sessions_with_mood,
    AVG(mood_rating) as avg_mood_rating,
    COUNT(CASE WHEN therapist_type = 'male' THEN 1 END) as male_therapist_sessions,
    COUNT(CASE WHEN therapist_type = 'female' THEN 1 END) as female_therapist_sessions,
    COUNT(CASE WHEN session_mode = 'voice' THEN 1 END) as voice_sessions,
    COUNT(CASE WHEN session_mode = 'video' THEN 1 END) as video_sessions,
    AVG(duration_minutes) as avg_duration_minutes,
    MAX(created_at) as last_session_date,
    MIN(created_at) as first_session_date
FROM therapy_sessions
GROUP BY user_id;

-- Mental Exercise Analytics View
CREATE OR REPLACE VIEW mental_exercise_analytics AS
SELECT 
    user_id,
    exercise_type,
    COUNT(*) as total_exercises,
    COUNT(CASE WHEN completion_status = 'completed' THEN 1 END) as completed_exercises,
    ROUND(
        COUNT(CASE WHEN completion_status = 'completed' THEN 1 END)::DECIMAL / 
        NULLIF(COUNT(*), 0) * 100, 2
    ) as completion_rate_percent,
    AVG(CASE WHEN mood_before IS NOT NULL AND mood_after IS NOT NULL 
        THEN mood_after - mood_before END) as avg_mood_improvement,
    AVG(mood_before) as avg_mood_before,
    AVG(mood_after) as avg_mood_after,
    MAX(created_at) as last_exercise_date,
    MIN(created_at) as first_exercise_date
FROM mental_exercises
GROUP BY user_id, exercise_type;

-- User Progress Summary View
CREATE OR REPLACE VIEW user_progress_summary AS
SELECT 
    tsa.user_id,
    tsa.total_sessions,
    tsa.avg_mood_rating as therapy_avg_mood,
    tsa.last_session_date,
    COALESCE(mea_summary.total_exercises, 0) as total_exercises,
    COALESCE(mea_summary.completed_exercises, 0) as completed_exercises,
    COALESCE(mea_summary.overall_completion_rate, 0) as exercise_completion_rate,
    COALESCE(mea_summary.avg_mood_improvement, 0) as avg_exercise_mood_improvement
FROM therapy_session_analytics tsa
LEFT JOIN (
    SELECT 
        user_id,
        SUM(total_exercises) as total_exercises,
        SUM(completed_exercises) as completed_exercises,
        ROUND(
            SUM(completed_exercises)::DECIMAL / 
            NULLIF(SUM(total_exercises), 0) * 100, 2
        ) as overall_completion_rate,
        AVG(avg_mood_improvement) as avg_mood_improvement
    FROM mental_exercise_analytics
    GROUP BY user_id
) mea_summary ON tsa.user_id = mea_summary.user_id;

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for therapy_sessions updated_at
DROP TRIGGER IF EXISTS update_therapy_sessions_updated_at ON therapy_sessions;
CREATE TRIGGER update_therapy_sessions_updated_at
    BEFORE UPDATE ON therapy_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Comments for documentation
COMMENT ON TABLE therapy_sessions IS 'Stores therapy session data with encrypted notes and session metadata';
COMMENT ON TABLE mental_exercises IS 'Stores mental exercise session data with mood tracking and personalization';

COMMENT ON COLUMN therapy_sessions.encrypted_notes IS 'Fernet encrypted JSON containing therapy notes, patterns, and insights';
COMMENT ON COLUMN therapy_sessions.exercises_recommended IS 'JSON array of recommended exercises from the therapy session';
COMMENT ON COLUMN therapy_sessions.reflection_questions IS 'JSON array of post-session reflection questions';
COMMENT ON COLUMN therapy_sessions.crisis_indicators IS 'JSON array of any crisis indicators detected during session';

COMMENT ON COLUMN mental_exercises.notes IS 'Fernet encrypted JSON containing exercise data and analysis';
COMMENT ON COLUMN mental_exercises.exercise_notes IS 'User provided notes about their exercise experience';
COMMENT ON COLUMN mental_exercises.personalization_data IS 'JSON containing personalization parameters for the exercise';
COMMENT ON COLUMN mental_exercises.effectiveness_analysis IS 'JSON containing AI analysis of exercise effectiveness'; 