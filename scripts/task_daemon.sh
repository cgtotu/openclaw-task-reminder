#!/bin/bash
# 任务提醒守护进程 - 每10秒检查一次 Redis 任务，到期发送飞书提醒

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/task_reminder.log"

echo "[$(date)] 任务提醒守护进程启动 (10秒间隔)" >> "$LOG_FILE"

while true; do
    python3 "$SCRIPT_DIR/task_reminder.py" >> "$LOG_FILE" 2>&1
    sleep 10
done
