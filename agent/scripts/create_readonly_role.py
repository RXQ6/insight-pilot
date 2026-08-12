import os
import sys
from pathlib import Path

import psycopg
from psycopg import sql

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from insight_agent.config import settings


def main() -> None:
    password = os.getenv("READONLY_PASSWORD", "insight")
    with psycopg.connect(settings.postgres_dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = 'insight_readonly'")
            if cur.fetchone() is None:
                cur.execute(
                    sql.SQL("CREATE ROLE insight_readonly LOGIN PASSWORD {}").format(
                        sql.Literal(password)
                    )
                )
            cur.execute("GRANT CONNECT ON DATABASE insight TO insight_readonly")
            cur.execute("GRANT USAGE ON SCHEMA public TO insight_readonly")
            cur.execute("GRANT SELECT ON ALL TABLES IN SCHEMA public TO insight_readonly")
            cur.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO insight_readonly")
    print("readonly role ready: insight_readonly")


if __name__ == "__main__":
    main()
