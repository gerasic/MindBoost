FROM python:3.11-slim

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
      postgresql-15 postgresql-client-15 libpq-dev gcc && \
    pip install --no-cache-dir patroni[etcd3] psycopg2-binary && \
    rm -rf /var/lib/apt/lists/*

COPY patroni.yml /etc/patroni.yml

RUN mkdir -p /var/lib/postgresql/pgdata && \
    chown -R postgres:postgres /var/lib/postgresql/pgdata && \
    chmod 0700 /var/lib/postgresql/pgdata

USER postgres

CMD ["patroni", "/etc/patroni.yml"]
