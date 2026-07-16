#!/usr/bin/env python3
"""
AI拖延症破解器 v1.1 — 战果仪表盘（增强版）

新增：连胜追踪、成功率、失败模式分析
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter

DATA_DIR = Path.home() / ".procrastination_breaker"
VICTORY_LOG = DATA_DIR / "victory_log.jsonl"
FAILURE_LOG = DATA_DIR / "failure_log.jsonl"


def load_records():
    if not VICTORY_LOG.exists():
        return [], []
    victories, failures = [], []
    with open(VICTORY_LOG, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                victories.append(json.loads(line))
    if FAILURE_LOG.exists():
        with open(FAILURE_LOG, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    failures.append(json.loads(line))
    return victories, failures


def calc_streak(victories):
    if not victories:
        return 0, 0
    active_dates = sorted(set(r.get("date", "") for r in victories))
    today = datetime.now().strftime("%Y-%m-%d")

    current = 0
    check = datetime.strptime(today, "%Y-%m-%d")
    for _ in range(365):
        ds = check.strftime("%Y-%m-%d")
        if ds in active_dates:
            current += 1
            check -= timedelta(days=1)
        else:
            if current == 0 and ds == today:
                check -= timedelta(days=1)
                continue
            break

    longest = 0
    temp = 0
    prev = None
    for ds in sorted(active_dates):
        curr = datetime.strptime(ds, "%Y-%m-%d")
        if prev is None:
            temp = 1
        elif (curr - prev).days == 1:
            temp += 1
        else:
            longest = max(longest, temp)
            temp = 1
        prev = curr
    longest = max(longest, temp)

    return current, longest


def format_dashboard(victories, failures):
    if not victories:
        return "📊 还没有任何战果记录，去破解一次拖延吧！"

    total = len(victories)
    fail_total = len(failures)
    types = Counter(r.get("root_cause", "未知") for r in victories)
    dates = Counter(r.get("date", "未知") for r in victories)
    current_streak, longest_streak = calc_streak(victories)

    lines = []
    lines.append("=" * 55)
    lines.append("  🏆 AI拖延症破解器 v1.1 — 战果仪表盘")
    lines.append("=" * 55)
    lines.append(f"  📊 总突破: {total}次  |  🔥 当前连胜: {current_streak}天")
    lines.append(f"  📈 成功率: {total/(total+fail_total)*100:.0f}%  |  🏅 最长连胜: {longest_streak}天" if fail_total else f"  🏅 最长连胜: {longest_streak}天")
    lines.append(f"  📅 活跃天数: {len(dates)}天")

    lines.append("")
    lines.append("  📈 拖延类型分布:")
    max_count = max(types.values()) if types else 1
    for ptype, count in types.most_common():
        bar_len = int(count / max_count * 25)
        bar = "█" * bar_len
        lines.append(f"    {ptype:<12} {bar} {count}")

    lines.append("")
    lines.append("  📅 最近7天:")
    for date in sorted(dates.keys(), reverse=True)[:7]:
        count = dates[date]
        fire = "🔥" * min(count, 10)
        lines.append(f"    {date}: {fire} {count}次")

    # 连胜鼓励
    if current_streak >= 14:
        lines.append(f"\n  🔥🔥 连胜{current_streak}天！你已经不是那个拖延的人了。")
    elif current_streak >= 7:
        lines.append(f"\n  🔥 连胜{current_streak}天！一周的坚持。")
    elif current_streak >= 3:
        lines.append(f"\n  💪 连胜{current_streak}天！继续加油。")

    return "\n".join(lines)


def main():
    victories, failures = load_records()
    print(format_dashboard(victories, failures))


if __name__ == "__main__":
    main()
