#!/usr/bin/env python3
"""
任务管理系统 - 增强版
支持：序号、时间、任务、是否发送提醒、完成状况、后续处理方式
"""

import json
import subprocess
import sys
from datetime import datetime, timedelta
import pytz

TZ = pytz.timezone('Asia/Shanghai')

def redis_get(key):
    r = subprocess.run(['redis-cli', 'GET', key], capture_output=True, text=True)
    return r.stdout.strip()

def redis_set(key, val):
    subprocess.run(['redis-cli', 'SET', key, val], capture_output=True)

def redis_zadd(key, score, member):
    subprocess.run(['redis-cli', 'ZADD', key, str(score), json.dumps(member, ensure_ascii=False)],
                  capture_output=True)

def redis_zrange(key, start, end, withscores=False):
    cmd = ['redis-cli', 'ZRANGE', key, str(start), str(end)]
    if withscores:
        cmd.append('WITHSCORES')
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.stdout.strip()

def redis_zrem(key, *members):
    if members:
        subprocess.run(['redis-cli', 'ZREM', key] + list(members), capture_output=True)

def redis_zadd_archive(key, score, member):
    subprocess.run(['redis-cli', 'ZADD', key, str(score), json.dumps(member, ensure_ascii=False)],
                  capture_output=True)

def get_next_id():
    current = redis_get('juzi:tasks:next_id')
    next_id = int(current) + 1 if current else 1
    redis_set('juzi:tasks:next_id', str(next_id))
    return next_id

def format_ts(ts):
    return datetime.fromtimestamp(ts, tz=TZ).strftime('%m-%d %H:%M')

def parse_time(time_str):
    """解析时间字符串为时间戳"""
    dt = datetime.strptime(time_str, '%Y-%m-%d %H:%M')
    local_dt = TZ.localize(dt)
    return int(local_dt.timestamp())

def parse_relative_time(time_str):
    """解析相对时间如 '1小时后', '明天10点' """
    now = datetime.now(TZ)
    if '小时后' in time_str:
        hours = int(time_str.replace('小时后', ''))
        future = now + timedelta(hours=hours)
        return int(TZ.localize(future.replace(hour=0, minute=0, second=0, microsecond=0) + 
                               timedelta(hours=hours)).timestamp())
    elif '明天' in time_str and '点' in time_str:
        hour = int(time_str.replace('明天', '').replace('点', ''))
        tomorrow = now + timedelta(days=1)
        future = tomorrow.replace(hour=hour, minute=0, second=0, microsecond=0)
        return int(TZ.localize(future).timestamp())
    elif '周' in time_str:
        # 周末提醒
        days_map = {'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'日':0}
        for k, v in days_map.items():
            if k in time_str:
                days_ahead = (v - now.weekday()) % 7
                if days_ahead == 0:
                    days_ahead = 7
                future = now + timedelta(days=days_ahead)
                if '点' in time_str:
                    hour = int(time_str.split('点')[0][-2:])
                    future = future.replace(hour=hour, minute=0, second=0, microsecond=0)
                else:
                    future = future.replace(hour=10, minute=0, second=0, microsecond=0)
                return int(TZ.localize(future).timestamp())
    return None

def create_task(title, due_time_str, follow_up='', completion_status='待处理'):
    """创建新任务"""
    task_id = get_next_id()
    now = int(datetime.now(TZ).timestamp())
    
    # 解析时间
    if '小时后' in due_time_str or '明天' in due_time_str or '周' in due_time_str:
        due_timestamp = parse_relative_time(due_time_str)
    else:
        due_timestamp = parse_time(due_time_str)
    
    task = {
        'id': task_id,
        'title': title,
        'due_time': due_timestamp,
        'created_at': now,
        'reminder_sent': False,
        'reminder_sent_time': None,
        'completion_status': completion_status,
        'follow_up': follow_up,
        'follow_up_time': None
    }
    
    # 如果有后续处理，设置follow_up_time
    if follow_up and follow_up != '无':
        if '小时后' in follow_up:
            task['follow_up_time'] = parse_relative_time(follow_up)
        elif '明天' in follow_up or '周' in follow_up:
            task['follow_up_time'] = parse_relative_time(follow_up)
        else:
            task['follow_up_time'] = due_timestamp + 3600  # 默认1小时
    
    redis_zadd('juzi:tasks:pending', due_timestamp, task)
    return task, due_timestamp

def list_tasks():
    """列出所有任务"""
    # Pending
    pending_raw = redis_zrange('juzi:tasks:pending', 0, -1, True)
    pending = []
    if pending_raw:
        lines = pending_raw.split('\n')
        for i in range(0, len(lines), 2):
            if i+1 < len(lines):
                pending.append((json.loads(lines[i]), float(lines[i+1])))
    
    # Completed
    completed_raw = redis_zrange('juzi:tasks:completed', 0, -1, True)
    completed = []
    if completed_raw:
        lines = completed_raw.split('\n')
        for i in range(0, len(lines), 2):
            if i+1 < len(lines):
                completed.append((json.loads(lines[i]), float(lines[i+1])))
    
    return pending, completed

def print_task_list():
    """打印任务列表"""
    pending, completed = list_tasks()
    
    print()
    print("=" * 75)
    print(f"{'📋 任务总览':^75}")
    print("=" * 75)
    
    print(f"\n{'⏳ 进行中任务 (' + str(len(pending)) + '项)':^75}")
    print("-" * 75)
    print(f"{'序号':<4} {'时间':<10} {'任务':<18} {'提醒':<8} {'状态':<8} {'后续处理'}")
    print("-" * 75)
    for i, (t, score) in enumerate(pending, 1):
        reminder = '✓' if t.get('reminder_sent') else '✗'
        status = t.get('completion_status', '待处理')
        follow_up = t.get('follow_up', '无')
        print(f"{i:<4} {format_ts(t['due_time']):<10} {t['title']:<18} {reminder:<8} {status:<8} {follow_up}")
    
    print(f"\n{'✅ 已完成任务 (' + str(len(completed)) + '项)':^75}")
    print("-" * 75)
    print(f"{'序号':<4} {'完成时间':<10} {'任务':<18} {'提醒':<8} {'状态':<8} {'后续处理'}")
    print("-" * 75)
    for i, (t, score) in enumerate(completed, 1):
        reminder = '✓' if t.get('reminder_sent') else '✗'
        status = t.get('completion_status', '已完成')
        follow_up = t.get('follow_up', '无')
        print(f"{i:<4} {format_ts(t['due_time']):<10} {t['title']:<18} {reminder:<8} {status:<8} {follow_up}")
    
    print("=" * 75)

def archive_tasks():
    """每日归档"""
    now = datetime.now(TZ)
    date_str = now.strftime('%Y-%m-%d')
    
    # 获取今天之前的所有待处理任务（已过期的）
    current_time = int(now.timestamp())
    
    # 归档已过期的pending任务
    pending_raw = redis_zrange('juzi:tasks:pending', 0, current_time, True)
    if pending_raw:
        lines = pending_raw.split('\n')
        for i in range(0, len(lines), 2):
            if i+1 < len(lines):
                task = json.loads(lines[i])
                redis_zadd_archive(f'juzi:tasks:archive:{date_str}', float(lines[i+1]), task)
                redis_zrem('juzi:tasks:pending', lines[i])
    
    print(f"✅ 已归档 {date_str} 的过期任务")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print_task_list()
    elif sys.argv[1] == 'archive':
        archive_tasks()
    elif sys.argv[1] == 'add' and len(sys.argv) >= 4:
        title = sys.argv[2]
        due_time = sys.argv[3]
        follow_up = sys.argv[4] if len(sys.argv) > 4 else ''
        task, ts = create_task(title, due_time, follow_up)
        print(f"✅ 任务已添加: {title}（{format_ts(ts)}）")
        if follow_up:
            print(f"   后续处理: {follow_up}")
        print_task_list()
    elif sys.argv[1] == 'done' and len(sys.argv) >= 3:
        # 标记任务完成
        task_id = int(sys.argv[2])
        pending, completed = list_tasks()
        for t, score in pending:
            if t['id'] == task_id:
                t['completion_status'] = '已完成'
                t['follow_up'] = '无'
                redis_zrem('juzi:tasks:pending', json.dumps(t))
                redis_zadd('juzi:tasks:completed', score, t)
                print(f"✅ 任务 '{t['title']}' 已标记完成")
                break
        print_task_list()
