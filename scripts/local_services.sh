#!/usr/bin/env bash
# Start the MySQL 8 and Redis a full test run needs, without Docker.
#
# The live-MySQL migration tests skip themselves when nothing answers on DB_HOST:DB_PORT, so a
# container that restarted overnight silently turns a "0 skips" run back into "6 skips" — and a
# skipped test proves nothing while still reporting green. Run this before `pytest` on any machine
# where the services are not already up; it is idempotent.
set -euo pipefail

if ! mysqladmin ping -h 127.0.0.1 --silent 2>/dev/null; then
  mkdir -p /var/run/mysqld && chown mysql:mysql /var/run/mysqld
  nohup mysqld --user=mysql --bind-address=127.0.0.1 --port=3306 \
    --character-set-server=utf8mb4 --collation-server=utf8mb4_0900_ai_ci >/tmp/mysqld.log 2>&1 &
  for _ in $(seq 1 60); do
    mysqladmin ping -h 127.0.0.1 --silent 2>/dev/null && break
    sleep 1
  done
fi
mysqladmin ping -h 127.0.0.1 --silent 2>/dev/null && echo "mysql: up" || { echo "mysql: FAILED"; exit 1; }

if ! redis-cli -h 127.0.0.1 ping >/dev/null 2>&1; then
  nohup redis-server --port 6379 --bind 127.0.0.1 --appendonly no --dir /tmp >/tmp/redis.log 2>&1 &
  sleep 2
fi
redis-cli -h 127.0.0.1 ping >/dev/null 2>&1 && echo "redis: up" || { echo "redis: FAILED"; exit 1; }

echo
echo "Run the suite with:"
echo "  cd backend && DB_HOST=127.0.0.1 MYSQL_ROOT_PASSWORD=root pytest"
