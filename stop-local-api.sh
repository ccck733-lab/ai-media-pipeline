#!/usr/bin/env bash
REPO="$(cd "$(dirname "$0")" && pwd)"
PIDFILE="$REPO/.api.pid"
if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
  echo "→ 停止后端进程 $(cat "$PIDFILE")"
  kill "$(cat "$PIDFILE")"
  rm -f "$PIDFILE"
else
  echo "→ 没有正在运行的后端进程"
  rm -f "$PIDFILE"
fi
