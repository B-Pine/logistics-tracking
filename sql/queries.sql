-- =============================================================================
-- Day 4: Tracking history query + performance benchmark
-- Run from the project root (Git Bash / macOS / Linux):
--   docker compose exec -T postgres psql -U postgres -d logistics < sql/queries.sql
-- Reset afterwards with: python -m pytest   (or reload schema.sql + seed.sql)
-- =============================================================================

-- 1. Large dataset: 100,000 packages x 10 events = 1,000,000 tracking events.
--    Events are inserted in time order across all packages (ORDER BY step),
--    so one package's events are scattered through the table, as in real life.
INSERT INTO packages (tracking_id, shipment_id, weight_kg, current_status)
SELECT 'BULK' || LPAD(n::text, 7, '0'), 1, 1.00, 'Delivered'
FROM generate_series(1, 100000) AS n;

INSERT INTO tracking_events (package_id, location_id, status, event_timestamp)
SELECT p.package_id,
       1 + (step % 4),
       (ARRAY['Label Created', 'Picked Up', 'In Transit', 'In Transit', 'In Transit',
              'In Transit', 'In Transit', 'In Transit', 'Out for Delivery', 'Delivered'])[step + 1],
       TIMESTAMPTZ '2026-01-01' + p.package_id * INTERVAL '1 minute' + step * INTERVAL '3 hours'
FROM packages p
CROSS JOIN generate_series(0, 9) AS step
WHERE p.tracking_id LIKE 'BULK%'
ORDER BY step, p.package_id;

ANALYZE;  -- refresh planner statistics after the bulk load

-- 2. BEFORE: no index on tracking_events(package_id, event_timestamp)
DROP INDEX IF EXISTS idx_tracking_events_package_time;

EXPLAIN ANALYZE
WITH package AS (
    SELECT package_id FROM packages WHERE tracking_id = 'BULK0050000'
),
events AS (
    SELECT e.event_id, e.status, e.location_id, e.event_timestamp,
           LAG(e.event_timestamp) OVER (ORDER BY e.event_timestamp, e.event_id) AS previous_timestamp
    FROM tracking_events e
    JOIN package USING (package_id)
)
SELECT ev.status,
       l.city || ', ' || l.state AS location,
       ev.event_timestamp,
       ev.event_timestamp - ev.previous_timestamp AS time_since_previous
FROM events ev
JOIN locations l USING (location_id)
ORDER BY ev.event_timestamp, ev.event_id;

-- 3. Add the composite index
CREATE INDEX idx_tracking_events_package_time ON tracking_events (package_id, event_timestamp);
ANALYZE tracking_events;

-- 4. AFTER: identical query
EXPLAIN ANALYZE
WITH package AS (
    SELECT package_id FROM packages WHERE tracking_id = 'BULK0050000'
),
events AS (
    SELECT e.event_id, e.status, e.location_id, e.event_timestamp,
           LAG(e.event_timestamp) OVER (ORDER BY e.event_timestamp, e.event_id) AS previous_timestamp
    FROM tracking_events e
    JOIN package USING (package_id)
)
SELECT ev.status,
       l.city || ', ' || l.state AS location,
       ev.event_timestamp,
       ev.event_timestamp - ev.previous_timestamp AS time_since_previous
FROM events ev
JOIN locations l USING (location_id)
ORDER BY ev.event_timestamp, ev.event_id;
