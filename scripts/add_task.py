#!/usr/bin/env python3
"""
添加新任务到 Redis，并显示完整任务总览
用法: python3 add_task.py "任务标题" "2026-04-28 09:00"
"""

import sys
import json
import subprocess
from datetime import datetime
import pytz

TZ = pytz.timezone('Asia/Shanghai')

def redis_zadd(key, score, member):
    result = subprocess.run(
        ['redis-cli', 'ZADD', key, str(score), json.dumps(member, ensure_ascii=False)],
        capture_output=True, text=True
    )
    return result.returncode == 0

def parse_time(time_str):
    """解析时间字符串为时间戳"""
    dt = datetime.strptime(time_str, '%Y-%m-%d %H:%M')
    local_dt = TZ.localize(dt)
    return int(local_dt.timestamp())

def get_next_id():
    """获取下一个任务 ID"""
    result = subprocess.run(['redis-cli', 'GET', 'juzi:tasks:next_id'], capture_output=True, text=True)
    current_id = int(result.stdout.strip()) if result.stdout.strip() else 0
    next_id = current_id + 1
    subprocess.run(['redis-cli', 'SET', 'juzi:tasks:next_id', str(next_id)], capture_output=True)
    return next_id

def format_ts(ts):
    return datetime.fromtimestamp(ts, tz=TZ).strftime('%H:%M')

def print_overview():
    """打印任务总览"""
    # Pending
    result = subprocess.run(['redis-cli', 'ZRANGE', 'juzi:tasks:pending', '0', '-1', 'WITHSCORES'],
                          capture_output=True, text=True)
    pending = []
    lines = result.stdout.strip().split('\n') if result.stdout.strip() else []
    for i in range(0, len(lines), 2):
        if i+1 < len(lines):
            pending.append((json.loads(lines[i]), float(lines[i+1])))
    
    # Completed
    result2 = subprocess.run(['redis-cli', 'ZREVRANGE', 'juzi:tasks:completed', '0', '9', 'WITHSCORES'],
                           capture_output=True, text=True)
    completed = []
    lines2 = result2.stdout.strip().split('\n') if result2.stdout.strip() else []
    for i in range(0, len(lines2), 2):
        if i+1 < len(lines2):
            completed.append((json.loads(lines2[i]), float(lines2[i+1])))
    
    print()
    print("📋 任务总览")
    print()
    print("⏳ 进行中任务：")
    if pending:
        for t, score in pending:
            print(f"  • {t['title']} — {format_ts(t['due_time'])}")
    else:
        print("  （无）")
    print()
    print("✅ 最近已完成：")
    if completed:
        for t, score in completed:
            print(f"  • {t['title']} — {format_ts(t['due_time'])}")
    else:
        print("  （无）")

def main():
    if len(sys.argv) < 3:
        print("用法: python3 add_task.py \"任务标题\" \"2026-04-28 09:00\"")
        sys.exit(1)

    title = sys.argv[1]
    time_str = sys.argv[2]

    try:
        due_timestamp = parse_time(time_str)
    except ValueError:
        print(f"❌ 时间格式错误，请使用格式: 2026-04-28 09:00")
        sys.exit(1)

    task_id = get_next_id()
    task = {
        'id': task_id,
        'title': title,
        'due_time': due_timestamp,
        'created_at': int(datetime.now(TZ).timestamp()),
        'reminded': False
    }

    success = redis_zadd('juzi:tasks:pending', due_timestamp, task)

    if success:
        due_time_display = datetime.fromtimestamp(due_timestamp, tz=TZ).strftime('%Y-%m-%d %H:%M')
        print(f"✅ 任务已添加: {title}（{due_time_display}）")
        print_overview()
    else:
        print("❌ 添加任务失败")
        sys.exit(1)

if __name__ == '__main__':
    main()
