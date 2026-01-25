"""
Schema bootstrap: create tables if missing.
Idempotent. No Alembic. Reintroduce migrations later via REINTRODUCE_ALEMBIC.md.
Repairs initiatives (and other critical tables) if they exist with wrong schema.
"""
import logging
import time

from sqlalchemy import text

logger = logging.getLogger(__name__)

# Max retries and sleep (seconds) while waiting for Postgres
DB_RETRY_ATTEMPTS = 20
DB_RETRY_SLEEP = 1.0


def _table_missing_column(engine, table_name: str, column_name: str) -> bool:
    """True if table exists but does not have the given column."""
    with engine.connect() as conn:
        has_table = conn.execute(
            text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = :t"
            ),
            {"t": table_name},
        ).fetchone()
        if not has_table:
            return False
        has_col = conn.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = :t AND column_name = :c"
            ),
            {"t": table_name, "c": column_name},
        ).fetchone()
    return has_col is None


def init_db(engine) -> None:
    """
    Create tables if missing. Idempotent.
    Repairs initiatives (and category_scores) if they exist with wrong schema.
    Drops memos table if present (memo feature removed).
    Retries connection up to DB_RETRY_ATTEMPTS times with DB_RETRY_SLEEP between attempts.
    """
    import app.db.models  # noqa: F401

    from app.db.session import Base

    for attempt in range(1, DB_RETRY_ATTEMPTS + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            break
        except Exception as e:
            logger.warning(
                "DB not ready (attempt %d/%d): %s. Retrying in %s s...",
                attempt,
                DB_RETRY_ATTEMPTS,
                e,
                DB_RETRY_SLEEP,
            )
            if attempt == DB_RETRY_ATTEMPTS:
                raise RuntimeError(
                    f"Database not ready after {DB_RETRY_ATTEMPTS} attempts. "
                    "Check that Postgres is running and reachable."
                ) from e
            time.sleep(DB_RETRY_SLEEP)

    logger.info("Creating tables if missing (Base.metadata.create_all)...")
    Base.metadata.create_all(bind=engine)

    # Repair tables that exist with wrong schema (e.g. old initiatives without cycle_id)
    for table_name, column_name in [
        ("initiatives", "cycle_id"),
        ("category_scores", "cycle_id"),
    ]:
        if _table_missing_column(engine, table_name, column_name):
            logger.warning(
                "Table %s missing column %s; dropping and recreating.",
                table_name,
                column_name,
            )
            with engine.begin() as conn:
                conn.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE"))
            Base.metadata.tables[table_name].create(bind=engine)

    # Drop memos table if present (memo feature removed)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS memos CASCADE"))

    tables = list(Base.metadata.tables.keys())
    logger.info("Schema bootstrap complete. Tables: %s", tables or "(none)")
