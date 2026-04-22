-- QuickApply Database Schema
-- Run this in your Supabase SQL Editor: Dashboard > SQL Editor > New Query

-- Profile table (single-row for the user's personal info)
CREATE TABLE IF NOT EXISTS profile (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    data JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Resumes metadata (PDFs stored locally, text + metadata here)
CREATE TABLE IF NOT EXISTS resumes (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    label TEXT NOT NULL UNIQUE,  -- "Data Engineer", "Data Analyst", "Data Science"
    file_name TEXT NOT NULL,
    parsed_text TEXT,
    uploaded_at TIMESTAMPTZ DEFAULT now()
);

-- Applications tracker
CREATE TABLE IF NOT EXISTS applications (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    job_url TEXT NOT NULL,
    company TEXT,
    job_title TEXT,
    location TEXT,
    salary_range TEXT,
    ats_platform TEXT,
    match_score INTEGER,
    resume_used TEXT,
    status TEXT DEFAULT 'Applied',
    job_description TEXT,
    answers_given JSONB,
    notes TEXT,
    applied_at TIMESTAMPTZ DEFAULT now(),
    follow_up_date TIMESTAMPTZ,
    last_status_update TIMESTAMPTZ DEFAULT now()
);

-- Settings key-value store
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- Insert default settings
INSERT INTO settings (key, value) VALUES
    ('use_ai', 'false'),
    ('default_mode', 'copilot'),
    ('browser_visible', 'true'),
    ('auto_submit', 'false'),
    ('typing_speed_ms', '60'),
    ('page_load_timeout', '30'),
    ('anthropic_model', 'claude-sonnet-4-6'),
    ('desktop_notifications', 'true'),
    ('max_apps_per_hour', '5')
ON CONFLICT (key) DO NOTHING;

-- Enable realtime for the applications table
ALTER PUBLICATION supabase_realtime ADD TABLE applications;

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);
CREATE INDEX IF NOT EXISTS idx_applications_applied_at ON applications(applied_at DESC);
CREATE INDEX IF NOT EXISTS idx_applications_company ON applications(company);

-- Optional: Row Level Security (disabled by default for local single-user use)
-- Uncomment these if you plan to expose the project publicly:
-- ALTER TABLE profile ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE resumes ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE applications ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE settings ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY "Allow all for anon" ON profile FOR ALL USING (true);
-- CREATE POLICY "Allow all for anon" ON resumes FOR ALL USING (true);
-- CREATE POLICY "Allow all for anon" ON applications FOR ALL USING (true);
-- CREATE POLICY "Allow all for anon" ON settings FOR ALL USING (true);
