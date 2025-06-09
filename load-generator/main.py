import os
import time
import psycopg2
from psycopg2 import OperationalError, InterfaceError
from flask import Flask, Response
from prometheus_client import Summary, Gauge, generate_latest, CONTENT_TYPE_LATEST, CollectorRegistry
from faker import Faker

app = Flask(__name__)

registry = CollectorRegistry()

REQUEST_TIME = Summary(
    'db_query_duration_seconds',
    'Time spent processing DB query',
    ['query_name'],
    registry=registry
)

REQUEST_TIME_MAX = Gauge(
    'db_query_duration_seconds_max',
    'Max time spent processing DB query',
    ['query_name'],
    registry=registry
)

PG_INDEX_SCANS = Gauge(
    'db_index_scans_total',
    'Number of index scans on table',
    ['table_name'],
    registry=registry
)

faker = Faker()

def get_connection():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'haproxy'),
        port=int(os.getenv('DB_PORT', 5432)),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        dbname=os.getenv('DB_NAME'),
        connect_timeout=3
    )

conn = get_connection()
cursor = conn.cursor()

indexed_tables = [
    'users',
    'user_achievements',
    'syllabuses'
]

@app.route('/metrics')
def metrics():
    global conn, cursor

    random_name_pattern = faker.name()
    queries = {
        'top_10_users_by_achievements': """
            SELECT u.user_id,
                   u.nickname,
                   COUNT(a.achievement_id) AS total_achievements
            FROM users u
            JOIN user_achievements a
              ON a.user_id = u.user_id
            GROUP BY u.user_id, u.nickname
            ORDER BY total_achievements DESC
            LIMIT 10
        """,

        'search_users_by_nickname': f"""
            SELECT user_id,
                   nickname,
                   email
            FROM users
            WHERE nickname ILIKE '%{random_name_pattern}%'
            LIMIT 50
        """,

        'top_10_syllabuses_by_favorites': """
            SELECT s.syllabus_id,
                   s.title,
                   COUNT(f.user_id) AS favorites_count
            FROM syllabuses s
            JOIN user_favorites f
              ON f.syllabus_id = s.syllabus_id
            GROUP BY s.syllabus_id, s.title
            ORDER BY favorites_count DESC
            LIMIT 10
        """
    }

    for name, sql in queries.items():
        try:
            start = time.time()
            cursor.execute(sql)
            cursor.fetchall()
            duration = time.time() - start

            REQUEST_TIME.labels(query_name=name).observe(duration)
            REQUEST_TIME_MAX.labels(query_name=name).set(duration)

        except (OperationalError, InterfaceError) as e:
            app.logger.warning(f"DB connection lost when executing `{name}`, reconnecting: {e}")

            try:
                cursor.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass

            conn = get_connection()
            cursor = conn.cursor()

            try:
                start = time.time()
                cursor.execute(sql)
                cursor.fetchall()
                duration = time.time() - start
                REQUEST_TIME.labels(query_name=name).observe(duration)
                REQUEST_TIME_MAX.labels(query_name=name).set(duration)
            except Exception as e2:
                conn.rollback()
                app.logger.error(f"Second attempt for `{name}` also failed: {e2}")

        except Exception as e:
            conn.rollback()
            app.logger.error(f"Query `{name}` failed: {e}")

    for tbl in indexed_tables:
        try:
            cursor.execute(
                """
                SELECT coalesce(idx_scan, 0)
                FROM pg_stat_user_tables
                WHERE schemaname = 'public'
                  AND relname = %s;
                """,
                (tbl,)
            )
            result = cursor.fetchone()
            idx_count = result[0] if result else 0
            PG_INDEX_SCANS.labels(table_name=tbl).set(idx_count)

        except (OperationalError, InterfaceError) as e:
            app.logger.warning(f"DB connection lost when fetching idx_scan for `{tbl}`, reconnecting: {e}")
            try:
                cursor.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass

            conn = get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    SELECT coalesce(idx_scan, 0)
                    FROM pg_stat_user_tables
                    WHERE schemaname = 'public'
                      AND relname = %s;
                    """,
                    (tbl,)
                )
                result = cursor.fetchone()
                idx_count = result[0] if result else 0
                PG_INDEX_SCANS.labels(table_name=tbl).set(idx_count)
            except Exception as e2:
                conn.rollback()
                app.logger.error(f"Second attempt for idx_scan `{tbl}` also failed: {e2}")

        except Exception as e:
            conn.rollback()
            app.logger.error(f"Failed to fetch idx_scan for `{tbl}`: {e}")

    data = generate_latest(registry)
    return Response(data, mimetype=CONTENT_TYPE_LATEST)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
