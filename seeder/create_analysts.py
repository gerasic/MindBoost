import os
import logging
import psycopg2

db_config = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", 5432),
    "dbname": os.getenv("DB_NAME", "main_db"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
}

def get_logger(name: str = __name__) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


logger = get_logger(__name__)

def create_analytic_users():
    names = os.getenv("ANALYST_NAMES", "")
    analyst_names = [name.strip() for name in names.split(",") if name.strip()]

    if not analyst_names:
        logger.warning("ANALYST_NAMES is not set or empty")
        return

    try:
        conn = psycopg2.connect(**db_config)
        conn.autocommit = True
        cur = conn.cursor()
    except Exception as e:
        logger.error(f"Failed to connect to the database: {e}")
        return

    for name in analyst_names:
        password = f"{name}_123"

        try:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (name,))
            exists = cur.fetchone()

            if not exists:
                cur.execute(
                    f"CREATE ROLE {name} WITH LOGIN PASSWORD %s INHERIT IN ROLE analytic",
                    (password,)
                )
                logger.info(f"Created user: {name}")
            else:
                logger.info(f"User {name} already exists")
        except Exception as e:
            logger.error(f"Error while creating user {name}: {e}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    create_analytic_users()
