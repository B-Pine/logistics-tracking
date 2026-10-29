from pathlib import Path
from datetime import timedelta

import psycopg
import pytest
import redis

from app.db import pg_pool, redis_client, scan_logs
from app.tracking import get_package_status, process_tracking_scan, get_package_history, get_scan_logs

SQL_DIR = Path(__file__).parent.parent / "sql"


@pytest.fixture(autouse=True)
def fresh_data():
    """Reset all three databases before every test."""
    with pg_pool.connection() as conn:
        conn.execute((SQL_DIR / "schema.sql").read_text())
        conn.execute((SQL_DIR / "seed.sql").read_text())
    redis_client.flushdb()
    scan_logs.delete_many({})


def package_state(package_id):
    with pg_pool.connection() as conn:
        return conn.execute(
            "SELECT current_status, (SELECT COUNT(*) FROM tracking_events WHERE package_id = %s) "
            "FROM packages WHERE package_id = %s",
            (package_id, package_id),
        ).fetchone()


def test_scan_updates_package_and_records_event():
    process_tracking_scan(3, 2, "In Transit")
    assert package_state(3) == ("In Transit", 2)


def test_scan_caches_status_and_logs_to_mongo():
    process_tracking_scan(3, 2, "In Transit", scanner_id="SCN-LOU-01")
    assert redis_client.get("package:TRK1003:status") == '{"status": "In Transit", "location": "Louisville, KY"}'
    assert scan_logs.count_documents({"tracking_id": "TRK1003", "scanner_id": "SCN-LOU-01"}) == 1


def test_unknown_package_is_rejected():
    with pytest.raises(ValueError):
        process_tracking_scan(999, 1, "In Transit")


def test_invalid_status_rolls_back_everything():
    before = package_state(3)
    with pytest.raises(psycopg.errors.CheckViolation):
        process_tracking_scan(3, 1, "Lost")
    assert package_state(3) == before
    assert redis_client.get("package:TRK1003:status") is None


def test_scan_succeeds_when_redis_is_down(monkeypatch):
    def redis_down(*args, **kwargs):
        raise redis.ConnectionError("Redis is down")

    monkeypatch.setattr(redis_client, "set", redis_down)    # Temporary substitute redis_client with 'set' set to redis_down
    process_tracking_scan(3, 2, "In Transit")
    assert package_state(3) == ("In Transit", 2)


def test_status_read_falls_back_to_postgres_and_refills_cache():
    assert get_package_status("TRK1001") == {"status": "Delivered", "location": "Atlanta, GA"}
    assert redis_client.get("package:TRK1001:status") is not None


def test_history_is_ordered_with_time_between_scans():
    history = get_package_history("TRK1001")
    assert [h["status"] for h in history] == [
        "Label Created", "Picked Up", "In Transit", "Out for Delivery", "Delivered"
    ]
    assert history[0]["time_since_previous"] is None
    assert history[1]["time_since_previous"] == timedelta(hours=3)
    assert get_package_history("TRK0000") == []


def test_scan_logs_can_be_read_back():
    process_tracking_scan(3, 2, "In Transit", scanner_id="SCN-LOU-01")
    process_tracking_scan(3, 4, "Out for Delivery", scanner_id="DRV-ATL-17")
    logs = get_scan_logs("TRK1003")
    assert [log["scanner_id"] for log in logs] == ["SCN-LOU-01", "DRV-ATL-17"]