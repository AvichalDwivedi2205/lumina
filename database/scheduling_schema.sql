-- Scheduling Agent Database Schema
-- Comprehensive schema for therapy, exercise, journaling, and sleep scheduling

-- Enable Row Level Security
ALTER DATABASE postgres SET row_security = on;

-- User Scheduling Preferences
CREATE TABLE IF NOT EXISTS user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    encrypted_preferences TEXT NOT NULL, -- Encrypted JSON with detailed preferences
    timezone TEXT DEFAULT 'UTC',
    work_schedule JSON DEFAULT '{}', -- Work hours and days
    sleep_preferences JSON DEFAULT '{}', -- Sleep schedule preferences
    notification_preferences JSON DEFAULT '{}', -- When to send reminders
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id)
);

-- User Schedules (Main scheduling table)
CREATE TABLE IF NOT EXISTS user_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('therapy', 'exercise', 'journal', 'sleep', 'routine')),
    title TEXT NOT NULL,
    description TEXT,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    duration INTEGER NOT NULL DEFAULT 30, -- Duration in minutes
    frequency TEXT NOT NULL CHECK (frequency IN ('once', 'daily', 'weekly', 'monthly', 'custom')),
    frequency_data JSON DEFAULT '{}', -- Custom frequency rules
    priority TEXT NOT NULL CHECK (priority IN ('low', 'medium', 'high', 'critical')) DEFAULT 'medium',
    encrypted_preferences TEXT, -- Encrypted specific preferences for this item
    is_active BOOLEAN DEFAULT TRUE,
    is_completed BOOLEAN DEFAULT FALSE,
    completion_date TIMESTAMP WITH TIME ZONE,
    optimization_applied BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Schedule Conflicts
CREATE TABLE IF NOT EXISTS schedule_conflicts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    conflict_type TEXT NOT NULL CHECK (conflict_type IN ('time_overlap', 'resource_conflict', 'priority_conflict')),
    schedule_item_1 UUID NOT NULL REFERENCES user_schedules(id) ON DELETE CASCADE,
    schedule_item_2 UUID NOT NULL REFERENCES user_schedules(id) ON DELETE CASCADE,
    severity TEXT NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')) DEFAULT 'medium',
    resolution_status TEXT NOT NULL CHECK (resolution_status IN ('unresolved', 'resolved', 'ignored')) DEFAULT 'unresolved',
    resolution_notes TEXT,
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE
);

-- Schedule Optimizations
CREATE TABLE IF NOT EXISTS schedule_optimizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    optimization_type TEXT NOT NULL CHECK (optimization_type IN ('time_blocking', 'energy_matching', 'conflict_resolution', 'efficiency')),
    original_schedule JSON NOT NULL, -- Snapshot of schedule before optimization
    optimized_schedule JSON NOT NULL, -- Optimized schedule data
    optimization_score DECIMAL(5,2), -- 0-100 score for optimization quality
    applied_at TIMESTAMP WITH TIME ZONE,
    is_applied BOOLEAN DEFAULT FALSE,
    user_feedback TEXT,
    effectiveness_score DECIMAL(5,2), -- User-reported effectiveness
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Schedule Analytics
CREATE TABLE IF NOT EXISTS schedule_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    date DATE NOT NULL,
    scheduled_items INTEGER DEFAULT 0,
    completed_items INTEGER DEFAULT 0,
    completion_rate DECIMAL(5,2) DEFAULT 0,
    therapy_sessions INTEGER DEFAULT 0,
    exercise_sessions INTEGER DEFAULT 0,
    journal_entries INTEGER DEFAULT 0,
    sleep_hours DECIMAL(4,2),
    schedule_adherence_score DECIMAL(5,2), -- 0-100 score
    optimization_suggestions TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, date)
);

-- Recurring Schedule Templates
CREATE TABLE IF NOT EXISTS schedule_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    template_name TEXT NOT NULL,
    template_type TEXT NOT NULL CHECK (template_type IN ('daily', 'weekly', 'monthly')),
    template_data JSON NOT NULL, -- Template structure
    is_active BOOLEAN DEFAULT TRUE,
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Schedule Recommendations
CREATE TABLE IF NOT EXISTS schedule_recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    recommendation_type TEXT NOT NULL CHECK (recommendation_type IN ('therapy', 'exercise', 'journal', 'sleep', 'routine', 'optimization')),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    priority TEXT NOT NULL CHECK (priority IN ('low', 'medium', 'high')) DEFAULT 'medium',
    recommendation_data JSON DEFAULT '{}',
    is_applied BOOLEAN DEFAULT FALSE,
    applied_at TIMESTAMP WITH TIME ZONE,
    effectiveness_rating INTEGER CHECK (effectiveness_rating BETWEEN 1 AND 5),
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_preferences_user_id ON user_preferences(user_id);
CREATE INDEX IF NOT EXISTS idx_user_schedules_user_id ON user_schedules(user_id);
CREATE INDEX IF NOT EXISTS idx_user_schedules_type ON user_schedules(type);
CREATE INDEX IF NOT EXISTS idx_user_schedules_start_time ON user_schedules(start_time);
CREATE INDEX IF NOT EXISTS idx_user_schedules_active ON user_schedules(is_active);
CREATE INDEX IF NOT EXISTS idx_schedule_conflicts_user_id ON schedule_conflicts(user_id);
CREATE INDEX IF NOT EXISTS idx_schedule_conflicts_status ON schedule_conflicts(resolution_status);
CREATE INDEX IF NOT EXISTS idx_schedule_optimizations_user_id ON schedule_optimizations(user_id);
CREATE INDEX IF NOT EXISTS idx_schedule_analytics_user_date ON schedule_analytics(user_id, date);
CREATE INDEX IF NOT EXISTS idx_schedule_templates_user_id ON schedule_templates(user_id);
CREATE INDEX IF NOT EXISTS idx_schedule_recommendations_user_id ON schedule_recommendations(user_id);

-- Row Level Security Policies

-- User Preferences RLS
ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own preferences" ON user_preferences
    FOR SELECT USING (user_id = current_setting('app.current_user_id', true));

CREATE POLICY "Users can insert own preferences" ON user_preferences
    FOR INSERT WITH CHECK (user_id = current_setting('app.current_user_id', true));

CREATE POLICY "Users can update own preferences" ON user_preferences
    FOR UPDATE USING (user_id = current_setting('app.current_user_id', true));

-- User Schedules RLS
ALTER TABLE user_schedules ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own schedules" ON user_schedules
    FOR SELECT USING (user_id = current_setting('app.current_user_id', true));

CREATE POLICY "Users can insert own schedules" ON user_schedules
    FOR INSERT WITH CHECK (user_id = current_setting('app.current_user_id', true));

CREATE POLICY "Users can update own schedules" ON user_schedules
    FOR UPDATE USING (user_id = current_setting('app.current_user_id', true));

CREATE POLICY "Users can delete own schedules" ON user_schedules
    FOR DELETE USING (user_id = current_setting('app.current_user_id', true));

-- Schedule Conflicts RLS
ALTER TABLE schedule_conflicts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own conflicts" ON schedule_conflicts
    FOR SELECT USING (user_id = current_setting('app.current_user_id', true));

CREATE POLICY "Users can insert own conflicts" ON schedule_conflicts
    FOR INSERT WITH CHECK (user_id = current_setting('app.current_user_id', true));

CREATE POLICY "Users can update own conflicts" ON schedule_conflicts
    FOR UPDATE USING (user_id = current_setting('app.current_user_id', true));

-- Schedule Optimizations RLS
ALTER TABLE schedule_optimizations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own optimizations" ON schedule_optimizations
    FOR SELECT USING (user_id = current_setting('app.current_user_id', true));

CREATE POLICY "Users can insert own optimizations" ON schedule_optimizations
    FOR INSERT WITH CHECK (user_id = current_setting('app.current_user_id', true));

CREATE POLICY "Users can update own optimizations" ON schedule_optimizations
    FOR UPDATE USING (user_id = current_setting('app.current_user_id', true));

-- Schedule Analytics RLS
ALTER TABLE schedule_analytics ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own analytics" ON schedule_analytics
    FOR SELECT USING (user_id = current_setting('app.current_user_id', true));

CREATE POLICY "Users can insert own analytics" ON schedule_analytics
    FOR INSERT WITH CHECK (user_id = current_setting('app.current_user_id', true));

CREATE POLICY "Users can update own analytics" ON schedule_analytics
    FOR UPDATE USING (user_id = current_setting('app.current_user_id', true));

-- Schedule Templates RLS
ALTER TABLE schedule_templates ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own templates" ON schedule_templates
    FOR SELECT USING (user_id = current_setting('app.current_user_id', true));

CREATE POLICY "Users can insert own templates" ON schedule_templates
    FOR INSERT WITH CHECK (user_id = current_setting('app.current_user_id', true));

CREATE POLICY "Users can update own templates" ON schedule_templates
    FOR UPDATE USING (user_id = current_setting('app.current_user_id', true));

CREATE POLICY "Users can delete own templates" ON schedule_templates
    FOR DELETE USING (user_id = current_setting('app.current_user_id', true));

-- Schedule Recommendations RLS
ALTER TABLE schedule_recommendations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own recommendations" ON schedule_recommendations
    FOR SELECT USING (user_id = current_setting('app.current_user_id', true));

CREATE POLICY "Users can insert own recommendations" ON schedule_recommendations
    FOR INSERT WITH CHECK (user_id = current_setting('app.current_user_id', true));

CREATE POLICY "Users can update own recommendations" ON schedule_recommendations
    FOR UPDATE USING (user_id = current_setting('app.current_user_id', true));

-- Triggers for updated_at timestamps
CREATE TRIGGER update_user_preferences_updated_at BEFORE UPDATE ON user_preferences
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_schedules_updated_at BEFORE UPDATE ON user_schedules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_schedule_templates_updated_at BEFORE UPDATE ON schedule_templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Analytics Views
CREATE OR REPLACE VIEW user_schedule_overview AS
SELECT 
    user_id,
    COUNT(*) as total_scheduled_items,
    COUNT(CASE WHEN is_completed THEN 1 END) as completed_items,
    COUNT(CASE WHEN type = 'therapy' THEN 1 END) as therapy_sessions,
    COUNT(CASE WHEN type = 'exercise' THEN 1 END) as exercise_sessions,
    COUNT(CASE WHEN type = 'journal' THEN 1 END) as journal_sessions,
    COUNT(CASE WHEN type = 'sleep' THEN 1 END) as sleep_schedules,
    AVG(CASE WHEN is_completed THEN 100.0 ELSE 0.0 END) as completion_rate
FROM user_schedules
WHERE is_active = TRUE
GROUP BY user_id;

CREATE OR REPLACE VIEW weekly_schedule_patterns AS
SELECT 
    user_id,
    EXTRACT(DOW FROM start_time) as day_of_week,
    EXTRACT(HOUR FROM start_time) as hour_of_day,
    type,
    COUNT(*) as frequency,
    AVG(duration) as avg_duration
FROM user_schedules
WHERE is_active = TRUE
GROUP BY user_id, EXTRACT(DOW FROM start_time), EXTRACT(HOUR FROM start_time), type;

CREATE OR REPLACE VIEW schedule_effectiveness AS
SELECT 
    user_id,
    type,
    COUNT(*) as total_scheduled,
    COUNT(CASE WHEN is_completed THEN 1 END) as completed,
    AVG(CASE WHEN is_completed THEN 100.0 ELSE 0.0 END) as completion_rate,
    AVG(duration) as avg_duration
FROM user_schedules
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY user_id, type;

-- Function to detect schedule conflicts
CREATE OR REPLACE FUNCTION detect_schedule_conflicts(schedule_user_id TEXT)
RETURNS INTEGER AS $$
DECLARE
    conflict_count INTEGER := 0;
    schedule_item RECORD;
    other_item RECORD;
BEGIN
    -- Clear existing unresolved conflicts for this user
    DELETE FROM schedule_conflicts 
    WHERE user_id = schedule_user_id AND resolution_status = 'unresolved';
    
    -- Check for time overlaps
    FOR schedule_item IN 
        SELECT * FROM user_schedules 
        WHERE user_id = schedule_user_id AND is_active = TRUE
    LOOP
        FOR other_item IN 
            SELECT * FROM user_schedules 
            WHERE user_id = schedule_user_id 
            AND is_active = TRUE 
            AND id != schedule_item.id
            AND start_time < schedule_item.start_time + (schedule_item.duration || ' minutes')::INTERVAL
            AND start_time + (duration || ' minutes')::INTERVAL > schedule_item.start_time
        LOOP
            INSERT INTO schedule_conflicts 
                (user_id, conflict_type, schedule_item_1, schedule_item_2, severity)
            VALUES 
                (schedule_user_id, 'time_overlap', schedule_item.id, other_item.id, 
                 CASE 
                     WHEN schedule_item.priority = 'critical' OR other_item.priority = 'critical' THEN 'critical'
                     WHEN schedule_item.priority = 'high' OR other_item.priority = 'high' THEN 'high'
                     ELSE 'medium'
                 END);
            conflict_count := conflict_count + 1;
        END LOOP;
    END LOOP;
    
    RETURN conflict_count;
END;
$$ LANGUAGE plpgsql;

-- Function to calculate schedule adherence score
CREATE OR REPLACE FUNCTION calculate_adherence_score(
    scheduled_count INTEGER,
    completed_count INTEGER,
    consistency_bonus DECIMAL DEFAULT 0
) RETURNS DECIMAL AS $$
BEGIN
    IF scheduled_count = 0 THEN
        RETURN 100.0;
    END IF;
    
    RETURN LEAST(100.0, 
        (completed_count::DECIMAL / scheduled_count::DECIMAL * 100.0) + consistency_bonus
    );
END;
$$ LANGUAGE plpgsql;

-- Function to update schedule analytics daily
CREATE OR REPLACE FUNCTION update_daily_schedule_analytics()
RETURNS VOID AS $$
DECLARE
    user_record RECORD;
    analytics_date DATE := CURRENT_DATE - INTERVAL '1 day';
BEGIN
    FOR user_record IN 
        SELECT DISTINCT user_id FROM user_schedules 
        WHERE DATE(start_time) = analytics_date
    LOOP
        INSERT INTO schedule_analytics 
            (user_id, date, scheduled_items, completed_items, completion_rate,
             therapy_sessions, exercise_sessions, journal_entries)
        SELECT 
            user_record.user_id,
            analytics_date,
            COUNT(*),
            COUNT(CASE WHEN is_completed THEN 1 END),
            AVG(CASE WHEN is_completed THEN 100.0 ELSE 0.0 END),
            COUNT(CASE WHEN type = 'therapy' THEN 1 END),
            COUNT(CASE WHEN type = 'exercise' THEN 1 END),
            COUNT(CASE WHEN type = 'journal' THEN 1 END)
        FROM user_schedules
        WHERE user_id = user_record.user_id 
        AND DATE(start_time) = analytics_date
        ON CONFLICT (user_id, date) DO UPDATE SET
            scheduled_items = EXCLUDED.scheduled_items,
            completed_items = EXCLUDED.completed_items,
            completion_rate = EXCLUDED.completion_rate,
            therapy_sessions = EXCLUDED.therapy_sessions,
            exercise_sessions = EXCLUDED.exercise_sessions,
            journal_entries = EXCLUDED.journal_entries;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Comments for documentation
COMMENT ON TABLE user_preferences IS 'User scheduling preferences with encrypted sensitive data';
COMMENT ON TABLE user_schedules IS 'Main scheduling table for all types of scheduled activities';
COMMENT ON TABLE schedule_conflicts IS 'Detected conflicts between scheduled items';
COMMENT ON TABLE schedule_optimizations IS 'AI-generated schedule optimizations';
COMMENT ON TABLE schedule_analytics IS 'Daily analytics for schedule adherence and patterns';
COMMENT ON TABLE schedule_templates IS 'Reusable schedule templates';
COMMENT ON TABLE schedule_recommendations IS 'AI-generated scheduling recommendations';
COMMENT ON FUNCTION detect_schedule_conflicts IS 'Detect and record schedule conflicts for a user';
COMMENT ON FUNCTION calculate_adherence_score IS 'Calculate schedule adherence score (0-100)';
COMMENT ON FUNCTION update_daily_schedule_analytics IS 'Update daily schedule analytics for all users'; 