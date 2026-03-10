"""Concurrency tests — SQLite WAL mode under concurrent access."""

from __future__ import annotations

import threading
import time


from tessera.core.database import Database


def _write_actions(db: Database, session_id: str, count: int, prefix: str) -> None:
    for i in range(count):
        db.record_action(
            session_id=session_id,
            action_type="graph_read",
            file_path=f"{prefix}_file_{i}.py",
        )


def test_concurrent_writes(tmp_path):
    """Multiple DB connections writing simultaneously should not deadlock."""
    db1 = Database(str(tmp_path))
    db2 = Database(str(tmp_path))

    sid1 = db1.create_new_session(str(tmp_path))
    sid2 = db2.create_new_session(str(tmp_path))

    errors: list[Exception] = []

    def writer1():
        try:
            _write_actions(db1, sid1, 20, "t1")
        except Exception as e:
            errors.append(e)

    def writer2():
        try:
            _write_actions(db2, sid2, 20, "t2")
        except Exception as e:
            errors.append(e)

    t1 = threading.Thread(target=writer1)
    t2 = threading.Thread(target=writer2)
    t1.start()
    t2.start()
    t1.join(timeout=30)
    t2.join(timeout=30)

    assert not errors, f"Concurrency errors: {errors}"

    # Both sessions should have their rows
    a1 = db1.get_session_actions(sid1)
    a2 = db2.get_session_actions(sid2)
    assert len(a1) == 20
    assert len(a2) == 20


def test_concurrent_reader_and_writer(tmp_path):
    """One connection writing while another reads should not block."""
    db_write = Database(str(tmp_path))
    db_read = Database(str(tmp_path))

    db_write.create_new_session(str(tmp_path))

    read_results: list = []
    errors: list[Exception] = []

    def reader():
        for _ in range(10):
            try:
                rows = db_read.get_all_files()
                read_results.append(len(rows))
                time.sleep(0.01)
            except Exception as e:
                errors.append(e)

    def writer():
        for i in range(10):
            try:
                db_write.upsert_file(f"file_{i}.py", ".py", "python", 10, f"h{i}", "", [], "code")
                time.sleep(0.01)
            except Exception as e:
                errors.append(e)

    r = threading.Thread(target=reader)
    w = threading.Thread(target=writer)
    r.start()
    w.start()
    r.join(timeout=15)
    w.join(timeout=15)

    assert not errors, f"Concurrency errors: {errors}"
    assert len(read_results) == 10


def test_retry_wrapper_on_locked(tmp_path):
    """_retry_write should retry on OperationalError: database is locked."""
    db = Database(str(tmp_path))
    call_count = [0]

    import sqlite3

    def flaky():
        call_count[0] += 1
        if call_count[0] < 3:
            raise sqlite3.OperationalError("database is locked")
        return "ok"

    result = db._retry_write(flaky)
    assert result == "ok"
    assert call_count[0] == 3
