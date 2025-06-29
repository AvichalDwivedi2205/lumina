-- Nutrition Agent Database Schema
-- Comprehensive schema for nutrition tracking, meal planning, and consultation

-- Enable Row Level Security
ALTER DATABASE postgres SET row_security = on;

-- User Nutrition Profiles
CREATE TABLE IF NOT EXISTS nutrition_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    daily_calorie_goal INTEGER DEFAULT 2000,
    dietary_restrictions TEXT[] DEFAULT '{}',
    food_preferences TEXT[] DEFAULT '{}',
    goals TEXT[] DEFAULT '{}',
    height_cm INTEGER,
    weight_kg DECIMAL(5,2),
    age INTEGER,
    gender TEXT CHECK (gender IN ('male', 'female', 'other', 'prefer_not_to_say')),
    activity_level TEXT CHECK (activity_level IN ('sedentary', 'lightly_active', 'moderately_active', 'very_active', 'extremely_active')) DEFAULT 'moderately_active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id)
);

-- Food Logs
CREATE TABLE IF NOT EXISTS food_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    meal_type TEXT CHECK (meal_type IN ('breakfast', 'lunch', 'dinner', 'snack')) NOT NULL,
    foods_data TEXT NOT NULL, -- Encrypted JSON with detailed food information
    total_calories DECIMAL(8,2) DEFAULT 0,
    total_protein DECIMAL(8,2) DEFAULT 0,
    total_carbs DECIMAL(8,2) DEFAULT 0,
    total_fat DECIMAL(8,2) DEFAULT 0,
    total_fiber DECIMAL(8,2) DEFAULT 0,
    total_sodium DECIMAL(8,2) DEFAULT 0,
    total_sugar DECIMAL(8,2) DEFAULT 0,
    image_url TEXT, -- Optional food image URL
    logged_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Meal Plans
CREATE TABLE IF NOT EXISTS meal_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    meal_plan_data TEXT NOT NULL, -- Encrypted JSON with complete meal plan
    week_start_date DATE NOT NULL,
    total_weekly_calories DECIMAL(10,2),
    average_daily_calories DECIMAL(8,2),
    protein_percent DECIMAL(5,2),
    carbs_percent DECIMAL(5,2),
    fat_percent DECIMAL(5,2),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Nutrition Consultations
CREATE TABLE IF NOT EXISTS nutrition_consultations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    query TEXT NOT NULL,
    response TEXT NOT NULL,
    consultation_type TEXT DEFAULT 'general',
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Daily Nutrition Summary (for analytics)
CREATE TABLE IF NOT EXISTS daily_nutrition_summary (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    date DATE NOT NULL,
    total_calories DECIMAL(8,2) DEFAULT 0,
    total_protein DECIMAL(8,2) DEFAULT 0,
    total_carbs DECIMAL(8,2) DEFAULT 0,
    total_fat DECIMAL(8,2) DEFAULT 0,
    total_fiber DECIMAL(8,2) DEFAULT 0,
    total_sodium DECIMAL(8,2) DEFAULT 0,
    total_sugar DECIMAL(8,2) DEFAULT 0,
    meals_logged INTEGER DEFAULT 0,
    calorie_goal_met BOOLEAN DEFAULT FALSE,
    macro_balance_score DECIMAL(5,2), -- 0-100 score for macro balance
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, date)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_nutrition_profiles_user_id ON nutrition_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_food_logs_user_id ON food_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_food_logs_logged_at ON food_logs(logged_at);
CREATE INDEX IF NOT EXISTS idx_food_logs_meal_type ON food_logs(meal_type);
CREATE INDEX IF NOT EXISTS idx_meal_plans_user_id ON meal_plans(user_id);
CREATE INDEX IF NOT EXISTS idx_meal_plans_week_start ON meal_plans(week_start_date);
CREATE INDEX IF NOT EXISTS idx_nutrition_consultations_user_id ON nutrition_consultations(user_id);
CREATE INDEX IF NOT EXISTS idx_daily_summary_user_date ON daily_nutrition_summary(user_id, date);

-- Row Level Security Policies

-- Nutrition Profiles RLS
ALTER TABLE nutrition_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own nutrition profile" ON nutrition_profiles
    FOR SELECT USING (user_id = current_setting('app.current_user_id', true));

CREATE POLICY "Users can insert own nutrition profile" ON nutrition_profiles
    FOR INSERT WITH CHECK (user_id = current_setting('app.current_user_id', true));

CREATE POLICY "Users can update own nutrition profile" ON nutrition_profiles
    FOR UPDATE USING (user_id = current_setting('app.current_user_id', true));

-- Food Logs RLS
ALTER TABLE food_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own food logs" ON food_logs
    FOR SELECT USING (user_id = current_setting('app.current_user_id', true));

CREATE POLICY "Users can insert own food logs" ON food_logs
    FOR INSERT WITH CHECK (user_id = current_setting('app.current_user_id', true));

CREATE POLICY "Users can update own food logs" ON food_logs
    FOR UPDATE USING (user_id = current_setting('app.current_user_id', true));

CREATE POLICY "Users can delete own food logs" ON food_logs
    FOR DELETE USING (user_id = current_setting('app.current_user_id', true));

-- Meal Plans RLS
ALTER TABLE meal_plans ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own meal plans" ON meal_plans
    FOR SELECT USING (user_id = current_setting('app.current_user_id', true));

CREATE POLICY "Users can insert own meal plans" ON meal_plans
    FOR INSERT WITH CHECK (user_id = current_setting('app.current_user_id', true));

CREATE POLICY "Users can update own meal plans" ON meal_plans
    FOR UPDATE USING (user_id = current_setting('app.current_user_id', true));

CREATE POLICY "Users can delete own meal plans" ON meal_plans
    FOR DELETE USING (user_id = current_setting('app.current_user_id', true));

-- Nutrition Consultations RLS
ALTER TABLE nutrition_consultations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own consultations" ON nutrition_consultations
    FOR SELECT USING (user_id = current_setting('app.current_user_id', true));

CREATE POLICY "Users can insert own consultations" ON nutrition_consultations
    FOR INSERT WITH CHECK (user_id = current_setting('app.current_user_id', true));

-- Daily Nutrition Summary RLS
ALTER TABLE daily_nutrition_summary ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own daily summary" ON daily_nutrition_summary
    FOR SELECT USING (user_id = current_setting('app.current_user_id', true));

CREATE POLICY "Users can insert own daily summary" ON daily_nutrition_summary
    FOR INSERT WITH CHECK (user_id = current_setting('app.current_user_id', true));

CREATE POLICY "Users can update own daily summary" ON daily_nutrition_summary
    FOR UPDATE USING (user_id = current_setting('app.current_user_id', true));

-- Triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_nutrition_profiles_updated_at BEFORE UPDATE ON nutrition_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_meal_plans_updated_at BEFORE UPDATE ON meal_plans
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Analytics Views
CREATE OR REPLACE VIEW user_nutrition_analytics AS
SELECT 
    user_id,
    DATE_TRUNC('week', date) as week_start,
    AVG(total_calories) as avg_daily_calories,
    AVG(total_protein) as avg_daily_protein,
    AVG(total_carbs) as avg_daily_carbs,
    AVG(total_fat) as avg_daily_fat,
    AVG(macro_balance_score) as avg_balance_score,
    COUNT(*) as days_logged,
    COUNT(CASE WHEN calorie_goal_met THEN 1 END) as days_goal_met
FROM daily_nutrition_summary
GROUP BY user_id, DATE_TRUNC('week', date);

CREATE OR REPLACE VIEW monthly_nutrition_trends AS
SELECT 
    user_id,
    DATE_TRUNC('month', date) as month,
    AVG(total_calories) as avg_calories,
    STDDEV(total_calories) as calories_consistency,
    AVG(meals_logged) as avg_meals_per_day,
    COUNT(*) as days_in_month
FROM daily_nutrition_summary
GROUP BY user_id, DATE_TRUNC('month', date);

-- Function to calculate macro balance score
CREATE OR REPLACE FUNCTION calculate_macro_balance_score(
    protein_g DECIMAL,
    carbs_g DECIMAL,
    fat_g DECIMAL,
    total_calories DECIMAL
) RETURNS DECIMAL AS $$
DECLARE
    protein_percent DECIMAL;
    carbs_percent DECIMAL;
    fat_percent DECIMAL;
    score DECIMAL;
BEGIN
    -- Calculate percentages
    protein_percent = (protein_g * 4) / NULLIF(total_calories, 0) * 100;
    carbs_percent = (carbs_g * 4) / NULLIF(total_calories, 0) * 100;
    fat_percent = (fat_g * 9) / NULLIF(total_calories, 0) * 100;
    
    -- Score based on recommended ranges
    -- Protein: 10-35%, Carbs: 45-65%, Fat: 20-35%
    score = 100;
    
    -- Deduct points for being outside ranges
    IF protein_percent < 10 OR protein_percent > 35 THEN
        score = score - 20;
    END IF;
    
    IF carbs_percent < 45 OR carbs_percent > 65 THEN
        score = score - 20;
    END IF;
    
    IF fat_percent < 20 OR fat_percent > 35 THEN
        score = score - 20;
    END IF;
    
    RETURN GREATEST(0, score);
END;
$$ LANGUAGE plpgsql;

-- Comments for documentation
COMMENT ON TABLE nutrition_profiles IS 'User nutrition profiles with goals and preferences';
COMMENT ON TABLE food_logs IS 'Individual food entries with detailed nutrition data';
COMMENT ON TABLE meal_plans IS 'Weekly meal plans with shopping lists and prep instructions';
COMMENT ON TABLE nutrition_consultations IS 'AI nutrition consultation history';
COMMENT ON TABLE daily_nutrition_summary IS 'Daily aggregated nutrition data for analytics';
COMMENT ON FUNCTION calculate_macro_balance_score IS 'Calculate macro balance score (0-100) based on recommended ranges'; 