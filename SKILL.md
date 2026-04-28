# Task Reminder Skill

## 简介

飞书任务提醒功能，通过 Redis + 守护进程实现定时飞书消息提醒。支持灵活的后续处理方式，如"1小时后再次提醒"等循环提醒。

## 触发场景

- 用户要求"X点提醒我做某事"
- 用户要求"提醒我Y，后续设置Z小时后再次提醒"
- 用户要求"查看任务列表"
- 用户要求"添加一个任务"
- 用户询问"待处理任务有哪些"

## 任务数据结构

每个任务包含以下字段：

| 字段 | 说明 | 示例 |
|------|------|------|
| id | 任务ID | 1 |
| title | 任务名称 | 常青热力 |
| due_time | 提醒时间戳 | 1777428000 |
| created_at | 创建时间戳 | 1777343820 |
| reminder_sent | 是否已发送提醒 | true/false |
| reminder_sent_time | 发送提醒时间戳 | 1777356054 |
| completion_status | 完成状况 | 待处理/跟进中/已完成 |
| follow_up | 后续处理方式 | 1小时后再次提醒 |
| follow_up_time | 下次跟进时间戳 | 1777366800 |

## Redis Key 结构

| Key | 类型 | 说明 |
|-----|------|------|
| `juzi:tasks:pending` | Sorted Set | 待提醒任务（按时间排序） |
| `juzi:tasks:completed` | Sorted Set | 已完成任务 |
| `juzi:tasks:next_id` | String | 任务ID自增计数器 |
| `juzi:tasks:archive:YYYY-MM-DD` | Sorted Set | 每日归档 |

## 核心文件

| 文件 | 路径 | 用途 |
|------|------|------|
| add_task.py | `scripts/add_task.py` | 添加任务入口（已集成总览显示） |
| task_reminder.py | `scripts/task_reminder.py` | 提醒检查脚本（增强版，支持后续处理） |
| task_manager.py | `scripts/task_manager.py` | 任务管理（查看/归档/完成标记） |
| task_daemon.sh | `scripts/task_daemon.sh` | 守护进程（10秒间隔） |

## 使用方法

### 添加任务

```bash
python3 scripts/add_task.py "任务标题" "2026-04-28 16:30"
```

**时间格式支持：**
- 标准格式：`YYYY-MM-DD HH:MM`（如 `2026-04-28 16:30`）
- 相对时间：`1小时后`、`明天10点`
- 周末提醒：`周五10点`

### 查看任务列表

```bash
python3 scripts/task_manager.py
```

输出格式为 Markdown 表格，包含：
- 序号、时间、任务、是否发送提醒、完成状况、后续处理方式

### 标记任务完成

```bash
python3 scripts/task_manager.py done <任务ID>
```

### 手动触发提醒检查

```bash
python3 scripts/task_reminder.py
```

## 提醒流程

1. **添加任务** → 存入 Redis `juzi:tasks:pending`
2. **守护进程** → 每10秒检查一次到期任务
3. **发送提醒** → 调用 `openclaw message send` 发送飞书消息
4. **处理后续** → 如果有 follow_up，设置下次提醒时间
5. **任务归档** → 无后续处理的任务移至 `juzi:tasks:completed`

## 任务状态流转

```
待处理 → (到提醒时间) → 发送提醒 → 
  ├─ 有后续处理 → 跟进中 → (到后续提醒时间) → 再次发送提醒 → ...
  └─ 无后续处理 → 已完成 → 归档
```

## 注意事项

- 守护进程需持续运行才能发送提醒
- 重启后需确认守护进程状态：`ps aux | grep task_daemon`
- 任务ID是自增的，可通过 `redis-cli GET juzi:tasks:next_id` 查看下一个ID
- 每日归档由 task_manager.py 的 archive 命令执行
- 周五总结：每周五手动执行 `python3 scripts/task_manager.py summary`

## 代码示例

### 添加任务（Python）

```python
import subprocess
result = subprocess.run([
    'python3', '/home/admin1/.openclaw/workspace/scripts/add_task.py',
    '任务标题', '2026-04-28 15:00'
], capture_output=True, text=True)
```

### 添加带后续提醒的任务

```python
result = subprocess.run([
    'python3', '/home/admin1/.openclaw/workspace/scripts/add_task.py',
    '常青热力', '2026-04-28 14:00', '1小时后再次提醒'
], capture_output=True, text=True)
```
