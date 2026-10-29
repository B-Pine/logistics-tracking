import json
import logging

import redis
from pymongo.errors import PyMongoError
from psycopg.rows import dict_row

from app.db import pg_pool, redis_client, scan_logs

CACHE_TTL_SECONDS = 3600


def _cache_status(tracking_id, payload):
    """Best-effort Redis write: a cache failure must never fail a scan."""
    try:
        redis_client.set(f"package:{tracking_id}:status", json.dumps(payload), ex=CACHE_TTL_SECONDS)
    except redis.RedisError as e:
        logging.warning("Redis cache not updated for %s: %s", tracking_id, e)


def process_tracking_scan(package_id, location_id, status, scanner_id="unknown", metadata=None):
    """Record a scan: one PostgreSQL transaction, then update Redis and MongoDB."""
    # 1. PostgreSQL: update the package and insert the event atomically
    with pg_pool.connection() as conn:
        row = conn.execute(
            "UPDATE packages SET current_status = %s WHERE package_id = %s RETURNING tracking_id",
            (status, package_id),
        ).fetchone()
        if row is None:
            raise ValueError(f"Package {package_id} not found")
        tracking_id = row[0]

        event_timestamp = conn.execute(
            "INSERT INTO tracking_events (package_id, location_id, status) "
            "VALUES (%s, %s, %s) RETURNING event_timestamp",
            (package_id, location_id, status),
        ).fetchone()[0]

        location = conn.execute(
            "SELECT city || ', ' || state FROM locations WHERE location_id = %s",
            (location_id,),
        ).fetchone()[0]
    # Reaching this line means the transaction committed.

    payload = {"status": status, "location": location}

    # 2. Redis: cache the latest status
    _cache_status(tracking_id, payload)

    # 3. MongoDB: keep the raw scan for auditing
    try:
        scan_logs.insert_one({
            "package_id": package_id,
            "tracking_id": tracking_id,
            "location_id": location_id,
            "status": status,
            "scanner_id": scanner_id,
            "scanned_at": event_timestamp,
            "metadata": metadata or {},
        })
    except PyMongoError as e:
        logging.warning("Scan log not written to MongoDB for %s: %s", tracking_id, e)

    return {"tracking_id": tracking_id, **payload}


def get_package_status(tracking_id):
    """Read the latest status from Redis, falling back to PostgreSQL."""
    try:
        cached = redis_client.get(f"package:{tracking_id}:status")
        if cached:
            return json.loads(cached)
    except redis.RedisError as e:
        logging.warning("Redis unavailable, reading from PostgreSQL: %s", e)

    with pg_pool.connection() as conn:
        row = conn.execute(
            """
                SELECT p.current_status, l.city || ', ' || l.state
                FROM packages p
                JOIN tracking_events e USING (package_id)
                JOIN locations l USING (location_id)
                WHERE p.tracking_id = %s
                ORDER BY e.event_timestamp DESC
                LIMIT 1
            """,
            (tracking_id,),
        ).fetchone()

    if row is None:
        return None
    payload = {"status": row[0], "location": row[1]}
    _cache_status(tracking_id, payload)  # refill the cache for next time
    return payload


def get_package_history(tracking_id):
    """Full tracking history, oldest first, with the time spent since the previous scan."""
    with pg_pool.connection() as conn:
        cur = conn.cursor(row_factory=dict_row)
        return cur.execute(
            """
            WITH package AS (
                SELECT package_id FROM packages WHERE tracking_id = %s
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
            ORDER BY ev.event_timestamp, ev.event_id
            """,
            (tracking_id,),
        ).fetchall()

def get_scan_logs(tracking_id):
    """Raw scanner logs from mongo Db, oldest first."""
    return list(scan_logs.find({"tracking_id": tracking_id}, {"_id":0}).sort("scanned_at", 1))