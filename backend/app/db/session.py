from time import perf_counter

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import Session, sessionmaker

from ..core.logging import get_logger


logger = get_logger("database")


def create_database_engine(
    database_url: str,
    *,
    sqlite_busy_timeout_ms: int = 5000,
    slow_query_ms: int = 500,
) -> Engine:
    is_sqlite = make_url(database_url).get_backend_name() == "sqlite"
    connect_args = {"check_same_thread": False} if is_sqlite else {}
    engine = create_engine(
        database_url,
        connect_args=connect_args,
        future=True,
        pool_pre_ping=True,
    )

    if is_sqlite:
        @event.listens_for(engine, "connect")
        def configure_sqlite(dbapi_connection, connection_record) -> None:
            del connection_record
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute(f"PRAGMA busy_timeout={int(sqlite_busy_timeout_ms)}")
                cursor.execute("PRAGMA synchronous=NORMAL")
                if make_url(database_url).database not in {None, "", ":memory:"}:
                    cursor.execute("PRAGMA journal_mode=WAL")
            finally:
                cursor.close()

    if slow_query_ms > 0:
        @event.listens_for(engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany) -> None:
            del cursor, statement, parameters, context, executemany
            conn.info.setdefault("query_started_at", []).append(perf_counter())

        @event.listens_for(engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany) -> None:
            del cursor, parameters, context, executemany
            starts = conn.info.get("query_started_at", [])
            if not starts:
                return
            duration_ms = (perf_counter() - starts.pop()) * 1000
            if duration_ms < slow_query_ms:
                return
            operation = statement.lstrip().partition(" ")[0].upper()[:20] or "UNKNOWN"
            logger.warning(
                "数据库查询耗时超过阈值",
                extra={
                    "event": "slow_database_query",
                    "duration_ms": round(duration_ms, 2),
                    "operation": operation,
                },
            )

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
