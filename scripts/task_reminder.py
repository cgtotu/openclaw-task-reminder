#!/usr/bin/env python3
"""
飞书任务提醒脚本 - 增强版
检查 Redis 中的待提醒任务，到期后发送飞书消息并处理后续
"""

import json
import subprocess
import time
from datetime import datetime
import pytz

TZ = pytz.timezone('Asia/Shanghai')
TARGET_USER = "user:ou_966caf12b8eb5a507e270d8467171da8"

def redis_zrange(key, min_score, max_score):
    result = subprocess.run(['redis-cli', 'ZREVRANGEBYSCORE', key, str(max_score), str(min_score), 'WITHSCORES'], 
                          capture_output=True, text=True)
    lines = result.stdout.strip().split('\n') if result.stdout.strip() else []
    tasks = []
    for i in range(0, len(lines), 2):
        if i+1 < len(lines):
            tasks.append((lines[i], float(lines[i+1])))
    return tasks

def redis_zadd(key, score, member):
    subprocess.run(['redis-cli', 'ZADD', key, str(score), json.dumps(member, ensure_ascii=False)],
                  capture_output=True)

def redis_zrem(key, *members):
    if members:
        subprocess.run(['redis-cli', 'ZREM', key] + list(members), capture_output=True)

def get_current_timestamp():
    return int(time.time())

def format_ts(ts):
    return datetime.fromtimestamp(ts, tz=TZ).strftime('%H:%M')

def format_full_ts(ts):
    return datetime.fromtimestamp(ts, tz=TZ).strftime('%m-%d %H:%M')

def send_feishu_reminder(title, due_time_str, follow_up='', completion_status='待处理'):
    """通过 openclaw 发送飞书消息"""
    follow_up_text = f"\n🔄 后续: {follow_up}" if follow_up else ""
    message = f"""⏰ 任务提醒

📌 {title}
🕐 提醒时间：{due_time_str}
📊 状态：{completion_status}{follow_up_text}

请及时处理！"""

    cmd = [
        'openclaw', 'message', 'send',
        '--channel', 'feishu',
        '--target', TARGET_USER,
        '--message', message
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        proc.communicate(timeout=30)
        return proc.returncode == 0
    except subprocess.TimeoutExpired:
        proc.kill()
        return False

def main():
    current_time = get_current_timestamp()
    print(f"[{datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S')}] 检查任务提醒...")

    # 获取所有已到期但未发送提醒的任务
    tasks = redis_zrange('juzi:tasks:pending', 0, current_time)

    if not tasks:
        print("没有需要提醒的任务")
        return

    reminded_count = 0
    for task_json, score in tasks:
        try:
            task = json.loads(task_json)
            
            title = task.get('title', '未知任务')
            due_time_str = format_full_ts(task.get('due_time', score))
            completion_status = task.get('completion_status', '待处理')
            follow_up = task.get('follow_up', '')
            
            print(f"提醒任务: {title} (截止: {due_time_str})")

            # 发送飞书提醒
            success = send_feishu_reminder(title, due_time_str, follow_up, completion_status)

            if success:
                # 标记已发送提醒
                task['reminder_sent'] = True
                task['reminder_sent_time'] = int(datetime.now(TZ).timestamp())
                
                # 如果有后续处理，调度下次提醒
                if follow_up and follow_up != '无' and task.get('follow_up_time'):
                    # 保留原任务记录到已完成（标记为进行中）
                    task['completion_status'] = '跟进中'
                    redis_zrem('juzi:tasks:pending', task_json)
                    redis_zadd('juzi:tasks:pending', task['follow_up_time'], task)
                    print(f"   🔄 已调度后续提醒: {follow_up} ({format_full_ts(task['follow_up_time'])})")
                else:
                    # 任务完成，移动到已完成
                    redis_zrem('juzi:tasks:pending', task_json)
                    redis_zadd('juzi:tasks:completed', score, task)
                    print(f"✅ 已发送提醒并归档任务: {title}")
                
                reminded_count += 1
            else:
                print(f"⚠️ 发送提醒失败: {title}")

        except json.JSONDecodeError as e:
            print(f"❌ 任务 JSON 解析失败: {task_json}, 错误: {e}")
        except Exception as e:
            print(f"❌ 处理任务时出错: {e}")

    print(f"本次处理 {reminded_count} 个任务提醒")

if __name__ == '__main__':
    main()
