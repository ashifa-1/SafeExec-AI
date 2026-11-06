-- SafeExec AI Database Ledger Schema & Seed
CREATE TABLE IF NOT EXISTS runs (
    run_id VARCHAR(100) PRIMARY KEY,
    sandbox_name VARCHAR(100) NOT NULL,
    problem_id VARCHAR(100) NOT NULL,
    state VARCHAR(50) NOT NULL CHECK (state IN ('created', 'ready', 'running', 'succeeded', 'failed', 'deleted')),
    execution_target VARCHAR(50) NOT NULL CHECK (execution_target = 'celesto_sandbox'),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN DEFAULT NULL,
    execution_time DOUBLE PRECISION DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS idx_runs_created_at ON runs (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_runs_sandbox_name ON runs (sandbox_name);

-- Seed initial demonstration record for verification
INSERT INTO runs (
    run_id,
    sandbox_name,
    problem_id,
    state,
    execution_target,
    created_at,
    updated_at,
    success,
    execution_time
) VALUES (
    'run-seed-0001',
    'sbx-seeddemo1',
    'problem-bootstrap-verification',
    'succeeded',
    'celesto_sandbox',
    CURRENT_TIMESTAMP - INTERVAL '1 hour',
    CURRENT_TIMESTAMP - INTERVAL '1 hour',
    TRUE,
    1.24
) ON CONFLICT (run_id) DO NOTHING;

