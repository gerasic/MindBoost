import os
import sys
import random
import datetime
import re
import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor, execute_values
from faker import Faker

faker = Faker()

enum_values = {}
table_pks = {}
table_info_map = {}

class ColumnInfo:
    def __init__(self, name, data_type):
        self.name = name
        self.data_type = data_type
        self.is_enum = False
        self.enum_type = None
        self.is_pk = False
        self.is_fk = False
        self.fk_table = None
        self.check_min = None
        self.check_max = None

class TableInfo:
    def __init__(self, name, columns):
        self.name = name
        self.columns = columns

def get_enum_values(conn, enum_type_name):
    if enum_type_name in enum_values:
        return enum_values[enum_type_name]
    with conn.cursor() as cur:
        cur.execute(sql.SQL("SELECT unnest(enum_range(NULL::{}))").format(
            sql.Identifier(enum_type_name)
        ))
        vals = [r[0] for r in cur.fetchall()]
    enum_values[enum_type_name] = vals
    return vals

def get_table_names(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT table_name
              FROM information_schema.tables
             WHERE table_schema = 'public'
               AND table_type = 'BASE TABLE'
               AND table_name <> 'flyway_schema_history'
            ORDER BY table_name;
        """)
        return [r[0] for r in cur.fetchall()]

def get_table_attributes(conn):
    tables = []
    for tbl in get_table_names(conn):
        columns = []

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT
                  c.column_name,
                  c.data_type,
                  c.udt_name,
                  (c.column_name = ANY (
                     SELECT kcu.column_name
                       FROM information_schema.key_column_usage kcu
                       JOIN information_schema.table_constraints tc
                         ON kcu.constraint_name = tc.constraint_name
                      WHERE tc.constraint_type = 'PRIMARY KEY'
                        AND tc.table_name = %s
                  )) AS is_pk
                FROM information_schema.columns c
               WHERE c.table_name = %s
               ORDER BY c.ordinal_position;
            """, (tbl, tbl))
            for r in cur.fetchall():
                ci = ColumnInfo(r['column_name'], r['data_type'])
                ci.is_pk = r['is_pk']
                if r['data_type'] == 'USER-DEFINED':
                    ci.is_enum = True
                    ci.enum_type = r['udt_name']
                    get_enum_values(conn, r['udt_name'])
                columns.append(ci)

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT
                  kcu.column_name,
                  ccu.table_name AS foreign_table_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage ccu
                  ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                  AND tc.table_name = %s;
            """, (tbl,))
            for fk_row in cur.fetchall():
                for ci in columns:
                    if ci.name == fk_row['column_name']:
                        ci.is_fk = True
                        ci.fk_table = fk_row['foreign_table_name']

        with conn.cursor() as cur:
            cur.execute("""
                SELECT cc.check_clause
                  FROM information_schema.check_constraints cc
                  JOIN information_schema.constraint_table_usage ctu
                    ON cc.constraint_name = ctu.constraint_name
                 WHERE ctu.table_name = %s;
            """, (tbl,))
            for (clause,) in cur.fetchall():
                m = re.search(
                    r"(?:\"(?P<col>\w+)\"|(?P<col>\w+))\s+BETWEEN\s*(?P<min>\d+)\s+AND\s*(?P<max>\d+)",
                    clause, re.IGNORECASE
                )
                if not m:
                    m = re.search(
                        r"(?:\"(?P<col>\w+)\"|(?P<col>\w+))\s*>=\s*(?P<min>\d+)\s+AND\s+(?:\"(?P<col2>\w+)\"|(?P<col2>\w+))\s*<=\s*(?P<max>\d+)",
                        clause, re.IGNORECASE
                    )
                if m:
                    colname = m.group('col') or m.group('col2')
                    minv = int(m.group('min'))
                    maxv = int(m.group('max'))
                    for ci in columns:
                        if ci.name == colname:
                            ci.check_min = minv
                            ci.check_max = maxv
                            break

        tables.append(TableInfo(tbl, columns))
    return tables

def get_pk_values(conn, table_name):
    if table_name in table_pks:
        return table_pks[table_name]

    ti = table_info_map[table_name]
    pk_cols = [c.name for c in ti.columns if c.is_pk]
    if not pk_cols:
        table_pks[table_name] = []
        return []

    col_list = sql.SQL(', ').join(sql.Identifier(c) for c in pk_cols)
    query = sql.SQL("SELECT {cols} FROM {tbl}").format(
        cols=col_list,
        tbl=sql.Identifier(table_name)
    )
    with conn.cursor() as cur:
        cur.execute(query)
        raw = cur.fetchall()

    if len(pk_cols) == 1:
        vals = [r[0] for r in raw]
    else:
        vals = [tuple(r) for r in raw]

    table_pks[table_name] = vals
    return vals

def generate_fake_value(conn, col: ColumnInfo):
    if col.check_min is not None and col.check_max is not None:
        return random.randint(col.check_min, col.check_max)

    if col.is_fk and col.fk_table:
        parent_vals = get_pk_values(conn, col.fk_table)
        return random.choice(parent_vals) if parent_vals else None

    if col.is_enum and col.enum_type:
        vals = enum_values.get(col.enum_type, [])
        return random.choice(vals) if vals else None

    dt = col.data_type.lower()
    if dt in ('integer', 'bigint', 'smallint'):
        return random.randint(0, 10000)
    if dt in ('character varying', 'varchar', 'text', 'character'):
        return faker.user_name() + str(random.randint(0, 100000))
    if dt == 'boolean':
        return random.choice([True, False])
    if dt in ('numeric', 'decimal', 'real', 'double precision'):
        return round(random.random() * 1000, 2)
    if dt == 'date':
        return (datetime.date.today() - datetime.timedelta(days=random.randint(0, 365))).isoformat()
    if 'timestamp' in dt:
        secs = random.randint(0, 86400)
        return (datetime.datetime.now() - datetime.timedelta(seconds=secs)).isoformat()
    return None

def topological_sort_tables(conn):
    all_tables = get_table_names(conn)
    graph = {t: [] for t in all_tables}
    indegree = {t: 0 for t in all_tables}

    for tbl in all_tables:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT ccu.table_name AS parent_table
                  FROM information_schema.table_constraints tc
                  JOIN information_schema.constraint_column_usage ccu
                    ON tc.constraint_name = ccu.constraint_name
                 WHERE tc.constraint_type = 'FOREIGN KEY'
                   AND tc.table_name = %s;
            """, (tbl,))
            for (parent,) in cur.fetchall():
                if parent in graph:
                    graph[parent].append(tbl)
                    indegree[tbl] += 1

    queue = [t for t, d in indegree.items() if d == 0]
    order = []
    while queue:
        node = queue.pop(0)
        order.append(node)
        for neigh in graph[node]:
            indegree[neigh] -= 1
            if indegree[neigh] == 0:
                queue.append(neigh)

    if len(order) != len(all_tables):
        raise RuntimeError("Цикл обнаружен в FK-зависимостях!")

    return order

def seed_table_batch(conn, ti: TableInfo, row_count: int, batch_size: int):
    cur = conn.cursor()
    table_name = ti.name

    if table_name == 'subscriptions':
        parent_pks = get_pk_values(conn, 'users')
        if not parent_pks:
            return

        rows = []
        cols_for_row = [c.name for c in ti.columns]

        for _ in range(row_count):
            u1 = random.choice(parent_pks)
            u2 = random.choice(parent_pks)
            while u2 == u1:
                u2 = random.choice(parent_pks)

            vals = []
            for col in ti.columns:
                if col.name == 'subscriber_id':
                    vals.append(u1)
                elif col.name == 'target_id':
                    vals.append(u2)
                else:
                    v = generate_fake_value(conn, col)
                    vals.append(v)
            rows.append(tuple(vals))

        if not rows:
            return

        col_idents = sql.SQL(', ').join(sql.Identifier(c) for c in cols_for_row)
        template = "(" + ", ".join(["%s"] * len(cols_for_row)) + ")"
        insert_sql = sql.SQL(
            "INSERT INTO {table} ({cols}) VALUES %s ON CONFLICT DO NOTHING"
        ).format(
            table=sql.Identifier(table_name),
            cols=col_idents
        )

        for i in range(0, len(rows), batch_size):
            batch = rows[i:i+batch_size]
            execute_values(cur, insert_sql.as_string(conn), batch, template=template)
        conn.commit()
        return

    single_fk_pk = [c for c in ti.columns if c.is_pk and c.is_fk]
    if len(single_fk_pk) == 1:
        fk_col = single_fk_pk[0].name
        parent_table = single_fk_pk[0].fk_table
        parent_pks = get_pk_values(conn, parent_table)
        if not parent_pks:
            return

        insert_cols = []
        for col in ti.columns:
            if col.is_pk and col.is_fk:
                insert_cols.append(col.name)
            elif not col.is_pk:
                insert_cols.append(col.name)
        if not insert_cols:
            return

        rows = []
        for parent_pk in parent_pks:
            vals = []
            for col_name in insert_cols:
                if col_name == fk_col:
                    vals.append(parent_pk)
                else:
                    col_obj = next(c for c in ti.columns if c.name == col_name)
                    v = generate_fake_value(conn, col_obj)
                    vals.append(v)
            rows.append(tuple(vals))

        col_idents = sql.SQL(', ').join(sql.Identifier(c) for c in insert_cols)
        template = "(" + ", ".join(["%s"] * len(insert_cols)) + ")"
        insert_sql = sql.SQL(
            "INSERT INTO {table} ({cols}) VALUES %s ON CONFLICT DO NOTHING"
        ).format(
            table=sql.Identifier(table_name),
            cols=col_idents
        )

        for i in range(0, len(rows), batch_size):
            batch = rows[i:i+batch_size]
            execute_values(cur, insert_sql.as_string(conn), batch, template=template)
        conn.commit()
        return

    insert_cols = []
    for col in ti.columns:
        if col.is_pk and not col.is_fk:
            continue
        insert_cols.append(col.name)
    if not insert_cols:
        return

    rows = []
    for _ in range(row_count):
        vals = []
        for col_name in insert_cols:
            col_obj = next(c for c in ti.columns if c.name == col_name)
            v = generate_fake_value(conn, col_obj)
            vals.append(v)
        rows.append(tuple(vals))

    col_idents = sql.SQL(', ').join(sql.Identifier(c) for c in insert_cols)
    template = "(" + ", ".join(["%s"] * len(insert_cols)) + ")"
    insert_sql = sql.SQL("INSERT INTO {table} ({cols}) VALUES %s ").format(
        table=sql.Identifier(table_name),
        cols=col_idents
    )
    if any(c.is_pk for c in ti.columns):
        insert_sql = sql.SQL("{} ON CONFLICT DO NOTHING").format(insert_sql)

    for i in range(0, len(rows), batch_size):
        batch = rows[i:i+batch_size]
        execute_values(cur, insert_sql.as_string(conn), batch, template=template)
    conn.commit()

def seed_database(conn, count: int, batch_size: int):
    tables_info = get_table_attributes(conn)
    for ti in tables_info:
        table_info_map[ti.name] = ti

    sorted_tables = topological_sort_tables(conn)
    for tbl in sorted_tables:
        ti = table_info_map[tbl]
        print(f"-> Сидирование таблицы {tbl} ({count} строк, batch={batch_size})")
        seed_table_batch(conn, ti, count, batch_size)

def parse_args():
    import argparse
    parser = argparse.ArgumentParser(
        description="Скрипт сидирования БД случайными данными на основе схемы."
    )
    parser.add_argument("--host",      default=os.getenv('DB_HOST', 'localhost'))
    parser.add_argument("--port",      default=os.getenv('DB_PORT', '5432'), type=int)
    parser.add_argument("--dbname",    default=os.getenv('DB_NAME', 'postgres'))
    parser.add_argument("--user",      default=os.getenv('DB_USER', 'postgres'))
    parser.add_argument("--password",  default=os.getenv('DB_PASSWORD', ''))
    parser.add_argument("--count",     default=int(os.getenv('SEED_COUNT', '10_000')), type=int,
                        help="Сколько строк генерировать на каждую таблицу")
    parser.add_argument("--batch-size", default=int(os.getenv('BATCH_SIZE', '1000')), type=int,
                        help="Размер батча для execute_values")
    parser.add_argument("--env",       default=os.getenv('APP_ENV', 'dev'),
                        choices=['dev','test','prod'],
                        help="Среда (dev/test/prod). В prod сидирование не выполняется.")
    return parser.parse_args()

def main():
    args = parse_args()
    if args.env.lower() not in ('dev', 'test'):
        print("Сидирование должно выполняться только в среде dev или test. Текущая среда:", args.env)
        sys.exit(0)

    try:
        conn = psycopg2.connect(
            host=args.host,
            port=args.port,
            dbname=args.dbname,
            user=args.user,
            password=args.password
        )
    except Exception as e:
        print("Не удалось подключиться к БД:", e)
        sys.exit(1)

    try:
        seed_database(conn, args.count, args.batch_size)
        print("Сидирование завершено успешно.")
    except Exception as e:
        print("Ошибка при сидировании базы данных:", e)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
