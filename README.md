# 🎯 OpenClaw Task Reminder

飞书任务提醒技能，基于 Redis + 守护进程实现定时飞书消息提醒。

## 📖 简介

这是一个为 [OpenClaw](https://github.com/openclaw/openclaw) 设计的任务提醒技能，可以帮助你在指定时间自动收到飞书消息提醒。

## ✨ 功能特性

- ⏰ **定时提醒** - 支持设置具体时间（如 `2026-04-28 15:00`）
- 🔄 **延时提醒** - 支持"1小时后再次提醒"等循环提醒
- 📋 **任务管理** - 查看进行中和已完成任务
- 📁 **每日归档** - 自动归档过期任务
- 📊 **状态追踪** - 记录提醒状态和完成状况

## 🏗️ 技术架构

```
用户添加任务 → Redis存储 → 守护进程监控 → 到期发送飞书消息 → 任务归档
```

- **存储层**：Redis（Sorted Set 按时间排序）
- **提醒层**：OpenClaw 消息发送
- **监控层**：后台守护进程（10秒间隔）

## 📁 目录结构

```
openclaw-task-reminder/
├── README.md           # 本文档
├── SKILL.md            # OpenClaw技能说明
└── scripts/
    ├── add_task.py      # 添加任务入口
    ├── task_reminder.py # 提醒检查脚本
    ├── task_manager.py  # 任务管理
    └── task_daemon.sh  # 守护进程
```

## 🚀 快速开始

### 1. 安装依赖

```bash
# Redis（已运行）
redis-server

# Python库
pip install redis pytz
```

### 2. 添加任务

```bash
python3 scripts/add_task.py "任务标题" "2026-04-28 15:00"
```

**时间格式：**
- 标准格式：`YYYY-MM-DD HH:MM`（如 `2026-04-28 15:00`）
- 相对时间：`1小时后`、`明天10点`
- 周末提醒：`周五10点`

### 3. 启动守护进程

```bash
nohup bash scripts/task_daemon.sh > /dev/null 2>&1 &
```

### 4. 查看任务列表

```bash
python3 scripts/task_manager.py
```

## 📋 任务数据结构

| 字段 | 说明 |
|------|------|
| id | 任务ID（自增） |
| title | 任务名称 |
| due_time | 提醒时间戳 |
| reminder_sent | 是否已发送提醒 |
| completion_status | 完成状况 |
| follow_up | 后续处理方式 |

## 🔄 任务状态流转

```
待处理 → (到提醒时间) → 发送提醒 → 
  ├─ 有后续处理 → 跟进中 → (到后续时间) → 再次提醒 → ...
  └─ 无后续处理 → 已完成 → 归档
```

## 📌 使用示例

### 基本提醒

```
你：下午4点提醒我开会
桔子：✅ 已添加：开会（16:00）
```

### 延时再次提醒

```
你：常青热力，今天15点提醒，完成后设置1小时后再次提醒
桔子：✅ 任务已添加，1小时后会再次提醒
```

### 查看任务

```
你：查看任务列表
桔子：
| 序号 | 时间 | 任务 | 提醒 | 状态 | 后续处理 |
|------|------|------|------|------|----------|
| 1 | 04-29 10:00 | 常青热力 | ✗ | 待处理 | 无 |
```

## ⚙️ Redis Key 结构

| Key | 类型 | 说明 |
|-----|------|------|
| `juzi:tasks:pending` | Sorted Set | 待提醒任务 |
| `juzi:tasks:completed` | Sorted Set | 已完成任务 |
| `juzi:tasks:next_id` | String | ID自增器 |
| `juzi:tasks:archive:YYYY-MM-DD` | Sorted Set | 每日归档 |

## 🔧 配置说明

### 修改目标用户

编辑 `scripts/task_reminder.py`，修改：

```python
TARGET_USER = "user:ou_xxxxxxxxxxxxxxxx"
```

### 修改检查间隔

编辑 `scripts/task_daemon.sh`，修改 sleep 值：

```bash
sleep 10  # 改为其他秒数
```

## 📄 License

MIT License

## 👤 作者

cgtotu

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

*如果你觉得这个技能有用，请给个 ⭐️*
