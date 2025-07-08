-- AI Trend Research Reports Table
CREATE TABLE IF NOT EXISTS ai_trend_reports (
    id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL,
    summary JSONB,
    detailed_results JSONB,
    new_keywords JSONB,
    recommendations JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index on date for efficient querying
CREATE INDEX IF NOT EXISTS idx_ai_trend_reports_date ON ai_trend_reports(date);

-- Create index on created_at for time-based queries
CREATE INDEX IF NOT EXISTS idx_ai_trend_reports_created_at ON ai_trend_reports(created_at);

-- Enable Row Level Security (RLS)
ALTER TABLE ai_trend_reports ENABLE ROW LEVEL SECURITY;

-- Create policy to allow authenticated users to read all reports
CREATE POLICY "Allow authenticated users to read reports" ON ai_trend_reports
    FOR SELECT USING (auth.role() = 'authenticated');

-- Create policy to allow authenticated users to insert reports
CREATE POLICY "Allow authenticated users to insert reports" ON ai_trend_reports
    FOR INSERT WITH CHECK (auth.role() = 'authenticated');

-- Create policy to allow authenticated users to update reports
CREATE POLICY "Allow authenticated users to update reports" ON ai_trend_reports
    FOR UPDATE USING (auth.role() = 'authenticated');

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to automatically update updated_at
CREATE TRIGGER update_ai_trend_reports_updated_at 
    BEFORE UPDATE ON ai_trend_reports 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Optional: Create a view for easier querying of recent reports
CREATE OR REPLACE VIEW recent_ai_trend_reports AS
SELECT 
    id,
    date,
    summary,
    detailed_results,
    new_keywords,
    recommendations,
    created_at,
    updated_at
FROM ai_trend_reports
ORDER BY created_at DESC;

-- Optional: Create a function to get reports by date range
CREATE OR REPLACE FUNCTION get_reports_by_date_range(
    start_date DATE,
    end_date DATE
)
RETURNS TABLE (
    id BIGINT,
    date DATE,
    summary JSONB,
    detailed_results JSONB,
    new_keywords JSONB,
    recommendations JSONB,
    created_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        r.id,
        r.date,
        r.summary,
        r.detailed_results,
        r.new_keywords,
        r.recommendations,
        r.created_at
    FROM ai_trend_reports r
    WHERE r.date BETWEEN start_date AND end_date
    ORDER BY r.date DESC;
END;
$$ LANGUAGE plpgsql; 