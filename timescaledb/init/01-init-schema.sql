-- TimescaleDB Initialization Script
-- Creates hypertables and indexes for agent metrics storage

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Create schema for agent metrics
CREATE SCHEMA IF NOT EXISTS agent_metrics;

-- Table 1: Agent Performance Metrics (High-frequency time-series)
CREATE TABLE IF NOT EXISTS agent_metrics.agent_performance (
    time TIMESTAMPTZ NOT NULL,
    agent_id TEXT NOT NULL,
    agent_type TEXT,
    host TEXT,
    cpu_usage DOUBLE PRECISION,
    memory_usage_mb DOUBLE PRECISION,
    active_tasks INTEGER,
    task_completion_rate DOUBLE PRECISION,
    latency_ms DOUBLE PRECISION,
    error_count INTEGER DEFAULT 0,
    custom_metrics JSONB
);

-- Convert to hypertable (partition by time)
SELECT create_hypertable(
    'agent_metrics.agent_performance',
    'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Table 2: Agent Events (Discrete events)
CREATE TABLE IF NOT EXISTS agent_metrics.agent_events (
    time TIMESTAMPTZ NOT NULL,
    agent_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    severity TEXT CHECK (severity IN ('info', 'warning', 'error', 'critical')),
    message TEXT,
    metadata JSONB,
    trace_id TEXT
);

-- Convert to hypertable
SELECT create_hypertable(
    'agent_metrics.agent_events',
    'time',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

-- Table 3: Agent State History (Less frequent snapshots)
CREATE TABLE IF NOT EXISTS agent_metrics.agent_state (
    time TIMESTAMPTZ NOT NULL,
    agent_id TEXT NOT NULL,
    state TEXT NOT NULL,
    configuration JSONB,
    version TEXT,
    uptime_seconds BIGINT
);

-- Convert to hypertable
SELECT create_hypertable(
    'agent_metrics.agent_state',
    'time',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

-- Table 4: Aggregated Metrics (Continuous aggregates will be created)
CREATE TABLE IF NOT EXISTS agent_metrics.metrics_1min (
    bucket TIMESTAMPTZ NOT NULL,
    agent_id TEXT NOT NULL,
    avg_cpu_usage DOUBLE PRECISION,
    max_cpu_usage DOUBLE PRECISION,
    avg_memory_usage DOUBLE PRECISION,
    max_memory_usage DOUBLE PRECISION,
    total_tasks_completed INTEGER,
    avg_latency_ms DOUBLE PRECISION,
    error_rate DOUBLE PRECISION
);

SELECT create_hypertable(
    'agent_metrics.metrics_1min',
    'bucket',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_agent_perf_agent_time 
    ON agent_metrics.agent_performance (agent_id, time DESC);

CREATE INDEX IF NOT EXISTS idx_agent_perf_type_time 
    ON agent_metrics.agent_performance (agent_type, time DESC);

CREATE INDEX IF NOT EXISTS idx_agent_perf_host_time 
    ON agent_metrics.agent_performance (host, time DESC);

CREATE INDEX IF NOT EXISTS idx_agent_events_agent_time 
    ON agent_metrics.agent_events (agent_id, time DESC);

CREATE INDEX IF NOT EXISTS idx_agent_events_type_severity 
    ON agent_metrics.agent_events (event_type, severity, time DESC);

CREATE INDEX IF NOT EXISTS idx_agent_state_agent_time 
    ON agent_metrics.agent_state (agent_id, time DESC);

-- Create continuous aggregate for 1-minute rollups
CREATE MATERIALIZED VIEW IF NOT EXISTS agent_metrics.agent_performance_1min
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 minute', time) AS bucket,
    agent_id,
    avg(cpu_usage) as avg_cpu_usage,
    max(cpu_usage) as max_cpu_usage,
    avg(memory_usage_mb) as avg_memory_usage,
    max(memory_usage_mb) as max_memory_usage,
    sum(active_tasks) as total_active_tasks,
    avg(latency_ms) as avg_latency_ms,
    sum(error_count) as total_errors
FROM agent_metrics.agent_performance
GROUP BY bucket, agent_id
WITH NO DATA;

-- Add retention policies (automatic data cleanup)
SELECT add_retention_policy(
    'agent_metrics.agent_performance',
    INTERVAL '30 days',
    if_not_exists => TRUE
);

SELECT add_retention_policy(
    'agent_metrics.agent_events',
    INTERVAL '90 days',
    if_not_exists => TRUE
);

SELECT add_retention_policy(
    'agent_metrics.agent_state',
    INTERVAL '365 days',
    if_not_exists => TRUE
);

-- Create compression policy for older data
ALTER TABLE agent_metrics.agent_performance SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'agent_id'
);

SELECT add_compression_policy(
    'agent_metrics.agent_performance',
    INTERVAL '7 days',
    if_not_exists => TRUE
);

-- Create functions for common queries

-- Function to get agent health status
CREATE OR REPLACE FUNCTION agent_metrics.get_agent_health(
    p_agent_id TEXT,
    p_lookback INTERVAL DEFAULT INTERVAL '5 minutes'
)
RETURNS TABLE (
    agent_id TEXT,
    health_score DOUBLE PRECISION,
    status TEXT,
    last_seen TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ap.agent_id,
        CASE 
            WHEN avg(ap.error_count) > 10 THEN 0.0
            WHEN avg(ap.latency_ms) > 1000 THEN 50.0
            WHEN avg(ap.cpu_usage) > 90 THEN 70.0
            ELSE 100.0 - (avg(ap.error_count) * 10 + avg(ap.latency_ms) / 100)
        END as health_score,
        CASE 
            WHEN max(ap.time) < NOW() - INTERVAL '5 minutes' THEN 'offline'
            WHEN avg(ap.error_count) > 10 THEN 'critical'
            WHEN avg(ap.latency_ms) > 1000 THEN 'degraded'
            WHEN avg(ap.cpu_usage) > 90 THEN 'stressed'
            ELSE 'healthy'
        END as status,
        max(ap.time) as last_seen
    FROM agent_metrics.agent_performance ap
    WHERE ap.agent_id = p_agent_id
      AND ap.time > NOW() - p_lookback
    GROUP BY ap.agent_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get top problematic agents
CREATE OR REPLACE FUNCTION agent_metrics.get_top_problematic_agents(
    p_limit INTEGER DEFAULT 10,
    p_lookback INTERVAL DEFAULT INTERVAL '1 hour'
)
RETURNS TABLE (
    agent_id TEXT,
    error_count BIGINT,
    avg_latency_ms DOUBLE PRECISION,
    incident_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ap.agent_id,
        sum(ap.error_count) as error_count,
        avg(ap.latency_ms) as avg_latency_ms,
        count(DISTINCT CASE WHEN ap.error_count > 0 THEN ap.time END) as incident_count
    FROM agent_metrics.agent_performance ap
    WHERE ap.time > NOW() - p_lookback
    GROUP BY ap.agent_id
    HAVING sum(ap.error_count) > 0
    ORDER BY sum(ap.error_count) DESC, avg(ap.latency_ms) DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA agent_metrics TO agent_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA agent_metrics TO agent_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA agent_metrics TO agent_user;

-- Insert sample data for testing
INSERT INTO agent_metrics.agent_performance (
    time, agent_id, agent_type, host, cpu_usage, memory_usage_mb, 
    active_tasks, task_completion_rate, latency_ms, error_count
)
SELECT 
    NOW() - (random() * INTERVAL '7 days'),
    'agent-' || (random() * 100)::int,
    CASE (random() * 3)::int 
        WHEN 0 THEN 'collector'
        WHEN 1 THEN 'processor'
        WHEN 2 THEN 'analyzer'
        ELSE 'coordinator'
    END,
    'host-' || (random() * 10)::int,
    random() * 100,
    random() * 8192,
    (random() * 50)::int,
    random(),
    random() * 500,
    CASE WHEN random() > 0.9 THEN (random() * 5)::int ELSE 0 END
FROM generate_series(1, 1000);

-- Insert sample events
INSERT INTO agent_metrics.agent_events (
    time, agent_id, event_type, severity, message, metadata
)
SELECT 
    NOW() - (random() * INTERVAL '7 days'),
    'agent-' || (random() * 100)::int,
    CASE (random() * 5)::int
        WHEN 0 THEN 'started'
        WHEN 1 THEN 'completed_task'
        WHEN 2 THEN 'error'
        WHEN 3 THEN 'warning'
        ELSE 'restarted'
    END,
    CASE (random() * 4)::int
        WHEN 0 THEN 'info'
        WHEN 1 THEN 'warning'
        WHEN 2 THEN 'error'
        ELSE 'critical'
    END,
    'Sample event message',
    '{"source": "initialization"}'::jsonb
FROM generate_series(1, 500);

-- Insert sample state
INSERT INTO agent_metrics.agent_state (
    time, agent_id, state, configuration, version, uptime_seconds
)
SELECT 
    NOW() - (random() * INTERVAL '7 days'),
    'agent-' || (random() * 100)::int,
    CASE (random() * 3)::int
        WHEN 0 THEN 'running'
        WHEN 1 THEN 'paused'
        ELSE 'stopped'
    END,
    '{"threads": 4, "batch_size": 100}'::jsonb,
    'v' || (random() * 10)::int || '.' || (random() * 10)::int,
    (random() * 86400 * 30)::bigint
FROM generate_series(1, 200);

-- Analyze tables for query optimization
ANALYZE agent_metrics.agent_performance;
ANALYZE agent_metrics.agent_events;
ANALYZE agent_metrics.agent_state;

-- Verify setup
SELECT 
    'agent_performance' as table_name,
    count(*) as row_count
FROM agent_metrics.agent_performance
UNION ALL
SELECT 
    'agent_events' as table_name,
    count(*) as row_count
FROM agent_metrics.agent_events
UNION ALL
SELECT 
    'agent_state' as table_name,
    count(*) as row_count
FROM agent_metrics.agent_state;