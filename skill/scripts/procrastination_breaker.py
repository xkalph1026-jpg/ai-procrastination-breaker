#!/usr/bin/env python3
"""
AI拖延症破解器 v1.2 — 主入口脚本

v1.2 改进（8项）：
  - 共享信号词层（"拖了N天""卡住了""不想写"等通用拖延信号）
  - 模糊匹配升级（反向子串匹配 + 短输入特殊处理）
  - 正则提取优化（非贪婪 + 标点截断 + 后处理清理）
  - 置信度重算（命中数/核心词数，更直观）
  - 成功型跟进检测（"做完了""接下来做什么"）
  - 仪表盘边界修复（无失败记录时正确显示）
  - 反拖延证据库（--history 命令）
  - 每日回顾提示（当天首次使用显示昨日战绩）

使用方式：
  python procrastination_breaker.py                   # 交互模式
  python procrastination_breaker.py --input "..."     # 单次模式
  python procrastination_breaker.py --dashboard       # 战果仪表盘
  python procrastination_breaker.py --history         # 反拖延证据库
  python procrastination_breaker.py --streak          # 连胜查询
  python procrastination_breaker.py --analyze         # 模式分析
"""

import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter, defaultdict

# ── 配置 ──────────────────────────────────────────────

DATA_DIR = Path.home() / ".procrastination_breaker"
VICTORY_LOG = DATA_DIR / "victory_log.jsonl"
PATTERN_DB = DATA_DIR / "pattern_db.json"
FAILURE_LOG = DATA_DIR / "failure_log.jsonl"
DAILY_STATE = DATA_DIR / "daily_state.json"  # v1.2新增：每日状态
CONFIG_FILE = DATA_DIR / "config.yaml"

# ── v1.2 新增：共享信号词层 ──────────────────────────
# 这些词独立于类型，用于触发「存在拖延行为」的判断，
# 具体类型由后续追问确定。

SIGNAL_WORDS = {
    "temporal": [
        "拖了", "又拖", "一直拖", "还没开始", "还没做", "还没写",
        "好几天了", "好几天没", "过了好几天", "又没做", "又没写",
        "又两天", "又三天", "又一周", "又一个月", "又搁置",
        "一直没", "到现在还没", "迟迟没", "一拖再拖"
    ],
    "stuck": [
        "卡住了", "卡着", "卡壳", "卡在", "停滞", "停住了",
        "做不下去", "写不下去", "进行不下去", "卡顿了",
        "动不了", "推不动", "无法推进"
    ],
    "avoidance": [
        "不想写", "不想做", "不想动", "不想干", "不想开始",
        "不想打开", "不想碰", "不想面对", "懒得动", "懒得做",
        "懒得写", "不想弄", "不想搞"
    ],
    "anxiety": [
        "来不及", "赶不上", "要截止了", "ddl", "deadline",
        "快到了还没", "时间不够", "做不完", "写不完",
        "来不及了", "急死了", "焦虑"
    ]
}


# ── v1.2 改进：关键词 + 模糊匹配 ─────────────────────

PROCRASTINATION_TYPES = {
    "完美主义": {
        "core_keywords": ["不够好", "不满意", "怕做不好", "掉水准", "达不到"],
        "expanded_keywords": [
            "不够好", "不满意", "怕做不好", "怕写不好", "怕不行", "怕翻车",
            "怕搞砸", "掉水准", "达不到", "不够完美", "怕写得差", "怕别人不满意",
            "怕被说", "怕批评", "怕不及格", "不敢交", "不敢发",
            "怕出错", "怕不对", "怕被笑话", "怕丢脸", "怕拿不出手"
        ],
        "min_chars": ["怕", "烂"],  # v1.2: 短词/单字匹配
        "root_cause": "对初稿质量有不切实际的期望",
        "micro_action_template": "写一个「烂版本」的{task_name}开头——故意写烂。{minutes}分钟。",
        "typical_questions": [
            "是怕做得不够好，还是不知道怎么做？",
            "如果质量不重要、没人会看到，你会先做什么？"
        ]
    },
    "任务模糊": {
        "core_keywords": ["不知道从哪开始", "怎么分析", "太笼统", "不清楚", "没头绪"],
        "expanded_keywords": [
            "不知道从哪开始", "怎么分析", "太笼统", "不清楚", "没头绪",
            "不知道怎么做", "不知道写什么", "不知道从何下手", "没方向",
            "一团乱", "没有思路", "不知道步骤", "不知道要干嘛", "不知道先做什么",
            "无从下手", "无从下笔", "不知道分析什么", "不知道怎么分析",
            "怎么开始", "不知道第一步", "没概念", "不了解", "不熟悉",
            "不知道从哪", "不知道该", "连什么都不知道", "连要做什么都不知道",
            "分析什么", "做什么都", "不知道该做什么"
        ],
        "min_chars": ["懵", "晕"],
        "root_cause": "任务定义不清，缺乏具体的切入角度",
        "micro_action_template": "打开{task_material} → 只看前{count}行 → 列出{count}个观察点 → 关掉。只观察不分析。{minutes}分钟。",
        "typical_questions": [
            "如果现在必须做一个动作，最让你头大的是什么？",
            "你手头有什么现成的材料可以先看看？"
        ]
    },
    "任务过大": {
        "core_keywords": ["太多了", "做不完", "根本来不及", "5门", "一堆", "全都"],
        "expanded_keywords": [
            "太多了", "做不完", "根本来不及", "一堆", "全都", "太多了做不完",
            "内容好多", "根本做不完", "太多了来不及", "量太大", "好多内容",
            "好几门", "好几科", "好多章", "好几章", "堆积如山", "任务太多",
            "工作量大", "体量太大", "巨多", "超级多", "特别多"
        ],
        "min_chars": [],
        "root_cause": "任务体量过大导致焦虑性瘫痪",
        "micro_action_template": "只拿{subject} → 拆出最小的{unit} → {specific_action} → 关掉。{minutes}分钟。",
        "typical_questions": [
            "如果只能做其中一小块，哪块最让你焦虑？",
            "最有底和最没底的分别是哪个？"
        ]
    },
    "缺乏动力": {
        "core_keywords": ["没意义", "无聊", "不想做", "看到就烦", "没意思"],
        "expanded_keywords": [
            "没意义", "无聊", "不想做", "看到就烦", "没意思", "没动力",
            "不想动", "没劲", "提不起劲", "懒得", "嫌麻烦", "好烦",
            "没心情", "不想干", "没兴趣", "不想搞", "不想弄",
            "不想做任何事", "只想躺着", "什么都不想做", "没有动力",
            "没热情", "麻木", "无感", "没盼头"
        ],
        "min_chars": ["烦", "累", "困"],
        "root_cause": "看不到任务与个人目标的连接",
        "micro_action_template": "找到任务里最容易的{count}个部分 → 做掉它们 → 计时 → 关掉。{minutes}分钟。",
        "typical_questions": [
            "做完这件事之后，你能得到的最好的结果是什么？",
            "这件事跟你真正想做的事有什么关系？"
        ]
    },
    "决策疲劳": {
        "core_keywords": ["选哪个", "都想试试", "定不下来", "太多了选", "纠结"],
        "expanded_keywords": [
            "选哪个", "都想试试", "定不下来", "纠结", "选择困难",
            "不知道选哪个", "好几个都想", "挑花眼", "拿不定主意",
            "选不好", "太多选择", "眼花缭乱", "不知选什么",
            "犹豫不决", "下不了决心", "做不了决定", "还没定下来", "没定下来"
        ],
        "min_chars": [],
        "root_cause": "FOMO（害怕错过更好选项）导致决策瘫痪",
        "micro_action_template": "最小后悔原则：不选哪个会最后悔？选它。今天就做：{specific_action}。{minutes}分钟。",
        "typical_questions": [
            "这几个里，哪个让你最不后悔放弃？",
            "哪个方向你能找到最多现成资料？"
        ]
    },
    "中断重启": {
        "core_keywords": ["之前做过", "忘了", "捡起来", "中断", "停了", "从头开始"],
        "expanded_keywords": [
            "之前做过", "忘了", "捡起来", "中断", "停了", "从头开始",
            "之前学过", "之前写过", "好久没", "荒废了", "放下了",
            "搁置", "断了", "忘了前面", "忘记前面", "不知道怎么继续",
            "断掉了", "又忘了", "忘记了", "想不起来"
        ],
        "min_chars": [],
        "root_cause": "中断导致的记忆衰减和心理锚点丢失",
        "micro_action_template": "找到之前写过的{task_material} → 读一遍 → 看能否理解 → 给每行写注释。{minutes}分钟。",
        "typical_questions": [
            "还记得当时停在哪一步吗？",
            "之前写的东西还找得到吗？"
        ]
    },
    "多任务并发": {
        "core_keywords": ["都还没做", "全都", "还要", "同时", "一起"],
        "expanded_keywords": [
            "都还没做", "全都还没", "还有", "同时还", "一起做",
            "都等着", "全部都要", "一堆ddl", "好几个ddl", "都截止",
            "各科", "每门都", "都要交", "全部没做", "都赶在一起"
        ],
        "min_chars": [],
        "root_cause": "多任务并发导致注意力分散和优先级混乱",
        "micro_action_template": "把{tasks}列出来 → 标紧迫度(1-3) → 只做最紧迫的最小一步：{specific_action} → {minutes}分钟。",
        "typical_questions": [
            "如果只能先救一个，哪个不做的后果最严重？",
            "这些任务里，有没有哪个其实不太急的可以先放下？"
        ]
    }
}


# ── v1.2 新增：模糊匹配 ───────────────────────────────

def has_signal(user_message: str) -> bool:
    """检测是否包含任何拖延信号词"""
    for category, words in SIGNAL_WORDS.items():
        for w in words:
            if w in user_message:
                return True
    return False


def fuzzy_match_keywords(user_message: str, config: dict) -> set:
    """
    v1.2 升级版匹配：
    1. 标准子串匹配（扩展关键词）
    2. 反向匹配：如果输入很短，检查扩展关键词是否包含输入
    3. min_chars 短词匹配（"烦"→匹配"好烦"、"嫌麻烦"）
    """
    matched = set()
    expanded = config.get("expanded_keywords", [])

    # 1. 标准匹配：关键词 in 用户输入
    for kw in expanded:
        if kw in user_message:
            matched.add(kw)

    # 2. 反向匹配（用户输入短 → 关键词包含它）
    if len(user_message) <= 3:
        for kw in expanded:
            if user_message in kw:
                matched.add(kw)

    # 3. min_chars 匹配（短词/单字）
    for ch in config.get("min_chars", []):
        if ch in user_message:
            # 确认至少命中一个完整扩展词来验证
            for kw in expanded:
                if ch in kw and ch in user_message:
                    matched.add(kw)
                    break

    return matched


# ── v1.2 改进：分类与置信度 ───────────────────────────

def classify_procrastination(user_message: str) -> list[tuple[str, float]]:
    """
    v1.2 改进：
    - 使用 fuzzy_match_keywords 替代简单子串
    - 置信度 = 命中核心词数 / 核心词总数（更直观）
    - 如果无类型匹配但有信号词 → 标记为待追问
    """
    scores = []
    for ptype, config in PROCRASTINATION_TYPES.items():
        matched = fuzzy_match_keywords(user_message, config)
        if matched:
            # v1.2: 基于核心词的置信度
            core_count = len(config.get("core_keywords", config.get("expanded_keywords", [])))
            confidence = round(len(matched) / max(core_count, 1), 2)
            scores.append((ptype, confidence))

    scores.sort(key=lambda x: x[1], reverse=True)
    return scores


# ── v1.2 改进：正则提取优化 ───────────────────────────

def extract_task_info(user_message: str) -> dict:
    """v1.2改进：非贪婪 + 标点截断 + 清理"""
    info = {
        "task_name": "这个任务",
        "task_part": "开头",
        "task_material": "原始材料",
        "subject": "它",
        "unit": "一小块",
        "count": "3",
        "specific_action": "做一个最小动作",
        "tasks": "所有任务",
        "minutes": "5"
    }

    # 提取数字
    num_match = re.search(r'(\d+)门', user_message)
    if num_match:
        info["count"] = num_match.group(1)

    # v1.2: 非贪婪提取 + 标点截断
    task_patterns = [
        (r'写\s*(.{0,6}?\s*(?:论文|报告|作业|文章|文档|代码|总结|计划|方案))', '写'),
        (r'做\s*(.{0,6}?\s*(?:作业|项目|报告|PPT|设计|表格|实验|任务))', '做'),
        (r'复习\s*(.{0,6}?\s*(?:考试|科目|专业课|政治|英语|数学|高数))', '复习'),
        (r'准备\s*(.{0,6}?\s*(?:考试|面试|pre|汇报|答辩|比赛|材料))', '准备'),
        (r'学\s*(.{0,6}?\s*(?:Python|Java|编程|英语|数学|专业课|软件))', '学'),
        (r'填\s*(.{0,6}?\s*(?:表|表格|问卷|申请|资料))', '填'),
        (r'读\s*(.{0,6}?\s*(?:书|论文|文献|材料|课本))', '读'),
    ]

    for pattern, verb in task_patterns:
        m = re.search(pattern, user_message)
        if m:
            raw = m.group(0)
            # v1.2: 标点截断
            cleaned = re.split(r'[，,。！？、；：\s]', raw)[0]
            # 清理冗余字
            cleaned = re.sub(r'了|的|还|都|就|又', '', cleaned).strip()
            if len(cleaned) >= 2:
                info["task_name"] = cleaned
                info["subject"] = cleaned
                info["task_material"] = cleaned + "文档"
                info["specific_action"] = f"{verb}{cleaned}的第一小步"
                break

    # 如果没提取到，尝试更宽泛的动词+名词
    if info["task_name"] == "这个任务":
        vn_match = re.search(r'(写|做|复习|准备|学|填|读|改|画|整理)\s*(.{1,5}?)(?:[，,。！？\s]|$)', user_message)
        if vn_match:
            cleaned = (vn_match.group(1) + vn_match.group(2)).strip()
            cleaned = re.sub(r'了|的|还|都|就|又', '', cleaned).strip()
            if len(cleaned) >= 2:
                info["task_name"] = cleaned
                info["subject"] = cleaned
                info["specific_action"] = f"打开{cleaned}的第一步"

    return info


# ── v1.2 新增：成功汇报检测 ───────────────────────────

def is_success_report(user_message: str) -> bool:
    """检测用户是否在汇报微行动完成"""
    success_patterns = [
        "做完了", "写完了", "完成了", "搞定了", "弄完了",
        "做好了", "写好了", "填完了", "做完了的", "写完了的",
        "还不错", "感觉不错", "感觉还行", "有效果", "有用了",
        "接下来做什么", "然后呢", "下一步", "继续", "还有什么",
        "按你说的", "试了一下", "试了试", "做了5分钟", "写了5分钟"
    ]
    return any(p in user_message for p in success_patterns)


def is_negative_feedback(user_message: str) -> bool:
    """检测否定型反馈"""
    negative_patterns = [
        "没用", "没效果", "不行", "做不到", "做不了",
        "试了但", "还是没", "不管用", "没帮助", "没变化",
        "还是不想", "还是没动", "还是一样的", "没区别"
    ]
    return any(p in user_message for p in negative_patterns)


# ── 数据管理 ──────────────────────────────────────────

def ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def log_victory(task: str, root_cause: str, micro_action: str, duration_seconds: int):
    ensure_data_dir()
    entry = {
        "timestamp": datetime.now().isoformat(),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "task": task,
        "root_cause": root_cause,
        "micro_action": micro_action,
        "completed": True,
        "duration_seconds": duration_seconds
    }
    with open(VICTORY_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def log_failure(task: str, root_cause: str, reason: str):
    ensure_data_dir()
    entry = {
        "timestamp": datetime.now().isoformat(),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "task": task,
        "root_cause": root_cause,
        "reason": reason,
        "completed": False
    }
    with open(FAILURE_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def load_victories(limit: int = 100) -> list:
    ensure_data_dir()
    if not VICTORY_LOG.exists():
        return []
    records = []
    with open(VICTORY_LOG, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records[-limit:]


def load_failures(limit: int = 50) -> list:
    ensure_data_dir()
    if not FAILURE_LOG.exists():
        return []
    records = []
    with open(FAILURE_LOG, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records[-limit:]


def load_patterns() -> dict:
    ensure_data_dir()
    if not PATTERN_DB.exists():
        return {"patterns": []}
    with open(PATTERN_DB, "r", encoding="utf-8") as f:
        return json.load(f)


def save_patterns(patterns: dict):
    ensure_data_dir()
    with open(PATTERN_DB, "w", encoding="utf-8") as f:
        json.dump(patterns, f, ensure_ascii=False, indent=2)


def update_pattern(root_cause: str, task: str, strategy: str):
    patterns = load_patterns()
    for p in patterns.get("patterns", []):
        if p["type"] == root_cause:
            p["occurrence_count"] += 1
            if task not in p["trigger_tasks"]:
                p["trigger_tasks"].append(task)
            if strategy not in p["success_strategies"]:
                p["success_strategies"].append(strategy)
            p["last_seen"] = datetime.now().strftime("%Y-%m-%d")
            save_patterns(patterns)
            return p
    new_pattern = {
        "type": root_cause,
        "trigger_tasks": [task],
        "occurrence_count": 1,
        "success_strategies": [strategy],
        "first_seen": datetime.now().strftime("%Y-%m-%d"),
        "last_seen": datetime.now().strftime("%Y-%m-%d")
    }
    patterns.setdefault("patterns", []).append(new_pattern)
    save_patterns(patterns)
    return new_pattern


def find_matching_pattern(user_message: str) -> dict | None:
    patterns = load_patterns()
    for p in patterns.get("patterns", []):
        type_config = PROCRASTINATION_TYPES.get(p["type"])
        if not type_config:
            continue
        for kw in type_config["expanded_keywords"]:
            if kw in user_message:
                return p
    return None


def generate_micro_action(ptype: str, user_message: str) -> str:
    config = PROCRASTINATION_TYPES.get(ptype)
    if not config:
        return "打开任务材料，只看一眼，然后关掉。2分钟。"
    template = config["micro_action_template"]
    info = extract_task_info(user_message)
    result = template
    for key, value in info.items():
        result = result.replace("{" + key + "}", value)
    # v1.2: 清理可能的残余占位符
    result = re.sub(r'\{[^}]+\}', '', result).strip()
    return result


# ── 连胜追踪 ──────────────────────────────────────────

def calc_streak() -> dict:
    records = load_victories(limit=200)
    if not records:
        return {"current_streak": 0, "longest_streak": 0, "total_days": 0}
    active_dates = set(r.get("date", "") for r in records)
    if not active_dates:
        return {"current_streak": 0, "longest_streak": 0, "total_days": 0}

    sorted_dates = sorted(active_dates)
    today = datetime.now().strftime("%Y-%m-%d")

    current_streak = 0
    check_date = datetime.strptime(today, "%Y-%m-%d")
    for _ in range(365):
        date_str = check_date.strftime("%Y-%m-%d")
        if date_str in active_dates:
            current_streak += 1
            check_date -= timedelta(days=1)
        else:
            if current_streak == 0 and date_str == today:
                check_date -= timedelta(days=1)
                continue
            break

    longest_streak = 0
    temp_streak = 0
    prev_date = None
    for date_str in sorted_dates:
        curr = datetime.strptime(date_str, "%Y-%m-%d")
        if prev_date is None:
            temp_streak = 1
        elif (curr - prev_date).days == 1:
            temp_streak += 1
        else:
            longest_streak = max(longest_streak, temp_streak)
            temp_streak = 1
        prev_date = curr
    longest_streak = max(longest_streak, temp_streak)

    return {
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "total_days": len(active_dates)
    }


def get_streak_message() -> str:
    streak = calc_streak()
    if streak["current_streak"] >= 30:
        return f"🔥🔥🔥 连胜 {streak['current_streak']} 天！习惯已成自然。"
    elif streak["current_streak"] >= 14:
        return f"🔥🔥 连胜 {streak['current_streak']} 天！两周了，你已经不是那个拖延的人了。"
    elif streak["current_streak"] >= 7:
        return f"🔥 连胜 {streak['current_streak']} 天！一周的坚持。"
    elif streak["current_streak"] >= 3:
        return f"💪 连胜 {streak['current_streak']} 天！"
    elif streak["current_streak"] >= 1:
        return "✅ 今天也战胜了拖延。"
    return ""


# ── v1.2 新增：每日回顾 ───────────────────────────────

def get_daily_state() -> dict:
    """获取每日状态"""
    ensure_data_dir()
    if not DAILY_STATE.exists():
        return {"last_active_date": None, "today_session_count": 0}
    with open(DAILY_STATE, "r", encoding="utf-8") as f:
        return json.load(f)


def update_daily_state():
    """更新每日状态"""
    ensure_data_dir()
    today = datetime.now().strftime("%Y-%m-%d")
    state = get_daily_state()
    if state.get("last_active_date") == today:
        state["today_session_count"] = state.get("today_session_count", 0) + 1
    else:
        state = {"last_active_date": today, "today_session_count": 1}
    with open(DAILY_STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)


def get_yesterday_summary() -> str:
    """获取昨日战绩摘要"""
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    records = load_victories(limit=200)
    yesterdays = [r for r in records if r.get("date") == yesterday]
    if not yesterdays:
        return ""
    types = Counter(r.get("root_cause", "") for r in yesterdays)
    return f"📅 昨日战绩：破解了 {len(yesterdays)} 次拖延（{', '.join(f'{t}{c}次' for t, c in types.most_common(3))}）"


def is_new_user() -> bool:
    victories = load_victories(limit=1)
    failures = load_failures(limit=1)
    return len(victories) == 0 and len(failures) == 0


def show_welcome():
    if is_new_user():
        print("""
╔══════════════════════════════════════════╗
║    🧠 欢迎！我是你的拖延破解教练。        ║
║                                          ║
║    你不需要列计划、不需要下决心、          ║
║    不需要打败懒惰——                       ║
║    你只需要告诉我你在拖延什么。            ║
║                                          ║
║    我会帮你找到卡住的真正原因，             ║
║    然后给你一个「小到不可能失败」的微行动。 ║
║                                          ║
║    现在，告诉我你在拖延什么？              ║
╚══════════════════════════════════════════╝
""")
    else:
        streak_msg = get_streak_message()
        yesterday = get_yesterday_summary()
        print(f"""
╔══════════════════════════════════════════╗
║     🧠 AI拖延症破解器 v1.2              ║
║     {streak_msg:<36} ║
╠══════════════════════════════════════════╣
║  输入你正在拖延的事，我来帮你破解。        ║
║  输入 dashboard 查看战果                  ║
║  输入 history 查看反拖延证据库             ║
║  输入 quit 退出                           ║
╚══════════════════════════════════════════╝
""")
        if yesterday:
            print(f"  {yesterday}")


# ── 仪表盘（v1.2 边界修复）───────────────────────────

def show_dashboard():
    records = load_victories(limit=100)
    failures = load_failures(limit=50)
    if not records:
        print("📊 还没有任何战果记录。快去破解一次拖延吧！")
        return

    total = len(records)
    fail_total = len(failures)
    by_type = {}
    by_date = {}
    for r in records:
        rc = r.get("root_cause", "未知")
        by_type[rc] = by_type.get(rc, 0) + 1
        date = r.get("date", "未知")
        by_date[date] = by_date.get(date, 0) + 1

    streak = calc_streak()

    print(f"\n{'='*55}")
    print(f"  🏆 AI拖延症破解器 v1.2 — 战果仪表盘")
    print(f"{'='*55}")
    print(f"  📊 总突破: {total}次  |  🔥 当前连胜: {streak['current_streak']}天")

    # v1.2 修复：仅在有失败记录时显示成功率
    if fail_total > 0:
        success_rate = total / (total + fail_total) * 100
        print(f"  📈 成功率: {success_rate:.0f}% ({total}/{total+fail_total})  |  🏅 最长连胜: {streak['longest_streak']}天")
    else:
        print(f"  📈 成功率: 100% (目前无失败记录)  |  🏅 最长连胜: {streak['longest_streak']}天")

    print(f"  📅 活跃天数: {len(by_date)}天")

    print(f"\n  📈 拖延类型分布:")
    max_count = max(by_type.values()) if by_type else 1
    for ptype, count in sorted(by_type.items(), key=lambda x: x[1], reverse=True):
        bar_len = int(count / max_count * 25)
        bar = "█" * bar_len
        print(f"    {ptype:<12} {bar} {count}")

    print(f"\n  📅 最近7天:")
    for date in sorted(by_date.keys(), reverse=True)[:7]:
        count = by_date[date]
        fire = "🔥" * min(count, 10)
        print(f"    {date}: {fire} {count}次")

    print(f"\n  {get_streak_message()}")


# ── v1.2 新增：反拖延证据库 ───────────────────────────

def show_history():
    """展示反拖延证据库"""
    records = load_victories(limit=50)
    if not records:
        print("📊 还没有战果记录。")
        return

    print(f"\n{'='*55}")
    print(f"  📚 反拖延证据库 — 最近{len(records)}条突破记录")
    print(f"{'='*55}")

    for i, r in enumerate(reversed(records[-20:]), 1):
        task = r.get("task", "未知任务")
        rc = r.get("root_cause", "未知")
        date = r.get("date", "")
        print(f"  {i:2}. [{date}] {task}")
        print(f"      类型: {rc}  |  ✅ 已破解")

    streak = calc_streak()
    print(f"\n  🔥 当前连胜: {streak['current_streak']}天 | 📅 活跃: {streak['total_days']}天")
    print(f"\n  💡 每次微行动都是你战胜拖延的证据。")


# ── v1.2 新增：降级回路 ───────────────────────────────

def handle_resistance(previous_root_cause: str, user_message: str) -> dict:
    scores = classify_procrastination(user_message)
    alternative_type = None
    for ptype, conf in scores:
        if ptype != previous_root_cause and conf > 0:
            alternative_type = ptype
            break
    return {
        "empathy": "谢谢你告诉我——这说明我给的行动可能还不够小。",
        "re_diagnose": True,
        "alternative_type": alternative_type,
        "halve_action": True
    }


def handle_success_report(user_message: str) -> dict:
    """v1.2新增：处理成功汇报"""
    return {
        "celebrate": "✅ 干得漂亮！每一次微行动都是对拖延的胜利反击。",
        "record": True,
        "follow_up": "趁现在动力还在，要不要趁热打铁，再来一个微行动？或者先休息一下也行。"
    }


# ── 主入口（v1.2）─────────────────────────────────────

def interactive_mode():
    update_daily_state()
    show_welcome()
    last_root_cause = None
    last_micro_action = None  # v1.2: 追踪上一次给出的微行动

    while True:
        try:
            user_input = input("\n👤 你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 再见！记住：每个微行动都是胜利。")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "退出", "q"):
            show_dashboard()
            print("\n👋 再见！")
            break

        if user_input.lower() in ("dashboard", "仪表盘", "统计"):
            show_dashboard()
            continue

        if user_input.lower() in ("history", "历史", "证据库", "战果"):
            show_history()
            continue

        if user_input.lower() in ("streak", "连胜"):
            s = calc_streak()
            print(f"\n🔥 当前连胜: {s['current_streak']}天 | 最长连胜: {s['longest_streak']}天 | 活跃天数: {s['total_days']}")
            continue

        # ── v1.2: 成功汇报检测（优先级最高）──
        if is_success_report(user_input) and last_micro_action:
            resp = handle_success_report(user_input)
            print(f"\n🤖 AI拖延症破解器:")
            print(f"   {resp['celebrate']}")
            if last_root_cause:
                log_victory(user_input[:50], last_root_cause, last_micro_action or "", 300)
                update_pattern(last_root_cause, user_input[:50], last_micro_action or "")
            streak_msg = get_streak_message()
            if streak_msg:
                print(f"   {streak_msg}")
            print(f"   💬 {resp['follow_up']}")
            continue

        # ── v1.1: 否定型反馈检测 ──
        if is_negative_feedback(user_input) and last_root_cause:
            resistance = handle_resistance(last_root_cause, user_input)
            print(f"\n🤖 AI拖延症破解器:")
            print(f"   💬 {resistance['empathy']}")
            print(f"   🔄 我们重新来看看卡在哪...")
            scores = classify_procrastination(user_input)
            if resistance["alternative_type"]:
                config = PROCRASTINATION_TYPES[resistance["alternative_type"]]
                print(f"   🔍 可能不是{last_root_cause}，更像是「{resistance['alternative_type']}」型")
                print(f"   💡 {config['root_cause']}")
                print(f"   ❓ {config['typical_questions'][0]}")
                last_root_cause = resistance["alternative_type"]
            else:
                print(f"   📐 我上次给的行动可能还是太大了。这次减半——2分钟的那种。")
            log_failure(user_input, last_root_cause or "未知", "用户反馈方法无效")
            continue

        # ── 正常分类流程 ──
        scores = classify_procrastination(user_input)
        has_sig = has_signal(user_input)
        pattern = find_matching_pattern(user_input)

        print(f"\n🤖 AI拖延症破解器:")

        if pattern:
            print(f"   🧠 我记得你之前也有类似的拖延:")
            print(f"      类型: {pattern['type']} (第{pattern['occurrence_count']}次)")
            print(f"      上次成功策略: {', '.join(pattern['success_strategies'][:2])}")
            print()

        if scores:
            top_type, confidence = scores[0]
            config = PROCRASTINATION_TYPES[top_type]
            last_root_cause = top_type

            print(f"   🔍 判断: {top_type}型拖延 (置信度: {confidence:.0%})")
            print(f"   💡 根因: {config['root_cause']}")

            micro = generate_micro_action(top_type, user_input)
            last_micro_action = micro
            print(f"\n   📌 微行动: {micro}")
            print(f"\n   ❓ {config['typical_questions'][0]}")

            streak_msg = get_streak_message()
            if streak_msg:
                print(f"\n   {streak_msg}")

            if len(scores) > 1:
                second_type, second_conf = scores[1]
                print(f"   📋 备选: {second_type} (置信度: {second_conf:.0%})")

        elif has_sig:
            # v1.2: 有拖延信号但类型不确定 → 触发追问
            print(f"   🎯 我感觉你在拖延，但还不确定具体原因。")
            print(f"   💬 能多说一点吗？是卡在哪一步？还是任务太大了？")
        else:
            # 完全无匹配
            if any(c in user_message for c in ("天气", "吃饭", "睡觉", "你好", "谢谢")):
                print(f"   😊 这个话题和拖延破解关系不大。有什么在拖着你的事想聊吗？")
            elif len(user_message) <= 2:
                # v1.2: 短输入特殊处理
                print(f"   🤔 听起来状态不太好。是不是有什么事在拖着你？")
            else:
                print(f"   🤔 我不太确定你在拖延什么。能描述一下吗？")
                print(f"   💡 比如：任务是什么？拖了多久？卡在哪一步？")


# ── CLI 入口 ──────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--dashboard":
            show_dashboard()
        elif sys.argv[1] == "--history":
            show_history()
        elif sys.argv[1] == "--streak":
            s = calc_streak()
            print(json.dumps(s, ensure_ascii=False, indent=2))
        elif sys.argv[1] == "--input" and len(sys.argv) > 2:
            user_input = sys.argv[2]
            scores = classify_procrastination(user_input)
            pattern = find_matching_pattern(user_input)
            task_info = extract_task_info(user_input)
            micro_action = generate_micro_action(scores[0][0], user_input) if scores else "无法生成"
            print(json.dumps({
                "input": user_input,
                "has_signal": has_signal(user_input),
                "classification": [{"type": t, "confidence": round(c, 2)} for t, c in scores],
                "matched_pattern": pattern,
                "extracted_task_info": task_info,
                "generated_micro_action": micro_action,
                "is_success_report": is_success_report(user_input),
                "is_negative_feedback": is_negative_feedback(user_input),
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False, indent=2))
        elif sys.argv[1] == "--analyze":
            records = load_victories()
            patterns = load_patterns()
            streak = calc_streak()
            print(json.dumps({
                "total_victories": len(records),
                "streak": streak,
                "patterns": patterns.get("patterns", []),
                "recent": records[-5:] if records else []
            }, ensure_ascii=False, indent=2))
        else:
            show_welcome()
    else:
        interactive_mode()
