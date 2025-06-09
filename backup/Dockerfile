FROM alpine:latest

RUN apk add --no-cache bash postgresql-client tzdata

COPY backup.sh /usr/local/bin/backup.sh
COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /usr/local/bin/backup.sh /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
